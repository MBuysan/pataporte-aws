"""Configuración de entrega independiente de las credenciales de la API y la base."""
import json
import time
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class MailSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    ENVIRONMENT: str = "production"
    MAIL_DELIVERY_ENABLED: bool = True
    MAIL_SECRET_ARN: str = ""
    MAIL_FROM: str = "noreply@example.invalid"
    MAIL_HOST: str = "not-configured.invalid"
    MAIL_PORT: int = 465
    MAIL_SSL: bool = True
    MAIL_STARTTLS: bool = False
    MAIL_TIMEOUT: int = 10
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: SecretStr = SecretStr("")


mail_settings = MailSettings()
_secret_cache = None


def get_mail_settings():
    """Leer el secreto en runtime; su valor nunca queda en el template ni en los logs."""
    global _secret_cache
    if not mail_settings.MAIL_DELIVERY_ENABLED or not mail_settings.MAIL_SECRET_ARN:
        return mail_settings
    now = time.monotonic()
    if _secret_cache and _secret_cache[0] == mail_settings.MAIL_SECRET_ARN and _secret_cache[1] > now:
        return _secret_cache[2]
    import boto3
    from botocore.config import Config
    try:
        response = boto3.client("secretsmanager", config=Config(connect_timeout=3, read_timeout=10,
                                retries={"max_attempts": 2})).get_secret_value(SecretId=mail_settings.MAIL_SECRET_ARN)
        secret = json.loads(response["SecretString"])
        allowed = {"MAIL_HOST", "MAIL_PORT", "MAIL_FROM", "MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_SSL", "MAIL_STARTTLS", "MAIL_TIMEOUT"}
        if not isinstance(secret, dict) or set(secret) - allowed or not {"MAIL_HOST", "MAIL_FROM"}.issubset(secret):
            raise ValueError("Invalid mail secret")
        config = MailSettings.model_validate({**mail_settings.model_dump(), **secret})
        if config.ENVIRONMENT != "development" and not (config.MAIL_SSL ^ config.MAIL_STARTTLS):
            raise ValueError("Mail requires one TLS mode")
        if not 1 <= config.MAIL_PORT <= 65535 or not 1 <= config.MAIL_TIMEOUT <= 30:
            raise ValueError("Mail bounds invalid")
        if any(character in config.MAIL_FROM + config.MAIL_HOST for character in "\r\n"):
            raise ValueError("Mail headers invalid")
    except Exception:
        raise RuntimeError("No se pudo cargar una configuración SMTP válida") from None
    _secret_cache = (mail_settings.MAIL_SECRET_ARN, now + 300, config)
    return config
