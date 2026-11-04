"""Migración explícita. Un esquema previo solo se adopta si coincide con el baseline."""
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import MetaData, create_engine, inspect, text

from config.db_connection import DatabaseSettings
from config.models import Base

BASELINE_REVISION = "0001_initial_schema"
MIGRATION_LOCK = 734128901


def baseline_metadata():
    """Tablas anteriores a Alembic; el outbox se agrega con la revisión 0003."""
    metadata = MetaData()
    for table in Base.metadata.sorted_tables:
        if table.name != "outbox_events":
            table.to_metadata(metadata)
    return metadata


def alembic_config():
    return Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))


def assert_schema_current(engine):
    expected = ScriptDirectory.from_config(alembic_config()).get_current_head()
    with engine.connect() as connection:
        installed = MigrationContext.configure(connection).get_current_heads()
    if installed != (expected,):
        raise RuntimeError("Esquema desactualizado: ejecutar la tarea python -m config.migrate antes de iniciar la API")


def migrate_database(engine=None):
    own_engine = engine is None
    if own_engine:
        settings = DatabaseSettings()
        engine = create_engine(settings.sqlalchemy_url(), pool_pre_ping=True,
                               connect_args=settings.database_connect_args())
    try:
        with engine.connect() as connection:
            acquired = connection.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": MIGRATION_LOCK}).scalar_one()
            connection.commit()
            if not acquired:
                raise RuntimeError("Otra tarea ya está migrando esta base; reintentar cuando termine")
            try:
                cfg = alembic_config()
                cfg.attributes["connection"] = connection
                tables = set(inspect(connection).get_table_names())
                installed = MigrationContext.configure(connection).get_current_heads()
                if not installed and tables - {"alembic_version"}:
                    context = MigrationContext.configure(connection, opts={"compare_type": True})
                    baseline = baseline_metadata()
                    differences = compare_metadata(context, baseline)
                    if tables - {"alembic_version"} != set(baseline.tables) or differences:
                        raise RuntimeError("El esquema previo no coincide con el baseline. No se marcó una versión ni se modificaron sus datos; revisar diferencias y preparar una migración específica")
                    connection.commit()
                    command.stamp(cfg, BASELINE_REVISION)
                else:
                    connection.commit()
                command.upgrade(cfg, "head")
                print("Migraciones aplicadas; esquema actualizado")
            finally:
                connection.rollback()
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK})
                connection.commit()
    finally:
        if own_engine:
            engine.dispose()


if __name__ == "__main__":
    migrate_database()
