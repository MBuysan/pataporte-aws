import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from messaging import consumer
from utils.email import enviar_email


class MessagingTests(unittest.TestCase):
    def test_success_is_acknowledged(self):
        channel = Mock()
        with patch.object(consumer, "procesar"):
            consumer.callback(channel, SimpleNamespace(delivery_tag=1), None, b"{}")
        channel.basic_ack.assert_called_once_with(delivery_tag=1)
        channel.basic_nack.assert_not_called()

    def test_smtp_failure_is_not_acknowledged_as_sent(self):
        channel = Mock()
        with patch.object(consumer, "procesar", side_effect=OSError("SMTP offline")):
            consumer.callback(channel, SimpleNamespace(delivery_tag=2), None, b"{}")
        channel.basic_ack.assert_not_called()
        channel.basic_nack.assert_called_once_with(delivery_tag=2, requeue=False)

    def test_recovery_selects_the_recovery_template(self):
        with patch.object(consumer, "_enviar_email_recuperacion") as recovery, patch.object(consumer, "_enviar_email_verificacion") as verification:
            consumer.procesar({"tipo": "recuperacion_password", "email": "prueba@example.com", "codigo": "ABCDEF"})
        recovery.assert_called_once_with("prueba@example.com", "ABCDEF")
        verification.assert_not_called()

    def test_unknown_message_cannot_be_silently_discarded(self):
        with self.assertRaises(ValueError):
            consumer.procesar({"tipo": "desconocido"})

    def test_smtp_rejection_propagates(self):
        config = SimpleNamespace(
            MAIL_SSL=False, MAIL_STARTTLS=False, ENVIRONMENT="development",
            MAIL_HOST="mailpit", MAIL_PORT=1025, MAIL_TIMEOUT=5, MAIL_USERNAME="",
            MAIL_FROM="pataporte@example.com",
        )
        with patch("utils.email.settings", config), patch("utils.email.smtplib.SMTP") as smtp:
            smtp.return_value.__enter__.return_value.sendmail.return_value = {"prueba@example.com": (550, b"rejected")}
            with self.assertRaises(RuntimeError):
                enviar_email("prueba@example.com", Mock())

    def test_unencrypted_smtp_is_rejected_outside_development(self):
        config = SimpleNamespace(MAIL_SSL=False, MAIL_STARTTLS=False, ENVIRONMENT="production")
        with patch("utils.email.settings", config), self.assertRaises(ValueError):
            enviar_email("prueba@example.com", Mock())
