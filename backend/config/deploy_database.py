"""One-off deployment: migrate, grant runtime DML and verify using that account.

Passwords arrive through ECS Secrets, are never printed, and existing passwords
are never reset. The write probe uses a synthetic row and rolls back its transaction.
"""
import json
import os
import uuid

from psycopg2 import sql
from sqlalchemy import create_engine, inspect, text

from config.db_connection import DatabaseSettings
from config.migrate import MIGRATION_LOCK, assert_schema_current, migrate_database
from config.models import Base


def provision_runtime_account(engine, username, password):
    if not username.startswith("pataporte_") or len(username) > 63:
        raise ValueError("El usuario de aplicación debe tener prefijo pataporte_ y hasta 63 caracteres")
    if username == engine.url.username or len(password) < 32:
        raise ValueError("Usar una cuenta distinta del administrador y una contraseña generada de 32+ caracteres")
    raw = engine.raw_connection()
    try:
        with raw.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", (MIGRATION_LOCK + 1,))
            cursor.execute("SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls FROM pg_roles WHERE rolname=%s", (username,))
            attributes = cursor.fetchone()
            if attributes is None:
                cursor.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS").format(sql.Identifier(username), sql.Literal(password)))
            elif attributes != (True, False, False, False, False, False):
                raise RuntimeError("La cuenta existente tiene atributos inesperados; no se modificaron")
            role = sql.Identifier(username)
            database = sql.Identifier(engine.url.database)
            cursor.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(database, role))
            cursor.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
            cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
            cursor.execute(sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}").format(role))
            cursor.execute(sql.SQL("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}").format(role))
            cursor.execute(sql.SQL("REVOKE INSERT, UPDATE, DELETE ON public.alembic_version FROM {}").format(role))
            cursor.execute(sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}").format(role))
            cursor.execute(sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {}").format(role))
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def verify_runtime(engine, require_tls=False):
    assert_schema_current(engine)
    probe_id = str(uuid.uuid4())
    tutor = Base.metadata.tables["usuario_tutor"]
    with engine.connect() as connection:
        version = connection.scalar(text("SELECT version_num FROM alembic_version"))
        tables = set(inspect(connection).get_table_names()) - {"alembic_version"}
        if tables != set(Base.metadata.tables):
            raise RuntimeError("Las tablas instaladas no coinciden con el modelo")
        vaccines = connection.scalar(text("SELECT count(*) FROM tipo_vacunas"))
        if vaccines < 5:
            raise RuntimeError("Falta el catálogo inicial de vacunas")
        tls = connection.execute(text("SELECT ssl, version, cipher FROM pg_stat_ssl WHERE pid=pg_backend_pid()")).mappings().one()
        if require_tls and not tls["ssl"]:
            raise RuntimeError("La conexión real a PostgreSQL no usa TLS")
        privileges = connection.execute(text("SELECT has_schema_privilege(current_user,'public','CREATE') AS schema_create, has_database_privilege(current_user,current_database(),'CREATE') AS database_create, has_table_privilege(current_user,'alembic_version','UPDATE') AS migration_update")).mappings().one()
        if any(privileges.values()):
            raise RuntimeError("La cuenta de aplicación tiene permisos de administración inesperados")
        connection.rollback()
        transaction = connection.begin()
        try:
            connection.execute(tutor.insert().values(id_tutor=probe_id, cedula="PROBE-" + probe_id[:12], nombre="Prueba efímera de despliegue", email=probe_id + "@example.invalid", password_hash="not-an-authentication-credential"))
            connection.execute(tutor.update().where(tutor.c.id_tutor == probe_id).values(nombre="Prueba actualizada"))
            if connection.scalar(tutor.select().with_only_columns(tutor.c.nombre).where(tutor.c.id_tutor == probe_id)) != "Prueba actualizada":
                raise RuntimeError("Falló la prueba de escritura y lectura")
            connection.execute(tutor.delete().where(tutor.c.id_tutor == probe_id))
        finally:
            transaction.rollback()
        if connection.scalar(text("SELECT count(*) FROM usuario_tutor WHERE id_tutor=:id"), {"id": probe_id}):
            raise RuntimeError("La prueba dejó datos persistidos")
    return {"revision": version, "application_tables": len(tables), "vaccines": vaccines,
            "tls": dict(tls), "administrative_privileges": dict(privileges),
            "runtime_crud": "passed", "probe_data_retained": False}


def main():
    settings = DatabaseSettings()
    username = os.environ["APP_DB_USER"]
    password = os.environ["APP_DB_PASSWORD"]
    kwargs = {"pool_pre_ping": True, "hide_parameters": True,
              "connect_args": settings.database_connect_args()}
    admin = create_engine(settings.sqlalchemy_url(), **kwargs)
    runtime = create_engine(settings.sqlalchemy_url().set(username=username, password=password), **kwargs)
    try:
        migrate_database(admin)
        provision_runtime_account(admin, username, password)
        result = verify_runtime(runtime, require_tls=settings.ENVIRONMENT not in {"development", "test"})
        print("PATAPORTE_MIGRATION_RESULT=" + json.dumps(result), flush=True)
    finally:
        runtime.dispose()
        admin.dispose()


if __name__ == "__main__":
    main()
