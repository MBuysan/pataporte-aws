#!/usr/bin/env python3
"""Compara tablas de una copia RDS con la original desde tareas ECS privadas, en modo SQL de solo lectura."""
import argparse
from datetime import datetime, timezone
import json
import re
import time

import boto3
from deploy_ecs import ACCOUNT, REGION, outputs, save
from restore_rds import validate_restore

SQL_PROBE = '''
import json
from sqlalchemy import text
from config.database import engine
try:
 with engine.connect() as c:
  c.execute(text("SET TRANSACTION READ ONLY"))
  revision=c.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
  ssl=c.execute(text("SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()")).scalar_one()
  names=c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename NOT IN ('alembic_version','outbox_events') ORDER BY tablename")).scalars().all()
  tables={}
  for name in names:
   quoted=engine.dialect.identifier_preparer.quote(name)
   count,fingerprint=c.execute(text("SELECT count(*), md5(coalesce(string_agg(row_to_json(t)::text, '' ORDER BY row_to_json(t)::text), '')) FROM "+quoted+" t")).one()
   tables[name]={"rows":count,"fingerprint":fingerprint}
  print("RESTORE_SQL="+json.dumps({"revision":revision,"ssl":ssl,"tables":tables}),flush=True)
except Exception as exc:
 print("RESTORE_SQL_FAILED="+type(exc).__name__,flush=True)
 raise SystemExit(1)
'''


def inspect_database(session, compute, network, host):
    ecs = session.client('ecs')
    result = ecs.run_task(cluster=compute['ClusterName'], taskDefinition=compute['ApiTaskDefinitionArn'],
        capacityProviderStrategy=[{'capacityProvider': compute['CapacityProviderName'], 'weight': 1}], count=1,
        startedBy='pataporte-restore-sql', networkConfiguration={'awsvpcConfiguration': {
            'subnets': [network['AppSubnetAId'], network['AppSubnetBId']],
            'securityGroups': [network['WorkerSecurityGroupId']], 'assignPublicIp': 'DISABLED'}},
        overrides={'memory': '192', 'containerOverrides': [{'name': 'api', 'memory': 192,
            'command': ['python', '-c', SQL_PROBE], 'environment': [{'name': 'DB_HOST', 'value': host}]}]})
    if result.get('failures') or len(result.get('tasks', [])) != 1:
        raise RuntimeError('No se pudo iniciar la tarea privada de lectura SQL')
    arn = result['tasks'][0]['taskArn']
    print('READ_ONLY_SQL_TASK', arn.rsplit('/', 1)[-1], flush=True)
    ecs.get_waiter('tasks_stopped').wait(cluster=compute['ClusterName'], tasks=[arn], WaiterConfig={'Delay': 10, 'MaxAttempts': 90})
    task = ecs.describe_tasks(cluster=compute['ClusterName'], tasks=[arn])['tasks'][0]
    if task['containers'][0].get('exitCode') != 0:
        raise RuntimeError('La lectura SQL privada falló; revisar sin publicar credenciales')
    log = 'ecs/api/' + arn.rsplit('/', 1)[-1]
    for _ in range(10):
        lines = session.client('logs').get_log_events(logGroupName='/pataporte/dev/api', logStreamName=log, startFromHead=True)['events']
        for line in lines:
            if line['message'].startswith('RESTORE_SQL='):
                return json.loads(line['message'].split('=', 1)[1])
        time.sleep(2)
    raise RuntimeError('Falta evidencia de la tarea SQL')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,24}', args.run):
        parser.error('Identificador de ensayo inválido')
    session = boto3.Session(region_name=REGION)
    if session.client('sts').get_caller_identity()['Account'] != ACCOUNT:
        raise RuntimeError('Cuenta distinta de Academy')
    cfn = session.client('cloudformation')
    data = outputs(cfn, 'pataporte-dev-data')
    compute = outputs(cfn, 'pataporte-dev-compute')
    network = outputs(cfn, 'pataporte-dev-network')
    rds = session.client('rds')
    source = rds.describe_db_instances(DBInstanceIdentifier=data['DatabaseIdentifier'])['DBInstances'][0]
    copy = rds.describe_db_instances(DBInstanceIdentifier='pataporte-restore-' + args.run)['DBInstances'][0]
    if not all(validate_restore(source, copy).values()) or copy['DBInstanceStatus'] != 'available':
        raise RuntimeError('La copia debe estar disponible y conservar el aislamiento antes de consultar SQL')
    original = inspect_database(session, compute, network, source['Endpoint']['Address'])
    restored = inspect_database(session, compute, network, copy['Endpoint']['Address'])
    passed = original['ssl'] and restored['ssl'] and original['tables'] == restored['tables'] and bool(restored['tables'])
    evidence = {'checked_at': datetime.now(timezone.utc).isoformat(), 'original': source['DBInstanceIdentifier'],
        'copy': copy['DBInstanceIdentifier'], 'private_read_only_tasks': True, 'sql_restore_verified': passed,
        'original_result': original, 'restored_result': restored, 'excluded_tables': ['alembic_version', 'outbox_events'],
        'limitation': 'Compara las tablas de negocio compartidas; el snapshot puede preceder a la migración 0003. No demuestra restauración del outbox ni un RTO integral.'}
    save('restore-sql-' + args.run, evidence)
    print(json.dumps(evidence, indent=2))
    if not passed:
        raise RuntimeError('La comparación de tablas restauradas no coincide')


if __name__ == '__main__':
    main()
