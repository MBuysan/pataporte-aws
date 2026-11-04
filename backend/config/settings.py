from pathlib import Path
from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # DATABASE_URL tiene prioridad; si no viene, se arma con las partes DB_*
    DATABASE_URL: str | None = None
    DB_HOST: str | None = None
    DB_PORT: int = 5432
    DB_NAME: str | None = None
    DB_USER: str | None = None
    DB_PASSWORD: str | None = None
    # TLS hacia RDS: en AWS DB_SSLMODE=verify-full; vacío = lo que diga libpq (Postgres local sin TLS)
    DB_SSLMODE: str = ""
    DB_SSLROOTCERT: str = str(Path(__file__).resolve().parents[1] / "certs" / "us-east-1-bundle.pem")
    # solo la tarea init_db: crea/actualiza el usuario de la app (DML) con esta contraseña
    APP_DB_USER: str = "pataporte_app"
    APP_DB_PASSWORD: str = ""

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost,http://localhost:3000,http://127.0.0.1,http://127.0.0.1:3000"

    # solo los usa el worker para enviar correos
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587

    AWS_REGION: str = "us-east-1"
    UPLOADS_BUCKET: str = ""
    QUEUE_URL: str = ""
    EVENT_BUS_NAME: str = ""
    # tabla DynamoDB de entregas ya procesadas por el worker (vacío = sin deduplicar)
    DEDUP_TABLE: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

    @model_validator(mode="after")
    def _armar_database_url(self):
        if not self.DATABASE_URL:
            if not all([self.DB_HOST, self.DB_NAME, self.DB_USER, self.DB_PASSWORD]):
                raise ValueError("Falta DATABASE_URL o DB_HOST/DB_NAME/DB_USER/DB_PASSWORD")
            self.DATABASE_URL = (
                f"postgresql://{quote_plus(self.DB_USER)}:{quote_plus(self.DB_PASSWORD)}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            )
        return self


settings = Settings()
