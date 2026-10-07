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
    assert response.status_code in (200, 503)
    data = response.json()
    assert data["status"] in ("ok", "degraded")
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


def test_apk_info_endpoint():
    """Verify GET /api/apk/info returns current release metadata."""
    response = client.get("/api/apk/info")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "HealthWatch"
    assert "version" in data
    assert "download_url" in data
    assert "canonical_url" in data
    assert "filename" in data


def test_apk_download_anti_cache_headers():
    """Verify APK download responses contain strict anti-cache headers."""
    response = client.get("/HealthWatch.apk", follow_redirects=False)
    # Status should be 200 (if file exists) or 404 (if no APK present during test)
    if response.status_code == 200:
        cache_ctrl = response.headers.get("cache-control", "").lower()
        assert "no-store" in cache_ctrl
        assert "no-cache" in cache_ctrl
        assert response.headers.get("pragma", "").lower() == "no-cache"


def test_obsolete_apk_version_redirect():
    """Verify requesting an outdated APK version triggers a 307 redirect to active release."""
    response = client.get("/HealthWatch-v0.0.1.apk", follow_redirects=False)
    assert response.status_code == 307
    location = response.headers.get("location", "")
    assert "HealthWatch-v" in location
    cache_ctrl = response.headers.get("cache-control", "").lower()
    assert "no-store" in cache_ctrl

