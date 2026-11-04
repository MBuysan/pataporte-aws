#!/usr/bin/env python3
"""Carga acotada sobre PATAPORTE local o su distribución AWS verificada."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def verify_target(url):
    target = urlsplit(url)
    if target.username or target.password or target.query or target.fragment:
        raise ValueError("La URL no puede contener credenciales, query ni fragmento")
    if target.scheme == "http" and target.hostname in {"localhost", "127.0.0.1"}:
        return "local"
    if target.scheme != "https":
        raise ValueError("El destino remoto requiere HTTPS")
    import boto3
    from deploy_ecs import ACCOUNT, REGION, outputs
    session = boto3.Session(region_name=REGION)
    if session.client("sts").get_caller_identity()["Account"] != ACCOUNT:
        raise ValueError("La cuenta no es Academy")
    distribution = outputs(session.client("cloudformation"), "pataporte-dev-edge")["Url"]
    if target.netloc != urlsplit(distribution).netloc or target.path.rstrip("/") != "/api":
        raise ValueError("El destino no coincide con la distribución PATAPORTE de esta cuenta")
    return "aws"


def measure(url, token, requests, concurrency, rps, opener=urlopen):
    headers = {"Authorization": "Bearer " + token} if token else {}
    paths = ["/mascotas/", "/health/ready"] if token else ["/health/ready"]
    def one(index):
        path = paths[index % len(paths)]
        started = time.monotonic()
        try:
            with opener(Request(url.rstrip("/") + path, headers=headers), timeout=15) as response:
                response.read()
                status = response.status
        except HTTPError as error:
            status = error.code
        except (URLError, TimeoutError, OSError):
            status = 0
        return status, (time.monotonic() - started) * 1000
    started = time.monotonic()
    futures = []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for index in range(requests):
            delay = started + index / rps - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            futures.append(pool.submit(one, index))
        results = [future.result() for future in futures]
    latencies = [latency for _, latency in results]
    return {"requests": requests, "concurrency": concurrency, "requested_rps": rps,
            "duration_seconds": round(time.monotonic() - started, 3),
            "status_counts": dict(Counter(str(status) for status, _ in results)),
            "errors": sum(status != 200 for status, _ in results),
            "p50_ms": round(percentile(latencies, .50), 3), "p95_ms": round(percentile(latencies, .95), 3),
            "p99_ms": round(percentile(latencies, .99), 3), "authenticated": bool(token), "paths": paths,
            "autoscaling_proven": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8085/api")
    parser.add_argument("--requests", type=int, default=80)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--rps", type=float, default=10)
    parser.add_argument("--local-account", action="store_true", help="Crear una cuenta ficticia con Mailpit, solo en localhost")
    parser.add_argument("--report", type=Path, default=ROOT / "deployment-results/load-probe.json")
    args = parser.parse_args()
    if not 1 <= args.requests <= 10000 or not 1 <= args.concurrency <= 16 or not 0 < args.rps <= 50:
        parser.error("Límites: 1–10000 solicitudes, 1–16 conexiones y hasta 50 solicitudes/s")
    destination = verify_target(args.url)
    token = os.getenv("PATAPORTE_TEST_TOKEN", "")
    if args.local_account:
        if destination != "local":
            parser.error("La cuenta de prueba automática requiere localhost y Mailpit")
        sys.path.insert(0, str(ROOT / "tests"))
        import test_local_flow
        test_local_flow.BASE = args.url.rstrip("/")
        token = test_local_flow.register("tutor")["session"]["access_token"]
    result = {"destination": destination, **measure(args.url, token, args.requests, args.concurrency, args.rps)}
    args.report.parent.mkdir(exist_ok=True, parents=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if result["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
