import pytest

from services.orchestrator.docker_control import DockerControl, DockerControlDisabled


@pytest.mark.asyncio
async def test_set_service_disabled_raises():
    control = DockerControl(enabled=False, socket_path="/nope", project="local-llm")
    with pytest.raises(DockerControlDisabled):
        await control.set_service("llama-main", "start")


@pytest.mark.asyncio
async def test_set_service_rejects_service_outside_allowlist():
    control = DockerControl(enabled=True, socket_path="/nope", project="local-llm")
    # Allowlist check happens before any socket access, so an arbitrary container is
    # rejected without touching Docker.
    with pytest.raises(PermissionError):
        await control.set_service("some-other-container", "start")


@pytest.mark.asyncio
async def test_set_service_rejects_invalid_action():
    control = DockerControl(enabled=True, socket_path="/nope", project="local-llm")
    with pytest.raises(ValueError):
        await control.set_service("llama-main", "destroy")


@pytest.mark.asyncio
async def test_list_services_disabled_returns_placeholders():
    control = DockerControl(enabled=False, socket_path="/nope", project="local-llm")
    services = await control.list_services()
    assert [s["name"] for s in services] == list(DockerControl.ALLOWED_SERVICES)
    assert all(not s["running"] and not s["exists"] for s in services)
