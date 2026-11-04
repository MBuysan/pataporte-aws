#!/usr/bin/env python3
"""Asistente loopback, con entrada humana, para un perfil Academy aislado del perfil personal."""
import configparser
import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import threading
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = "476855088538"
PROFILE = "pataporte-lab"
STORE = ROOT / ".local" / "aws"
CSRF = secrets.token_urlsafe(32)
connected = False


def validate_and_save(block):
    config = configparser.RawConfigParser()
    config.read_string(block.strip())
    if len(config.sections()) != 1:
        raise ValueError("Pegá el bloque AWS CLI completo de una sola sesión.")
    section = config[config.sections()[0]]
    keys = {key: section.get(key, "").strip() for key in ["aws_access_key_id", "aws_secret_access_key", "aws_session_token"]}
    if not all(keys.values()) or any(any(char in value for char in "\r\n") for value in keys.values()):
        raise ValueError("El bloque debe incluir access key, secret key y session token.")
    aws = shutil.which("aws")
    if not aws:
        raise RuntimeError("Falta AWS CLI en esta computadora.")
    env = {key: value for key, value in os.environ.items() if not key.startswith("AWS_")}
    env.update({key.upper(): value for key, value in keys.items()})
    env["AWS_EC2_METADATA_DISABLED"] = "true"
    response = subprocess.run([aws, "sts", "get-caller-identity", "--region", "us-east-1", "--query", "Account", "--output", "text"],
                              env=env, capture_output=True, text=True, timeout=30)
    if response.returncode or response.stdout.strip() != ACCOUNT:
        raise ValueError("La sesión venció, es inválida o pertenece a otra cuenta. Iniciá el Learner Lab del proyecto y copiá sus credenciales nuevas.")
    STORE.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(STORE, 0o700)
    output = configparser.RawConfigParser()
    output[PROFILE] = keys
    fd, temporary = tempfile.mkstemp(prefix=".credentials-", dir=STORE)
    try:
        with os.fdopen(fd, "w") as stream:
            output.write(stream)
        os.chmod(temporary, 0o600)
        os.replace(temporary, STORE / "credentials")
    finally:
        Path(temporary).unlink(missing_ok=True)
    (STORE / "status.json").write_text(json.dumps({"account": ACCOUNT, "profile": PROFILE, "ready": True}))


def page(message="", done=False):
    form = "" if done else f'''<ol><li>Abrí <a href="https://awsacademy.instructure.com/courses/182602/modules/items/18009275" target="_blank" rel="noreferrer">Learner Lab</a> en Chrome.</li><li>Pulsá <b>Start Lab</b> y esperá a que AWS quede verde.</li><li>Entrá a <b>AWS Details → AWS CLI</b>, copiá el bloque completo (empieza por <code>[default]</code>) y pegalo abajo.</li></ol><form method="post" action="/connect"><input type="hidden" name="csrf" value="{CSRF}"><label for="block">Credenciales temporales del laboratorio</label><textarea id="block" name="block" required spellcheck="false" autocomplete="off" autocapitalize="off" placeholder="[default]&#10;aws_access_key_id=…&#10;aws_secret_access_key=…&#10;aws_session_token=…"></textarea><button>Verificar cuenta y conectar</button></form>'''
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Conectar PATAPORTE con Academy</title><style>body{{margin:0;background:#f7f5ef;color:#263d32;font:15px/1.7 "Avenir Next",sans-serif}}main{{max-width:690px;padding:45px 25px;margin:auto}}small{{letter-spacing:2px;color:#ac5936;font-weight:700}}h1{{font:44px/1.1 Georgia,serif;letter-spacing:-1px}}a{{color:#2d5c43}}ol{{padding-left:22px}}li{{padding:5px}}label{{display:block;font-size:12px;font-weight:700;margin-top:24px}}textarea{{box-sizing:border-box;width:100%;min-height:180px;resize:vertical;border:1px solid #bfcbb6;border-radius:5px;background:#fffefa;padding:15px;font:12px/1.6 monospace;-webkit-text-security:disc}}button{{border:0;border-radius:5px;background:#2d5c43;color:white;padding:13px 20px;font:600 14px sans-serif;margin-top:15px;cursor:pointer}}.message{{padding:15px;border:1px solid #bfcbb6;background:#e8eddf}}.note{{font-size:12px;color:#677260;border-top:1px solid #d7ddce;padding-top:20px;margin-top:27px}}</style></head><body><main><small>PATAPORTE · AWS ACADEMY</small><h1>{'Laboratorio conectado.' if done else 'Conectar el laboratorio.'}</h1><p class="message" role="status">{html.escape(message) if message else 'Un solo paso para que pueda continuar el despliegue en tu cuenta Academy.'}</p>{form}<p class="note">Esta página funciona únicamente en tu computadora. Las claves se validan con AWS STS y se guardan en un archivo local privado, excluido de Git. Tu perfil personal no se modifica. Cuenta permitida: {ACCOUNT}. No pegues claves en el chat.</p></main></body></html>'''.encode()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, code, body, content_type="text/html; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        # no-referrer makes browsers send Origin: null on form POSTs, which
        # conflicts with the strict same-origin check below.
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def valid_host(self):
        return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

    def do_GET(self):
        if not self.valid_host():
            return self.respond(403, b"Forbidden")
        if self.path not in ("/", "/connect"):
            return self.respond(404, b"Not found")
        self.respond(200, page("Cuenta verificada. Podés volver al chat; continúo desde acá.", True) if connected else page())

    def do_POST(self):
        global connected
        expected_origin = f"http://127.0.0.1:{self.server.server_port}"
        if not self.valid_host() or self.path != "/connect":
            return self.respond(403, b"Forbidden")
        if connected:
            return self.respond(200, page("La cuenta ya está conectada. Podés volver al chat.", True))
        if self.headers.get("Origin") != expected_origin:
            return self.respond(403, page("La pestaña tenía una configuración anterior. Esta página ya se actualizó: pegá el bloque vigente y volvé a conectar."))
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 32768:
                return self.respond(413, b"Invalid size")
            data = parse_qs(self.rfile.read(size).decode(), strict_parsing=True)
            if not secrets.compare_digest(data.get("csrf", [""])[0], CSRF):
                return self.respond(403, page("El formulario venció al reiniciar el asistente. Pegá el bloque vigente en este formulario nuevo."))
            validate_and_save(data.get("block", [""])[0])
        except (ValueError, configparser.Error):
            return self.respond(400, page("No se pudo verificar el bloque: comprobá que esté completo, vigente y sea del Learner Lab de PATAPORTE."))
        except Exception:
            return self.respond(503, page("No se pudo verificar con AWS. Revisá que Start Lab haya terminado y volvé a intentarlo."))
        connected = True
        self.respond(200, page("Cuenta verificada. Podés volver al chat; continúo desde acá.", True))
        print("LAB_PROFILE_READY account=" + ACCOUNT, flush=True)
        threading.Timer(30, self.server.shutdown).start()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8767), Handler)
    print("LAB_SETUP_URL=http://127.0.0.1:8767/", flush=True)
    server.serve_forever()
