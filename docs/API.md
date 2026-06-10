# API

All protected endpoints use:

```http
Authorization: Bearer <ORCHESTRATOR_API_KEY>
```

`GET /health` is intentionally public and reveals only service status.

## OpenAI-Compatible

### `GET /v1/models`

Returns physical and virtual models configured in `models.json`.

### `POST /v1/chat/completions`

```json
{
  "model": "auto",
  "messages": [
    {"role": "user", "content": "Write a Python health checker"}
  ],
  "stream": true
}
```

Physical/direct models preserve llama.cpp streaming. Virtual workflow models support the same request schema but may buffer internal workflow steps.

## Workflow Endpoints

### `POST /prompt/improve`

```json
{
  "prompt": "build api",
  "model": "prompt",
  "temperature": 0.15,
  "max_tokens": 800
}
```

### `POST /orchestrate/chat`

Allows per-request overrides:

```json
{
  "model": "main-llm",
  "improve_prompt": true,
  "use_tools": false,
  "messages": [
    {"role": "user", "content": "Build an API"}
  ]
}
```

`improve_prompt` and `use_tools` accept `true`, `false`, or `"auto"`.

## MCP Endpoints

### `GET /mcp/tools`

Lists allowed MCP tools in OpenAI function format.

### `POST /mcp/call`

```json
{
  "name": "search",
  "arguments": {"query": "llama.cpp"}
}
```

This endpoint is intended for trusted administration and testing. Public clients should normally use a tool-enabled virtual model.

## Operations

### `GET /ready`

Checks connectivity to llama.cpp.

### `POST /admin/reload`

Reloads `models.json` without restarting FastAPI. Changes to `models.ini` require restarting llama.cpp.

## Errors

Errors use an HTTP status and structured detail:

```json
{
  "detail": {
    "code": "model_not_found",
    "model": "unknown"
  }
}
```

Responses include `X-Request-ID`. Clients may send their own `X-Request-ID` for correlation.

