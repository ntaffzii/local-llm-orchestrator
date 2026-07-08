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

### `POST /prompt/consult`

```json
{
  "prompt": "ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server",
  "preferred_language": "English"
}
```

Returns deterministic prompt-consultant guidance before rewriting the prompt.
It detects the task type, recommends how to write the prompt, lists questions to
ask first, and returns template examples, anti-patterns, and a rubric.

You can also use the consultant through the OpenAI-compatible chat endpoint:

```json
{
  "model": "prompt-consultant",
  "messages": [
    {"role": "user", "content": "ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server"}
  ]
}
```

The chat response content is a JSON string containing the same consultation
data. This model is for planning prompts; it does not generate the final answer.

### `POST /prompt/improve`

```json
{
  "prompt": "build api",
  "model": "prompt",
  "temperature": 0.15,
  "max_tokens": 800
}
```

Returns the rewritten prompt only. The response includes the provider/model used
for the rewrite, so clients can send `improved_prompt` to any main provider they
choose.

This endpoint uses the local prompt engine plus the configured prompt model. It
does not call MCP tools. For details about task templates, rule-based guardrails,
and MCP prompt tools, see [Prompt Engine and MCP Prompt Tools](PROMPT_ENGINE.md).

For code/API prompts, the endpoint also post-cleans common small-model drift.
When the user already provided details such as `Python FastAPI`, `/health`,
`200`, or `503`, the improved prompt preserves those details instead of adding
redundant `<framework>` or `<endpoint_path>` placeholders. For health-check
APIs, `503` is treated as an internal dependency or explicit health-check
failure, not as a response from a completely unreachable application.

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
The selected virtual model decides which provider/model receives the final
request after prompt improvement.
When tool use is enabled, the response includes a top-level `tool_trace` array
with the MCP tools that were actually called, their arguments, error state, and
a short result preview.
For provider setup and full PowerShell examples, see
[Provider Routing and Prompt Improvement](PROVIDER_ROUTING.md).

## MCP Endpoints

### `GET /mcp/tools`

Lists MCP tools in OpenAI function format.

Response fields:

- `enabled`: whether MCP execution is enabled.
- `tool_allowlist`: tool names currently allowed by config.
- `tools`: allowed tools that will be sent to tool-enabled models.
- `available_tools`: all tools discovered from the MCP server, including tools
  that are currently disabled by the allowlist.

### `POST /mcp/call`

```json
{
  "name": "search",
  "arguments": {"query": "llama.cpp"}
}
```

This endpoint is intended for trusted administration and testing. Public clients should normally use a tool-enabled virtual model.

Prompt-related MCP tools include `prompt_analyze`, `prompt_consult`, `prompt_improve_rule_based`,
`prompt_history_save`, `prompt_history_search`, `prompt_history_stats`, and
`prompt_history_export_markdown`.

## Operations

### `GET /admin/ui`

Serves the browser admin panel for provider routing and prompt improver
settings. The page itself is public, but all config reads and writes require
`Authorization: Bearer <ORCHESTRATOR_API_KEY>`.

### `GET /admin/config`

Returns `models.json` as currently loaded by the orchestrator.

### `POST /admin/config/virtual-model`

Updates one virtual model route, writes `models.json`, and reloads the
orchestrator components.

### `POST /admin/config/prompt-improver`

Updates prompt improver provider/model settings, writes `models.json`, and
reloads the orchestrator components.

### `PUT /admin/config`

Replaces the complete `models.json` configuration and reloads the orchestrator.
Use this only from trusted admin clients because it writes the full config file.

### `PATCH /admin/mcp/tools`

Updates MCP enablement and the tool allowlist without replacing the full config.
Use `set_tools` from the Admin UI when replacing the whole allowlist.

```json
{
  "enabled": true,
  "set_tools": ["prompt_consult", "prompt_improve_rule_based"],
  "allow_tools": ["route_request", "read_file"],
  "deny_tools": ["write_file"]
}
```

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
