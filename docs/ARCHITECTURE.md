# Architecture

## Responsibilities

### GoModel API Gateway

- รับ traffic จาก Tailscale หรือ client
- Authentication, quota, rate limiting และ usage accounting
- Forward OpenAI-compatible requests ไป Orchestrator

### FastAPI Orchestrator

- แสดง physical และ virtual model names
- เลือก target model จาก request หรือ auto routing
- เรียก LFM2.5 เพื่อปรับ prompt เมื่อ policy กำหนด
- แปลง MCP schemas เป็น OpenAI tool schemas
- ทำ tool-calling loop และส่งผล tool กลับเข้าโมเดล
- Retry, concurrency limit, request ID และ error normalization

Orchestrator ไม่โหลด GGUF และไม่จัดสรร VRAM โดยตรง

### llama.cpp Router

- เปิด physical GGUF models ตาม `config/models.ini`
- โหลดและถอดโมเดลตาม request
- จัด CPU/GPU offload, mmap, KV cache, batching และ model slots
- จำกัดโมเดลที่โหลดพร้อมกันด้วย `--models-max`

### MCP Tools

- ให้ tools ด้าน filesystem, GitHub, browser, RAG และบริการส่วนตัว
- เปิดแยก process ผ่าน streamable HTTP
- Orchestrator เรียกเฉพาะ tool ที่อยู่ใน allowlist เมื่อมีการกำหนด allowlist

## Request Flows

### Direct Model

```text
Open WebUI selects main-llm
  -> GoModel
  -> POST /v1/chat/completions
  -> Orchestrator maps main-llm to gemma4-e2b
  -> llama.cpp loads/runs gemma4-e2b
  -> token stream returns to client
```

### Improved Prompt

```text
Client selects main-llm-improved
  -> Orchestrator calls LFM2.5
  -> replaces only the latest text user message
  -> sends rewritten prompt to gemma4-e2b
  -> returns final answer
```

### Auto Route

Routing order:

1. Image content routes to the vision model.
2. Coding keywords route to the coding model.
3. Remaining requests route to the main model.
4. Short, unstructured prompts may be improved.
5. Tool keywords may enable MCP tools.

Auto routing is intentionally deterministic and configurable. It does not call another classifier model.

### MCP Tool Loop

```text
User request
  -> model receives MCP tool schemas
  -> model emits tool_calls
  -> Orchestrator validates allowlist
  -> MCP server executes tool
  -> result is appended as a tool message
  -> model produces final answer
```

The loop stops after `max_tool_rounds` to prevent unbounded execution.

## Concurrency

Direct model requests stream without the workflow semaphore. Requests that rewrite prompts or use tools pass through `max_concurrent_workflows`. Run one Uvicorn worker so this coordination remains process-wide. GoModel should own public-facing rate limits.

## Streaming

Direct requests use native llama.cpp token streaming. Multi-step workflows must complete their internal LFM/MCP calls first; the current implementation returns the completed answer as a valid single SSE chunk when `stream=true`.

