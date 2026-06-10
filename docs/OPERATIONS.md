# Operations

## Start and Stop

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\validate.ps1
.\scripts\start.ps1
.\scripts\status.ps1
.\scripts\health.ps1
.\scripts\stop.ps1
```

Runtime PID and log files are written to `run/` and excluded from Git.

## Logs

```text
run/llama-router.out.log
run/llama-router.err.log
run/orchestrator.out.log
run/orchestrator.err.log
```

Every Orchestrator request receives an `X-Request-ID` and produces a completion log with status and duration.

## RAM and VRAM

llama.cpp owns model memory. Orchestrator influences memory indirectly through model selection and `LLAMA_MODELS_MAX`.

Start with:

```text
LFM2.5 on CPU/RAM
One large model on GPU/VRAM
LLAMA_MODELS_MAX=2
```

If VRAM is insufficient:

1. Reduce quantization size or context length.
2. Keep fewer models loaded.
3. Reduce GPU layers for the large model.
4. Quantize KV cache where supported.
5. Inspect llama.cpp metrics and logs before changing routing policy.

## MCP

Run the MCP server separately, for example:

```powershell
python ..\mcp-tools\server_http.py --transport streamable-http --host 127.0.0.1 --port 8765
```

Then configure:

```env
MCP_ENABLED=true
MCP_SERVER_URL=http://127.0.0.1:8765/mcp
MCP_TOOL_ALLOWLIST=search,read_file,repo_index
```

Begin with a small read-only allowlist. Do not expose write, shell, email, or database mutation tools until their confirmation policy is defined.

## Remote Access

Preferred path:

```text
Remote client -> Tailscale -> GoModel -> Orchestrator
```

Keep llama.cpp on `127.0.0.1`. Orchestrator may also stay on localhost when GoModel runs on the same machine. Do not port-forward llama.cpp directly.

## Backup

Back up only configuration and documentation. GGUF files can be downloaded again and should not be stored in Git. Secrets belong in a password manager, not backups of the repository.

