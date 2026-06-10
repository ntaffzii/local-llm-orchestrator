from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from typing import Any

from .llama_client import LlamaClient
from .mcp_client import McpClient, tool_result_text
from .prompt_service import improve_prompt
from .registry import ModelSelection
from .router import RequestRouter
from .schemas import ChatRequest, OrchestrateRequest


class OrchestratorService:
    def __init__(
        self,
        client: LlamaClient,
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

    async def orchestrate(self, request: OrchestrateRequest) -> dict[str, Any]:
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
                return await self._run_tool_loop(payload)
            return await self.client.post_json("/v1/chat/completions", payload)

    async def _rewrite_last_user(self, messages: list[dict[str, Any]], prompt_model: str | None) -> None:
        target_prompt_model = self.config["routing"]["prompt_model"]
        if prompt_model:
            target_prompt_model = self.router.registry.selection(prompt_model).target
        for message in reversed(messages):
            if message.get("role") == "user" and isinstance(message.get("content"), str):
                message["content"] = await improve_prompt(
                    self.client,
                    message["content"],
                    self.config,
                    model=target_prompt_model,
                )
                return

    async def _run_tool_loop(self, payload: dict[str, Any]) -> dict[str, Any]:
        tools = await self.mcp.list_openai_tools()
        if not tools:
            payload.pop("tools", None)
            payload.pop("tool_choice", None)
            return await self.client.post_json("/v1/chat/completions", payload)
        payload["tools"] = tools
        payload.setdefault("tool_choice", "auto")
        max_rounds = int(self.config["orchestration"].get("max_tool_rounds", 4))

        for _ in range(max_rounds):
            response = await self.client.post_json("/v1/chat/completions", payload)
            message = response["choices"][0]["message"]
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                return response
            payload["messages"].append(deepcopy(message))
            for tool_call in tool_calls:
                function = tool_call["function"]
                arguments = function.get("arguments", {})
                if isinstance(arguments, str):
                    arguments = json.loads(arguments or "{}")
                result = await self.mcp.call_tool(function["name"], arguments)
                payload["messages"].append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": function["name"],
                        "content": tool_result_text(result),
                    }
                )
        raise RuntimeError(f"Tool loop exceeded {max_rounds} rounds")

    @staticmethod
    def _apply_defaults(payload: dict[str, Any], selection: ModelSelection) -> None:
        for key in ("temperature", "max_tokens"):
            if payload.get(key) is None and key in selection.defaults:
                payload[key] = selection.defaults[key]

    def _inject_skill_agent_prompt(self, messages: list[dict[str, Any]]) -> None:
        skill_agent = self.config.get("skill_agent", {})
        prompt = skill_agent.get("system_prompt", "").strip()
        if not skill_agent.get("enabled", False) or not prompt:
            return
        for message in messages:
            if message.get("role") in {"system", "developer"} and message.get("content") == prompt:
                return
        messages.insert(0, {"role": "system", "content": prompt})
