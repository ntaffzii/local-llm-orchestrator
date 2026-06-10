from fastapi.testclient import TestClient

from services.orchestrator.main import app


def test_health_does_not_require_api_key():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_models_require_configured_api_key():
    client = TestClient(app)
    response = client.get("/v1/models", headers={"Authorization": "Bearer change-me"})
    assert response.status_code == 200
    assert any(model["id"] == "auto" for model in response.json()["data"])

