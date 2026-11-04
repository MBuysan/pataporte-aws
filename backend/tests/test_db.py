"""
Tests de integración contra PostgreSQL real: migraciones, usuario de la app y outbox.
Corren solo con TEST_DATABASE_URL (usuario con permiso de crear bases), p. ej.:
  docker run --rm -d -p 55440:5432 -e POSTGRES_PASSWORD=tmp postgres:16
  TEST_DATABASE_URL=postgresql://postgres:tmp@localhost:55440/postgres pytest tests/test_db.py
Cada test usa una base efímera propia.
"""
import os
import threading
import uuid
from datetime import datetime, timezone

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from config import database
from config.database import Base, Outbox, VerificacionEmail
from messaging import publisher
from scripts import init_db

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="requiere TEST_DATABASE_URL (PostgreSQL)")


@pytest.fixture
def base_vacia(monkeypatch):
    """Base nueva y vacía; config.database apunta a ella."""
    admin = create_engine(URL, isolation_level="AUTOCOMMIT")
    nombre = "pataporte_test_" + uuid.uuid4().hex[:10]
    with admin.connect() as c:
        c.execute(text(f'CREATE DATABASE "{nombre}"'))
    engine = create_engine(make_url(URL).set(database=nombre))
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=engine, autoflush=False))
    monkeypatch.setattr(init_db, "engine", engine)
    yield engine
    engine.dispose()
    with admin.connect() as c:
        c.execute(text(f'DROP DATABASE "{nombre}" WITH (FORCE)'))
    admin.dispose()


@pytest.fixture
def base(base_vacia):
    init_db.migrar()
    return base_vacia


def contar(engine, sql):
    with engine.connect() as c:
        return c.execute(text(sql)).scalar()


# ── migraciones ───────────────────────────────────────────────────────────────

def test_migraciones_coinciden_con_los_modelos_y_son_idempotentes(base):
    init_db.migrar()  # segunda corrida: no cambia nada
    with base.connect() as c:
        assert compare_metadata(MigrationContext.configure(c, opts={"compare_type": True}), Base.metadata) == []
    assert contar(base, "SELECT count(*) FROM tipo_vacunas") == 5


def test_base_creada_con_create_all_se_adopta_sin_perder_datos(base_vacia):
    Base.metadata.drop_all(base_vacia)
    # así quedaba la base antes de Alembic: create_all sin la outbox (llega con 0003)
    tablas_viejas = [t for t in Base.metadata.sorted_tables if t.name != "outbox"]
    Base.metadata.create_all(base_vacia, tables=tablas_viejas)
    with base_vacia.begin() as c:
        c.execute(text("INSERT INTO organizacion (id_organizacion, rut, fecha_registro) VALUES (gen_random_uuid(), '1', now())"))

    init_db.migrar()

    assert contar(base_vacia, "SELECT version_num FROM alembic_version") == "0003"
    assert contar(base_vacia, "SELECT count(*) FROM organizacion") == 1
    assert contar(base_vacia, "SELECT count(*) FROM outbox") == 0


def test_usuario_app_solo_tiene_permisos_dml(base):
    usuario = "pataporte_app_" + uuid.uuid4().hex[:6]
    init_db.usuario_app(usuario, "clave-de-prueba-1")
    init_db.usuario_app(usuario, "clave-de-prueba-2")  # actualiza la contraseña
    app = create_engine(base.url.set(username=usuario, password="clave-de-prueba-2"))
    try:
        with app.connect() as c:
            permisos = c.execute(text(
                "SELECT has_schema_privilege(current_user, 'public', 'CREATE'),"
                " has_table_privilege(current_user, 'alembic_version', 'UPDATE'),"
                " has_table_privilege(current_user, 'outbox', 'INSERT'),"
                " has_table_privilege(current_user, 'tipo_vacunas', 'SELECT')"
            )).one()
            assert tuple(permisos) == (False, False, True, True)
    finally:
        app.dispose()
        with base.begin() as c:
            c.execute(text(f'DROP OWNED BY "{usuario}"; DROP ROLE "{usuario}"'))


# ── outbox ────────────────────────────────────────────────────────────────────

def test_rollback_no_deja_ni_el_cambio_ni_el_evento(base):
    with database.SessionLocal() as db:
        db.add(VerificacionEmail(email="a@b.c", tipo_usuario="tutor", codigo_hash="x",
                                 expiracion=datetime.now(timezone.utc)))
        publisher.publicar_evento(db, "VerificacionEmailSolicitada", {"email": "a@b.c"})
        db.flush()
        db.rollback()
    assert contar(base, "SELECT count(*) FROM verificacion_email") == 0
    assert contar(base, "SELECT count(*) FROM outbox") == 0


def test_el_servicio_confirma_el_evento_con_el_codigo(base):
    from services import auth_service

    with database.SessionLocal() as db:
        auth_service.generar_y_enviar_codigo_verificacion(db, "a@b.c", "tutor")
    assert contar(base, "SELECT count(*) FROM verificacion_email") == 1
    assert contar(base, "SELECT tipo FROM outbox") == "VerificacionEmailSolicitada"


def test_caida_del_broker_reintenta_con_el_mismo_id(base, monkeypatch):
    with database.SessionLocal() as db:
        id_evento = publisher.publicar_evento(db, "PataporteEmitido", {"email": "a@b.c"})
        db.commit()

    def caido(*_):
        raise OSError("broker caído")

    monkeypatch.setattr(publisher, "enviar", caido)
    assert publisher.despachar_lote() == 0
    with database.SessionLocal() as db:
        fila = db.get(Outbox, id_evento)
        assert (fila.enviado, fila.intentos, fila.ultimo_error) == (None, 1, "broker caído")
    assert publisher.despachar_lote() == 0  # en backoff: todavía no se reintenta

    with base.begin() as c:
        c.execute(text("UPDATE outbox SET disponible_desde = now()"))
    enviados = []
    monkeypatch.setattr(publisher, "enviar", lambda i, n, d: enviados.append((i, n, d)))
    assert publisher.despachar_lote() == 1
    assert publisher.despachar_lote() == 0  # ya enviado: no se repite
    assert enviados == [(id_evento, "PataporteEmitido", {"email": "a@b.c"})]


def test_skip_locked_no_despacha_filas_tomadas_por_otro(base, monkeypatch):
    with database.SessionLocal() as db:
        publisher.publicar_evento(db, "X", {})
        db.commit()
    enviados = []
    monkeypatch.setattr(publisher, "enviar", lambda *a: enviados.append(a))

    otro = base.connect()
    tx = otro.begin()
    otro.execute(text("SELECT id FROM outbox FOR UPDATE"))  # otro despachador tiene la fila
    resultado = []
    hilo = threading.Thread(target=lambda: resultado.append(publisher.despachar_lote()))
    hilo.start()
    hilo.join(timeout=10)
    tx.rollback()
    otro.close()

    assert resultado == [0] and enviados == []
    assert publisher.despachar_lote() == 1
