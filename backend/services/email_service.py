import smtplib

from config.settings import settings


def enviar(mensaje):
    """Envía un email ya armado (MIME). Solo lo usa el worker; si falla, la excepción sube para reintentar."""
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as servidor:
        servidor.starttls()
        servidor.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        servidor.send_message(mensaje)
