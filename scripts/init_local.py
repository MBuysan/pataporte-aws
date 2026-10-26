#!/usr/bin/env python3
"""Crear .env local con claves nuevas sin sobrescribir uno existente."""
import argparse
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, default=ROOT / ".env")
args = parser.parse_args()
if args.output.exists():
    print("Se conserva la configuración existente:", args.output.name)
else:
    values = {
        "DB_PASSWORD": secrets.token_hex(20),
        "SECRET_KEY": secrets.token_hex(32),
        "RABBITMQ_PASSWORD": secrets.token_hex(20),
    }
    lines = []
    for line in (ROOT / ".env_example").read_text().splitlines():
        name = line.split("=", 1)[0]
        if name in values:
            line = name + "=" + values[name]
        if name == "DATABASE_URL":
            line = "DATABASE_URL=postgresql://pataporte:" + values["DB_PASSWORD"] + "@db:5432/pataporte"
        lines.append(line)
    with args.output.open("x") as handle:
        handle.write("\n".join(lines) + "\n")
    args.output.chmod(0o600)
    print("Configuración local creada. Buzón: http://localhost:8025")
