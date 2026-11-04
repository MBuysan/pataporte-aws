#!/usr/bin/env python3
"""Comprobar acceso AWS y la red propuesta, sin crear ni modificar recursos."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True, help="Región habilitada por el laboratorio")
    parser.add_argument("--profile", help="Perfil AWS CLI con credenciales temporales de Academy")
    parser.add_argument("--expected-account", help="Detenerse si STS devuelve otra cuenta AWS")
    args = parser.parse_args()
    if not shutil.which("aws"):
        parser.error("Falta instalar AWS CLI")

    env = dict(os.environ, AWS_PAGER="", AWS_CLI_AUTO_PROMPT="off",
               AWS_EC2_METADATA_DISABLED="true", AWS_MAX_ATTEMPTS="1")
    common = ["aws", "--region", args.region, "--output", "json",
              "--cli-connect-timeout", "5", "--cli-read-timeout", "15"]
    if args.profile:
        common.extend(["--profile", args.profile])

    def call(*command, dry_run=False):
        try:
            result = subprocess.run(common + list(command), env=env, capture_output=True,
                                    text=True, timeout=30, check=False)
        except subprocess.TimeoutExpired:
            return False, "Tiempo de espera agotado; revisar conectividad."
        if dry_run and "(DryRunOperation)" in result.stderr:
            return True, "Permiso CreateVpc confirmado mediante --dry-run; no se creó una VPC."
        if result.returncode:
            return False, result.stderr.strip()
        try:
            return True, json.loads(result.stdout)
        except json.JSONDecodeError:
            return False, "AWS CLI no devolvió JSON válido."

    ok, identity = call("sts", "get-caller-identity")
    if not ok:
        print("PENDIENTE: credenciales o sesión de AWS.\n" + identity)
        print("Iniciar Learner Lab y configurar sus credenciales temporales en AWS CLI.")
        return 1
    account = identity["Account"]
    print(f"Cuenta: {account}\nIdentidad: {identity['Arn']}\nRegión: {args.region}")
    if args.expected_account and args.expected_account != account:
        print("ERROR: la cuenta no coincide; no se consultaron otros servicios.")
        return 1

    template = Path(__file__).resolve().parents[1] / "infra" / "network.yaml"
    checks = [
        ("Plantilla CloudFormation", ("cloudformation", "validate-template",
         "--template-body", template.as_uri()), False),
        ("Zonas disponibles", ("ec2", "describe-availability-zones", "--filters",
         "Name=state,Values=available", "--query", "AvailabilityZones[].ZoneName"), False),
        ("Inventario de red PATAPORTE", ("ec2", "describe-vpcs", "--filters",
         "Name=tag:project,Values=pataporte", "--query", "Vpcs[].{Id:VpcId,Cidr:CidrBlock}"), False),
        ("Permiso inicial de VPC", ("ec2", "create-vpc", "--cidr-block",
         "10.20.0.0/16", "--dry-run"), True),
        ("Rol existente LabRole", ("iam", "get-role", "--role-name", "LabRole",
         "--query", "Role.Arn"), False),
    ]
    pending = 0
    for title, command, dry_run in checks:
        ok, data = call(*command, dry_run=dry_run)
        if title == "Zonas disponibles" and ok and len(data) < 2:
            ok, data = False, "La plantilla requiere al menos dos zonas disponibles."
        pending += not ok
        print(f"\n{'OK' if ok else 'PENDIENTE'}: {title}")
        print(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, indent=2))

    print("\nNo se crearon recursos. Estos chequeos no garantizan permisos de despliegue, "
          "cuotas ni saldo; revisar también Learner Lab y el resultado de CloudFormation.")
    return int(pending > 0)


if __name__ == "__main__":
    sys.exit(main())
