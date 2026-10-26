"""Pruebas reales contra Compose y el buzón Mailpit; solo datos ficticios."""
import email
from email import policy
import json
import os
import re
import secrets
import time
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4
from datetime import date

BASE = os.getenv("PATAPORTE_BASE_URL", "http://127.0.0.1:8085/api")
MAIL = os.getenv("PATAPORTE_MAIL_URL", "http://127.0.0.1:8025")


def request(path, method="GET", data=None, token=None, form=False):
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = None
    if data is not None:
        body = urlencode(data).encode() if form else json.dumps(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
    try:
        with urlopen(Request(BASE + path, data=body, headers=headers, method=method), timeout=15) as response:
            content = response.read()
            return response.status, json.loads(content) if content else None
    except HTTPError as error:
        return error.code, json.loads(error.read())


def document_number(weights):
    digits = "".join(str(secrets.randbelow(10)) for _ in weights)
    return digits + str((10 - sum(int(n) * w for n, w in zip(digits, weights)) % 10) % 10)


def wait_mail(address, subject=""):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        with urlopen(MAIL + "/api/v1/messages", timeout=5) as response:
            messages = json.load(response).get("messages", [])
        for item in messages:
            recipients = [recipient["Address"] for recipient in item.get("To", [])]
            if address in recipients and subject.lower() in item["Subject"].lower():
                with urlopen(MAIL + "/api/v1/message/" + item["ID"], timeout=5) as response:
                    return json.load(response)
        time.sleep(0.2)
    raise AssertionError("No llegó al buzón de prueba el correo esperado")


def register(kind):
    address = kind + "-" + uuid4().hex + "@example.com"
    password = "PruebaLocal1!"
    data = {"nombre": "Persona de prueba", "email": address, "password": password}
    if kind == "tutor":
        data["cedula"] = document_number([2, 9, 8, 7, 6, 3, 4])
        path = "/tutores/"
    else:
        data.update(rut_organizacion=document_number([4, 3, 2, 9, 8, 7, 6, 3, 4, 5, 2]), matricula=uuid4().hex)
        path = "/veterinarios/"
    status, account = request(path, "POST", data)
    if status != 201:
        raise AssertionError("Falló el registro de prueba: " + str(status))
    message = wait_mail(address)
    code = re.search(r"\b[A-Z0-9]{6}\b", message["Text"]).group()
    status, _ = request("/auth/verificar-email", "POST", {"email": address, "tipo_usuario": kind, "codigo": "123456"})
    if status != 400:
        raise AssertionError("Un código no recibido permitió verificar la cuenta")
    status, session = request("/auth/verificar-email", "POST", {"email": address, "tipo_usuario": kind, "codigo": code})
    if status != 200:
        raise AssertionError("No se pudo verificar el código real: " + str(status))
    return {"email": address, "password": password, "account": account, "session": session, "code": code}


@unittest.skipUnless(os.getenv("PATAPORTE_RUN_INTEGRATION") == "1", "Ejecutar con scripts/check_local.py y Compose iniciado")
class LocalFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tutor = register("tutor")
        cls.other = register("tutor")
        cls.vet = register("veterinario")
        cls.token = cls.tutor["session"]["access_token"]
        cls.other_token = cls.other["session"]["access_token"]
        cls.vet_token = cls.vet["session"]["access_token"]
        cls.tutor_id = cls.tutor["account"]["id_tutor"]
        status, cls.pet = request("/mascotas/", "POST", {
            "id_tutor": cls.tutor_id, "nombre": "Luna " + uuid4().hex[:6],
            "especie": "perro", "sexo": "hembra", "fecha_de_nacimiento": "2023-01-01",
        }, cls.token, form=True)
        if status != 201:
            raise AssertionError("Falló la creación de mascota: " + str(status))

    def test_health_and_same_origin(self):
        self.assertEqual(request("/health/live")[0], 200)
        self.assertEqual(request("/health/ready")[0], 200)

    def test_login_and_wrong_password(self):
        self.assertEqual(request("/auth/login", "POST", {
            "identificador": self.tutor["email"], "password": "incorrecta",
        })[0], 401)
        status, result = request("/auth/login", "POST", {
            "identificador": self.tutor["email"], "password": self.tutor["password"],
        })
        self.assertEqual(status, 200)
        self.assertIn("access_token", result)

    def test_verification_code_cannot_be_reused(self):
        self.assertEqual(request("/auth/verificar-email", "POST", {
            "email": self.tutor["email"], "tipo_usuario": "tutor", "codigo": self.tutor["code"],
        })[0], 400)

    def test_anonymous_and_other_tutor_are_denied(self):
        pet_id = self.pet["id_mascota"]
        for path in ["/mascotas/" + pet_id, "/historial/" + pet_id + "/unificado",
                     "/tratamientos/" + pet_id, "/vacunas/" + pet_id + "/carnet",
                     "/tutores/" + self.tutor_id]:
            with self.subTest(path=path):
                self.assertIn(request(path)[0], (401, 403))
                self.assertEqual(request(path, token=self.other_token)[0], 403)

    def test_cannot_create_pet_for_another_tutor(self):
        status, _ = request("/mascotas/", "POST", {
            "id_tutor": self.tutor_id, "nombre": "No permitido", "especie": "gato",
        }, self.other_token, form=True)
        self.assertEqual(status, 403)

    def test_listing_only_returns_own_pets(self):
        status, pets = request("/mascotas/", token=self.other_token)
        self.assertEqual(status, 200)
        self.assertNotIn(self.pet["id_mascota"], [pet["id_mascota"] for pet in pets])

    def test_tutor_cannot_write_clinical_records(self):
        self.assertEqual(request("/historial/consultas", "POST", {
            "id_mascota": self.pet["id_mascota"], "motivo": "No permitido",
        }, self.token)[0], 403)
        self.assertEqual(request("/tratamientos/" + self.pet["id_mascota"], "POST", {
            "nombre": "No permitido",
        }, self.token)[0], 403)

    def test_consultation_vaccine_certificate_and_pdf(self):
        pet_id = self.pet["id_mascota"]
        self.assertEqual(request("/vacunas/" + pet_id + "/carnet", token=self.vet_token)[0], 200)
        status, types = request("/vacunas/tipos?especie=perro", token=self.vet_token)
        self.assertEqual(status, 200)
        vaccine_id = types[0]["id_vacuna"]
        status, consultation = request("/historial/consultas", "POST", {
            "id_mascota": pet_id, "motivo": "Control de prueba", "diagnostico": "Prueba automatizada",
            "nuevas_vacunas": [vaccine_id],
            "dosis": [{"id_vacuna_nueva": vaccine_id, "fecha_aplicacion": date.today().isoformat()}],
        }, self.vet_token)
        self.assertEqual(status, 201)
        status, detail = request("/historial/" + pet_id + "/detalle/" + consultation["id_consulta"], token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(len(detail["dosis"]), 1)
        status, certificate = request("/pataporte/" + pet_id, "POST", token=self.token)
        self.assertEqual(status, 201)
        path = "/pataporte/verificar/" + certificate["hash_verificacion"]
        status, verified = request(path, token=self.token)
        self.assertEqual(status, 200)
        self.assertTrue(verified["valido"])
        self.assertEqual(request(path, token=self.other_token)[0], 403)
        message = wait_mail(self.tutor["email"], "Pataporte de vacunación")
        with urlopen(MAIL + "/api/v1/message/" + message["ID"] + "/raw", timeout=5) as response:
            parsed = email.message_from_bytes(response.read(), policy=policy.default)
        attachments = list(parsed.iter_attachments())
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].get_content_type(), "application/pdf")
        self.assertTrue(attachments[0].get_payload(decode=True).startswith(b"%PDF"))

    def test_recovery_uses_its_template_and_code_is_single_use(self):
        status, _ = request("/auth/recuperar", "POST", {"email": self.other["email"]})
        self.assertEqual(status, 200)
        message = wait_mail(self.other["email"], "recuper")
        code = re.search(r"\b[A-Z0-9]{6}\b", message["Text"]).group()
        payload = {"codigo": code, "nueva_password": "NuevaLocal2!", "confirmar_password": "NuevaLocal2!"}
        self.assertEqual(request("/auth/reset", "POST", payload)[0], 200)
        self.assertEqual(request("/auth/reset", "POST", payload)[0], 400)
        self.assertEqual(request("/auth/login", "POST", {
            "identificador": self.other["email"], "password": "NuevaLocal2!",
        })[0], 200)

    def test_veterinarian_response_does_not_expose_password_hash(self):
        status, account = request("/veterinarios/" + self.vet["account"]["id_veterinario"], token=self.vet_token)
        self.assertEqual(status, 200)
        self.assertNotIn("password_hash", account)
