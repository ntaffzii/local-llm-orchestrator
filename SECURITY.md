# Security Policy

This service controls local models and may reach private MCP tools. Treat it as trusted infrastructure.

## Deployment Rules

- Bind llama.cpp to `127.0.0.1`.
- Place GoModel and Tailscale in front of remote traffic.
- Use a long `ORCHESTRATOR_API_KEY` and rotate it after accidental exposure.
- Set `ORCHESTRATOR_ADMIN_API_KEY` to a different long random value in any shared setup, so an inference client cannot rewrite routing and config.
- Keep `MCP_ENABLED=false` until an allowlist is configured.
- Prefer read-only MCP tools.
- Never commit `.env`, GGUF files, logs, prompts, API keys, or Tailscale credentials.
- Do not expose `/mcp/call` to untrusted users.
- Review GoModel rate limits before allowing remote access.
- Set `ADMIN_UI_ENABLED=false` in production if the console is not needed.

## Authentication Model

Two levels of credential, deliberately separated:

- **Root key** (`ORCHESTRATOR_API_KEY`) — unrestricted inference. Also acts as the admin key when `ORCHESTRATOR_ADMIN_API_KEY` is unset.
- **Admin key** (`ORCHESTRATOR_ADMIN_API_KEY`) — the only credential accepted by `/admin/*`. Managed keys never satisfy it, so issuing an inference key can never grant config access.
- **Managed keys** (issued from the Access tab) — inference only. Stored as SHA-256 hashes; the raw key is shown once at creation and never again. Each key carries a model allowlist, an MCP tool scope, an optional per-minute rate limit, and an optional expiry.

Auth-failure lockout is tracked per client IP, with **separate state for inference and admin**, so a client retrying a bad inference key cannot lock the admin out of the console needed to revoke it.

### Key hygiene

- Prefer an expiry (`Expires in days`) for temporary or third-party access — an expiring key stops working on its own, without relying on anyone remembering to revoke it. `0` means never expires.
- Revoke immediately when a key is no longer needed; revocation takes effect on the next request.
- The root and admin keys have no built-in expiry. Rotate them by changing the environment variable and restarting the service.
- The console keeps keys in `sessionStorage` for that browser tab only, and clears them after 30 minutes of inactivity. Close the tab when finished on a shared machine.

## Audit Logging

Every admin config mutation is recorded with the action, source IP, request ID, and timestamp. Entries go to the application log and to an in-memory ring buffer that powers the console's Recent Activity view.

That buffer is capped and **lost on restart**, which is exactly when an investigation needs it. Set `AUDIT_LOG_PATH` to also append each entry as one JSON line to a file that outlives the process. If that file cannot be written (read-only or full filesystem) the admin action still succeeds and a warning is logged — auditing never blocks operations.

## Docker Control (opt-in)

`compose.docker-control.yaml` lets the console start/stop the model containers. It mounts the Docker socket and runs the orchestrator container as root, which is **roughly host-root access**. It is disabled by default (`DOCKER_CONTROL_ENABLED=false`) and gated behind the admin key.

Defence in depth when it is enabled:

- A hard-coded allowlist (`llama-main`, `llama-prompt`) is checked before any socket call, so no other container can be touched even if requested.
- Only `start` and `stop` actions are accepted.
- Container IDs come from Docker's own API response, never from user input.

Enable it only on a machine you trust. For anything less trusted, put a `docker-socket-proxy` in front, point `DOCKER_SOCKET` at the proxy so only container start/stop is exposed, and drop the `user: root` override.

## Known Limits

- Auth lockout and per-key rate limits are **in-process**. With `ORCHESTRATOR_WORKERS > 1` each worker keeps its own counters, so effective thresholds are multiplied by the worker count. Keep workers at 1, or enforce limits in the reverse proxy.
- `TRUST_FORWARDED_FOR` must stay `false` unless a trusted reverse proxy sets `X-Forwarded-For`. Enabling it without one lets clients spoof their source IP and evade the lockout.
- MCP tool allowlists in `config/models.json` are an operator-controlled capability grant. Tools that reach the network (web fetch/search) let a model act on prompt content, so grant them only when the deployment needs them, and use per-key tool scopes to narrow which keys may call them.

## Reporting

Do not include real secrets, private prompts, local paths, or model output in public issues. Rotate affected credentials before publishing a report.
