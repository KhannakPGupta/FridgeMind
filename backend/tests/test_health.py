"""Tests for health check endpoint."""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_check_returns_ok():
    """Verify GET /api/health returns 200 with required status fields."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "environment" in data
    assert "gemini_configured" in data
    assert "timestamp" in data


def test_root_endpoint_returns_metadata():
    """Verify GET / returns project metadata and navigation links."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "FridgeMind API"
    assert "/docs" in data["docs"]
