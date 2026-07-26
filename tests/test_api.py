import json
import time
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
    assert "Local LLM Orchestrator" in response.text


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
    main_module.admin_auth_throttle.reset()
    client = TestClient(main_module.app)
    try:
        statuses = [
            client.get("/admin/config", headers={"Authorization": "Bearer wrong"}).status_code
            for _ in range(main_module.admin_auth_throttle.max_failures + 2)
        ]
        # First failures are 401; once the lockout trips, requests get 429.
        assert statuses[0] == 401
        assert 429 in statuses
    finally:
        main_module.admin_auth_throttle.reset()
        monkeypatch.setattr(main_module, "settings", original_settings)
        main_module.reload_components()


def test_inference_auth_failures_do_not_lock_out_admin(tmp_path, monkeypatch):
    # Inference and admin auth keep separate throttle state: a client hammering a wrong
    # inference key from a shared egress IP must not lock the admin out of the console,
    # which is the very surface needed to revoke that client's key.
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
        inference_statuses = [
            client.get("/v1/models", headers={"Authorization": "Bearer wrong"}).status_code
            for _ in range(main_module.auth_throttle.max_failures + 2)
        ]
        assert 429 in inference_statuses  # the inference side did trip

        # The admin side is untouched and still authenticates normally.
        assert client.get("/admin/config", headers={"Authorization": "Bearer admin-key"}).status_code == 200
    finally:
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


def test_admin_audit_records_config_changes(tmp_path, monkeypatch):
    original_settings = main_module.settings
    temp_config = tmp_path / "models.json"
    temp_config.write_text(Path(original_settings.model_config_path).read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(original_settings, api_key="k", admin_api_key="", model_config_path=temp_config),
    )
    main_module.reload_components()
    main_module.AUDIT_LOG.clear()
    client = TestClient(main_module.app)
    headers = {"Authorization": "Bearer k"}
    try:
        client.patch("/admin/mcp/tools", headers=headers, json={"enabled": True, "set_tools": ["route_request"]})
        response = client.get("/admin/audit", headers=headers)
        assert response.status_code == 200
        entries = response.json()["entries"]
        assert entries and entries[0]["action"] == "patch_mcp_tools"
        assert "at" in entries[0] and "ip" in entries[0]
        # Audit requires admin auth.
        assert TestClient(main_module.app).get("/admin/audit").status_code == 401
    finally:
        main_module.AUDIT_LOG.clear()
        monkeypatch.setattr(main_module, "settings", original_settings)
        main_module.reload_components()


def test_admin_metrics_endpoint(tmp_path, monkeypatch):
    original_settings = main_module.settings
    temp_config = tmp_path / "models.json"
    temp_config.write_text(Path(original_settings.model_config_path).read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(original_settings, api_key="k", admin_api_key="", model_config_path=temp_config),
    )
    main_module.reload_components()
    client = TestClient(main_module.app)
    try:
        response = client.get("/admin/metrics", headers={"Authorization": "Bearer k"})
        assert response.status_code == 200
        body = response.json()
        assert "current" in body and "delta_pct" in body and "series" in body
        # Admin auth required.
        assert TestClient(main_module.app).get("/admin/metrics").status_code == 401
    finally:
        monkeypatch.setattr(main_module, "settings", original_settings)
        main_module.reload_components()


def test_docker_services_control(tmp_path, monkeypatch):
    from services.orchestrator.docker_control import DockerControl

    original_settings = main_module.settings
    temp_config = tmp_path / "models.json"
    temp_config.write_text(Path(original_settings.model_config_path).read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(original_settings, api_key="k", admin_api_key="", model_config_path=temp_config),
    )
    main_module.reload_components()
    headers = {"Authorization": "Bearer k"}
    try:
        # Disabled by default: state is reported, actions are refused with 503.
        monkeypatch.setattr(main_module, "docker_control", DockerControl(False, "/nope", "local-llm"))
        client = TestClient(main_module.app)
        listing = client.get("/admin/services", headers=headers)
        assert listing.status_code == 200
        assert listing.json()["enabled"] is False
        assert client.post("/admin/services/llama-main/start", headers=headers).status_code == 503
        # Admin auth required.
        assert TestClient(main_module.app).get("/admin/services").status_code == 401

        # Enabled: an out-of-allowlist container is forbidden without touching Docker.
        monkeypatch.setattr(main_module, "docker_control", DockerControl(True, "/nope", "local-llm"))
        assert client.post("/admin/services/evil-container/start", headers=headers).status_code == 403
    finally:
        monkeypatch.setattr(main_module, "settings", original_settings)
        main_module.reload_components()


def test_api_key_lifecycle_and_managed_key_auth(tmp_path, monkeypatch):
    from services.orchestrator.api_keys import ApiKeyStore

    original_settings = main_module.settings
    temp_config = tmp_path / "models.json"
    temp_config.write_text(Path(original_settings.model_config_path).read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(original_settings, api_key="root", admin_api_key="admin", model_config_path=temp_config),
    )
    monkeypatch.setattr(main_module, "api_key_store", ApiKeyStore(tmp_path / "api_keys.json"))
    main_module.reload_components()
    client = TestClient(main_module.app)
    admin = {"Authorization": "Bearer admin"}
    try:
        # Create returns the raw key exactly once.
        created = client.post("/admin/api-keys", headers=admin, json={"label": "member-a"})
        assert created.status_code == 200
        raw = created.json()["key"]
        key_id = created.json()["record"]["id"]

        # The managed key works for inference endpoints...
        assert client.get("/v1/models", headers={"Authorization": f"Bearer {raw}"}).status_code == 200
        # ...but not for admin endpoints.
        assert client.get("/admin/config", headers={"Authorization": f"Bearer {raw}"}).status_code == 401

        # Listing never leaks the secret.
        listing = client.get("/admin/api-keys", headers=admin).json()["keys"]
        assert any(k["id"] == key_id for k in listing)
        assert all("hash" not in k for k in listing)

        # Revoke disables it.
        assert client.delete(f"/admin/api-keys/{key_id}", headers=admin).status_code == 200
        assert client.get("/v1/models", headers={"Authorization": f"Bearer {raw}"}).status_code == 401
        # Creating a key requires admin auth.
        assert client.post("/admin/api-keys", json={"label": "x"}).status_code == 401
    finally:
        monkeypatch.setattr(main_module, "settings", original_settings)
        main_module.reload_components()


def test_api_key_scope_and_rate_limit(tmp_path, monkeypatch):
    from services.orchestrator.api_keys import ApiKeyStore

    original_settings = main_module.settings
    temp_config = tmp_path / "models.json"
    temp_config.write_text(Path(original_settings.model_config_path).read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(original_settings, api_key="root", admin_api_key="admin", model_config_path=temp_config),
    )
    monkeypatch.setattr(main_module, "api_key_store", ApiKeyStore(tmp_path / "api_keys.json"))
    main_module.reload_components()
    client = TestClient(main_module.app)
    admin = {"Authorization": "Bearer admin"}
    try:
        created = client.post(
            "/admin/api-keys",
            headers=admin,
            json={"label": "scoped", "models": ["main-llm"], "rate_limit_per_min": 2},
        )
        assert created.status_code == 200
        raw = created.json()["key"]
        key_headers = {"Authorization": f"Bearer {raw}", "Content-Type": "application/json"}

        # /v1/models is filtered to the allowed model for this key.
        model_ids = {m["id"] for m in client.get("/v1/models", headers=key_headers).json()["data"]}
        assert model_ids == {"main-llm"}

        # A disallowed model is rejected with 403 before reaching the backend.
        forbidden = client.post(
            "/v1/chat/completions",
            headers=key_headers,
            json={"model": "coding", "messages": [{"role": "user", "content": "hi"}]},
        )
        assert forbidden.status_code == 403
        assert forbidden.json()["detail"]["code"] == "model_forbidden"

        # Rate limit: /v1/models counts as a request; the 2/min key trips on the 3rd.
        main_module.rate_limiter.reset()
        statuses = [client.get("/v1/models", headers=key_headers).status_code for _ in range(3)]
        assert statuses[0] == 200 and statuses[-1] == 429

        # Metrics attribute traffic to the key label.
        summary = client.get("/admin/metrics", headers=admin).json()
        assert "by_key" in summary
    finally:
        monkeypatch.setattr(main_module, "settings", original_settings)
        main_module.reload_components()


def test_api_key_model_scope_blocks_prompt_model_override(tmp_path, monkeypatch):
    from services.orchestrator.api_keys import ApiKeyStore

    original_settings = main_module.settings
    temp_config = tmp_path / "models.json"
    temp_config.write_text(Path(original_settings.model_config_path).read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(original_settings, api_key="root", admin_api_key="admin", model_config_path=temp_config),
    )
    monkeypatch.setattr(main_module, "api_key_store", ApiKeyStore(tmp_path / "api_keys.json"))
    main_module.reload_components()
    client = TestClient(main_module.app)
    admin = {"Authorization": "Bearer admin"}
    try:
        created = client.post(
            "/admin/api-keys",
            headers=admin,
            json={"label": "scoped", "models": ["main-llm-improved"]},
        )
        raw = created.json()["key"]
        key_headers = {"Authorization": f"Bearer {raw}", "Content-Type": "application/json"}

        # `model` is in scope, but `prompt_model` names a model outside the key's scope --
        # must be rejected before any prompt-improvement call is made, not silently allowed.
        response = client.post(
            "/orchestrate/chat",
            headers=key_headers,
            json={
                "model": "main-llm-improved",
                "prompt_model": "coding",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "model_forbidden"

        # The same smuggling attempt through the OpenAI-compatible endpoint. "main-llm-improved"
        # already has improve_prompt=true in its own virtual-model policy (so workflow_required
        # triggers the workflow path), and ChatRequest's extra="allow" lets the extra
        # `prompt_model` field survive into the OrchestrateRequest promotion.
        response = client.post(
            "/v1/chat/completions",
            headers=key_headers,
            json={
                "model": "main-llm-improved",
                "prompt_model": "coding",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "model_forbidden"
    finally:
        monkeypatch.setattr(main_module, "settings", original_settings)
        main_module.reload_components()


def test_expired_api_key_is_rejected_by_the_api(tmp_path, monkeypatch):
    from services.orchestrator.api_keys import ApiKeyStore

    original_settings = main_module.settings
    temp_config = tmp_path / "models.json"
    temp_config.write_text(Path(original_settings.model_config_path).read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(original_settings, api_key="root", admin_api_key="admin", model_config_path=temp_config),
    )
    store = ApiKeyStore(tmp_path / "api_keys.json")
    monkeypatch.setattr(main_module, "api_key_store", store)
    main_module.reload_components()
    client = TestClient(main_module.app)
    admin = {"Authorization": "Bearer admin"}
    try:
        created = client.post(
            "/admin/api-keys", headers=admin, json={"label": "temp", "expires_in_days": 1}
        )
        assert created.status_code == 200
        raw = created.json()["key"]
        key_headers = {"Authorization": f"Bearer {raw}"}
        assert client.get("/v1/models", headers=key_headers).status_code == 200

        # Move the expiry into the past; the same key must now be refused.
        store._keys[0]["expires_at"] = time.time() - 1
        assert client.get("/v1/models", headers=key_headers).status_code == 401

        # The expired key is flagged in the admin listing so it can be cleaned up.
        listed = client.get("/admin/api-keys", headers=admin).json()["keys"]
        assert listed[0]["expired"] is True
    finally:
        monkeypatch.setattr(main_module, "settings", original_settings)
        main_module.reload_components()


def test_audit_entries_are_appended_to_the_audit_file(tmp_path, monkeypatch):
    # The in-memory ring buffer is capped and lost on restart, which is exactly when an
    # investigation needs it -- AUDIT_LOG_PATH persists each entry as a JSON line.
    original_settings = main_module.settings
    temp_config = tmp_path / "models.json"
    temp_config.write_text(Path(original_settings.model_config_path).read_text(encoding="utf-8"), encoding="utf-8")
    audit_path = tmp_path / "nested" / "audit.jsonl"
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(
            original_settings,
            api_key="root",
            admin_api_key="admin",
            model_config_path=temp_config,
            audit_log_path=audit_path,
        ),
    )
    main_module.reload_components()
    client = TestClient(main_module.app)
    try:
        assert client.post("/admin/reload", headers={"Authorization": "Bearer admin"}, json={}).status_code == 200
        assert audit_path.exists()  # parent directory is created on demand
        entries = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert entries[-1]["action"] == "reload"
        assert "at" in entries[-1] and "ip" in entries[-1]
    finally:
        monkeypatch.setattr(main_module, "settings", original_settings)
        main_module.reload_components()


def test_audit_file_write_failure_does_not_break_the_admin_action(tmp_path, monkeypatch):
    # A read-only or full filesystem must degrade to "no file entry", not a 500 that
    # blocks the admin from actually managing the service.
    original_settings = main_module.settings
    temp_config = tmp_path / "models.json"
    temp_config.write_text(Path(original_settings.model_config_path).read_text(encoding="utf-8"), encoding="utf-8")
    # A path whose parent is an existing *file* cannot be created as a directory.
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(
            original_settings,
            api_key="root",
            admin_api_key="admin",
            model_config_path=temp_config,
            audit_log_path=blocker / "audit.jsonl",
        ),
    )
    main_module.reload_components()
    client = TestClient(main_module.app)
    try:
        response = client.post("/admin/reload", headers={"Authorization": "Bearer admin"}, json={})
        assert response.status_code == 200
        # The in-memory audit still recorded it.
        entries = client.get("/admin/audit", headers={"Authorization": "Bearer admin"}).json()["entries"]
        assert any(entry["action"] == "reload" for entry in entries)
    finally:
        monkeypatch.setattr(main_module, "settings", original_settings)
        main_module.reload_components()


def test_api_key_tools_scope_enforced(tmp_path, monkeypatch):
    from services.orchestrator.api_keys import ApiKeyStore

    original_settings = main_module.settings
    temp_config = tmp_path / "models.json"
    temp_config.write_text(Path(original_settings.model_config_path).read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(
        main_module,
        "settings",
        replace(original_settings, api_key="root", admin_api_key="admin", model_config_path=temp_config),
    )
    monkeypatch.setattr(main_module, "api_key_store", ApiKeyStore(tmp_path / "api_keys.json"))
    main_module.reload_components()
    client = TestClient(main_module.app)
    admin = {"Authorization": "Bearer admin"}
    try:
        created = client.post(
            "/admin/api-keys", headers=admin, json={"label": "toolscoped", "tools": ["route_request"]}
        )
        raw = created.json()["key"]
        key_headers = {"Authorization": f"Bearer {raw}", "Content-Type": "application/json"}
        # A tool outside the key's scope is rejected with 403 before MCP is contacted.
        forbidden = client.post("/mcp/call", headers=key_headers, json={"name": "read_file", "arguments": {}})
        assert forbidden.status_code == 403
        assert forbidden.json()["detail"]["code"] == "tool_forbidden"
        # The audit records the tools scope on creation.
        entries = client.get("/admin/audit", headers=admin).json()["entries"]
        assert any(e["action"] == "create_api_key" and e["fields"].get("tools") == "route_request" for e in entries)
    finally:
        monkeypatch.setattr(main_module, "settings", original_settings)
        main_module.reload_components()


def test_ready_reports_per_provider_health(monkeypatch):
    from services.orchestrator.llama_client import ProviderClients

    # Fast-failing client (closed port, no retries) so the probe returns immediately.
    fast = ProviderClients(
        main_module.model_config.get("providers", {}),
        timeout=0.2,
        attempts=1,
        backoff=0.0,
        default_base_url="http://127.0.0.1:59999",
    )
    monkeypatch.setattr(main_module, "provider_clients", fast)
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {main_module.settings.api_key}"}
    response = client.get("/ready", headers=headers)
    # No backend running: 200 with a per-provider health map and an overall status.
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ready", "unavailable"}
    assert "providers" in body and isinstance(body["providers"], dict)
    # Referenced providers include the dedicated main/prompt providers.
    assert "main" in body["providers"] and "prompt" in body["providers"]
