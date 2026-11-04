#!/usr/bin/env python3
"""Verificar configuración RDS sin leer contraseñas ni conectarse a SQL."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True)
    parser.add_argument("--expected-account", required=True)
    parser.add_argument("--stack", default="pataporte-dev-data")
    parser.add_argument("--network-stack", default="pataporte-dev-network")
    parser.add_argument("--profile")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if not shutil.which("aws"):
        parser.error("Falta AWS CLI")
    common = ["aws", "--region", args.region, "--output", "json",
              "--cli-connect-timeout", "5", "--cli-read-timeout", "20"]
    if args.profile:
        common += ["--profile", args.profile]
    env = dict(os.environ, AWS_PAGER="", AWS_CLI_AUTO_PROMPT="off",
               AWS_EC2_METADATA_DISABLED="true", AWS_MAX_ATTEMPTS="1")

    def aws(*command):
        result = subprocess.run(common + list(command), env=env, capture_output=True,
                                text=True, timeout=40, check=False)
        if result.returncode:
            raise RuntimeError(result.stderr.strip())
        return json.loads(result.stdout)

    account = aws("sts", "get-caller-identity")["Account"]
    if account != args.expected_account:
        raise RuntimeError("La cuenta no coincide con --expected-account")
    stack = aws("cloudformation", "describe-stacks", "--stack-name", args.stack)["Stacks"][0]
    if stack["StackStatus"] not in {"CREATE_COMPLETE", "UPDATE_COMPLETE"}:
        raise RuntimeError(f"Stack todavía no verificable: {stack['StackStatus']}")
    network = aws("cloudformation", "describe-stacks", "--stack-name", args.network_stack)["Stacks"][0]
    network_outputs = {x["OutputKey"]: x["OutputValue"] for x in network["Outputs"]}
    outputs = {x["OutputKey"]: x["OutputValue"] for x in stack["Outputs"]}
    params = {x["ParameterKey"]: x["ParameterValue"] for x in stack["Parameters"]}
    db = aws("rds", "describe-db-instances", "--db-instance-identifier", outputs["DatabaseIdentifier"])["DBInstances"][0]
    resources = aws("cloudformation", "list-stack-resources", "--stack-name", args.stack)["StackResourceSummaries"]
    parameter_group = db["DBParameterGroups"][0]
    parameters = aws("rds", "describe-db-parameters", "--db-parameter-group-name", parameter_group["DBParameterGroupName"])["Parameters"]
    log_group_name = f"/aws/rds/instance/{db['DBInstanceIdentifier']}/postgresql"
    logs = aws("logs", "describe-log-groups", "--log-group-name-prefix", log_group_name)["logGroups"]
    checks = []

    def check(name, valid):
        checks.append({"check": name, "passed": bool(valid)})
        print(f"{'OK' if valid else 'FALLO'}: {name}")

    check("Cuatro recursos completos en CloudFormation", len(resources) == 4 and all(x["ResourceStatus"] in {"CREATE_COMPLETE", "UPDATE_COMPLETE"} for x in resources))
    check("PostgreSQL 15 disponible", db["DBInstanceStatus"] == "available" and db["Engine"] == "postgres" and db["EngineVersion"].startswith("15."))
    check("Clase de instancia prevista", db["DBInstanceClass"] == params["InstanceClass"])
    check("Almacenamiento gp2 acotado al laboratorio", db["StorageType"] == "gp2" and db["AllocatedStorage"] == int(params["AllocatedStorage"]) and 20 <= db["AllocatedStorage"] <= 100)
    check("Almacenamiento cifrado", db["StorageEncrypted"] and bool(db.get("KmsKeyId")))
    check("Base privada en la VPC de PATAPORTE", not db["PubliclyAccessible"] and db["DBSubnetGroup"]["VpcId"] == network_outputs["VpcId"])
    subnet_ids = {x["SubnetIdentifier"] for x in db["DBSubnetGroup"]["Subnets"]}
    subnet_zones = {x["SubnetAvailabilityZone"]["Name"] for x in db["DBSubnetGroup"]["Subnets"]}
    check("DB Subnet Group en las dos subredes privadas de datos", subnet_ids == {network_outputs["DataSubnetAId"], network_outputs["DataSubnetBId"]} and len(subnet_zones) == 2)
    check("RDS utiliza solo el SG de base previsto", {x["VpcSecurityGroupId"] for x in db["VpcSecurityGroups"]} == {network_outputs["DatabaseSecurityGroupId"]} and all(x["Status"] == "active" for x in db["VpcSecurityGroups"]))
    check("Puerto PostgreSQL 5432", db["Endpoint"]["Port"] == 5432 and str(db["Endpoint"]["Port"]) == outputs["DatabasePort"])
    check("TLS obligatorio en parámetros aplicados", parameter_group["ParameterApplyStatus"] == "in-sync" and any(x["ParameterName"] == "rds.force_ssl" and x.get("ParameterValue") == "1" for x in parameters))
    check("Contraseña maestra administrada y activa", db.get("MasterUserSecret", {}).get("SecretStatus") == "active" and db["MasterUserSecret"]["SecretArn"] == outputs["MasterSecretArn"])
    check("Backups automáticos configurados", db["BackupRetentionPeriod"] == int(params["BackupRetentionDays"]) and db["BackupRetentionPeriod"] >= 1 and db["CopyTagsToSnapshot"])
    check("Protección de borrado habilitada", db["DeletionProtection"])
    check("Logs PostgreSQL con retención de siete días", "postgresql" in db.get("EnabledCloudwatchLogsExports", []) and any(x["logGroupName"] == log_group_name and x.get("retentionInDays") == 7 for x in logs))
    check("Multi-AZ coincide con la decisión del laboratorio", db["MultiAZ"] == (params["EnableMultiAZ"] == "true"))
    check("Supervisión mejorada desactivada según Academy", db.get("MonitoringInterval", 0) == 0 and not db.get("PerformanceInsightsEnabled", False))
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(), "region": args.region,
        "account_suffix": account[-4:], "stack": args.stack, "status": stack["StackStatus"],
        "identifier": db["DBInstanceIdentifier"], "database_name": db["DBName"],
        "endpoint": db["Endpoint"]["Address"], "port": db["Endpoint"]["Port"],
        "engine_version": db["EngineVersion"], "instance_class": db["DBInstanceClass"],
        "storage_type": db["StorageType"], "storage_gb": db["AllocatedStorage"],
        "multi_az": db["MultiAZ"], "backup_retention_days": db["BackupRetentionPeriod"],
        "latest_restorable_time": str(db.get("LatestRestorableTime", "pending")),
        "ca_identifier": db.get("CACertificateIdentifier"),
        "schema_migrations": "not_checked_by_this_configuration_verifier", "checks": checks,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Evidencia: {args.report}")
    failures = sum(not x["passed"] for x in checks)
    print(f"Resultado: {len(checks) - failures}/{len(checks)} comprobaciones correctas")
    print("Esta verificación no ejecuta migraciones SQL ni prueba una restauración.")
    return int(failures > 0)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, KeyError, ValueError, OSError, subprocess.TimeoutExpired) as error:
        print(f"No se pudo verificar RDS: {error}", file=sys.stderr)
        sys.exit(1)
