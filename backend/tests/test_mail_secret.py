import json
import unittest
from unittest.mock import Mock, patch
from config import mail


class MailSecretTests(unittest.TestCase):
    def setUp(self):
        self.config = mail.MailSettings(_env_file=None, ENVIRONMENT="production", MAIL_DELIVERY_ENABLED=True,
                                       MAIL_SECRET_ARN="arn:aws:secretsmanager:us-east-1:476855088538:secret:fictional")
        self.payload = {"MAIL_HOST": "smtp.example.com", "MAIL_FROM": "fictional@example.com", "MAIL_PASSWORD": "fictional-secret", "MAIL_SSL": True}

    def test_secret_is_validated_cached_and_does_not_replace_environment(self):
        client = Mock()
        client.get_secret_value.return_value = {"SecretString": json.dumps(self.payload)}
        with patch.object(mail, "mail_settings", self.config), patch.object(mail, "_secret_cache", None), \
             patch("boto3.client", return_value=client):
            first = mail.get_mail_settings()
            self.assertIs(first, mail.get_mail_settings())
            self.assertEqual(first.MAIL_HOST, "smtp.example.com")
            self.assertEqual(first.ENVIRONMENT, "production")
            client.get_secret_value.assert_called_once_with(SecretId=self.config.MAIL_SECRET_ARN)

    def test_secret_cannot_disable_tls_by_changing_environment(self):
        for extra in [{"ENVIRONMENT": "development"}, {"MAIL_SSL": False, "MAIL_STARTTLS": False}]:
            with self.subTest(extra=extra):
                client = Mock()
                client.get_secret_value.return_value = {"SecretString": json.dumps({**self.payload, **extra})}
                with patch.object(mail, "mail_settings", self.config), patch.object(mail, "_secret_cache", None), \
                     patch("boto3.client", return_value=client), self.assertRaises(RuntimeError) as error:
                    mail.get_mail_settings()
                self.assertNotIn("fictional-secret", str(error.exception))

    def test_disabled_delivery_does_not_fetch_credentials(self):
        self.config.MAIL_DELIVERY_ENABLED = False
        with patch.object(mail, "mail_settings", self.config), patch("boto3.client") as client:
            self.assertIs(mail.get_mail_settings(), self.config)
        client.assert_not_called()

    def test_bad_secret_is_not_retained_in_errors(self):
        client = Mock()
        client.get_secret_value.side_effect = ValueError("fictional-secret")
        with patch.object(mail, "mail_settings", self.config), patch.object(mail, "_secret_cache", None), \
             patch("boto3.client", return_value=client), self.assertRaises(RuntimeError) as error:
            mail.get_mail_settings()
        self.assertNotIn("fictional-secret", str(error.exception))
