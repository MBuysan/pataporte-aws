from fastapi.testclient import TestClient

from main import app


def test_health_no_toca_la_db():
    respuesta = TestClient(app).get("/api/health")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_docs_bajo_api():
    assert TestClient(app).get("/api/openapi.json").status_code == 200
