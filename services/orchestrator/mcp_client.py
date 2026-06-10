from __future__ import annotations

import json
from contextlib import AsyncExitStack
from typing import Any


class McpClient:
    def __init__(self, enabled: bool, server_url: str, allowlist: tuple[str, ...] = ()) -> None:
        self.enabled = enabled
        self.server_url = server_url
        self.allowlist = frozenset(allowlist)

    async def list_openai_tools(self) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        async with self._session() as session:
            result = await session.list_tools()
        tools = []
        for tool in result.tools:
            if self.allowlist and tool.name not in self.allowlist:
                continue
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.inputSchema or {"type": "object", "properties": {}},
                    },
                }
            )
        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("MCP integration is disabled")
        if self.allowlist and name not in self.allowlist:
            raise PermissionError(f"MCP tool is not allowed: {name}")
        async with self._session() as session:
            result = await session.call_tool(name, arguments=arguments)
        content = []
        for item in result.content:
            if hasattr(item, "model_dump"):
                content.append(item.model_dump(mode="json"))
            else:
                content.append({"type": "text", "text": str(item)})
        return {"is_error": bool(result.isError), "content": content}

    def _session(self):
        return _McpSessionContext(self.server_url)


class _McpSessionContext:
    def __init__(self, server_url: str) -> None:
        self.server_url = server_url
        self.stack = AsyncExitStack()

    async def __aenter__(self):
        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamable_http_client
        except ImportError as exc:
            raise RuntimeError("Install the 'mcp' package to enable MCP integration") from exc
        read_stream, write_stream, _ = await self.stack.enter_async_context(streamable_http_client(self.server_url))
        session = await self.stack.enter_async_context(ClientSession(read_stream, write_stream))
        await session.initialize()
        return session

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.stack.aclose()


def tool_result_text(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, separators=(",", ":"))
