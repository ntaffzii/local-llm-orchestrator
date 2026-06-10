from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _csv(name: str, default: str = "") -> tuple[str, ...]:
    return tuple(item.strip() for item in os.getenv(name, default).split(",") if item.strip())


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    llama_base_url: str
    api_key: str
    request_timeout: float
    model_config_path: Path
    log_level: str
    cors_origins: tuple[str, ...]
    mcp_enabled: bool
    mcp_server_url: str
    mcp_tool_allowlist: tuple[str, ...]


def get_settings() -> Settings:
    config_path = Path(os.getenv("MODEL_CONFIG_PATH", str(ROOT / "config" / "models.json")))
    if not config_path.is_absolute():
        config_path = (ROOT / config_path).resolve()
    return Settings(
        llama_base_url=os.getenv("LLAMA_BASE_URL", "http://127.0.0.1:8080").rstrip("/"),
        api_key=os.getenv("ORCHESTRATOR_API_KEY", ""),
        request_timeout=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "300")),
        model_config_path=config_path,
        log_level=os.getenv("ORCHESTRATOR_LOG_LEVEL", "INFO").upper(),
        cors_origins=_csv("ORCHESTRATOR_CORS_ORIGINS"),
        mcp_enabled=_bool("MCP_ENABLED"),
        mcp_server_url=os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8765/mcp"),
        mcp_tool_allowlist=_csv("MCP_TOOL_ALLOWLIST"),
    )


def load_model_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        config = json.load(file)
    if not config.get("models") or not config.get("virtual_models"):
        raise ValueError("models.json must define models and virtual_models")
    return config
