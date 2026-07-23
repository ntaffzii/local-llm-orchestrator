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
    prompt_call = client.post_json.await_args_list[0].args
    assert prompt_call[0] == "prompt"
    assert prompt_call[2]["model"] == "lfm2.5-prompt"
    final_payload = client.post_json.await_args_list[1].args[2]
    assert client.post_json.await_args_list[1].args[0] == "main"
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
    assert response["tool_trace"] == [
        {
            "round": 1,
            "id": "call-1",
            "name": "search",
            "arguments": {"query": "local llm"},
            "is_error": False,
            "result_preview": "result",
        }
    ]
    mcp.call_tool.assert_awaited_once_with("search", {"query": "local llm"})
    first_payload = client.post_json.await_args_list[0].args[2]
    assert first_payload["messages"][0]["role"] == "system"
    assert "route_request" in first_payload["messages"][0]["content"]
    assert "prompt_consult first" in first_payload["messages"][0]["content"]
    assert "prompt_improve_rule_based after prompt_consult" in first_payload["messages"][0]["content"]
    assert "do not execute the improved prompt" in first_payload["messages"][0]["content"]
    assert "do not write the final code" in first_payload["messages"][0]["content"]
    assert "tools used, detected task type, quality score" in first_payload["messages"][0]["content"]
    assert "For skill/workflow selection requests, call route_request at most once" in first_payload["messages"][0]["content"]
    assert "do not claim that no SKILL.md files exist unless you explicitly searched for SKILL.md" in first_payload["messages"][0]["content"]


def test_model_defaults_include_stop_and_chat_template_kwargs():
    service = OrchestratorService(AsyncMock(), AsyncMock(), RequestRouter(ModelRegistry(CONFIG)), CONFIG)
    selection = ModelRegistry(CONFIG).selection("qwen-tools")
    payload = {"model": selection.target, "messages": [{"role": "user", "content": "hi"}], "stop": ["custom"]}

    service._apply_defaults(payload, selection)

    assert payload["temperature"] == 0.1
    assert payload["max_tokens"] == 1536
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert payload["stop"] == ["custom", "<|im_end|>", "<|im_start|>"]


@pytest.mark.asyncio
async def test_virtual_model_can_use_remote_provider_after_local_prompt_rewrite():
    config = {
        **CONFIG,
        "providers": {
            **CONFIG["providers"],
            "openrouter": {
                "type": "openai-compatible",
                "base_url": "https://openrouter.ai/api/v1",
                "api_key_env": "OPENROUTER_API_KEY",
            },
        },
        "virtual_models": {
            **CONFIG["virtual_models"],
            "remote-main-improved": {
                "provider": "openrouter",
                "model": "openai/gpt-4.1-mini",
                "improve_prompt": True,
                "tools": False,
            },
        },
    }
    client = AsyncMock()
    client.post_json.side_effect = [
        {"choices": [{"message": {"content": "Clarified prompt"}}]},
        {"choices": [{"message": {"content": "remote answer"}, "finish_reason": "stop"}]},
    ]
    mcp = AsyncMock()
    service = OrchestratorService(client, mcp, RequestRouter(ModelRegistry(config)), config)
    request = OrchestrateRequest(
        model="remote-main-improved",
        messages=[{"role": "user", "content": "ช่วยทำ api"}],
    )

    response = await service.orchestrate(request)

    assert response["choices"][0]["message"]["content"] == "remote answer"
    # The prompt rewrite runs on the dedicated prompt provider; the main answer is remote.
    assert client.post_json.await_args_list[0].args[0] == "prompt"
    assert client.post_json.await_args_list[1].args[0] == "openrouter"
    assert client.post_json.await_args_list[1].args[2]["model"] == "openai/gpt-4.1-mini"


@pytest.mark.asyncio
async def test_tool_loop_exceeded_max_rounds_finishes_without_tools():
    config = {
        **CONFIG,
        "orchestration": {
            **CONFIG.get("orchestration", {}),
            "max_tool_rounds": 2,
        }
    }
    client = AsyncMock()
    # Mocking 3 unique rounds of tool calls, then a forced final answer without tools.
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
                                "function": {"name": "search", "arguments": "{\"round\":1}"},
                            }
                        ],
                    }
                }
            ]
        },
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call-2",
                                "type": "function",
                                "function": {"name": "search", "arguments": "{\"round\":2}"},
                            }
                        ],
                    }
                }
            ]
        },
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call-3",
                                "type": "function",
                                "function": {"name": "search", "arguments": "{\"round\":3}"},
                            }
                        ],
                    }
                }
            ]
        },
        {"choices": [{"message": {"content": "final after tool limit"}, "finish_reason": "stop"}]},
    ]
    mcp = AsyncMock()
    mcp.list_openai_tools.return_value = [
        {"type": "function", "function": {"name": "search", "parameters": {"type": "object"}}}
    ]
    mcp.call_tool.return_value = {"is_error": False, "content": [{"type": "text", "text": "result"}]}
    service = OrchestratorService(client, mcp, RequestRouter(ModelRegistry(config)), config)
    request = OrchestrateRequest(
        model="main-llm-tools",
        improve_prompt=False,
        messages=[{"role": "user", "content": "Search request"}],
    )

    response = await service.orchestrate(request)

    assert response["choices"][0]["message"]["content"] == "final after tool limit"
    final_payload = client.post_json.await_args_list[-1].args[2]
    assert "tools" not in final_payload
    assert "tool_choice" not in final_payload
    assert final_payload["messages"][-1]["role"] == "user"
    assert "Stop calling MCP tools now" in final_payload["messages"][-1]["content"]
    assert response["tool_trace"] == [
        {
            "round": 1,
            "id": "call-1",
            "name": "search",
            "arguments": {"round": 1},
            "is_error": False,
            "result_preview": "result",
        },
        {
            "round": 2,
            "id": "call-2",
            "name": "search",
            "arguments": {"round": 2},
            "is_error": False,
            "result_preview": "result",
        },
    ]


@pytest.mark.asyncio
async def test_repeated_tool_call_finishes_without_tools():
    config = {
        **CONFIG,
        "orchestration": {
            **CONFIG.get("orchestration", {}),
            "max_tool_rounds": 4,
        }
    }
    repeated_tool_call = {
        "id": "call-1",
        "type": "function",
        "function": {"name": "search", "arguments": "{\"query\":\"local llm\"}"},
    }
    client = AsyncMock()
    client.post_json.side_effect = [
        {"choices": [{"message": {"role": "assistant", "content": "", "tool_calls": [repeated_tool_call]}}]},
        {"choices": [{"message": {"role": "assistant", "content": "", "tool_calls": [{**repeated_tool_call, "id": "call-2"}]}}]},
        {"choices": [{"message": {"content": "final after repeat"}, "finish_reason": "stop"}]},
    ]
    mcp = AsyncMock()
    mcp.list_openai_tools.return_value = [
        {"type": "function", "function": {"name": "search", "parameters": {"type": "object"}}}
    ]
    mcp.call_tool.return_value = {"is_error": False, "content": [{"type": "text", "text": "result"}]}
    service = OrchestratorService(client, mcp, RequestRouter(ModelRegistry(config)), config)
    request = OrchestrateRequest(
        model="main-llm-tools",
        improve_prompt=False,
        messages=[{"role": "user", "content": "Search request"}],
    )

    response = await service.orchestrate(request)

    assert response["choices"][0]["message"]["content"] == "final after repeat"
    assert mcp.call_tool.await_count == 1
    assert response["tool_trace"] == [
        {
            "round": 1,
            "id": "call-1",
            "name": "search",
            "arguments": {"query": "local llm"},
            "is_error": False,
            "result_preview": "result",
        }
    ]


@pytest.mark.asyncio
async def test_allowed_tools_scope_filters_offered_tools():
    client = AsyncMock()
    client.post_json.return_value = {"choices": [{"message": {"content": "answered without tools"}, "finish_reason": "stop"}]}
    mcp = AsyncMock()
    mcp.list_openai_tools.return_value = [
        {"type": "function", "function": {"name": "search", "parameters": {"type": "object"}}}
    ]
    service = OrchestratorService(client, mcp, RequestRouter(ModelRegistry(CONFIG)), CONFIG)
    request = OrchestrateRequest(
        model="main-llm-tools",
        improve_prompt=False,
        messages=[{"role": "user", "content": "Search for local LLM information"}],
    )

    # The key may only use "route_request", so "search" is filtered out -> no tools offered.
    response = await service.orchestrate(request, allowed_tools={"route_request"})

    assert response["choices"][0]["message"]["content"] == "answered without tools"
    mcp.call_tool.assert_not_awaited()
    payload = client.post_json.await_args_list[0].args[2]
    assert "tools" not in payload
