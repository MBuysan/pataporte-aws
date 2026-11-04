"""
Aplica las migraciones de Alembic (esquema + seed de vacunas) y, si viene
APP_DB_PASSWORD, crea/actualiza el usuario de la app con permisos solo DML. Es idempotente.
Se corre como tarea one-off (con el usuario maestro) antes de cada deploy:  python -m scripts.init_db
"""
from pathlib import Path

from alembic import command
from alembic.config import Config
from psycopg2 import sql
from sqlalchemy import inspect

from config.database import engine
from config.settings import settings

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def migrar():
    cfg = Config(str(ALEMBIC_INI))
    tablas = inspect(engine).get_table_names()
    if "usuario_tutor" in tablas and "alembic_version" not in tablas:
        # ponytail: base creada antes con create_all desde los mismos modelos = revisión 0001.
        # Se marca sin comparar; si alguien la tocó a mano, revisar con `alembic check`.
        command.stamp(cfg, "0001")
    command.upgrade(cfg, "head")


def usuario_app(usuario: str, password: str):
    """Usuario de runtime (API y worker): lee y escribe datos, no cambia el esquema."""
    rol = sql.Identifier(usuario)
    base = sql.Identifier(engine.url.database)
    crudo = engine.raw_connection()
    try:
        with crudo.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (usuario,))
            accion = "ALTER" if cur.fetchone() else "CREATE"
            cur.execute(sql.SQL(accion + " ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE")
                        .format(rol, sql.Literal(password)))
            for sentencia in (
                "GRANT CONNECT ON DATABASE {base} TO {rol}",
                "REVOKE CREATE ON SCHEMA public FROM PUBLIC",
                "GRANT USAGE ON SCHEMA public TO {rol}",
                "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {rol}",
                "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {rol}",
                "REVOKE INSERT, UPDATE, DELETE ON alembic_version FROM {rol}",
                # tablas que creen migraciones futuras (las corre este mismo usuario maestro)
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {rol}",
                "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {rol}",
            ):
                cur.execute(sql.SQL(sentencia).format(base=base, rol=rol))
        crudo.commit()
    finally:
        crudo.close()


def init_db():
    migrar()
    # ponytail: en local (docker compose) no se setea APP_DB_PASSWORD y todo usa un solo usuario
    if settings.APP_DB_PASSWORD:
        usuario_app(settings.APP_DB_USER, settings.APP_DB_PASSWORD)


if __name__ == "__main__":
    init_db()
    print("init_db: migraciones OK")
