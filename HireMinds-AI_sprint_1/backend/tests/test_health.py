"""
Pytest unit tests for Health Check endpoint
"""
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)


def test_health_check_endpoint():
    """
    Test that /api/v1/health returns HTTP 200 and expected schema payload.
    """
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["project"] == settings.PROJECT_NAME
    assert data["version"] == settings.VERSION
    assert data["environment"] == settings.ENVIRONMENT
    assert "timestamp" in data
    assert "services" in data
    assert data["services"]["api"] == "online"
    assert data["services"]["database"]["status"] == "connected"


def test_root_redirect_to_docs():
    """
    Test that root / redirects to API docs.
    """
    response = client.get("/", follow_redirects=False)
    assert response.status_code in [307, 308]
    assert response.headers["location"] == f"{settings.API_V1_STR}/docs"
