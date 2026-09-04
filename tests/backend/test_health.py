import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent.parent / "backend"
sys.path.append(str(backend_path))

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify GET / returns valid service info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "HealthWatch"
    assert "version" in data
    assert data["health"] == "/api/health"


def test_health_endpoint():
    """Verify GET /api/health returns valid schema and status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app_name"] == "HealthWatch"
    assert "version" in data
    assert "timestamp" in data
    assert "database" in data
    assert "status" in data["database"]


def test_api_v1_root():
    """Verify GET /api/v1/ returns API version metadata."""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    data = response.json()
    assert data["api_version"] == "v1"
    assert len(data["endpoints"]) > 0
