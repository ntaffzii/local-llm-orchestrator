import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest

from services.orchestrator.config import load_model_config
from services.orchestrator.prompt_service import contains_thai
from services.orchestrator.registry import ModelRegistry
from services.orchestrator.router import RequestRouter
from services.orchestrator.schemas import OrchestrateRequest
from services.orchestrator.service import OrchestratorService


CONFIG = load_model_config(Path(__file__).parents[1] / "config" / "models.json")


def test_contains_thai_detects_thai_script_only():
    assert contains_thai("ช่วยเขียน API ระบบล็อกอิน") is True
    assert contains_thai("mixed ข้อความ text") is True
    assert contains_thai("Write a login API") is False
    assert contains_thai("") is False
    assert contains_thai(None) is False


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
async def test_thai_prompt_is_translated_before_improvement_and_answered_in_thai():
    # lfm2.5 (the dedicated prompt-improver) is unreliable at Thai, so Thai input must
    # be translated by the answering model first (one extra round trip), improved as
    # plain English by lfm2.5 as usual, then answered with an instruction to respond
    # in Thai -- no separate "translate the answer back" call.
    client = AsyncMock()
    client.post_json.side_effect = [
        {"choices": [{"message": {"content": "Help write a login API."}}]},
        {"choices": [{"message": {"content": "Write a documented login API with tests."}}]},
        {"choices": [{"message": {"content": "done"}, "finish_reason": "stop"}]},
    ]
    mcp = AsyncMock()
    service = OrchestratorService(client, mcp, RequestRouter(ModelRegistry(CONFIG)), CONFIG)
    request = OrchestrateRequest(
        model="main-llm-improved",
        messages=[{"role": "user", "content": "ช่วยเขียน API ระบบล็อกอิน"}],
    )

    response = await service.orchestrate(request)

    assert response["choices"][0]["message"]["content"] == "done"
    calls = client.post_json.await_args_list
    assert len(calls) == 3

    # 1. Translate with the *answering* model/provider (not the prompt improver).
    translate_call = calls[0].args
    assert translate_call[0] == "main"
    assert translate_call[2]["model"] == "gemma4-e2b"
    assert translate_call[2]["messages"][-1]["content"] == "ช่วยเขียน API ระบบล็อกอิน"

    # 2. Improve the now-English text on the dedicated prompt provider, as usual.
    improve_call = calls[1].args
    assert improve_call[0] == "prompt"
    assert improve_call[2]["model"] == "lfm2.5-prompt"
    assert "Help write a login API." in improve_call[2]["messages"][-1]["content"]

    # 3. Final answer call gets the improved English prompt plus a Thai-response note.
    # (improve_prompt's real guardrail pass may append extra required-guardrail lines
    # to the mocked "improved" text, so check the shape rather than an exact match.)
    final_call = calls[2].args
    assert final_call[0] == "main"
    assert final_call[2]["model"] == "gemma4-e2b"
    final_content = final_call[2]["messages"][-1]["content"]
    assert final_content.startswith("Write a documented login API with tests.")
    assert final_content.endswith("\n\nRespond in Thai.")


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
        messages=[{"role": "user", "content": "help me build an api"}],
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


@pytest.mark.asyncio
async def test_allowed_models_scope_blocks_prompt_model_override():
    # A key scoped to a specific set of models must not be able to redirect
    # prompt-improvement to a model outside that scope via `prompt_model` -- that
    # would let a restricted key reach an unauthorized model/provider.
    client = AsyncMock()
    mcp = AsyncMock()
    service = OrchestratorService(client, mcp, RequestRouter(ModelRegistry(CONFIG)), CONFIG)
    request = OrchestrateRequest(
        model="main-llm",
        improve_prompt=True,
        prompt_model="coding",
        messages=[{"role": "user", "content": "Build API"}],
    )

    with pytest.raises(PermissionError):
        await service.orchestrate(request, allowed_models={"main-llm"})

    # No upstream call should have been made -- the check happens before any call.
    client.post_json.assert_not_awaited()


@pytest.mark.asyncio
async def test_orchestrate_stream_streams_real_tokens_after_prompt_improvement():
    # The improved-prompt path should still block through the (fast, mocked) rewrite
    # call, but the final generation must come through as real incremental chunks
    # from client.stream(), not one buffered chunk after everything finishes.
    client = AsyncMock()
    client.post_json.return_value = {"choices": [{"message": {"content": "Write a documented REST API."}}]}

    async def fake_stream(provider, path, payload):
        assert provider == "main"
        assert payload["stream"] is True
        assert payload["messages"][-1]["content"].startswith("Write a documented REST API.")
        yield b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'
        yield b'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
        yield b"data: [DONE]\n\n"

    # client.stream must return an async iterator directly (like the real
    # ProviderClients.stream(), an async-generator function) -- AsyncMock's default
    # call machinery returns a coroutine instead, which `async for` can't consume.
    client.stream = fake_stream
    mcp = AsyncMock()
    service = OrchestratorService(client, mcp, RequestRouter(ModelRegistry(CONFIG)), CONFIG)
    request = OrchestrateRequest(model="main-llm-improved", messages=[{"role": "user", "content": "Build API"}])

    chunks = [chunk async for chunk in service.orchestrate_stream(request)]

    assert chunks == [
        b'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n',
        b'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n',
        b"data: [DONE]\n\n",
    ]
    prompt_call = client.post_json.await_args_list[0].args
    assert prompt_call[0] == "prompt"


@pytest.mark.asyncio
async def test_orchestrate_stream_sends_heartbeats_while_blocked():
    # With a near-zero heartbeat interval, a slow (mocked) prompt-improve call must
    # surface keep-alive SSE comments before the final streamed content -- otherwise
    # the connection looks dead to clients for the whole blocking duration.
    client = AsyncMock()

    async def slow_post_json(provider, path, payload):
        await asyncio.sleep(0.05)
        return {"choices": [{"message": {"content": "Improved."}}]}

    client.post_json.side_effect = slow_post_json

    async def fake_stream(provider, path, payload):
        yield b"data: [DONE]\n\n"

    client.stream = fake_stream
    mcp = AsyncMock()
    service = OrchestratorService(
        client, mcp, RequestRouter(ModelRegistry(CONFIG)), CONFIG, heartbeat_interval=0.01
    )
    request = OrchestrateRequest(model="main-llm-improved", messages=[{"role": "user", "content": "Build API"}])

    chunks = [chunk async for chunk in service.orchestrate_stream(request)]

    assert chunks.count(b": keep-alive\n\n") > 0
    assert chunks[-1] == b"data: [DONE]\n\n"


@pytest.mark.asyncio
async def test_orchestrate_stream_emits_sse_error_on_upstream_failure_during_improve():
    # A blocking phase (prompt-improve here) now runs *inside* the streaming
    # generator, after the ASGI response has already committed to 200 -- an
    # unhandled exception here would crash the app the same way the old
    # non-streaming upstream-error bug did. It must degrade to an SSE error event.
    client = AsyncMock()
    upstream_response = httpx.Response(400, json={"error": "context length exceeded"}, request=httpx.Request("POST", "http://x"))
    client.post_json.side_effect = httpx.HTTPStatusError("bad request", request=upstream_response.request, response=upstream_response)
    mcp = AsyncMock()
    service = OrchestratorService(client, mcp, RequestRouter(ModelRegistry(CONFIG)), CONFIG)
    request = OrchestrateRequest(model="main-llm-improved", messages=[{"role": "user", "content": "Build API"}])

    chunks = [chunk async for chunk in service.orchestrate_stream(request)]

    assert len(chunks) == 1
    body = chunks[0].decode("utf-8")
    assert body.startswith("data: ")
    event = json.loads(body.split("\n\n")[0][len("data: "):])
    assert event["error"]["status"] == 400
    assert "data: [DONE]" in body


@pytest.mark.asyncio
async def test_orchestrate_stream_emits_sse_error_on_unknown_model():
    # registry.selection() raises a plain KeyError for an unknown model id -- that is
    # not an httpx exception, so it must be caught separately or it crashes the ASGI
    # app mid-stream (the response has already committed to 200 by this point) the
    # same way unhandled upstream errors used to.
    client = AsyncMock()
    mcp = AsyncMock()
    service = OrchestratorService(client, mcp, RequestRouter(ModelRegistry(CONFIG)), CONFIG)
    request = OrchestrateRequest(model="does-not-exist", messages=[{"role": "user", "content": "hi"}])

    chunks = [chunk async for chunk in service.orchestrate_stream(request)]

    assert len(chunks) == 1
    body = chunks[0].decode("utf-8")
    event = json.loads(body.split("\n\n")[0][len("data: "):])
    assert event["error"]["status"] == 404
    assert "data: [DONE]" in body


@pytest.mark.asyncio
async def test_orchestrate_stream_emits_sse_error_when_prompt_model_outside_scope():
    client = AsyncMock()
    mcp = AsyncMock()
    service = OrchestratorService(client, mcp, RequestRouter(ModelRegistry(CONFIG)), CONFIG)
    request = OrchestrateRequest(
        model="main-llm",
        improve_prompt=True,
        prompt_model="coding",
        messages=[{"role": "user", "content": "Build API"}],
    )

    chunks = [chunk async for chunk in service.orchestrate_stream(request, allowed_models={"main-llm"})]

    assert len(chunks) == 1
    body = chunks[0].decode("utf-8")
    event = json.loads(body.split("\n\n")[0][len("data: "):])
    assert event["error"]["status"] == 403
    client.post_json.assert_not_awaited()


@pytest.mark.asyncio
async def test_orchestrate_stream_tool_loop_stays_buffered_as_single_chunk():
    # Tool-loop responses can't be split into real tokens after the fact (the tool
    # trace only exists once the whole loop finishes), so this path stays a single
    # buffered SSE chunk -- confirm it still round-trips correctly through the
    # streaming entrypoint.
    client = AsyncMock()
    client.post_json.return_value = {"choices": [{"message": {"content": "answered without tools"}, "finish_reason": "stop"}]}
    mcp = AsyncMock()
    mcp.list_openai_tools.return_value = [
        {"type": "function", "function": {"name": "search", "parameters": {"type": "object"}}}
    ]
    service = OrchestratorService(client, mcp, RequestRouter(ModelRegistry(CONFIG)), CONFIG)
    request = OrchestrateRequest(
        model="main-llm-tools", improve_prompt=False, messages=[{"role": "user", "content": "Search"}]
    )

    chunks = [chunk async for chunk in service.orchestrate_stream(request, allowed_tools={"route_request"})]

    assert len(chunks) == 2
    assert chunks[1] == b"data: [DONE]\n\n"
    event = json.loads(chunks[0].decode("utf-8")[len("data: "):].split("\n\n")[0])
    assert event["choices"][0]["delta"]["content"] == "answered without tools"
