#!/usr/bin/env python3
"""Crear snapshot y copia RDS privada para un ensayo. Nunca borra ni modifica la instancia original."""
import argparse
from datetime import datetime, timezone
import json
import re

import boto3
from botocore.exceptions import ClientError
from deploy_ecs import ACCOUNT, REGION, outputs, save


def validate_restore(source, target):
    if target["DBInstanceIdentifier"] == source["DBInstanceIdentifier"]:
        raise RuntimeError("La copia no puede ser la instancia original")
    expected_groups = {s["VpcSecurityGroupId"] for s in source["VpcSecurityGroups"]}
    actual_groups = {s["VpcSecurityGroupId"] for s in target["VpcSecurityGroups"]}
    return {"different_instance": True, "private": not target["PubliclyAccessible"],
            "encrypted": target["StorageEncrypted"], "single_az_test_copy": not target["MultiAZ"],
            "same_engine": target["Engine"] == source["Engine"],
            "same_vpc": target["DBSubnetGroup"]["VpcId"] == source["DBSubnetGroup"]["VpcId"],
            "same_security_groups": actual_groups == expected_groups,
            "same_parameter_group": {g["DBParameterGroupName"] for g in target["DBParameterGroups"]} == {g["DBParameterGroupName"] for g in source["DBParameterGroups"]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "create", "verify"])
    parser.add_argument("--run", required=True, help="Identificador único del ensayo, p.ej. 20261103-a")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,24}", args.run):
        parser.error("run debe usar hasta 25 letras minúsculas/dígitos/guiones")
    session = boto3.Session(region_name=REGION)
    if session.client("sts").get_caller_identity()["Account"] != ACCOUNT:
        raise RuntimeError("Cuenta distinta de Academy")
    db_id = outputs(session.client("cloudformation"), "pataporte-dev-data")["DatabaseIdentifier"]
    rds = session.client("rds")
    source = rds.describe_db_instances(DBInstanceIdentifier=db_id)["DBInstances"][0]
    snapshot_id = "pataporte-restore-" + args.run
    target_id = "pataporte-restore-" + args.run
    plan = {"original": db_id, "snapshot": snapshot_id, "copy": target_id,
            "class": "db.t3.micro", "publicly_accessible": False, "multi_az": False,
            "deletion_protection": True, "original_modified": False,
            "generates_hourly_and_snapshot_storage_costs": True,
            "cleanup": "La copia y snapshot quedan retenidos; revisar y eliminar solo esos recursos después de guardar evidencia."}
    if args.action == "plan":
        save("restore-plan-" + args.run, plan)
        print(json.dumps(plan, indent=2))
        return
    if args.action == "create":
        tags = [{"Key": "project", "Value": "pataporte"}, {"Key": "purpose", "Value": "restore-test"}, {"Key": "restore-run", "Value": args.run}]
        try:
            snapshot = rds.describe_db_snapshots(DBSnapshotIdentifier=snapshot_id)["DBSnapshots"][0]
        except ClientError as error:
            if error.response["Error"]["Code"] != "DBSnapshotNotFound":
                raise
            snapshot = rds.create_db_snapshot(DBInstanceIdentifier=db_id, DBSnapshotIdentifier=snapshot_id, Tags=tags)["DBSnapshot"]
        if snapshot["DBInstanceIdentifier"] != db_id:
            raise RuntimeError("El snapshot existente pertenece a otra instancia")
        print("Esperando snapshot", snapshot_id, flush=True)
        rds.get_waiter("db_snapshot_available").wait(DBSnapshotIdentifier=snapshot_id, WaiterConfig={"Delay": 30, "MaxAttempts": 60})
        snapshot = rds.describe_db_snapshots(DBSnapshotIdentifier=snapshot_id)["DBSnapshots"][0]
        try:
            target = rds.describe_db_instances(DBInstanceIdentifier=target_id)["DBInstances"][0]
        except ClientError as error:
            if error.response["Error"]["Code"] != "DBInstanceNotFound":
                raise
            target = rds.restore_db_instance_from_db_snapshot(DBInstanceIdentifier=target_id, DBSnapshotIdentifier=snapshot_id,
                DBInstanceClass="db.t3.micro", DBSubnetGroupName=source["DBSubnetGroup"]["DBSubnetGroupName"],
                VpcSecurityGroupIds=[g["VpcSecurityGroupId"] for g in source["VpcSecurityGroups"]],
                DBParameterGroupName=source["DBParameterGroups"][0]["DBParameterGroupName"],
                PubliclyAccessible=False, MultiAZ=False, DeletionProtection=True, CopyTagsToSnapshot=True, Tags=tags)["DBInstance"]
        initial_checks = validate_restore(source, target)
        # RDS can initially report default.postgres15/applying while restoring
        # the requested parameter group. Validate the final group after available.
        if not all(value for key, value in initial_checks.items() if key != "same_parameter_group"):
            raise RuntimeError("La copia no conserva el aislamiento esperado")
        print("Esperando copia privada", target_id, flush=True)
        rds.get_waiter("db_instance_available").wait(DBInstanceIdentifier=target_id, WaiterConfig={"Delay": 30, "MaxAttempts": 100})
        save("restore-snapshot-" + args.run, {**plan, "snapshot_created_at": str(snapshot.get("SnapshotCreateTime"))})
    target = rds.describe_db_instances(DBInstanceIdentifier=target_id)["DBInstances"][0]
    checks = validate_restore(source, target)
    result = {**plan, "checked_at": datetime.now(timezone.utc).isoformat(), "status": target["DBInstanceStatus"],
              "endpoint": target.get("Endpoint", {}).get("Address"), "checks": checks,
              "sql_restore_verified": False, "rto_measured": False,
              "next_step": "Verificar SQL y recorrido funcional desde una tarea privada; esta comprobación solo cubre la copia/configuración."}
    save("restore-verification-" + args.run, result)
    print(json.dumps(result, indent=2))
    if not all(checks.values()) or target["DBInstanceStatus"] != "available":
        raise RuntimeError("La copia restaurada todavía no está disponible con el aislamiento esperado")


if __name__ == "__main__":
    main()
