import httpx
import pytest

from services.orchestrator.llama_client import LlamaClient


def _patch_transport(monkeypatch, transport: httpx.MockTransport) -> None:
    original_client = httpx.AsyncClient

    def patched(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched)


async def test_stream_passes_through_chunks_on_success(monkeypatch):
    async def body():
        yield b"data: hello\n\n"
        yield b"data: [DONE]\n\n"

    def handler(request):
        # A true async body (not pre-materialized bytes) so aiter_raw() genuinely
        # streams, matching how a live upstream connection behaves.
        return httpx.Response(200, content=body())

    _patch_transport(monkeypatch, httpx.MockTransport(handler))
    client = LlamaClient("http://fake:8080", timeout=5.0)

    chunks = [chunk async for chunk in client.stream("/v1/chat/completions", {"model": "x"})]

    assert b"".join(chunks) == b"data: hello\n\ndata: [DONE]\n\n"


async def test_stream_emits_sse_error_on_upstream_4xx_instead_of_crashing(monkeypatch):
    # Reproduces the real failure: llama.cpp rejects an over-long conversation with a
    # 400 mid-stream. Previously raise_for_status() propagated unhandled through the
    # ASGI stack (StreamingResponse had already sent 200); now it must be swallowed
    # into one clean SSE error event instead of crashing the app.
    def handler(request):
        return httpx.Response(
            400, json={"error": "request (8280 tokens) exceeds the available context size (8192 tokens)"}
        )

    _patch_transport(monkeypatch, httpx.MockTransport(handler))
    client = LlamaClient("http://fake:8080", timeout=5.0)

    chunks = [chunk async for chunk in client.stream("/v1/chat/completions", {"model": "x"})]

    assert len(chunks) == 1
    text = chunks[0].decode("utf-8")
    assert text.startswith("data: ") and text.endswith("data: [DONE]\n\n")
    assert '"status": 400' in text
    assert "context size" in text


async def test_stream_emits_sse_error_on_connection_failure(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    _patch_transport(monkeypatch, httpx.MockTransport(handler))
    client = LlamaClient("http://fake:8080", timeout=5.0)

    chunks = [chunk async for chunk in client.stream("/v1/chat/completions", {"model": "x"})]

    assert len(chunks) == 1
    text = chunks[0].decode("utf-8")
    assert '"status": 503' in text
    assert "connection refused" in text
