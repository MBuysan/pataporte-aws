#!/usr/bin/env python3
"""Run inside CloudShell with the Academy session; never supply persistent AWS keys.

plan creates a CloudFormation change set. apply executes that reviewed set.
build uses an ephemeral Docker auth directory. migrate runs privately and checks
the exit code and database verification result before declaring success.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

import boto3
from botocore.exceptions import WaiterError

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = "476855088538"
REGION = "us-east-1"


def save(name, value):
    directory = ROOT / "deployment-results"
    directory.mkdir(exist_ok=True)
    (directory / (name + ".json")).write_text(json.dumps(value, default=str, indent=2) + "\n")


def outputs(cfn, name):
    return {v["OutputKey"]: v["OutputValue"] for v in cfn.describe_stacks(StackName=name)["Stacks"][0].get("Outputs", [])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply", "build", "migrate", "verify"])
    parser.add_argument("--component", choices=["bootstrap", "network", "compute", "async", "edge"])
    parser.add_argument("--change-set")
    parser.add_argument("--image")
    parser.add_argument("--migration-image")
    parser.add_argument("--kind", choices=["api", "worker"], default="api")
    parser.add_argument("--parameters-file", type=Path,
                        help="CloudFormation parameter list; no passwords or literal secret values")
    parser.add_argument("--api-count", type=int, default=0, choices=[0, 1, 2])
    args = parser.parse_args()
    session = boto3.Session(region_name=REGION)
    assert session.client("sts").get_caller_identity()["Account"] == ACCOUNT, "Unexpected AWS account"
    cfn = session.client("cloudformation")
    ecs = session.client("ecs")
    ecr = session.client("ecr")
    now = datetime.now(timezone.utc).isoformat()

    if args.action == "plan":
        if not args.component or not args.change_set:
            parser.error("plan requires --component and --change-set")
        stack = "pataporte-dev-" + args.component
        body = (ROOT / "infra" / (args.component + ".yaml")).read_text()
        cfn.validate_template(TemplateBody=body)
        try:
            old = cfn.describe_stacks(StackName=stack)["Stacks"][0]
        except cfn.exceptions.ClientError as error:
            if "does not exist" not in str(error):
                raise
            old = None
        kind = "UPDATE" if old else "CREATE"
        # Preserve explicit settings from previous releases, including task roles and feature flags.
        params = {p["ParameterKey"]: {"ParameterKey": p["ParameterKey"], "UsePreviousValue": True}
                  for p in (old or {}).get("Parameters", [])}
        overrides = []
        if args.component == "network":
            overrides = json.loads((ROOT / "infra/parameters/network-dev.json").read_text())
            for p in overrides:
                if p["ParameterKey"] == "NatMode":
                    p["ParameterValue"] = "single"
        elif args.component == "compute":
            if not args.image:
                parser.error("compute requires --image repository@sha256:digest")
            overrides = [{"ParameterKey": "ImageUri", "ParameterValue": args.image},
                         {"ParameterKey": "ApiDesiredCount", "ParameterValue": str(args.api_count)}]
            # Freeze the AMI actually deployed when migrating away from a moving
            # public SSM parameter. UsePreviousValue preserves its key, not its
            # resolved image, and can otherwise update hosts during an API release.
            for previous_parameter in (old or {}).get("Parameters", []):
                if previous_parameter["ParameterKey"] == "EcsAmi" and previous_parameter.get("ResolvedValue"):
                    overrides.append({"ParameterKey": "EcsAmi", "ParameterValue": previous_parameter["ResolvedValue"]})
            if args.migration_image:
                overrides.append({"ParameterKey": "MigrationImageUri", "ParameterValue": args.migration_image})
        if args.parameters_file:
            overrides.extend(json.loads(args.parameters_file.read_text()))
        params.update({p["ParameterKey"]: p for p in overrides})
        cfn.create_change_set(StackName=stack, ChangeSetName=args.change_set,
                              ChangeSetType=kind, TemplateBody=body, Parameters=list(params.values()),
                              Tags=[{"Key": "project", "Value": "pataporte"},
                                    {"Key": "environment", "Value": "dev"},
                                    {"Key": "managed-by", "Value": "cloudformation"}])
        try:
            cfn.get_waiter("change_set_create_complete").wait(StackName=stack, ChangeSetName=args.change_set)
        except WaiterError:
            description = cfn.describe_change_set(StackName=stack, ChangeSetName=args.change_set)
            if "didn't contain changes" not in description.get("StatusReason", ""):
                raise
        description = cfn.describe_change_set(StackName=stack, ChangeSetName=args.change_set)
        summary = {"stack": stack, "type": kind, "change_set": args.change_set, "created_at": now,
                   "changes": [{k: x["ResourceChange"].get(k) for k in ("Action", "LogicalResourceId", "ResourceType", "Replacement")} for x in description.get("Changes", [])]}
        save(args.component + "-plan", summary)
        print(json.dumps(summary, indent=2), flush=True)

    elif args.action == "apply":
        if not args.component or not args.change_set:
            parser.error("apply requires --component and --change-set")
        stack = "pataporte-dev-" + args.component
        change = cfn.describe_change_set(StackName=stack, ChangeSetName=args.change_set)
        if change["Status"] == "FAILED" and "didn't contain changes" in change.get("StatusReason", ""):
            print("NO_CHANGES", stack, flush=True)
            return
        if change["Status"] != "CREATE_COMPLETE" or change["ExecutionStatus"] != "AVAILABLE":
            raise RuntimeError("Change set is not available")
        # Never replace or remove a resource as a side effect of this bootstrap.
        if any(x["ResourceChange"]["Action"] == "Remove" or (
            x["ResourceChange"].get("Replacement") in {"True", "Conditional"}
            and x["ResourceChange"]["ResourceType"] != "AWS::ECS::TaskDefinition") for x in change["Changes"]):
            raise RuntimeError("Refusing deletion/replacement; review separately")
        previous = cfn.describe_stacks(StackName=stack)["Stacks"][0]["StackStatus"]
        cfn.execute_change_set(StackName=stack, ChangeSetName=args.change_set)
        waiter = "stack_create_complete" if previous == "REVIEW_IN_PROGRESS" else "stack_update_complete"
        print("WAITING", stack, flush=True)
        cfn.get_waiter(waiter).wait(StackName=stack, WaiterConfig={"Delay": 20, "MaxAttempts": 90})
        status = cfn.describe_stacks(StackName=stack)["Stacks"][0]["StackStatus"]
        result = {"stack": stack, "status": status, "outputs": outputs(cfn, stack), "verified_at": datetime.now(timezone.utc).isoformat()}
        save(args.component + "-stack", result)
        print(json.dumps(result, indent=2), flush=True)

    elif args.action == "build":
        repo = outputs(cfn, "pataporte-dev-bootstrap")
        manifest = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted((ROOT / "backend").rglob("*"))
                    if p.is_file() and not any(part in {"uploads", "__pycache__", ".venv", ".git"} for part in p.parts)
                    and not p.name.startswith(".env") and p.suffix not in {".pyc", ".pyo"}}
        manifest["image_kind"] = args.kind
        source_id = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        tag = args.kind + "-" + source_id[:16]
        image = repo["RepositoryUri"] + ":" + tag
        try:
            images = ecr.describe_images(repositoryName=repo["RepositoryName"], imageIds=[{"imageTag": tag}])["imageDetails"]
        except ecr.exceptions.ImageNotFoundException:
            images = []
        if not images:
            dockerfile = ROOT / "backend" / ("Dockerfile.lambda" if args.kind == "worker" else "Dockerfile")
            subprocess.run(["docker", "build", "--pull", "--platform", "linux/amd64", "-f", str(dockerfile), "-t", image, str(ROOT / "backend")], check=True)
            with tempfile.TemporaryDirectory(prefix="pataporte-docker-auth-") as config:
                env = dict(os.environ, DOCKER_CONFIG=config)
                authorization = ecr.get_authorization_token()["authorizationData"][0]
                username, password = base64.b64decode(authorization["authorizationToken"]).decode().split(":", 1)
                subprocess.run(["docker", "login", "--username", username, "--password-stdin", authorization["proxyEndpoint"]], input=password, text=True, env=env, check=True)
                subprocess.run(["docker", "push", image], env=env, check=True)
            images = ecr.describe_images(repositoryName=repo["RepositoryName"], imageIds=[{"imageTag": tag}])["imageDetails"]
        detail = images[0]
        result = {"repository": repo["RepositoryUri"], "tag": tag, "digest": detail["imageDigest"],
                  "image": repo["RepositoryUri"] + "@" + detail["imageDigest"],
                  "size_bytes": detail["imageSizeInBytes"], "source_manifest_sha256": source_id,
                  "published_at": str(detail["imagePushedAt"]), "verified_at": now}
        save("image" if args.kind == "api" else "worker-image", result)
        save("source-manifest-" + args.kind, manifest)
        print("PATAPORTE_IMAGE=" + json.dumps(result), flush=True)

    elif args.action == "migrate":
        compute = outputs(cfn, "pataporte-dev-compute")
        network = outputs(cfn, "pataporte-dev-network")
        response = ecs.run_task(cluster=compute["ClusterName"], taskDefinition=compute["MigrationTaskDefinitionArn"],
                                count=1, capacityProviderStrategy=[{"capacityProvider": compute["CapacityProviderName"], "weight": 1}],
                                startedBy="pataporte-migrate", networkConfiguration={"awsvpcConfiguration": {
                                    "subnets": [network["AppSubnetAId"], network["AppSubnetBId"]],
                                    "securityGroups": [network["WorkerSecurityGroupId"]], "assignPublicIp": "DISABLED"}})
        if response.get("failures") or len(response.get("tasks", [])) != 1:
            raise RuntimeError(json.dumps(response.get("failures")))
        arn = response["tasks"][0]["taskArn"]
        save("migration-started", {"task_arn": arn, "started_at": now})
        print("MIGRATION_TASK", arn, flush=True)
        ecs.get_waiter("tasks_stopped").wait(cluster=compute["ClusterName"], tasks=[arn], WaiterConfig={"Delay": 15, "MaxAttempts": 100})
        task = ecs.describe_tasks(cluster=compute["ClusterName"], tasks=[arn])["tasks"][0]
        container = task["containers"][0]
        logs = session.client("logs")
        try:
            events = logs.get_log_events(logGroupName="/pataporte/dev/migrate", logStreamName="ecs/migrate/" + arn.rsplit("/", 1)[1], startFromHead=True)["events"]
        except logs.exceptions.ResourceNotFoundException:
            events = []
        messages = [e["message"] for e in events]
        prefix = "PATAPORTE_MIGRATION_RESULT="
        result = {"task_arn": arn, "exit_code": container.get("exitCode"), "stop_reason": task.get("stoppedReason"),
                  "container_reason": container.get("reason"),
                  "image_digest": container.get("imageDigest"), "verified_at": datetime.now(timezone.utc).isoformat(),
                  "database": next((json.loads(m[len(prefix):]) for m in messages if m.startswith(prefix)), None)}
        save("migration", result)
        print(json.dumps(result, indent=2), flush=True)
        if container.get("exitCode") != 0 or result["database"] is None:
            print("\n".join(messages[-30:]), flush=True)
            raise RuntimeError("Migration did not complete; do not start API")

    elif args.action == "verify":
        import urllib.request
        import urllib.error
        compute = outputs(cfn, "pataporte-dev-compute")
        service = ecs.describe_services(cluster=compute["ClusterName"], services=[compute["ServiceName"]])["services"][0]
        arns = ecs.list_tasks(cluster=compute["ClusterName"], serviceName=compute["ServiceName"])["taskArns"]
        tasks = ecs.describe_tasks(cluster=compute["ClusterName"], tasks=arns)["tasks"] if arns else []
        targets = session.client("elbv2").describe_target_health(TargetGroupArn=compute["TargetGroupArn"])["TargetHealthDescriptions"]
        definition = ecs.describe_task_definition(taskDefinition=compute["ApiTaskDefinitionArn"])["taskDefinition"]
        container_instances = ecs.list_container_instances(cluster=compute["ClusterName"])["containerInstanceArns"]
        hosts = ecs.describe_container_instances(cluster=compute["ClusterName"], containerInstances=container_instances)["containerInstances"] if container_instances else []
        ec2 = session.client("ec2")
        instances = [i for r in ec2.describe_instances(InstanceIds=[h["ec2InstanceId"] for h in hosts])["Reservations"] for i in r["Instances"]] if hosts else []
        network = outputs(cfn, "pataporte-dev-network")
        allowed_subnets = {network["AppSubnetAId"], network["AppSubnetBId"]}
        expected_image = json.loads((ROOT / "deployment-results/image.json").read_text())["image"]
        image_matches = definition["containerDefinitions"][0]["image"] == expected_image and all(c.get("imageDigest") == expected_image.rsplit("@", 1)[1] for t in tasks for c in t["containers"])
        private_hosts = bool(instances) and all(not i.get("PublicIpAddress") and i["SubnetId"] in allowed_subnets and i["MetadataOptions"]["HttpTokens"] == "required" and i["MetadataOptions"]["HttpPutResponseHopLimit"] == 1 for i in instances)
        private_tasks = bool(tasks) and all(d.get("value") in allowed_subnets for t in tasks for a in t["attachments"] for d in a.get("details", []) if d["name"] == "subnetId")
        runtime_secret_arns = [s["valueFrom"] for s in definition["containerDefinitions"][0].get("secrets", [])]
        parameters = {p["ParameterKey"]: p.get("ParameterValue") for p in cfn.describe_stacks(StackName="pataporte-dev-compute")["Stacks"][0]["Parameters"]}
        expected_role = parameters.get("ApplicationRoleArn") if parameters.get("EnableCloudFeatures") == "true" else None
        limited_execution = definition.get("taskRoleArn") == expected_role and definition["executionRoleArn"] == f"arn:aws:iam::{ACCOUNT}:role/LabRole" and all("pataporte/dev/" in arn for arn in runtime_secret_arns)
        url = "http://" + compute["LoadBalancerDnsName"]
        health = {}
        for path in ["/health/live", "/health/ready", "/docs", "/"]:
            try:
                with urllib.request.urlopen(url + path, timeout=15) as response:
                    health[path] = {"status": response.status, "body": response.read().decode()}
            except urllib.error.HTTPError as response:
                health[path] = {"status": response.code}
        result = {"verified_at": now, "cluster": compute["ClusterName"], "service": compute["ServiceName"],
                  "desired": service["desiredCount"], "running": service["runningCount"], "pending": service["pendingCount"],
                  "deployments": [{k: d.get(k) for k in ("status", "rolloutState", "runningCount", "desiredCount")} for d in service["deployments"]],
                  "tasks": [{"arn": t["taskArn"], "az": t.get("availabilityZone"), "status": t["lastStatus"], "digest": t["containers"][0].get("imageDigest")} for t in tasks],
                  "targets": [{"ip": t["Target"]["Id"], "state": t["TargetHealth"]["State"]} for t in targets],
                  "hosts": [{"id": i["InstanceId"], "az": i["Placement"]["AvailabilityZone"], "subnet": i["SubnetId"], "public_ip": i.get("PublicIpAddress"), "imds_tokens": i["MetadataOptions"]["HttpTokens"]} for i in instances],
                  "checks": {"image_digest_matches": image_matches, "private_hosts_imdsv2": private_hosts, "tasks_in_private_app_subnets": private_tasks, "configured_task_role_and_no_master_secret_in_api_environment": limited_execution},
                  "url": url, "http": health}
        save("compute-verification", result)
        print(json.dumps(result, indent=2), flush=True)
        assert service["desiredCount"] == service["runningCount"] == 2 and service["pendingCount"] == 0
        assert len({t.get("availabilityZone") for t in tasks}) == 2
        assert len(targets) == 2 and all(t["TargetHealth"]["State"] == "healthy" for t in targets)
        assert health["/health/live"]["status"] == health["/health/ready"]["status"] == 200
        assert health["/docs"]["status"] == health["/"]["status"] == 404
        assert all(result["checks"].values()), "Runtime security/configuration check failed"
        print("VERIFICATION_PASSED", flush=True)


if __name__ == "__main__":
    main()
