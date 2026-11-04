#!/usr/bin/env python3
"""Ejecutar personalmente en una terminal: entradas ocultas, sin claves en chat/historial."""
import configparser
from getpass import getpass
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

EXPECTED_ACCOUNT = "476855088538"
PROFILE = "pataporte-lab"


def main():
    aws = shutil.which("aws")
    if not aws:
        raise SystemExit("Instalá AWS CLI desde la web oficial de AWS antes de continuar.")
    print("Learner Lab → AWS Details → AWS CLI. Copiá solo los valores, sin comillas.")
    keys = {
        "aws_access_key_id": getpass("aws_access_key_id (entrada oculta): ").strip(),
        "aws_secret_access_key": getpass("aws_secret_access_key (entrada oculta): ").strip(),
        "aws_session_token": getpass("aws_session_token (entrada oculta): ").strip(),
    }
    if not all(keys.values()) or any("\n" in value for value in keys.values()):
        raise SystemExit("Falta un valor válido; no se guardó nada.")
    env = {k: v for k, v in os.environ.items() if not k.startswith("AWS_")}
    env.update({key.upper(): value for key, value in keys.items()})
    result = subprocess.run([aws, "sts", "get-caller-identity", "--region", "us-east-1", "--output", "json"],
                            env=env, capture_output=True, text=True, timeout=30)
    if result.returncode or json.loads(result.stdout).get("Account") != EXPECTED_ACCOUNT:
        raise SystemExit("Credenciales vencidas, inválidas o de otra cuenta; no se guardó nada.")
    folder = Path.home() / ".aws"
    folder.mkdir(mode=0o700, exist_ok=True)
    target = folder / "credentials"
    parser = configparser.RawConfigParser()
    if target.exists():
        parser.read(target)
    parser[PROFILE] = keys
    # Conserva default y los demás perfiles; reemplazo atómico con permisos privados.
    fd, temporary = tempfile.mkstemp(prefix=".pataporte-", dir=folder)
    try:
        with os.fdopen(fd, "w") as stream:
            parser.write(stream)
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    print(f"Perfil {PROFILE} listo. Cuenta {EXPECTED_ACCOUNT}; usar región us-east-1.")


if __name__ == "__main__":
    main()
