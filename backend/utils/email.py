"""SMTP configurable para desarrollo y proveedores externos."""
import smtplib
import ssl
from config.mail import mail_settings as settings, get_mail_settings


def enviar_email(destinatario: str, mensaje) -> None:
    config = get_mail_settings() if getattr(settings, "MAIL_SECRET_ARN", "") else settings
    if not getattr(config, "MAIL_DELIVERY_ENABLED", True):
        raise RuntimeError("La entrega de correo todavía no está habilitada")
    if config.MAIL_SSL and config.MAIL_STARTTLS:
        raise ValueError("MAIL_SSL y MAIL_STARTTLS son excluyentes")
    if config.ENVIRONMENT != "development" and not (
        config.MAIL_SSL or config.MAIL_STARTTLS
    ):
        raise ValueError("El correo fuera de desarrollo requiere TLS")
    smtp = smtplib.SMTP_SSL if config.MAIL_SSL else smtplib.SMTP
    options = {"timeout": config.MAIL_TIMEOUT}
    if config.MAIL_SSL:
        options["context"] = ssl.create_default_context()
    with smtp(config.MAIL_HOST, config.MAIL_PORT, **options) as server:
        if config.MAIL_STARTTLS:
            server.starttls(context=ssl.create_default_context())
        if config.MAIL_USERNAME:
            password = config.MAIL_PASSWORD.get_secret_value() if hasattr(config.MAIL_PASSWORD, "get_secret_value") else config.MAIL_PASSWORD
            server.login(config.MAIL_USERNAME, password)
        if mensaje.get("From"):
            mensaje.replace_header("From", config.MAIL_FROM)
        else:
            mensaje["From"] = config.MAIL_FROM
        rejected = server.sendmail(config.MAIL_FROM, destinatario, mensaje.as_string())
        if rejected:
            raise RuntimeError("El servidor rechazó el destinatario")
