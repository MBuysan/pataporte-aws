from config.db_connection import DatabaseSettings


class Settings(DatabaseSettings):
    AWS_REGION: str = "us-east-1"
    STORAGE_BACKEND: str = "local"
    ASSETS_BUCKET: str = ""
    PHOTO_MAX_BYTES: int = 5 * 1024 * 1024
    MESSAGE_TRANSPORT: str = "rabbitmq"
    SQS_QUEUE_URL: str = ""
    IDEMPOTENCY_TABLE: str = ""
    MAIL_DELIVERY_ENABLED: bool = True
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str
    MAIL_HOST: str = "smtp.gmail.com"
    MAIL_PORT: int = 465
    MAIL_SSL: bool = True
    MAIL_STARTTLS: bool = False
    MAIL_TIMEOUT: int = 10

    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"

settings = Settings()
