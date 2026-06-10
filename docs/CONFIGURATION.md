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

`models` describes physical model capabilities and generation defaults.

`virtual_models` defines client-visible behavior:

```json
"main-llm-improved": {
  "route": "gemma4-e2b",
  "improve_prompt": true,
  "tools": false
}
```

`routing` contains deterministic keywords and target models used by `auto`.

`orchestration` controls retry, concurrent workflows and maximum tool rounds.

After editing `models.json`, call:

```http
POST /admin/reload
```

After editing `models.ini`, restart the services.

