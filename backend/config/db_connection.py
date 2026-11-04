"""Configuración de PostgreSQL compartida por API, Alembic y tareas de migración."""
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


class DatabaseSettings(BaseSettings):
    DATABASE_URL: SecretStr | None = None
    DB_HOST: str | None = None
    DB_PORT: int = 5432
    DB_NAME: str = "pataporte"
    DB_USER: str | None = None
    DB_PASSWORD: SecretStr | None = None
    DATABASE_SSLMODE: str = "prefer"
    DATABASE_SSLROOTCERT: str | None = None
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def sqlalchemy_url(self) -> URL:
        if self.DATABASE_URL:
            url = make_url(self.DATABASE_URL.get_secret_value())
        else:
            if not self.DB_HOST or not self.DB_USER or not self.DB_PASSWORD:
                raise ValueError("Configurar DATABASE_URL o DB_HOST/DB_USER/DB_PASSWORD")
            url = URL.create(
                "postgresql+psycopg2", username=self.DB_USER,
                password=self.DB_PASSWORD.get_secret_value(), host=self.DB_HOST,
                port=self.DB_PORT, database=self.DB_NAME,
            )
        if url.get_backend_name() != "postgresql":
            raise ValueError("PATAPORTE requiere PostgreSQL")
        return url

    def database_connect_args(self) -> dict:
        url = self.sqlalchemy_url()
        mode = url.query.get("sslmode", self.DATABASE_SSLMODE)
        rootcert = url.query.get("sslrootcert", self.DATABASE_SSLROOTCERT)
        if mode not in {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}:
            raise ValueError("DATABASE_SSLMODE inválido")
        if self.ENVIRONMENT not in {"development", "test"} and mode != "verify-full":
            raise ValueError("Fuera de desarrollo/pruebas PostgreSQL requiere sslmode=verify-full")
        if mode in {"verify-ca", "verify-full"}:
            if not rootcert or not Path(rootcert).is_file():
                raise ValueError("Configurar DATABASE_SSLROOTCERT con un certificado CA existente")
        result = {"connect_timeout": 5, "sslmode": mode}
        if rootcert:
            result["sslrootcert"] = rootcert
        return result
