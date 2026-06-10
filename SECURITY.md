# Security Policy

This service controls local models and may reach private MCP tools. Treat it as trusted infrastructure.

## Deployment Rules

- Bind llama.cpp to `127.0.0.1`.
- Place GoModel and Tailscale in front of remote traffic.
- Use a long `ORCHESTRATOR_API_KEY` and rotate it after accidental exposure.
- Keep `MCP_ENABLED=false` until an allowlist is configured.
- Prefer read-only MCP tools.
- Never commit `.env`, GGUF files, logs, prompts, API keys, or Tailscale credentials.
- Do not expose `/mcp/call` to untrusted users.
- Review GoModel rate limits before allowing remote access.

## Reporting

Do not include real secrets, private prompts, local paths, or model output in public issues. Rotate affected credentials before publishing a report.

