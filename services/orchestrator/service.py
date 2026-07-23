from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from typing import Any

from .llama_client import ProviderClients
from .mcp_client import McpClient, tool_result_text
from .prompt_service import improve_prompt
from .registry import ModelSelection
from .router import RequestRouter
from .schemas import ChatRequest, OrchestrateRequest


class OrchestratorService:
    def __init__(
        self,
        client: ProviderClients,
        mcp: McpClient,
        router: RequestRouter,
        config: dict[str, Any],
    ) -> None:
        self.client = client
        self.mcp = mcp
        self.router = router
        self.config = config
        limit = int(config["orchestration"].get("max_concurrent_workflows", 2))
        self.workflow_slots = asyncio.Semaphore(max(1, limit))

    def prepare_direct(self, request: ChatRequest) -> tuple[dict[str, Any], ModelSelection]:
        selection = self.router.route(request.model, request.messages)
        payload = request.model_dump(exclude_none=True)
        payload["model"] = selection.target
        self._apply_defaults(payload, selection)
        return payload, selection

    async def orchestrate(
        self, request: OrchestrateRequest, allowed_tools: set[str] | None = None
    ) -> dict[str, Any]:
        async with self.workflow_slots:
            selection = self.router.route(request.model, request.messages)
            messages = [message.model_dump(exclude_none=True) for message in request.messages]
            improve_policy = request.improve_prompt if request.improve_prompt is not None else selection.improve_prompt
            tools_policy = request.use_tools if request.use_tools is not None else selection.use_tools

            if self.router.should_improve(improve_policy, request.messages):
                await self._rewrite_last_user(messages, request.prompt_model)

            use_tools = self.router.should_use_tools(tools_policy, request.messages)
            if use_tools:
                self._inject_skill_agent_prompt(messages)

            payload = request.model_dump(exclude_none=True)
            for key in ("improve_prompt", "use_tools", "prompt_model"):
                payload.pop(key, None)
            payload.update({"model": selection.target, "messages": messages, "stream": False})
            self._apply_defaults(payload, selection)

            if use_tools:
                return await self._run_tool_loop(selection.provider, payload, allowed_tools)
            return await self.client.post_json(selection.provider, "/v1/chat/completions", payload)

    async def _rewrite_last_user(self, messages: list[dict[str, Any]], prompt_model: str | None) -> None:
        target_prompt_model = self.config.get("prompt_improver", {}).get("model") or self.config["routing"]["prompt_model"]
        prompt_selection = self.router.registry.selection(prompt_model or target_prompt_model)
        for message in reversed(messages):
            if message.get("role") == "user" and isinstance(message.get("content"), str):
                message["content"] = await improve_prompt(
                    self.client,
                    message["content"],
                    self.config,
                    selection=prompt_selection,
                )
                return

    async def _run_tool_loop(
        self, provider: str, payload: dict[str, Any], allowed_tools: set[str] | None = None
    ) -> dict[str, Any]:
        tool_trace: list[dict[str, Any]] = []
        try:
            tools = await self.mcp.list_openai_tools()
        except Exception as exc:
            payload.pop("tools", None)
            payload.pop("tool_choice", None)
            payload["messages"].append(
                {
                    "role": "user",
                    "content": f"MCP tools are unavailable: {exc}. Answer without using tools.",
                }
            )
            response = await self.client.post_json(provider, "/v1/chat/completions", payload)
            return self._attach_tool_trace(
                response,
                [
                    {
                        "round": 0,
                        "name": "__mcp_unavailable__",
                        "arguments": {},
                        "is_error": True,
                        "error": str(exc),
                    }
                ],
            )
        if allowed_tools is not None:
            # Per-key tools scope: only offer the tools this key may use.
            tools = [tool for tool in tools if (tool.get("function") or {}).get("name") in allowed_tools]
        if not tools:
            payload.pop("tools", None)
            payload.pop("tool_choice", None)
            response = await self.client.post_json(provider, "/v1/chat/completions", payload)
            return self._attach_tool_trace(response, tool_trace)
        payload["tools"] = tools
        payload.setdefault("tool_choice", "auto")
        max_rounds = int(self.config["orchestration"].get("max_tool_rounds", 4))
        tool_rounds = 0
        seen_tool_calls: set[str] = set()
        while True:
            response = await self.client.post_json(provider, "/v1/chat/completions", payload)
            message = response["choices"][0]["message"]
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                return self._attach_tool_trace(response, tool_trace)
            if tool_rounds >= max_rounds:
                return await self._finish_tool_loop(provider, payload, f"Tool loop reached {max_rounds} rounds.", tool_trace)

            repeated_call = self._find_repeated_tool_call(tool_calls, seen_tool_calls)
            if repeated_call:
                return await self._finish_tool_loop(
                    provider,
                    payload,
                    f"Repeated MCP tool call detected: {repeated_call}.",
                    tool_trace,
                )

            payload["messages"].append(deepcopy(message))
            for tool_call in tool_calls:
                function = tool_call["function"]
                arguments = function.get("arguments", {})
                if isinstance(arguments, str):
                    arguments = json.loads(arguments or "{}")
                seen_tool_calls.add(self._tool_call_signature(function["name"], arguments))
                if allowed_tools is not None and function["name"] not in allowed_tools:
                    result = {
                        "is_error": True,
                        "content": [{"type": "text", "text": f"Tool not permitted for this key: {function['name']}"}],
                    }
                else:
                    try:
                        result = await self.mcp.call_tool(function["name"], arguments)
                    except Exception as exc:
                        result = {"is_error": True, "content": [{"type": "text", "text": f"MCP tool failed: {exc}"}]}
                tool_trace.append(
                    {
                        "round": tool_rounds + 1,
                        "id": tool_call.get("id"),
                        "name": function["name"],
                        "arguments": arguments,
                        "is_error": bool(result.get("is_error")),
                        "result_preview": self._tool_result_preview(result),
                    }
                )
                payload["messages"].append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": function["name"],
                        "content": tool_result_text(result),
                    }
                )
            tool_rounds += 1

    async def _finish_tool_loop(
        self,
        provider: str,
        payload: dict[str, Any],
        reason: str,
        tool_trace: list[dict[str, Any]],
    ) -> dict[str, Any]:
        final_payload = deepcopy(payload)
        final_payload.pop("tools", None)
        final_payload.pop("tool_choice", None)
        final_payload["messages"].append(
            {
                "role": "user",
                "content": (
                    f"{reason} Stop calling MCP tools now. "
                    "Use the tool results already present in the conversation and provide the final answer. "
                    "If the available tool results are insufficient, say what is missing instead of calling another tool."
                ),
            }
        )
        response = await self.client.post_json(provider, "/v1/chat/completions", final_payload)
        return self._attach_tool_trace(response, tool_trace)

    def _find_repeated_tool_call(self, tool_calls: list[dict[str, Any]], seen: set[str]) -> str | None:
        for tool_call in tool_calls:
            function = tool_call["function"]
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                arguments = json.loads(arguments or "{}")
            signature = self._tool_call_signature(function["name"], arguments)
            if signature in seen:
                return signature
        return None

    @staticmethod
    def _tool_call_signature(name: str, arguments: dict[str, Any]) -> str:
        return f"{name}:{json.dumps(arguments, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}"

    @staticmethod
    def _attach_tool_trace(response: dict[str, Any], tool_trace: list[dict[str, Any]]) -> dict[str, Any]:
        response["tool_trace"] = tool_trace
        return response

    @staticmethod
    def _tool_result_preview(result: dict[str, Any]) -> str:
        content = result.get("content")
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    texts.append(item["text"])
            if texts:
                return "\n".join(texts)[:500]
        return tool_result_text(result)[:500]

    @staticmethod
    def _apply_defaults(payload: dict[str, Any], selection: ModelSelection) -> None:
        for key in ("temperature", "max_tokens", "chat_template_kwargs"):
            if payload.get(key) is None and key in selection.defaults:
                payload[key] = selection.defaults[key]

        if "stop" not in selection.defaults:
            return
        target_stops = selection.defaults["stop"]
        if not isinstance(target_stops, list):
            target_stops = [target_stops]

        client_stops = payload.get("stop")
        if client_stops is None:
            payload["stop"] = target_stops
        elif isinstance(client_stops, str):
            payload["stop"] = list(dict.fromkeys([client_stops] + target_stops))
        elif isinstance(client_stops, list):
            payload["stop"] = list(dict.fromkeys(client_stops + target_stops))

    def _inject_skill_agent_prompt(self, messages: list[dict[str, Any]]) -> None:
        skill_agent = self.config.get("skill_agent", {})
        prompt = skill_agent.get("system_prompt", "").strip()
        if not skill_agent.get("enabled", False) or not prompt:
            return
        for message in messages:
            if message.get("role") != "system":
                continue
            content = message.get("content")
            if content == prompt or (isinstance(content, str) and prompt in content):
                return
            if isinstance(content, str):
                message["content"] = f"{content.rstrip()}\n\n{prompt}"
                return
        messages.insert(0, {"role": "system", "content": prompt})
