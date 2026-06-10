from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .config import get_settings, load_model_config
from .llama_client import LlamaClient
from .mcp_client import McpClient
from .prompt_service import improve_prompt
from .registry import ModelRegistry
from .router import RequestRouter
from .schemas import ChatRequest, ImprovePromptRequest, OrchestrateRequest, ToolCallRequest
from .service import OrchestratorService


settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("local_llm.orchestrator")


def build_components() -> tuple[dict[str, Any], ModelRegistry, RequestRouter, LlamaClient, McpClient, OrchestratorService]:
    config = load_model_config(settings.model_config_path)
    registry = ModelRegistry(config)
    router = RequestRouter(registry)
    orchestration = config["orchestration"]
    llama = LlamaClient(
        settings.llama_base_url,
        settings.request_timeout,
        attempts=int(orchestration.get("retry_attempts", 2)),
        backoff=float(orchestration.get("retry_backoff_seconds", 0.5)),
    )
    mcp = McpClient(settings.mcp_enabled, settings.mcp_server_url, settings.mcp_tool_allowlist)
    service = OrchestratorService(llama, mcp, router, config)
    return config, registry, router, llama, mcp, service


model_config, registry, router, llama_client, mcp_client, orchestrator = build_components()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("orchestrator_started llama=%s mcp_enabled=%s", settings.llama_base_url, settings.mcp_enabled)
    yield
    logger.info("orchestrator_stopped")


app = FastAPI(
    title="Local LLM Orchestrator",
    description="OpenAI-compatible orchestration layer for llama.cpp and MCP tools.",
    version="1.0.0",
    lifespan=lifespan,
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request_failed id=%s method=%s path=%s", request_id, request.method, request.url.path)
        raise
    response.headers["X-Request-ID"] = request_id
    elapsed_ms = (time.perf_counter() - started) * 1000
    logger.info(
        "request_complete id=%s method=%s path=%s status=%s elapsed_ms=%.1f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


def require_api_key(authorization: str | None = Header(default=None)) -> None:
    if settings.api_key and authorization != f"Bearer {settings.api_key}":
        raise HTTPException(status_code=401, detail={"code": "invalid_api_key", "message": "Invalid API key"})


def upstream_error(exc: httpx.HTTPStatusError) -> HTTPException:
    try:
        detail: Any = exc.response.json()
    except ValueError:
        detail = exc.response.text
    return HTTPException(
        status_code=exc.response.status_code,
        detail={"code": "upstream_error", "message": "llama.cpp rejected the request", "upstream": detail},
    )


def workflow_required(request: ChatRequest) -> bool:
    selection = registry.selection(request.model)
    return selection.target == "auto" or selection.improve_prompt is not False or selection.use_tools is not False


def completion_as_sse(response: dict[str, Any]):
    choice = response.get("choices", [{}])[0]
    message = choice.get("message", {})
    chunk = {
        "id": response.get("id", f"chatcmpl-{uuid.uuid4().hex}"),
        "object": "chat.completion.chunk",
        "created": response.get("created", int(time.time())),
        "model": response.get("model", "local-orchestrator"),
        "choices": [
            {
                "index": choice.get("index", 0),
                "delta": {"role": "assistant", "content": message.get("content", "")},
                "finish_reason": choice.get("finish_reason", "stop"),
            }
        ],
    }
    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode("utf-8")
    yield b"data: [DONE]\n\n"


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "service": "local-llm-orchestrator", "version": app.version}


@app.get("/ready")
async def ready(_: None = Depends(require_api_key)) -> dict[str, Any]:
    try:
        upstream = await llama_client.get_json("/health")
        return {"status": "ready", "llama_cpp": upstream, "mcp_enabled": settings.mcp_enabled}
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "llama_unavailable", "message": str(exc)},
        ) from exc


@app.get("/v1/models")
async def models(_: None = Depends(require_api_key)) -> dict[str, Any]:
    return registry.openai_models()


@app.post("/v1/chat/completions")
async def chat(request: ChatRequest, _: None = Depends(require_api_key)) -> Any:
    try:
        if workflow_required(request):
            workflow_request = OrchestrateRequest.model_validate(request.model_dump())
            response = await orchestrator.orchestrate(workflow_request)
            if request.stream:
                return StreamingResponse(completion_as_sse(response), media_type="text/event-stream")
            return JSONResponse(response)

        payload, _ = orchestrator.prepare_direct(request)
        if request.stream:
            return StreamingResponse(
                llama_client.stream("/v1/chat/completions", payload),
                media_type="text/event-stream",
            )
        return JSONResponse(await llama_client.post_json("/v1/chat/completions", payload))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "model_not_found", "model": str(exc)}) from exc
    except httpx.HTTPStatusError as exc:
        raise upstream_error(exc) from exc
    except (httpx.ConnectError, httpx.ReadTimeout) as exc:
        raise HTTPException(status_code=503, detail={"code": "llama_unavailable", "message": str(exc)}) from exc


@app.post("/prompt/improve")
async def improve(request: ImprovePromptRequest, _: None = Depends(require_api_key)) -> dict[str, Any]:
    try:
        model = registry.selection(request.model).target
        improved = await improve_prompt(
            llama_client,
            request.prompt,
            model_config,
            model=model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        return {"success": True, "model": model, "original_prompt": request.prompt, "improved_prompt": improved}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "model_not_found", "model": str(exc)}) from exc
    except httpx.HTTPStatusError as exc:
        raise upstream_error(exc) from exc


@app.post("/orchestrate/chat")
async def orchestrate(request: OrchestrateRequest, _: None = Depends(require_api_key)) -> Any:
    try:
        response = await orchestrator.orchestrate(request)
        if request.stream:
            return StreamingResponse(completion_as_sse(response), media_type="text/event-stream")
        return JSONResponse(response)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "model_not_found", "model": str(exc)}) from exc
    except httpx.HTTPStatusError as exc:
        raise upstream_error(exc) from exc


@app.get("/mcp/tools")
async def list_mcp_tools(_: None = Depends(require_api_key)) -> dict[str, Any]:
    try:
        return {"enabled": settings.mcp_enabled, "tools": await mcp_client.list_openai_tools()}
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"code": "mcp_unavailable", "message": str(exc)}) from exc


@app.post("/mcp/call")
async def call_mcp_tool(request: ToolCallRequest, _: None = Depends(require_api_key)) -> dict[str, Any]:
    try:
        return await mcp_client.call_tool(request.name, request.arguments)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail={"code": "tool_forbidden", "message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"code": "mcp_unavailable", "message": str(exc)}) from exc


@app.post("/admin/reload")
async def reload_config(_: None = Depends(require_api_key)) -> dict[str, Any]:
    global model_config, registry, router, llama_client, mcp_client, orchestrator
    model_config, registry, router, llama_client, mcp_client, orchestrator = build_components()
    return {"success": True, "models": len(model_config["models"]), "virtual_models": len(model_config["virtual_models"])}
