import unittest
from unittest.mock import patch
from messaging.delivery import _generar_pdf


class DeliveryTests(unittest.TestCase):
    def test_names_are_text_and_cannot_load_external_images_in_pdf(self):
        credential = {"issuanceDate": "2026-11-03T00:00:00Z", "credentialSubject": {
            "nombre": 'Luna <img src="https://example.invalid/should-never-load.png"/> & Sol',
            "especie": "perro", "tutor": {"nombre": "A < B & C"},
            "vacunas": [{"nombre": "Vacuna <prueba>", "descripcion": "Dosis A & B", "esquema_completo": False}]}}
        with patch("reportlab.platypus.paraparser.ImageReader", side_effect=AssertionError("PDF must not interpret user input as an image")):
            pdf = _generar_pdf(credential, "f" * 64)
        self.assertTrue(pdf.startswith(b"%PDF-"))
