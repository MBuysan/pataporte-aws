#!/usr/bin/env python3
"""Prueba real SQS → Lambda → DynamoDB/S3 con evento ficticio y sin destinatarios."""
from datetime import datetime, timezone
import json
import time
from uuid import uuid4

import boto3
from deploy_ecs import ACCOUNT, REGION, outputs, save


def main():
    session = boto3.Session(region_name=REGION)
    if session.client('sts').get_caller_identity()['Account'] != ACCOUNT:
        raise RuntimeError('Cuenta distinta de Academy')
    info = outputs(session.client('cloudformation'), 'pataporte-dev-async')
    lam = session.client('lambda')
    config = lam.get_function_configuration(FunctionName=info['WorkerName'])
    if config['Environment']['Variables']['MAIL_DELIVERY_ENABLED'] != 'false':
        raise RuntimeError('Esta prueba requiere envío de correo desactivado')
    mappings = lam.list_event_source_mappings(FunctionName=info['WorkerName'], EventSourceArn=info['QueueArn'])['EventSourceMappings']
    if len(mappings) != 1 or mappings[0]['State'] != 'Enabled':
        raise RuntimeError('El consumidor de la cola debe estar habilitado para la prueba')
    event_id = str(uuid4())
    envelope = {'schema_version': 1, 'event_id': event_id, 'payload': {'tipo': 'probe'}}
    session.client('sqs').send_message(QueueUrl=info['QueueUrl'], MessageBody=json.dumps(envelope))
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        item = session.client('dynamodb').get_item(TableName=info['IdempotencyTableName'], Key={'event_id': {'S': event_id}}, ConsistentRead=True).get('Item', {})
        if item.get('status', {}).get('S') == 'DONE':
            break
        time.sleep(3)
    else:
        raise RuntimeError('El evento no llegó a DONE en tres minutos')
    s3 = session.client('s3')
    key = f'probes/{event_id}.json'
    first = s3.head_object(Bucket=info['AssetsBucketName'], Key=key)
    duplicate = lam.invoke(FunctionName=info['WorkerName'], InvocationType='RequestResponse', Payload=json.dumps({'Records': [{'messageId': str(uuid4()), 'body': json.dumps(envelope)}]}).encode())
    response = json.loads(duplicate['Payload'].read())
    if duplicate.get('FunctionError') or response != {'batchItemFailures': []}:
        raise RuntimeError('Falló la repetición controlada del evento')
    second = s3.head_object(Bucket=info['AssetsBucketName'], Key=key)
    versions = s3.list_object_versions(Bucket=info['AssetsBucketName'], Prefix=key).get('Versions', [])
    if first.get('VersionId') != second.get('VersionId') or len([v for v in versions if v['Key'] == key]) != 1:
        raise RuntimeError('La repetición volvió a escribir el objeto')
    result = {'checked_at': datetime.now(timezone.utc).isoformat(), 'account': ACCOUNT, 'region': REGION,
              'sqs_lambda_dynamodb_s3': 'passed', 'duplicate_direct_lambda_invocation': 'passed',
              'event_id': event_id, 'artifact_version': first.get('VersionId'), 'artifact_encryption': first.get('ServerSideEncryption'),
              'smtp_delivery_verified': False, 'exactly_once_smtp_proven': False}
    save('async-verification', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
