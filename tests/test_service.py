from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from services.orchestrator.config import load_model_config
from services.orchestrator.registry import ModelRegistry
from services.orchestrator.router import RequestRouter
from services.orchestrator.schemas import OrchestrateRequest
from services.orchestrator.service import OrchestratorService


CONFIG = load_model_config(Path(__file__).parents[1] / "config" / "models.json")


@pytest.mark.asyncio
async def test_improved_virtual_model_rewrites_then_calls_main():
    client = AsyncMock()
    client.post_json.side_effect = [
        {"choices": [{"message": {"content": "Write a documented REST API with tests."}}]},
        {"choices": [{"message": {"content": "done"}, "finish_reason": "stop"}]},
    ]
    mcp = AsyncMock()
    service = OrchestratorService(client, mcp, RequestRouter(ModelRegistry(CONFIG)), CONFIG)
    request = OrchestrateRequest(
        model="main-llm-improved",
        messages=[{"role": "user", "content": "Build API"}],
    )

    response = await service.orchestrate(request)

    assert response["choices"][0]["message"]["content"] == "done"
    final_payload = client.post_json.await_args_list[1].args[1]
    assert final_payload["model"] == "gemma4-e2b"
    assert final_payload["messages"][-1]["content"].startswith("Write a documented")


@pytest.mark.asyncio
async def test_tool_model_executes_mcp_tool_and_returns_final_answer():
    client = AsyncMock()
    client.post_json.side_effect = [
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {"name": "search", "arguments": "{\"query\":\"local llm\"}"},
                            }
                        ],
                    }
                }
            ]
        },
        {"choices": [{"message": {"content": "final answer"}, "finish_reason": "stop"}]},
    ]
    mcp = AsyncMock()
    mcp.list_openai_tools.return_value = [
        {"type": "function", "function": {"name": "search", "parameters": {"type": "object"}}}
    ]
    mcp.call_tool.return_value = {"is_error": False, "content": [{"type": "text", "text": "result"}]}
    service = OrchestratorService(client, mcp, RequestRouter(ModelRegistry(CONFIG)), CONFIG)
    request = OrchestrateRequest(
        model="main-llm-tools",
        improve_prompt=False,
        messages=[{"role": "user", "content": "Search for local LLM information"}],
    )

    response = await service.orchestrate(request)

    assert response["choices"][0]["message"]["content"] == "final answer"
    mcp.call_tool.assert_awaited_once_with("search", {"query": "local llm"})
    first_payload = client.post_json.await_args_list[0].args[1]
    assert first_payload["messages"][0]["role"] == "system"
    assert "route_request" in first_payload["messages"][0]["content"]
