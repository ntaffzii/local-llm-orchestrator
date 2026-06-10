# GitHub Repository Guide

Recommended repository: `https://github.com/ntaffzii/local-llm-orchestrator`

See [REPOSITORY.md](REPOSITORY.md) for the complete split and publication workflow.

## Commit These Files

```text
.env.example
.env.docker.example
.dockerignore
.github/workflows/ci.yml
Dockerfile
compose.yaml
compose.cuda.yaml
.gitignore
LICENSE
README.md
pyproject.toml
requirements.txt
requirements-dev.txt
config/models.json
config/models.ini
docs/
models/**/.gitkeep
scripts/
services/
tests/
SECURITY.md
CONTRIBUTING.md
```

## Never Commit

```text
.env
.venv/
run/
.env.docker
*.gguf
*.bin
API keys
Tailscale credentials
private prompts or tool outputs
```

## Suggested Repository Metadata

Description:

```text
Private OpenAI-compatible orchestrator for llama.cpp multi-model routing, prompt improvement, and MCP tools.
```

Topics:

```text
llama-cpp local-llm fastapi openai-compatible mcp open-webui orchestration gguf
```

## Before First Push

1. Replace placeholder model names only if you want the public defaults to match your hardware.
2. Verify `.env` and GGUF files are ignored with `git status`.
3. Run the test suite.
4. Run `scripts/validate.ps1` on the deployment machine.
5. Scan repository history for secrets.
6. Keep the repository private until authentication and tool allowlists are reviewed.

## Suggested First Release

Tag: `v1.0.0`

Release scope:

- llama.cpp router presets
- OpenAI-compatible model API
- virtual model and auto routing
- LFM2.5 prompt workflow
- optional MCP tool loop
- Windows lifecycle scripts
- operations and security documentation
