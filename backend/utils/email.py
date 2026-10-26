"""SMTP configurable para desarrollo y proveedores externos."""
import smtplib
import ssl
from config.settings import settings


def enviar_email(destinatario: str, mensaje) -> None:
    if settings.MAIL_SSL and settings.MAIL_STARTTLS:
        raise ValueError("MAIL_SSL y MAIL_STARTTLS son excluyentes")
    if settings.ENVIRONMENT != "development" and not (
        settings.MAIL_SSL or settings.MAIL_STARTTLS
    ):
        raise ValueError("El correo fuera de desarrollo requiere TLS")
    smtp = smtplib.SMTP_SSL if settings.MAIL_SSL else smtplib.SMTP
    options = {"timeout": settings.MAIL_TIMEOUT}
    if settings.MAIL_SSL:
        options["context"] = ssl.create_default_context()
    with smtp(settings.MAIL_HOST, settings.MAIL_PORT, **options) as server:
        if settings.MAIL_STARTTLS:
            server.starttls(context=ssl.create_default_context())
        if settings.MAIL_USERNAME:
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        rejected = server.sendmail(settings.MAIL_FROM, destinatario, mensaje.as_string())
        if rejected:
            raise RuntimeError("El servidor rechazó el destinatario")
