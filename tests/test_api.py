from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from services.orchestrator.main import app
import services.orchestrator.main as main_module


def test_health_does_not_require_api_key():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_models_require_configured_api_key():
    client = TestClient(app)
    response = client.get("/v1/models", headers={"Authorization": "Bearer change-me"})
    assert response.status_code == 200
    assert any(model["id"] == "auto" for model in response.json()["data"])


def test_admin_ui_is_served_without_api_key():
    response = TestClient(app).get("/admin/ui")
    assert response.status_code == 200
    assert "Local LLM Admin" in response.text


def test_admin_config_requires_api_key():
    response = TestClient(app).get("/admin/config")
    assert response.status_code == 401


def test_patch_mcp_tools_updates_config_and_reloads(tmp_path, monkeypatch):
    original_settings = main_module.settings
    temp_config = tmp_path / "models.json"
    temp_config.write_text(Path(original_settings.model_config_path).read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(original_settings, api_key="test-admin-key", model_config_path=temp_config),
    )
    main_module.reload_components()
    client = TestClient(main_module.app)
    headers = {"Authorization": "Bearer test-admin-key"}

    try:
        response = client.patch(
            "/admin/mcp/tools",
            headers=headers,
            json={
                "enabled": False,
                "set_tools": ["route_request", "test_tool_abc"],
                "allow_tools": ["test_tool_abc"],
                "deny_tools": ["route_request"],
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["mcp_enabled"] is False
        assert "test_tool_abc" in body["tool_allowlist"]
        assert "route_request" not in body["tool_allowlist"]
    finally:
        monkeypatch.setattr(main_module, "settings", original_settings)
        main_module.reload_components()
