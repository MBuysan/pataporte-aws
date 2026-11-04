#!/usr/bin/env python3
"""Entrega conjunta: migración, Lambda/SQS, API/dispatcher, frontend y comprobaciones."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import urlopen
from uuid import uuid4

import boto3
from deploy_ecs import ACCOUNT, REGION, ROOT, outputs, save

RESULTS = ROOT / "deployment-results"


def read(name):
    return json.loads((RESULTS / (name + ".json")).read_text())


def run(script, *args):
    subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args], check=True)


def configuration():
    keys = {"domain": "PATAPORTE_API_DOMAIN", "certificate": "PATAPORTE_ALB_CERTIFICATE_ARN",
            "mail_secret": "PATAPORTE_SMTP_SECRET_ARN", "task_role": "PATAPORTE_TASK_ROLE_ARN"}
    config = {key: os.getenv(variable, "").strip() for key, variable in keys.items()}
    missing = [variable for key, variable in keys.items() if not config[key]]
    if missing:
        raise RuntimeError("Falta configurar en el environment academy: " + ", ".join(missing))
    if not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9.-]{0,250})\.[a-zA-Z]{2,63}", config["domain"]):
        raise RuntimeError("Dominio de origen inválido")
    for key, prefix in [("certificate", f"arn:aws:acm:{REGION}:{ACCOUNT}:certificate/"),
                        ("mail_secret", f"arn:aws:secretsmanager:{REGION}:{ACCOUNT}:secret:"),
                        ("task_role", f"arn:aws:iam::{ACCOUNT}:role/")]:
        if not config[key].startswith(prefix):
            raise RuntimeError("Recurso de otra cuenta/región o ARN inválido: " + key)
    return config


def parameters(name, values):
    save(name, [{"ParameterKey": key, "ParameterValue": str(value)} for key, value in values.items()])
    return str(RESULTS / (name + ".json"))


def apply(component, run_id, values, *, image=None):
    args = ["plan", "--component", component, "--change-set", f"full-{component}-{run_id}",
            "--parameters-file", parameters("full-" + component + "-parameters", values)]
    if component == "compute":
        args += ["--image", image, "--migration-image", image, "--api-count", "2"]
    run("deploy_ecs.py", *args)
    run("deploy_ecs.py", "apply", "--component", component, "--change-set", f"full-{component}-{run_id}")


def verify(session):
    cfn = session.client("cloudformation")
    edge = outputs(cfn, "pataporte-dev-edge")
    asynchronous = outputs(cfn, "pataporte-dev-async")
    statuses = {}
    for path, expected in [("/", {200}), ("/api/health/ready", {200}), ("/api/mascotas/", {401, 403})]:
        try:
            with urlopen(edge["Url"] + path, timeout=20) as response:
                code = response.status
        except HTTPError as error:
            code = error.code
        statuses[path] = code
        if code not in expected:
            raise RuntimeError("Falló el smoke de la distribución; revisar status HTTP sin publicar cuerpos de respuesta")
    event_id = str(uuid4())
    envelope = {"schema_version": 1, "event_id": event_id, "payload": {"tipo": "probe"}}
    session.client("sqs").send_message(QueueUrl=asynchronous["QueueUrl"], MessageBody=json.dumps(envelope))
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        result = session.client("dynamodb").get_item(TableName=asynchronous["IdempotencyTableName"],
                 Key={"event_id": {"S": event_id}}, ConsistentRead=True).get("Item", {})
        if result.get("status", {}).get("S") == "DONE":
            artifact = session.client("s3").head_object(Bucket=asynchronous["AssetsBucketName"], Key=f"probes/{event_id}.json")
            save("full-verification", {"url": edge["Url"], "http": statuses, "sqs_lambda_dynamodb_s3_probe": "passed",
                                      "event_id": event_id, "artifact_version": artifact.get("VersionId"),
                                      "smtp_delivery_verified": False, "load_and_restore_verified": False})
            return
        time.sleep(3)
    raise RuntimeError("El evento de comprobación no llegó a DONE dentro de tres minutos")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "deploy"])
    args = parser.parse_args()
    config = configuration()
    session = boto3.Session(region_name=REGION)
    if session.client("sts").get_caller_identity()["Account"] != ACCOUNT:
        raise RuntimeError("Cuenta distinta de Academy")
    cfn = session.client("cloudformation")
    ecs = session.client("ecs")
    compute = outputs(cfn, "pataporte-dev-compute")
    if args.action == "plan":
        # Validar existencia sin leer valores SMTP ni imprimir certificados completos.
        session.client("secretsmanager").describe_secret(SecretId=config["mail_secret"])
        certificate = session.client("acm").describe_certificate(CertificateArn=config["certificate"])["Certificate"]
        if certificate["Status"] != "ISSUED":
            raise RuntimeError("El certificado de origen todavía no está emitido")
        names = certificate.get("SubjectAlternativeNames", [certificate["DomainName"]])
        if not any(config["domain"].lower() == name.lower() or
                   (name.startswith("*.") and config["domain"].split(".", 1)[1].lower() == name[2:].lower()) for name in names):
            raise RuntimeError("El certificado no cubre el hostname del origen")
        stack = cfn.describe_stacks(StackName="pataporte-dev-compute")["Stacks"][0]
        stack_parameters = {p["ParameterKey"]: p.get("ParameterValue") for p in stack["Parameters"]}
        if stack_parameters.get("EnableApiScaling", "false") == "true":
            raise RuntimeError("Para esta entrega inicial, desactivar y estabilizar el escalado antes del plan conjunto")
        task = ecs.describe_task_definition(taskDefinition=compute["ApiTaskDefinitionArn"])["taskDefinition"]
        service = ecs.describe_services(cluster=compute["ClusterName"], services=[compute["ServiceName"]])["services"][0]
        if service["desiredCount"] != 2 or service["runningCount"] != 2 or service["pendingCount"]:
            raise RuntimeError("Se requieren dos réplicas estables antes de planear")
        run_id = os.getenv("GITHUB_RUN_ID", "local") + "-" + os.getenv("GITHUB_RUN_ATTEMPT", "1")
        if not re.fullmatch(r"[a-zA-Z0-9-]{1,70}", run_id):
            raise RuntimeError("Identificador inválido")
        run("deploy_ecs.py", "build")
        run("deploy_ecs.py", "build", "--kind", "worker")
        image = read("image")["image"]
        run("deploy_ecs.py", "plan", "--component", "compute", "--change-set", "full-stage-" + run_id,
            "--image", task["containerDefinitions"][0]["image"], "--migration-image", image, "--api-count", "2")
        save("full-release", {"run": run_id, "previous_task": task["taskDefinitionArn"], "configuration": config,
                              "api_image": image, "worker_image": read("worker-image")["image"],
                              "frontend_release": "web-" + run_id})
        print("Plan conjunto preparado: revisar compute-plan.json, full-release.json y las plantillas antes de aprobar.")
    else:
        release = read("full-release")
        if config != release["configuration"] or compute["ApiTaskDefinitionArn"] != release["previous_task"]:
            raise RuntimeError("La configuración o la API cambiaron desde el plan")
        run_id = release["run"]
        run("deploy_ecs.py", "apply", "--component", "compute", "--change-set", "full-stage-" + run_id)
        run("deploy_ecs.py", "migrate")
        apply("async", run_id, {"WorkerImageUri": release["worker_image"], "MailSecretArn": config["mail_secret"],
              "EnableMailDelivery": "true", "EnableQueueConsumer": "true"})
        apply("compute", run_id, {"EnableCloudFeatures": "true", "ApplicationRoleArn": config["task_role"],
              "DispatcherDesiredCount": "1", "DispatcherImageUri": release["api_image"],
              "EnableEdgeApi": "true", "AlbCertificateArn": config["certificate"]}, image=release["api_image"])
        run("deploy_ecs.py", "verify")
        edge_values = {"ApiOriginHostName": config["domain"], "ApiOriginProtocol": "https-only"}
        apply("edge", run_id + "-prepare", edge_values)
        run("publish_frontend.py", "--release", release["frontend_release"])
        apply("edge", run_id + "-publish", {**edge_values, "ReleaseId": release["frontend_release"]})
        edge = outputs(cfn, "pataporte-dev-edge")
        cloudfront = session.client("cloudfront")
        invalidation = cloudfront.create_invalidation(DistributionId=edge["DistributionId"], InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": ["/*"]}, "CallerReference": "pataporte-" + run_id})
        cloudfront.get_waiter("invalidation_completed").wait(DistributionId=edge["DistributionId"], Id=invalidation["Invalidation"]["Id"])
        verify(session)


if __name__ == "__main__":
    main()
