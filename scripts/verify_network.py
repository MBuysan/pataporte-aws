#!/usr/bin/env python3
"""Verificar la red de PATAPORTE y su modo NAT previsto, sin modificarla."""
import argparse
from collections import Counter
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
    parser.add_argument("--stack", default="pataporte-dev-network")
    parser.add_argument("--profile")
    parser.add_argument("--nat-mode", choices=["none", "single", "per-az"], default="none")
    parser.add_argument("--health-http", action="store_true", help="Aceptar HTTP del ALB para health checks; verificar sus reglas con deploy_ecs.py verify")
    parser.add_argument("--report", type=Path, help="Guardar evidencia JSON sin credenciales")
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
        result = subprocess.run(common + list(command), env=env, text=True,
                                capture_output=True, timeout=40, check=False)
        if result.returncode:
            raise RuntimeError(result.stderr.strip())
        return json.loads(result.stdout)

    account = aws("sts", "get-caller-identity")["Account"]
    if account != args.expected_account:
        raise RuntimeError("La cuenta no coincide con --expected-account")
    stack = aws("cloudformation", "describe-stacks", "--stack-name", args.stack)["Stacks"][0]
    if stack["StackStatus"] not in {"CREATE_COMPLETE", "UPDATE_COMPLETE"}:
        raise RuntimeError(f"Stack todavía no verificable: {stack['StackStatus']}")
    outputs = {x["OutputKey"]: x["OutputValue"] for x in stack["Outputs"]}
    params = {x["ParameterKey"]: x["ParameterValue"] for x in stack["Parameters"]}
    vpc = outputs["VpcId"]
    resources = aws("cloudformation", "list-stack-resources", "--stack-name", args.stack)["StackResourceSummaries"]
    resource_ids = {x["LogicalResourceId"]: x["PhysicalResourceId"] for x in resources}
    filters = ["--filters", f"Name=vpc-id,Values={vpc}"]
    subnets = aws("ec2", "describe-subnets", *filters)["Subnets"]
    subnets_by_id = {x["SubnetId"]: x for x in subnets}
    tables = aws("ec2", "describe-route-tables", *filters)["RouteTables"]
    subnet_routes = {a["SubnetId"]: t["Routes"] for t in tables for a in t["Associations"] if "SubnetId" in a}
    endpoints = aws("ec2", "describe-vpc-endpoints", *filters)["VpcEndpoints"]
    nat = aws("ec2", "describe-nat-gateways", "--filter", f"Name=vpc-id,Values={vpc}")["NatGateways"]
    group_keys = ["AlbSecurityGroupId", "ApiSecurityGroupId", "WorkerSecurityGroupId", "DatabaseSecurityGroupId"]
    groups = aws("ec2", "describe-security-groups", "--group-ids", *[outputs[k] for k in group_keys])["SecurityGroups"]
    groups = {x["GroupId"]: x for x in groups}
    checks = []

    def check(name, valid):
        checks.append({"check": name, "passed": bool(valid)})
        print(f"{'OK' if valid else 'FALLO'}: {name}")

    nat_count = {"none": 0, "single": 1, "per-az": 2}[args.nat_mode]
    expected_resources = 27 + (2 + 2 * nat_count if nat_count else 0)
    check(f"{expected_resources} recursos de red completos", len(resources) == expected_resources and all(x["ResourceStatus"] in {"CREATE_COMPLETE", "UPDATE_COMPLETE"} for x in resources))
    active_nat = [x for x in nat if x["State"] != "deleted"]
    check("NAT e IP elasticas coinciden con el modo previsto", params["NatMode"] == args.nat_mode and len(active_nat) == nat_count and all(x["State"] == "available" for x in active_nat) and sum(x["ResourceType"] == "AWS::EC2::EIP" for x in resources) == nat_count)
    check("DNS de VPC habilitado", all(aws("ec2", "describe-vpc-attribute", "--vpc-id", vpc, "--attribute", attr)[attr[0].upper() + attr[1:]]["Value"] for attr in ["enableDnsSupport", "enableDnsHostnames"]))
    vpc_info = aws("ec2", "describe-vpcs", "--vpc-ids", vpc)["Vpcs"][0]
    check("CIDR y etiquetas de proyecto", vpc_info["CidrBlock"] == params["VpcCidr"] and {x["Key"]: x["Value"] for x in vpc_info.get("Tags", [])}.get("project") == "pataporte")
    expected_subnets = [(tier, zone, outputs[f"{tier}Subnet{zone}Id"]) for tier in ["Public", "App", "Data"] for zone in ["A", "B"]]
    check("Seis subredes con sus CIDR previstos y sin IP publica automatica", len(subnets) == 6 and all(subnets_by_id.get(sid, {}).get("CidrBlock") == params[f"{tier}Subnet{zone}Cidr"] and not subnets_by_id[sid]["MapPublicIpOnLaunch"] and subnets_by_id[sid]["State"] == "available" for tier, zone, sid in expected_subnets))
    check("Capas publica/app/datos distribuidas en dos AZ", len({x["AvailabilityZone"] for x in subnets}) == 2 and all(len({subnets_by_id[outputs[f"{tier}Subnet{zone}Id"]]["AvailabilityZone"] for tier in ["Public", "App", "Data"]}) == 1 for zone in ["A", "B"]) and subnets_by_id[outputs["AppSubnetAId"]]["AvailabilityZone"] != subnets_by_id[outputs["AppSubnetBId"]]["AvailabilityZone"])
    check("Subredes publicas con ruta al Internet Gateway", all(any(r.get("DestinationCidrBlock") == "0.0.0.0/0" and r.get("GatewayId") == resource_ids["InternetGateway"] and r["State"] == "active" for r in subnet_routes.get(outputs[f"PublicSubnet{zone}Id"], [])) for zone in ["A", "B"]))
    private_ids = [outputs[f"{tier}Subnet{zone}Id"] for tier in ["App", "Data"] for zone in ["A", "B"]]
    def expected_private_routes(tier, zone):
        routes = subnet_routes.get(outputs[f"{tier}Subnet{zone}Id"], [])
        defaults = [r for r in routes if r.get("DestinationCidrBlock") == "0.0.0.0/0" or r.get("DestinationIpv6CidrBlock") == "::/0"]
        if tier == "Data" or nat_count == 0:
            return bool(routes) and not defaults
        nat_key = "NatGatewayB" if args.nat_mode == "per-az" and zone == "B" else "NatGatewayA"
        return len(defaults) == 1 and defaults[0].get("NatGatewayId") == resource_ids[nat_key] and defaults[0]["State"] == "active"
    check("Datos sin Internet; app usa solo la salida NAT prevista", all(expected_private_routes(tier, zone) for tier in ["App", "Data"] for zone in ["A", "B"]))
    private_tables = {t["RouteTableId"] for t in tables if any(a.get("SubnetId") in private_ids for a in t["Associations"])}
    check("S3 y DynamoDB por Gateway Endpoints disponibles", len(endpoints) == 2 and all(any(e["ServiceName"] == f"com.amazonaws.{args.region}.{service}" and e["VpcEndpointType"] == "Gateway" and e["State"] == "available" and set(e["RouteTableIds"]) == private_tables for e in endpoints) for service in ["s3", "dynamodb"]))

    def only_groups(key, port, sources):
        permissions = groups[outputs[key]]["IpPermissions"]
        # AWS puede combinar los grupos origen en una regla o devolver reglas separadas.
        return bool(permissions) and all(p["IpProtocol"] == "tcp" and p.get("FromPort") == port and p.get("ToPort") == port and not p.get("IpRanges") and not p.get("Ipv6Ranges") and not p.get("PrefixListIds") for p in permissions) and {pair["GroupId"] for p in permissions for pair in p.get("UserIdGroupPairs", [])} == set(sources)

    check("API accesible por 8000 solo desde ALB", only_groups("ApiSecurityGroupId", 8000, [outputs["AlbSecurityGroupId"]]))
    check("PostgreSQL accesible por 5432 solo desde API/workers", only_groups("DatabaseSecurityGroupId", 5432, [outputs["ApiSecurityGroupId"], outputs["WorkerSecurityGroupId"]]))
    check("Workers sin reglas de entrada", not groups[outputs["WorkerSecurityGroupId"]]["IpPermissions"])
    alb_rules = groups[outputs["AlbSecurityGroupId"]]["IpPermissions"]
    expected_ports = {80, 443} if args.health_http else {443}
    check("Puertos ALB coinciden con la etapa prevista", len(alb_rules) == len(expected_ports) and {p.get("FromPort") for p in alb_rules} == expected_ports and all(p["IpProtocol"] == "tcp" and p.get("FromPort") == p.get("ToPort") and {r["CidrIp"] for r in p.get("IpRanges", [])} == {"0.0.0.0/0"} and not p.get("Ipv6Ranges") and not p.get("UserIdGroupPairs") and not p.get("PrefixListIds") for p in alb_rules))
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(), "region": args.region,
        "account_suffix": account[-4:], "stack": args.stack, "status": stack["StackStatus"],
        "vpc": vpc, "nat_mode": params["NatMode"], "outputs": outputs,
        "subnets": [{"id": x["SubnetId"], "cidr": x["CidrBlock"], "az": x["AvailabilityZone"]} for x in subnets],
        "resource_types": dict(Counter(x["ResourceType"] for x in resources)), "checks": checks,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Evidencia: {args.report}")
    failures = sum(not x["passed"] for x in checks)
    print(f"Resultado: {len(checks) - failures}/{len(checks)} comprobaciones correctas")
    return int(failures > 0)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, KeyError, ValueError, OSError, subprocess.TimeoutExpired) as error:
        print(f"No se pudo verificar la red: {error}", file=sys.stderr)
        sys.exit(1)
