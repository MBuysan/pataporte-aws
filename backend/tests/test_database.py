import os
import secrets
from pathlib import Path
import unittest
import uuid

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from config.db_connection import DatabaseSettings
from config.migrate import MIGRATION_LOCK, alembic_config, assert_schema_current, migrate_database, baseline_metadata
from config.models import Base
from config.deploy_database import provision_runtime_account, verify_runtime


class ConnectionConfigurationTests(unittest.TestCase):
    def test_separate_fields_preserve_password_special_characters(self):
        config = DatabaseSettings(_env_file=None, DATABASE_URL=None, DB_HOST="db",
                                  DB_USER="pataporte", DB_PASSWORD="fictional:@/%+# password")
        url = config.sqlalchemy_url()
        self.assertEqual(url.password, "fictional:@/%+# password")
        self.assertNotIn("fictional", str(url))

    def test_production_rejects_unverified_tls_even_inside_url(self):
        config = DatabaseSettings(_env_file=None, DATABASE_URL="postgresql://u:p@db/app?sslmode=disable",
                                  ENVIRONMENT="production", DATABASE_SSLMODE="verify-full")
        with self.assertRaisesRegex(ValueError, "verify-full"):
            config.database_connect_args()

    def test_verified_tls_requires_an_existing_ca_file(self):
        config = DatabaseSettings(_env_file=None, DATABASE_URL="postgresql://u:p@db/app",
                                  ENVIRONMENT="production", DATABASE_SSLMODE="verify-full",
                                  DATABASE_SSLROOTCERT="/missing/pataporte-ca.pem")
        with self.assertRaisesRegex(ValueError, "certificado CA"):
            config.database_connect_args()

    def test_rds_ca_is_available_for_production(self):
        cert = Path(__file__).resolve().parents[1] / "certs" / "us-east-1-bundle.pem"
        config = DatabaseSettings(_env_file=None, DATABASE_URL="postgresql://u:p@db/app",
                                  ENVIRONMENT="production", DATABASE_SSLMODE="verify-full",
                                  DATABASE_SSLROOTCERT=str(cert))
        self.assertEqual(config.database_connect_args()["sslmode"], "verify-full")


@unittest.skipUnless(os.getenv("PATAPORTE_RUN_MIGRATION_TESTS") == "1", "Requiere PostgreSQL local y habilitación explícita")
class MigrationTests(unittest.TestCase):
    def setUp(self):
        config = DatabaseSettings()
        url = config.sqlalchemy_url()
        if url.host not in {"db", "localhost", "127.0.0.1"} or config.ENVIRONMENT not in {"development", "test"}:
            self.skipTest("Las pruebas crean bases efímeras únicamente en PostgreSQL local")
        self.database_name = "pataporte_test_" + uuid.uuid4().hex[:12]
        self.admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT",
                                   connect_args=config.database_connect_args())
        with self.admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{self.database_name}"'))
        self.engine = create_engine(url.set(database=self.database_name),
                                    connect_args=config.database_connect_args())

    def tearDown(self):
        self.engine.dispose()
        with self.admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{self.database_name}"'))
        self.admin.dispose()

    def test_empty_database_upgrade_downgrade_and_replay(self):
        with self.assertRaisesRegex(RuntimeError, "desactualizado"):
            assert_schema_current(self.engine)
        migrate_database(self.engine)
        assert_schema_current(self.engine)
        migrate_database(self.engine)
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text("SELECT count(*) FROM tipo_vacunas")), 5)
            self.assertEqual(compare_metadata(MigrationContext.configure(connection, opts={"compare_type": True}), Base.metadata), [])
        cfg = alembic_config()
        with self.engine.connect() as connection:
            cfg.attributes["connection"] = connection
            command.downgrade(cfg, "base")
        with self.engine.connect() as connection:
            self.assertEqual(set(inspect(connection).get_table_names()), {"alembic_version"})
            self.assertEqual(connection.scalar(text("SELECT count(*) FROM pg_type WHERE typname IN ('sexo_mascota','especie','estado_general','rol_tutor','estado_esquema','estado_pataporte')")), 0)
        migrate_database(self.engine)
        assert_schema_current(self.engine)

    def test_adopts_legacy_schema_without_losing_existing_records(self):
        baseline_metadata().create_all(self.engine)
        tutor_id = str(uuid.uuid4())
        vaccine_id = str(uuid.uuid4())
        with self.engine.begin() as connection:
            connection.execute(Base.metadata.tables["usuario_tutor"].insert().values(
                id_tutor=tutor_id, cedula="TEST-LEGACY", nombre="Tutor ficticio",
                email="legacy@example.com", password_hash="fictional-hash"))
            connection.execute(Base.metadata.tables["tipo_vacunas"].insert().values(
                id_vacuna=vaccine_id, nombre="Moquillo", descripcion="Descripción previa",
                especie_objetivo="perro", cantidad_dosis_requeridas=3))
        migrate_database(self.engine)
        assert_schema_current(self.engine)
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text("SELECT count(*) FROM usuario_tutor")), 1)
            self.assertEqual(connection.scalar(text("SELECT id_tutor::text FROM usuario_tutor")), tutor_id)
            self.assertEqual(connection.scalar(text("SELECT id_vacuna::text FROM tipo_vacunas WHERE nombre='Moquillo'")), vaccine_id)
            self.assertEqual(connection.scalar(text("SELECT count(*) FROM tipo_vacunas")), 5)

    def test_rejects_legacy_schema_drift_without_stamping(self):
        baseline_metadata().create_all(self.engine)
        with self.engine.begin() as connection:
            connection.execute(text("ALTER TABLE mascota ADD COLUMN unexpected_field text"))
        with self.assertRaisesRegex(RuntimeError, "no coincide"):
            migrate_database(self.engine)
        with self.engine.connect() as connection:
            self.assertNotIn("alembic_version", inspect(connection).get_table_names())
            self.assertIn("unexpected_field", {c["name"] for c in inspect(connection).get_columns("mascota")})

    def test_refuses_concurrent_migration(self):
        with self.engine.connect() as connection:
            connection.execute(text("SELECT pg_advisory_lock(:key)"), {"key": MIGRATION_LOCK})
            connection.commit()
            try:
                with self.assertRaisesRegex(RuntimeError, "Otra tarea"):
                    migrate_database(self.engine)
            finally:
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": MIGRATION_LOCK})
                connection.commit()
        with self.engine.connect() as connection:
            self.assertEqual(inspect(connection).get_table_names(), [])

    def test_runtime_account_crud_without_schema_or_migration_permissions(self):
        migrate_database(self.engine)
        username = "pataporte_test_app_" + uuid.uuid4().hex[:12]
        password = secrets.token_urlsafe(40)
        runtime = create_engine(self.engine.url.set(username=username, password=password))
        wrong = create_engine(self.engine.url.set(username=username, password=secrets.token_urlsafe(40)))
        try:
            provision_runtime_account(self.engine, username, password)
            provision_runtime_account(self.engine, username, password)
            result = verify_runtime(runtime)
            self.assertEqual(result["runtime_crud"], "passed")
            self.assertFalse(result["probe_data_retained"])
            with runtime.connect() as connection:
                self.assertEqual(connection.scalar(text("SELECT count(*) FROM usuario_tutor")), 0)
                with self.assertRaises(Exception):
                    connection.execute(text("CREATE TABLE forbidden_probe(id int)"))
                connection.rollback()
                with self.assertRaises(Exception):
                    connection.execute(text("UPDATE alembic_version SET version_num=version_num"))
                connection.rollback()
            with self.assertRaises(Exception):
                wrong.connect()
        finally:
            runtime.dispose()
            wrong.dispose()
            with self.engine.begin() as connection:
                connection.execute(text(f'DROP OWNED BY "{username}"'))
                connection.execute(text(f'DROP ROLE "{username}"'))


if __name__ == "__main__":
    unittest.main()
