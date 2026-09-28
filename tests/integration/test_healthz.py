from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_healthz_endpoint() -> None:
    response = client.get("/healthz")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "postgres" in data
    assert "redis" in data
