from __future__ import annotations

import json
import logging
import secrets
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from copy import deepcopy
from typing import Any

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from prompt_engine import consult_prompt

from .admin_ui import admin_ui_html
from .config import get_settings, load_model_config, save_model_config, validate_model_config
from .llama_client import ProviderClients
from .mcp_client import McpClient
from .metrics import MetricsStore
from .prompt_service import improve_prompt
from .registry import ModelRegistry
from .router import RequestRouter
from .schemas import (
    ChatRequest,
    ConsultPromptRequest,
    ImprovePromptRequest,
    OrchestrateRequest,
    PatchMcpToolsRequest,
    ToolCallRequest,
    UpdatePromptImproverRequest,
    UpdateVirtualModelRequest,
)
from .service import OrchestratorService


settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("local_llm.orchestrator")

# Paths whose latency/success feed the traffic metrics.
INFERENCE_PATHS = {"/v1/chat/completions", "/orchestrate/chat", "/prompt/improve"}
metrics_store = MetricsStore()


def build_components(
    config: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], ModelRegistry, RequestRouter, ProviderClients, McpClient, OrchestratorService]:
    if config is None:
        config = load_model_config(settings.model_config_path)
    else:
        validate_model_config(config)
    registry = ModelRegistry(config)
    router = RequestRouter(registry)
    orchestration = config["orchestration"]
    providers = ProviderClients(
        config.get("providers", {}),
        settings.request_timeout,
        attempts=int(orchestration.get("retry_attempts", 2)),
        backoff=float(orchestration.get("retry_backoff_seconds", 0.5)),
        default_base_url=settings.llama_base_url,
    )
    mcp_config = config.get("mcp", {})
    mcp_enabled = mcp_config.get("enabled", settings.mcp_enabled)
    mcp_allowlist = tuple(mcp_config.get("tool_allowlist", list(settings.mcp_tool_allowlist)))
    mcp = McpClient(mcp_enabled, settings.mcp_server_url, mcp_allowlist)
    service = OrchestratorService(providers, mcp, router, config)
    return config, registry, router, providers, mcp, service


model_config, registry, router, provider_clients, mcp_client, orchestrator = build_components()


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
    except RuntimeError as exc:
        if request.url.path.startswith("/mcp/") and "No response returned" in str(exc):
            logger.exception("request_failed id=%s method=%s path=%s", request_id, request.method, request.url.path)
            return JSONResponse(
                status_code=503,
                content={
                    "detail": {
                        "code": "mcp_unavailable",
                        "message": "MCP server did not return a response before the request was cancelled.",
                    }
                },
            )
        logger.exception("request_failed id=%s method=%s path=%s", request_id, request.method, request.url.path)
        raise
    except Exception:
        logger.exception("request_failed id=%s method=%s path=%s", request_id, request.method, request.url.path)
        raise
    response.headers["X-Request-ID"] = request_id
    elapsed_ms = (time.perf_counter() - started) * 1000
    if request.url.path in INFERENCE_PATHS:
        metrics_store.record(
            model=getattr(request.state, "metric_model", "unknown"),
            latency_ms=elapsed_ms,
            ok=response.status_code < 400,
        )
    logger.info(
        "request_complete id=%s method=%s path=%s status=%s elapsed_ms=%.1f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


class AuthThrottle:
    """Small in-process throttle that locks out an IP after repeated auth failures.

    This is defence-in-depth for a locally exposed admin API, not a substitute for a
    real WAF. State is per-process and resets on restart.
    """

    def __init__(self, max_failures: int = 10, window_seconds: float = 60.0, lockout_seconds: float = 300.0) -> None:
        self.max_failures = max_failures
        self.window = window_seconds
        self.lockout = lockout_seconds
        self._failures: dict[str, list[float]] = {}
        self._locked_until: dict[str, float] = {}

    def check(self, ip: str) -> None:
        locked_until = self._locked_until.get(ip)
        if locked_until and time.time() < locked_until:
            raise HTTPException(
                status_code=429,
                detail={"code": "too_many_attempts", "message": "Too many failed authentication attempts. Try again later."},
            )

    def record_failure(self, ip: str) -> None:
        now = time.time()
        recent = [t for t in self._failures.get(ip, []) if t >= now - self.window]
        recent.append(now)
        if len(recent) >= self.max_failures:
            self._locked_until[ip] = now + self.lockout
            self._failures.pop(ip, None)
        else:
            self._failures[ip] = recent

    def record_success(self, ip: str) -> None:
        self._failures.pop(ip, None)
        self._locked_until.pop(ip, None)

    def reset(self) -> None:
        self._failures.clear()
        self._locked_until.clear()


auth_throttle = AuthThrottle()


def _client_ip(request: Request) -> str:
    if settings.trust_forwarded_for:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Left-most entry is the original client when set by a trusted proxy.
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _bearer_matches(authorization: str | None, expected: str) -> bool:
    if not authorization:
        return False
    return secrets.compare_digest(authorization, f"Bearer {expected}")


def require_api_key(request: Request, authorization: str | None = Header(default=None)) -> None:
    if not settings.api_key:
        return
    ip = _client_ip(request)
    auth_throttle.check(ip)
    if not _bearer_matches(authorization, settings.api_key):
        auth_throttle.record_failure(ip)
        raise HTTPException(status_code=401, detail={"code": "invalid_api_key", "message": "Invalid API key"})
    auth_throttle.record_success(ip)


def require_admin_api_key(request: Request, authorization: str | None = Header(default=None)) -> None:
    admin_key = settings.admin_api_key or settings.api_key
    if not admin_key:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "api_key_required",
                "message": "Set ORCHESTRATOR_ADMIN_API_KEY (or ORCHESTRATOR_API_KEY) before using admin APIs",
            },
        )
    ip = _client_ip(request)
    auth_throttle.check(ip)
    if not _bearer_matches(authorization, admin_key):
        auth_throttle.record_failure(ip)
        logger.warning("admin_auth_failed ip=%s path=%s", ip, request.url.path)
        raise HTTPException(status_code=401, detail={"code": "invalid_admin_api_key", "message": "Invalid admin API key"})
    auth_throttle.record_success(ip)


def upstream_error(exc: httpx.HTTPStatusError) -> HTTPException:
    try:
        detail: Any = exc.response.json()
    except ValueError:
        detail = exc.response.text
    return HTTPException(
        status_code=exc.response.status_code,
        detail={"code": "upstream_error", "message": "llama.cpp rejected the request", "upstream": detail},
    )


def reload_components() -> None:
    global model_config, registry, router, provider_clients, mcp_client, orchestrator
    model_config, registry, router, provider_clients, mcp_client, orchestrator = build_components()


def workflow_required(request: ChatRequest) -> bool:
    if request.model == "prompt-consultant":
        return False
    selection = registry.selection(request.model)
    return selection.target == "auto" or selection.improve_prompt is not False or selection.use_tools is not False


def last_user_content(messages: list[Any]) -> str:
    for message in reversed(messages):
        role = getattr(message, "role", None) if not isinstance(message, dict) else message.get("role")
        if role != "user":
            continue
        content = getattr(message, "content", None) if not isinstance(message, dict) else message.get("content")
        if isinstance(content, str):
            return content
        return json.dumps(content, ensure_ascii=False)
    return ""


def consultation_completion(prompt: str, model: str = "prompt-consultant") -> dict[str, Any]:
    consultation = consult_prompt(prompt)
    content = json.dumps(consultation, ensure_ascii=False, indent=2)
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": content},
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }


def completion_as_sse(response: dict[str, Any]):
    choice = response.get("choices", [{}])[0]
    message = choice.get("message", {})
    chunk_id = response.get("id", f"chatcmpl-{uuid.uuid4().hex}")
    created = response.get("created", int(time.time()))
    model = response.get("model", "local-orchestrator")
    reasoning = message.get("reasoning_content", "")
    if reasoning:
        reasoning_chunk = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": choice.get("index", 0),
                    "delta": {"role": "assistant", "reasoning_content": reasoning},
                    "finish_reason": None,
                }
            ],
        }
        yield f"data: {json.dumps(reasoning_chunk, ensure_ascii=False)}\n\n".encode("utf-8")
    chunk = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
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


@app.get("/admin/ui", response_class=HTMLResponse)
async def admin_ui() -> HTMLResponse:
    if not settings.admin_ui_enabled:
        raise HTTPException(status_code=404, detail={"code": "admin_ui_disabled", "message": "Admin UI is disabled"})
    return HTMLResponse(admin_ui_html())


@app.get("/ready")
async def ready(_: None = Depends(require_api_key)) -> dict[str, Any]:
    try:
        upstream = await provider_clients.get_json("local", "/health")
        return {"status": "ready", "llama_cpp": upstream, "mcp_enabled": mcp_client.enabled}
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "llama_unavailable", "message": str(exc)},
        ) from exc


@app.get("/v1/models")
async def models(_: None = Depends(require_api_key)) -> dict[str, Any]:
    return registry.openai_models()


@app.post("/v1/chat/completions")
async def chat(request: ChatRequest, http_request: Request, _: None = Depends(require_api_key)) -> Any:
    http_request.state.metric_model = request.model
    try:
        if request.model == "prompt-consultant":
            response = consultation_completion(last_user_content(request.messages), request.model)
            if request.stream:
                return StreamingResponse(completion_as_sse(response), media_type="text/event-stream")
            return JSONResponse(response)

        if workflow_required(request):
            workflow_request = OrchestrateRequest.model_validate(request.model_dump())
            response = await orchestrator.orchestrate(workflow_request)
            if request.stream:
                return StreamingResponse(completion_as_sse(response), media_type="text/event-stream")
            return JSONResponse(response)

        payload, selection = orchestrator.prepare_direct(request)
        if request.stream:
            return StreamingResponse(
                provider_clients.stream(selection.provider, "/v1/chat/completions", payload),
                media_type="text/event-stream",
            )
        return JSONResponse(await provider_clients.post_json(selection.provider, "/v1/chat/completions", payload))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "model_not_found", "model": str(exc)}) from exc
    except httpx.HTTPStatusError as exc:
        raise upstream_error(exc) from exc
    except (httpx.ConnectError, httpx.ReadTimeout) as exc:
        raise HTTPException(status_code=503, detail={"code": "llama_unavailable", "message": str(exc)}) from exc


@app.post("/prompt/improve")
async def improve(request: ImprovePromptRequest, http_request: Request, _: None = Depends(require_api_key)) -> dict[str, Any]:
    http_request.state.metric_model = request.model
    try:
        selection = registry.selection(request.model)
        improved = await improve_prompt(
            provider_clients,
            request.prompt,
            model_config,
            selection=selection,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        return {
            "success": True,
            "provider": selection.provider,
            "model": selection.target,
            "original_prompt": request.prompt,
            "improved_prompt": improved,
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"code": "model_not_found", "model": str(exc)}) from exc
    except httpx.HTTPStatusError as exc:
        raise upstream_error(exc) from exc


@app.post("/prompt/consult")
async def consult(request: ConsultPromptRequest, _: None = Depends(require_api_key)) -> dict[str, Any]:
    return consult_prompt(request.prompt, preferred_language=request.preferred_language)


@app.post("/orchestrate/chat")
async def orchestrate(request: OrchestrateRequest, http_request: Request, _: None = Depends(require_api_key)) -> Any:
    http_request.state.metric_model = request.model
    try:
        if request.model == "prompt-consultant":
            response = consultation_completion(last_user_content(request.messages), request.model)
            if request.stream:
                return StreamingResponse(completion_as_sse(response), media_type="text/event-stream")
            return JSONResponse(response)

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
        return {
            "enabled": mcp_client.enabled,
            "tool_allowlist": sorted(mcp_client.allowlist),
            "tools": await mcp_client.list_openai_tools(),
            "available_tools": await mcp_client.list_openai_tools(include_blocked=True, include_disabled=True),
        }
    except BaseExceptionGroup as exc:
        raise HTTPException(status_code=503, detail={"code": "mcp_unavailable", "message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"code": "mcp_unavailable", "message": str(exc)}) from exc


@app.post("/mcp/call")
async def call_mcp_tool(request: ToolCallRequest, _: None = Depends(require_api_key)) -> dict[str, Any]:
    try:
        return await mcp_client.call_tool(request.name, request.arguments)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail={"code": "tool_forbidden", "message": str(exc)}) from exc
    except BaseExceptionGroup as exc:
        raise HTTPException(status_code=503, detail={"code": "mcp_unavailable", "message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"code": "mcp_unavailable", "message": str(exc)}) from exc


# Recent admin config changes, newest first. In-memory only (resets on restart),
# which is enough to power the console's activity view without a datastore.
AUDIT_LOG: deque[dict[str, Any]] = deque(maxlen=200)


def _audit(http_request: Request, action: str, **fields: Any) -> None:
    request_id = getattr(http_request.state, "request_id", "-")
    # Strip CR/LF from user-supplied values so a crafted model/provider name cannot
    # forge extra log lines.
    def _clean(value: Any) -> str:
        return str(value).replace("\r", " ").replace("\n", " ")

    clean_fields = {key: _clean(value) for key, value in fields.items()}
    AUDIT_LOG.appendleft(
        {"id": request_id, "ip": _client_ip(http_request), "action": action, "fields": clean_fields, "at": time.time()}
    )
    extra = " ".join(f"{key}={value}" for key, value in clean_fields.items())
    logger.info("admin_audit id=%s ip=%s action=%s %s", request_id, _client_ip(http_request), action, extra)


@app.post("/admin/reload")
async def reload_config(http_request: Request, _: None = Depends(require_admin_api_key)) -> dict[str, Any]:
    reload_components()
    _audit(http_request, "reload")
    return {"success": True, "models": len(model_config["models"]), "virtual_models": len(model_config["virtual_models"])}


@app.get("/admin/config")
async def admin_config(_: None = Depends(require_admin_api_key)) -> dict[str, Any]:
    return model_config


@app.get("/admin/audit")
async def admin_audit_log(_: None = Depends(require_admin_api_key)) -> dict[str, Any]:
    return {"entries": list(AUDIT_LOG)}


@app.get("/admin/metrics")
async def admin_metrics(window_seconds: float = 3600.0, _: None = Depends(require_admin_api_key)) -> dict[str, Any]:
    return metrics_store.summary(window_seconds=window_seconds)


@app.post("/admin/config/virtual-model")
async def update_virtual_model(
    request: UpdateVirtualModelRequest,
    http_request: Request,
    _: None = Depends(require_admin_api_key),
) -> dict[str, Any]:
    if request.provider not in model_config.get("providers", {"local": {}}):
        raise HTTPException(status_code=400, detail={"code": "provider_not_found", "provider": request.provider})
    if request.virtual_model not in model_config.get("virtual_models", {}):
        raise HTTPException(status_code=404, detail={"code": "virtual_model_not_found", "model": request.virtual_model})
    updated = deepcopy(model_config)
    updated["virtual_models"][request.virtual_model] = {
        "provider": request.provider,
        "model": request.model,
        "improve_prompt": request.improve_prompt,
        "tools": request.tools,
    }
    save_model_config(settings.model_config_path, updated)
    reload_components()
    _audit(http_request, "update_virtual_model", virtual_model=request.virtual_model, provider=request.provider, target=request.model)
    return model_config


@app.post("/admin/config/prompt-improver")
async def update_prompt_improver(
    request: UpdatePromptImproverRequest,
    http_request: Request,
    _: None = Depends(require_admin_api_key),
) -> dict[str, Any]:
    if request.provider not in model_config.get("providers", {"local": {}}):
        raise HTTPException(status_code=400, detail={"code": "provider_not_found", "provider": request.provider})
    updated = deepcopy(model_config)
    prompt = dict(updated.get("prompt_improver", {}))
    prompt["provider"] = request.provider
    prompt["model"] = request.model
    if request.temperature is not None:
        prompt["temperature"] = request.temperature
    if request.max_tokens is not None:
        prompt["max_tokens"] = request.max_tokens
    updated["prompt_improver"] = prompt
    save_model_config(settings.model_config_path, updated)
    reload_components()
    _audit(http_request, "update_prompt_improver", provider=request.provider, model=request.model)
    return model_config


@app.put("/admin/config")
async def update_admin_config(
    new_config: dict[str, Any],
    http_request: Request,
    _: None = Depends(require_admin_api_key),
) -> dict[str, Any]:
    try:
        # Dry-run: fully build components from the candidate config before touching disk,
        # so an invalid payload can never corrupt the persisted config or break a restart.
        build_components(new_config)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_config", "message": f"Config rejected: {exc}"},
        ) from exc
    save_model_config(settings.model_config_path, new_config)
    reload_components()
    _audit(http_request, "replace_config", models=len(model_config["models"]), virtual_models=len(model_config["virtual_models"]))
    return {"success": True, "models": len(model_config["models"]), "virtual_models": len(model_config["virtual_models"])}


@app.patch("/admin/mcp/tools")
async def patch_mcp_tools(
    request: PatchMcpToolsRequest,
    http_request: Request,
    _: None = Depends(require_admin_api_key),
) -> dict[str, Any]:
    updated = deepcopy(model_config)
    mcp_config = updated.setdefault("mcp", {})
    if request.enabled is not None:
        mcp_config["enabled"] = request.enabled

    if request.set_tools is not None:
        allowlist = set(request.set_tools)
    else:
        allowlist = set(mcp_config.get("tool_allowlist", list(settings.mcp_tool_allowlist)))
    if request.allow_tools:
        allowlist.update(request.allow_tools)
    if request.deny_tools:
        allowlist.difference_update(request.deny_tools)

    mcp_config["tool_allowlist"] = sorted(allowlist)
    save_model_config(settings.model_config_path, updated)
    reload_components()
    _audit(http_request, "patch_mcp_tools", enabled=mcp_client.enabled, tools=len(mcp_client.allowlist))
    return {
        "success": True,
        "mcp_enabled": mcp_client.enabled,
        "tool_allowlist": list(mcp_client.allowlist),
    }
