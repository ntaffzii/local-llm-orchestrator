from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import os
import re
from typing import Any

import httpx


_ENV_REF = re.compile(r"^\$\{(\w+)\}$")


def resolve_base_url(raw: str | None, default: str) -> str:
    """Resolve a provider base_url, expanding a ``${ENV_VAR}`` reference.

    An unset or empty env var (or an empty literal) falls back to ``default`` so a
    provider can point at a dedicated service in one deployment and transparently
    reuse the shared router in another.
    """
    value = (raw or "").strip()
    match = _ENV_REF.match(value)
    if match:
        return os.getenv(match.group(1), "").strip() or default
    return value or default


class LlamaClient:
    def __init__(
        self,
        base_url: str,
        timeout: float,
        attempts: int = 2,
        backoff: float = 0.5,
        api_key: str = "",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.attempts = max(1, attempts)
        self.backoff = max(0.0, backoff)
        self.api_key = api_key

    async def get_json(self, path: str) -> Any:
        return await self._request_json("GET", path)

    async def post_json(self, path: str, payload: dict[str, Any]) -> Any:
        return await self._request_json("POST", path, payload)

    async def _request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        last_error: httpx.HTTPError | None = None
        for attempt in range(self.attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(method, self._url(path), json=payload, headers=self._headers())
                    response.raise_for_status()
                    return response.json()
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
                last_error = exc
                if attempt + 1 < self.attempts:
                    await asyncio.sleep(self.backoff * (2**attempt))
        assert last_error is not None
        raise last_error

    async def ping(self, path: str = "/health", timeout: float = 2.0) -> Any:
        # A single-attempt, short-timeout probe for readiness checks -- retries and the
        # long request timeout make a health snapshot needlessly slow.
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(self._url(path), headers=self._headers())
            response.raise_for_status()
            return response.json()

    async def stream(self, path: str, payload: dict[str, Any]) -> AsyncIterator[bytes]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", self._url(path), json=payload, headers=self._headers()) as response:
                response.raise_for_status()
                async for chunk in response.aiter_raw():
                    yield chunk

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            return {}
        return {"Authorization": f"Bearer {self.api_key}"}

    def _url(self, path: str) -> str:
        if self.base_url.endswith("/v1") and path.startswith("/v1/"):
            path = path[3:]
        return f"{self.base_url}{path}"


class ProviderClients:
    def __init__(
        self,
        providers: dict[str, Any],
        timeout: float,
        attempts: int = 2,
        backoff: float = 0.5,
        default_base_url: str = "http://127.0.0.1:8080",
    ) -> None:
        provider_config = dict(providers or {})
        provider_config.setdefault("local", {"base_url": default_base_url})
        self.clients = {
            name: LlamaClient(
                resolve_base_url(details.get("base_url"), default_base_url),
                timeout,
                attempts=attempts,
                backoff=backoff,
                api_key=self._api_key(details),
            )
            for name, details in provider_config.items()
        }

    async def get_json(self, provider: str, path: str) -> Any:
        return await self._client(provider).get_json(path)

    async def ping(self, provider: str, timeout: float = 2.0) -> Any:
        return await self._client(provider).ping(timeout=timeout)

    async def post_json(self, provider: str, path: str, payload: dict[str, Any]) -> Any:
        return await self._client(provider).post_json(path, payload)

    async def stream(self, provider: str, path: str, payload: dict[str, Any]) -> AsyncIterator[bytes]:
        async for chunk in self._client(provider).stream(path, payload):
            yield chunk

    def _client(self, provider: str) -> LlamaClient:
        try:
            return self.clients[provider]
        except KeyError as exc:
            raise KeyError(f"provider_not_found:{provider}") from exc

    @staticmethod
    def _api_key(details: dict[str, Any]) -> str:
        if details.get("api_key"):
            return str(details["api_key"])
        env_name = details.get("api_key_env")
        if env_name:
            return os.getenv(str(env_name), "")
        return ""
