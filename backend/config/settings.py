from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ENVIRONMENT: str = "development"
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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
