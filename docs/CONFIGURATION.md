# Configuration

## `.env`

Copy `.env.example` to `.env`. Important settings:

| Setting | Purpose |
|---|---|
| `LLAMA_SERVER_EXE` | Path or command for `llama-server` |
| `LLAMA_MODELS_MAX` | Maximum physical models loaded together |
| `LLAMA_SLEEP_IDLE_SECONDS` | Idle period before router sleep behavior |
| `ORCHESTRATOR_API_KEY` | Private API credential |
| `ORCHESTRATOR_WORKERS` | Keep at `1` for in-process coordination |
| `LLAMA_BASE_URL` | Internal llama.cpp URL |
| `MCP_ENABLED` | Enables MCP discovery and tool execution |
| `MCP_SERVER_URL` | Streamable HTTP MCP endpoint |
| `MCP_TOOL_ALLOWLIST` | Comma-separated allowed tool names |

Use a long random API key. Never commit `.env`.

## `config/models.ini`

This file controls physical llama.cpp models. The section name is the model ID sent to llama.cpp.

```ini
[gemma4-e2b]
model = ../models/chat/gemma4-e2b-Q4_K_M.gguf
n-gpu-layers = auto
n-predict = 4096
```

Recommended initial policy:

- LFM2.5: `n-gpu-layers = 0` to keep it in system RAM.
- Main/coding/vision: `n-gpu-layers = auto` and let llama.cpp fit VRAM.
- `LLAMA_MODELS_MAX=2`: one helper model plus one large model.

Replace all placeholder filenames before starting the service.

## `config/models.json`

`providers` defines OpenAI-compatible upstreams. `local` defaults to the
llama.cpp router, while remote providers can read API keys from environment
variables.

```json
"providers": {
  "local": {
    "type": "openai-compatible",
    "base_url": "http://127.0.0.1:8080",
    "api_key_env": ""
  },
  "openrouter": {
    "type": "openai-compatible",
    "base_url": "https://openrouter.ai/api/v1",
    "api_key_env": "OPENROUTER_API_KEY"
  }
}
```

`models` describes physical model capabilities and generation defaults.
Defaults may include `stop` and `chat_template_kwargs`; these are passed to
the selected provider request. Model-specific stop tokens are merged with
client-supplied stop tokens to reduce runaway generation loops.

`virtual_models` defines client-visible behavior:

```json
"main-llm-improved": {
  "provider": "local",
  "model": "gemma4-e2b",
  "improve_prompt": true,
  "tools": false
}
```

To keep prompt improvement local but send the final answer to another provider,
change only the virtual model:

```json
"main-llm-improved": {
  "provider": "openrouter",
  "model": "openai/gpt-4.1-mini",
  "improve_prompt": true,
  "tools": false
}
```

`prompt_improver.provider` and `prompt_improver.model` choose the model that
rewrites user prompts. This can stay local even when the main model is remote.
See [Provider Routing and Prompt Improvement](PROVIDER_ROUTING.md) for the
end-to-end usage guide and request examples.

`routing` contains deterministic keywords and target models used by `auto`.

`orchestration` controls retry, concurrent workflows and maximum tool rounds.

`mcp` controls MCP enablement and the active tool allowlist:

```json
"mcp": {
  "enabled": true,
  "tool_allowlist": [
    "route_request",
    "build_agent_context",
    "read_file"
  ]
}
```

Use `PATCH /admin/mcp/tools` or the admin UI to update this list without
editing JSON manually.

In Docker, `config/models.json` is mounted writable so the admin UI and admin
APIs can persist changes. Keep `.env` and API keys outside this file.

After editing `models.json`, call:

```http
POST /admin/reload
```

After editing `models.ini`, restart the services.
