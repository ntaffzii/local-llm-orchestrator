# Docker Deployment

Docker Compose runs two core services:

```text
orchestrator :8090 -> llama-router :8080 -> mounted GGUF files
```

Only Orchestrator is published to the host. llama.cpp remains inside the private Compose network.

Start Docker Desktop and wait until the Linux engine reports that it is running before using the commands below.

## Files

| File | Purpose |
|---|---|
| `Dockerfile` | Builds the FastAPI Orchestrator image |
| `compose.yaml` | CPU/default deployment |
| `compose.cuda.yaml` | NVIDIA CUDA override |
| `.env.docker.example` | Compose environment template |
| `.dockerignore` | Excludes models, secrets and local artifacts from builds |

The llama.cpp container uses the official `ghcr.io/ggml-org/llama.cpp:server` image. CUDA uses `server-cuda`.

## Prepare Models

Place GGUF files under:

```text
models/prompt/
models/chat/
models/coding/
models/vision/
```

Update `config/models.ini`. Paths remain relative to `/config` in the container, so this works:

```ini
[gemma4-e2b]
model = ../models/chat/gemma4-e2b-Q4_K_M.gguf
```

Models are mounted read-only at `/models`. They are not copied into either image.

## Configure

```powershell
cd C:\Users\natth\Documents\Skill-Agents\local-llm
Copy-Item .env.docker.example .env.docker
```

Edit `.env.docker` and replace `ORCHESTRATOR_API_KEY` with a long random value.

Validate Docker and all mounted model paths:

```powershell
.\scripts\docker-validate.ps1
```

## CPU

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\docker-up.ps1 -Build
```

Equivalent command:

```powershell
docker compose --env-file .env.docker up -d --build
```

## NVIDIA CUDA

Docker Desktop must use the WSL2 backend and GPU access must work:

```powershell
docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi
```

Then start:

```powershell
.\scripts\docker-up.ps1 -Cuda -Build
```

Equivalent command:

```powershell
docker compose --env-file .env.docker `
  -f compose.yaml `
  -f compose.cuda.yaml `
  up -d --build
```

The official GPU images are built by llama.cpp, but their documentation notes that GPU variants receive less CI runtime testing than CPU images. Pin an image digest or dated tag before treating a deployment as stable.

## Operations

```powershell
.\scripts\docker-status.ps1
.\scripts\docker-logs.ps1 -Service all
.\scripts\docker-logs.ps1 -Service llama-router
.\scripts\docker-down.ps1
```

Test the API:

```powershell
$key = "your-api-key"
Invoke-RestMethod `
  -Uri http://127.0.0.1:8090/v1/models `
  -Headers @{ Authorization = "Bearer $key" }
```

## Open WebUI / GoModel

Use:

```text
Base URL: http://host.docker.internal:8090/v1  # client runs in Docker
Base URL: http://127.0.0.1:8090/v1             # client runs on host
API Key: ORCHESTRATOR_API_KEY
```

If Open WebUI is in another Compose project, `host.docker.internal` is the simplest starting point. A shared external Docker network can be added later.

## Network Exposure

Default binding is:

```env
ORCHESTRATOR_BIND_IP=127.0.0.1
```

Keep this setting when GoModel runs on the same machine. For Tailscale, prefer publishing through GoModel. Do not publish llama.cpp port `8080` directly.

## Troubleshooting

### Container exits immediately

```powershell
.\scripts\docker-logs.ps1 -Service llama-router
```

Usually a GGUF filename in `models.ini` does not match the mounted file.

### CUDA is not detected

Check Docker Desktop WSL2 mode, NVIDIA drivers, `docker run --gpus all ... nvidia-smi`, and that `compose.cuda.yaml` was included.

### Orchestrator is healthy but not ready

`/health` checks FastAPI. `/ready` also checks llama.cpp. Model loading can make readiness slow on first use.
