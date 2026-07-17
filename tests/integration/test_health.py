from __future__ import annotations

from apps.api.main import app as fastapi_app
from apps.web.app import create_app as create_flask_app
from fastapi.testclient import TestClient


def test_fastapi_liveness() -> None:
    client = TestClient(fastapi_app)
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_fastapi_readiness_reports_database_state() -> None:
    client = TestClient(fastapi_app)
    response = client.get("/api/v1/health/ready")
    # Whatever the DB state, the endpoint must respond with a clear status
    # rather than erroring — 200 when reachable, 503 when not.
    assert response.status_code in (200, 503)
    assert "database" in response.json()


def test_flask_healthz() -> None:
    app = create_flask_app()
    app.config.update(TESTING=True)
    with app.test_client() as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.get_json() == {"status": "ok"}
