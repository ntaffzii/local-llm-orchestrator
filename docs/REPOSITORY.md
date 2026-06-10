# Local LLM Repository

## Recommended Identity

```text
Owner:       ntaffzii
Repository:  local-llm-orchestrator
URL:         https://github.com/ntaffzii/local-llm-orchestrator
Visibility:  Private initially
License:     MIT
```

The URL is the recommended destination. This workspace currently has no Git remote configured for the new Local LLM project, so the repository must still be created on GitHub before pushing.

## Purpose

```text
Private OpenAI-compatible orchestrator for llama.cpp multi-model routing,
LFM2.5 prompt improvement, MCP tools, and Skill-Agents workflows.
```

Suggested topics:

```text
llama-cpp local-llm fastapi openai-compatible mcp skill-agents open-webui gguf docker
```

## Relationship to Other Repositories

```text
ntaffzii/Skill-Agents
  Skills, workflows, prompts and routing metadata

ntaffzii/ai-desk-tools
  MCP server, executable tools and runtime safety policy

ntaffzii/local-llm-orchestrator
  llama.cpp runtime deployment and FastAPI orchestration
```

The Local LLM repository should not copy all Skill or MCP source. It connects to `ai-desk-tools` over MCP, and `ai-desk-tools` reads the Skill-Agents repository available on its machine.

## Publish from the Current Workspace

Create the GitHub repository first without generating a README, license or `.gitignore`, because these files already exist locally.

Then copy the project into a clean folder:

```powershell
$source = "C:\Users\natth\Documents\Skill-Agents\local-llm"
$target = "C:\Users\natth\Documents\local-llm-orchestrator"

New-Item -ItemType Directory -Force -Path $target | Out-Null
Copy-Item -Recurse -Force "$source\*" $target
Copy-Item -Force "$source\.env.example" $target
Copy-Item -Force "$source\.env.docker.example" $target
Copy-Item -Force "$source\.gitignore" $target
Copy-Item -Force "$source\.dockerignore" $target
Copy-Item -Recurse -Force "$source\.github" $target
```

Review before Git initialization:

```powershell
cd $target
Get-ChildItem -Force
```

Initialize and push:

```powershell
git init
git branch -M main
git add .
git status
git diff --cached --name-only
git commit -m "Initial local LLM orchestrator"
git remote add origin https://github.com/ntaffzii/local-llm-orchestrator.git
git push -u origin main
```

Do not run the push command until the GitHub repository exists and `git status` confirms that `.env`, `.env.docker`, GGUF files, `.venv`, logs and caches are absent.

## Files to Publish

```text
.github/workflows/ci.yml
.dockerignore
.env.example
.env.docker.example
.gitignore
Dockerfile
compose.yaml
compose.cuda.yaml
config/
docs/
models/**/.gitkeep
scripts/
services/
tests/
CONTRIBUTING.md
LICENSE
README.md
SECURITY.md
pyproject.toml
requirements.txt
requirements-dev.txt
```

## Files Never to Publish

```text
.env
.env.docker
.venv/
run/
*.gguf
*.bin
API keys
private prompts
MCP tool outputs
Tailscale credentials
```

## Suggested Releases

### `v1.0.0`

- llama.cpp multi-model Router
- FastAPI OpenAI-compatible API
- virtual models and deterministic auto routing
- LFM2.5 prompt improvement
- optional MCP and Skill-Agents tool workflow
- CPU and NVIDIA CUDA Compose deployments
- Windows operation scripts

## Deployment Repository Policy

- Keep model binaries outside Git.
- Pin container image tags or digests before stable deployment.
- Keep the repository private until auth, MCP allowlists and network exposure are reviewed.
- Use GitHub Actions only for unit/config validation; CI should not require GGUF files or a GPU.
