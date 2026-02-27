from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.models import HealthResponse, APIStatusResponse


def test_root_returns_ok():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
