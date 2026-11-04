"""
Aplica las migraciones de Alembic (esquema + seed de vacunas). Es idempotente.
Se corre como tarea one-off antes de cada deploy:  python -m scripts.init_db
"""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from config.database import engine

ALEMBIC_INI = Path(__file__).resolve().parents[1] / "alembic.ini"


def init_db():
    cfg = Config(str(ALEMBIC_INI))
    tablas = inspect(engine).get_table_names()
    if "usuario_tutor" in tablas and "alembic_version" not in tablas:
        # ponytail: base creada antes con create_all desde los mismos modelos = revisión 0001.
        # Se marca sin comparar; si alguien la tocó a mano, revisar con `alembic check`.
        command.stamp(cfg, "0001")
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    init_db()
    print("init_db: migraciones OK")
