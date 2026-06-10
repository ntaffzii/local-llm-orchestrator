from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import httpx


class LlamaClient:
    def __init__(self, base_url: str, timeout: float, attempts: int = 2, backoff: float = 0.5) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.attempts = max(1, attempts)
        self.backoff = max(0.0, backoff)

    async def get_json(self, path: str) -> Any:
        return await self._request_json("GET", path)

    async def post_json(self, path: str, payload: dict[str, Any]) -> Any:
        return await self._request_json("POST", path, payload)

    async def _request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        last_error: httpx.HTTPError | None = None
        for attempt in range(self.attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(method, f"{self.base_url}{path}", json=payload)
                    response.raise_for_status()
                    return response.json()
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
                last_error = exc
                if attempt + 1 < self.attempts:
                    await asyncio.sleep(self.backoff * (2**attempt))
        assert last_error is not None
        raise last_error

    async def stream(self, path: str, payload: dict[str, Any]) -> AsyncIterator[bytes]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", f"{self.base_url}{path}", json=payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_raw():
                    yield chunk
