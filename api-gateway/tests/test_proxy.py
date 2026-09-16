from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api-gateway"}

def test_unknown_service_returns_404():
    response = client.get("/api/v1/unknown/endpoint")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
