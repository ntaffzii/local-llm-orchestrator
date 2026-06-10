# Contributing

Keep component ownership clear:

- llama.cpp owns inference and model memory.
- Orchestrator owns workflow and routing policy.
- GoModel owns public API governance.
- MCP servers own tool implementation and safety policy.

For changes:

1. Keep configuration backward-compatible when practical.
2. Add tests for routing or workflow behavior.
3. Do not add secrets, model binaries, generated logs, or personal data.
4. Run `python -m pytest` before submitting changes.
5. Update the relevant document under `docs/`.
