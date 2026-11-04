#!/usr/bin/env python3
"""Entrega de la API: plan → revisión → migración → cambio de imagen → comprobación."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import boto3
from deploy_ecs import ACCOUNT, REGION, outputs, save

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "deployment-results"


def read(name):
    return json.loads((RESULTS / (name + ".json")).read_text())


def command(*args):
    subprocess.run([sys.executable, str(ROOT / "scripts/deploy_ecs.py"), *args], check=True)


def safe_final_change(change):
    if change['Action'] == 'Remove':
        return False
    if change['ResourceType'] in {'AWS::ECS::TaskDefinition', 'AWS::ECS::Service'}:
        return True
    # Its service-name dimension depends on ApiService.Name, so CloudFormation
    # includes the existing alarm when the task revision changes.
    return (change['ResourceType'] == 'AWS::CloudWatch::Alarm'
            and change.get('LogicalResourceId') == 'ApiMemoryAlarm'
            and change['Action'] == 'Modify' and change.get('Replacement') == 'False')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["snapshot", "plan-stage", "summary", "deploy"])
    args = parser.parse_args()
    if args.action == "summary":
        release = read("release")
        print("### Entrega PATAPORTE\n\nCuenta: `" + ACCOUNT + "`; región: `" + REGION + "`.\n")
        print("Imagen nueva: `" + read("image")["image"] + "`.\n")
        print("Se conserva la API actual mientras se ejecuta la migración. Solo si termina en cero se actualiza el servicio a dos réplicas.\n")
        print("El entorno GitHub **academy** debe tener un revisor obligatorio configurado antes de usar este flujo.\n")
        print("No crea IAM, no abre rutas públicas adicionales y no restaura automáticamente el esquema ante un fallo.\n")
        print("Plan de etapa: `" + release["stage_change_set"] + "`. Evidencia adjunta en academy-release-plan.")
        return
    session = boto3.Session(region_name=REGION)
    if session.client("sts").get_caller_identity()["Account"] != ACCOUNT:
        raise RuntimeError("Cuenta distinta de Academy; no se ejecutó la entrega")
    cfn = session.client("cloudformation")
    ecs = session.client("ecs")
    if args.action == "snapshot":
        info = outputs(cfn, "pataporte-dev-compute")
        definition = ecs.describe_task_definition(taskDefinition=info["ApiTaskDefinitionArn"])["taskDefinition"]
        service = ecs.describe_services(cluster=info["ClusterName"], services=[info["ServiceName"]])["services"][0]
        if service["desiredCount"] != 2 or service["runningCount"] != 2 or service["pendingCount"]:
            raise RuntimeError("La entrega requiere la base existente de dos réplicas estables")
        parameters = {p["ParameterKey"]: p.get("ParameterValue") for p in cfn.describe_stacks(StackName="pataporte-dev-compute")["Stacks"][0]["Parameters"]}
        if parameters.get("EnableCloudFeatures", "false") != "false":
            raise RuntimeError("Este flujo entrega solo la API de la base inicial. Para la etapa con dispatcher, preparar un plan conjunto explícito")
        run = os.getenv("GITHUB_RUN_ID", "local") + "-" + os.getenv("GITHUB_RUN_ATTEMPT", "1")
        if not re.fullmatch(r"[a-zA-Z0-9-]{1,70}", run):
            raise RuntimeError("Identificador de entrega inválido")
        save("release", {"account": ACCOUNT, "region": REGION, "run": run, "previous_image": definition["containerDefinitions"][0]["image"],
                         "previous_task_definition": definition["taskDefinitionArn"], "cluster": info["ClusterName"],
                         "service": info["ServiceName"], "stage_change_set": "release-stage-" + run,
                         "api_change_set": "release-api-" + run})
    elif args.action == "plan-stage":
        release = read("release")
        command("plan", "--component", "compute", "--change-set", release["stage_change_set"],
                "--image", release["previous_image"], "--migration-image", read("image")["image"], "--api-count", "2")
        save("stage-plan", read("compute-plan"))
    elif args.action == "deploy":
        release = read("release")
        current = outputs(cfn, "pataporte-dev-compute")
        definition = ecs.describe_task_definition(taskDefinition=current["ApiTaskDefinitionArn"])["taskDefinition"]
        if definition["taskDefinitionArn"] != release["previous_task_definition"]:
            raise RuntimeError("Otra entrega cambió la API desde el plan; preparar un plan nuevo")
        command("apply", "--component", "compute", "--change-set", release["stage_change_set"])
        command("migrate")
        image = read("image")["image"]
        command("plan", "--component", "compute", "--change-set", release["api_change_set"],
                "--image", image, "--migration-image", image, "--api-count", "2")
        if any(not safe_final_change(c) for c in read("compute-plan")["changes"]):
            raise RuntimeError("La etapa final contiene cambios fuera de las tareas/servicio; revisar manualmente")
        command("apply", "--component", "compute", "--change-set", release["api_change_set"])
        command("verify")


if __name__ == "__main__":
    main()
