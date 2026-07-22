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
    # Use whatever key the environment configured rather than a hard-coded literal,
    # so the test does not depend on the developer's local .env value.
    headers = {"Authorization": f"Bearer {main_module.settings.api_key}"}
    response = client.get("/v1/models", headers=headers)
    assert response.status_code == 200
    assert any(model["id"] == "auto" for model in response.json()["data"])


def test_models_reject_wrong_api_key():
    client = TestClient(app)
    response = client.get("/v1/models", headers={"Authorization": "Bearer definitely-wrong"})
    assert response.status_code == 401


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
        replace(original_settings, api_key="test-admin-key", admin_api_key="", model_config_path=temp_config),
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


def test_put_invalid_config_is_rejected_without_corrupting_disk(tmp_path, monkeypatch):
    import json
    from services.orchestrator.config import load_model_config

    original_settings = main_module.settings
    temp_config = tmp_path / "models.json"
    good_text = Path(original_settings.model_config_path).read_text(encoding="utf-8")
    temp_config.write_text(good_text, encoding="utf-8")
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(original_settings, api_key="k", admin_api_key="", model_config_path=temp_config),
    )
    main_module.reload_components()
    client = TestClient(main_module.app)
    headers = {"Authorization": "Bearer k"}
    try:
        good = json.loads(good_text)
        # Missing orchestration/routing -> must be rejected with 400, disk unchanged.
        response = client.put(
            "/admin/config",
            headers=headers,
            json={"models": good["models"], "virtual_models": good["virtual_models"]},
        )
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "invalid_config"
        # On-disk config must still be the original, valid one.
        assert load_model_config(temp_config)["orchestration"]
    finally:
        monkeypatch.setattr(main_module, "settings", original_settings)
        main_module.reload_components()


def test_admin_key_separates_from_inference_key(tmp_path, monkeypatch):
    original_settings = main_module.settings
    temp_config = tmp_path / "models.json"
    temp_config.write_text(Path(original_settings.model_config_path).read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(original_settings, api_key="user-key", admin_api_key="admin-key", model_config_path=temp_config),
    )
    main_module.reload_components()
    client = TestClient(main_module.app)
    try:
        # Inference key must not unlock admin endpoints.
        assert client.get("/admin/config", headers={"Authorization": "Bearer user-key"}).status_code == 401
        # Admin key does.
        assert client.get("/admin/config", headers={"Authorization": "Bearer admin-key"}).status_code == 200
        # Inference key still works for inference endpoints.
        assert client.get("/v1/models", headers={"Authorization": "Bearer user-key"}).status_code == 200
    finally:
        monkeypatch.setattr(main_module, "settings", original_settings)
        main_module.reload_components()


def test_repeated_bad_admin_auth_gets_throttled(tmp_path, monkeypatch):
    original_settings = main_module.settings
    temp_config = tmp_path / "models.json"
    temp_config.write_text(Path(original_settings.model_config_path).read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(original_settings, api_key="user-key", admin_api_key="admin-key", model_config_path=temp_config),
    )
    main_module.reload_components()
    main_module.auth_throttle.reset()
    client = TestClient(main_module.app)
    try:
        statuses = [
            client.get("/admin/config", headers={"Authorization": "Bearer wrong"}).status_code
            for _ in range(main_module.auth_throttle.max_failures + 2)
        ]
        # First failures are 401; once the lockout trips, requests get 429.
        assert statuses[0] == 401
        assert 429 in statuses
    finally:
        main_module.auth_throttle.reset()
        monkeypatch.setattr(main_module, "settings", original_settings)
        main_module.reload_components()


def test_admin_ui_can_be_disabled(monkeypatch):
    original_settings = main_module.settings
    monkeypatch.setattr(main_module, "settings", replace(original_settings, admin_ui_enabled=False))
    try:
        response = TestClient(main_module.app).get("/admin/ui")
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "admin_ui_disabled"
    finally:
        monkeypatch.setattr(main_module, "settings", original_settings)


def test_forwarded_for_is_ignored_unless_trusted(monkeypatch):
    original_settings = main_module.settings
    # Not trusted: spoofed X-Forwarded-For must not change the throttle key.
    monkeypatch.setattr(main_module, "settings", replace(original_settings, trust_forwarded_for=False))
    from starlette.datastructures import Headers

    class _Req:
        headers = Headers({"X-Forwarded-For": "9.9.9.9"})

        class client:
            host = "127.0.0.1"

    assert main_module._client_ip(_Req()) == "127.0.0.1"
    monkeypatch.setattr(main_module, "settings", replace(original_settings, trust_forwarded_for=True))
    assert main_module._client_ip(_Req()) == "9.9.9.9"
    monkeypatch.setattr(main_module, "settings", original_settings)
