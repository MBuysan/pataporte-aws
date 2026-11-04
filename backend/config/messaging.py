"""Configuración del broker sin exigir JWT ni credenciales SMTP."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class MessagingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    AWS_REGION: str = "us-east-1"
    MESSAGE_TRANSPORT: str = "rabbitmq"
    SQS_QUEUE_URL: str = ""
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"


messaging_settings = MessagingSettings()
