from __future__ import annotations

import json
from typing import Any

import httpx


class DockerControlDisabled(RuntimeError):
    """Raised when a control action is attempted while control is turned off."""


class DockerControlError(RuntimeError):
    """Raised when the Docker Engine API cannot be reached or returns an error."""


class DockerControl:
    """Start/stop a fixed allowlist of model containers via the Docker Engine API.

    Talks to the Docker socket over httpx (no extra dependency). This is powerful --
    socket access is roughly host root -- so it is disabled by default, gated by the
    admin key at the API layer, and hard-limited to ALLOWED_SERVICES here so it can
    never touch an arbitrary container even if the caller asks.
    """

    ALLOWED_SERVICES: tuple[str, ...] = ("llama-main", "llama-prompt")

    def __init__(self, enabled: bool, socket_path: str, project: str, timeout: float = 10.0) -> None:
        self.enabled = bool(enabled)
        self.socket_path = socket_path
        self.project = project
        self.timeout = timeout

    def _client(self) -> httpx.AsyncClient:
        transport = httpx.AsyncHTTPTransport(uds=self.socket_path)
        return httpx.AsyncClient(transport=transport, base_url="http://docker", timeout=self.timeout)

    async def _project_containers(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        filters = json.dumps({"label": [f"com.docker.compose.project={self.project}"]})
        response = await client.get("/containers/json", params={"all": "1", "filters": filters})
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _service_of(container: dict[str, Any]) -> str | None:
        return (container.get("Labels") or {}).get("com.docker.compose.service")

    async def list_services(self) -> list[dict[str, Any]]:
        if not self.enabled:
            return [self._absent(name, "control disabled") for name in self.ALLOWED_SERVICES]
        try:
            async with self._client() as client:
                containers = await self._project_containers(client)
        except Exception as exc:
            raise DockerControlError(str(exc)) from exc
        found: dict[str, dict[str, Any]] = {}
        for container in containers:
            service = self._service_of(container)
            if service in self.ALLOWED_SERVICES:
                found[service] = {
                    "name": service,
                    "exists": True,
                    "running": container.get("State") == "running",
                    "status": container.get("Status", ""),
                    "container_id": (container.get("Id") or "")[:12],
                }
        return [found.get(name, self._absent(name, "not created")) for name in self.ALLOWED_SERVICES]

    @staticmethod
    def _absent(name: str, status: str) -> dict[str, Any]:
        return {"name": name, "exists": False, "running": False, "status": status, "container_id": ""}

    async def set_service(self, name: str, action: str) -> dict[str, Any]:
        if not self.enabled:
            raise DockerControlDisabled("Docker control is disabled")
        if name not in self.ALLOWED_SERVICES:
            raise PermissionError(f"Service is not controllable: {name}")
        if action not in ("start", "stop"):
            raise ValueError(f"Invalid action: {action}")
        try:
            async with self._client() as client:
                containers = await self._project_containers(client)
                target = next((c for c in containers if self._service_of(c) == name), None)
                if target is None:
                    raise DockerControlError(
                        f"Container for {name} not found; bring it up once with `--profile models`."
                    )
                response = await client.post(f"/containers/{target['Id']}/{action}")
                if response.status_code not in (204, 304):
                    response.raise_for_status()
        except (DockerControlDisabled, DockerControlError, PermissionError, ValueError):
            raise
        except Exception as exc:
            raise DockerControlError(str(exc)) from exc
        return {"success": True, "service": name, "action": action}
