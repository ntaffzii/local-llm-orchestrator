from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

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
    admin_api_key: str
    request_timeout: float
    model_config_path: Path
    log_level: str
    cors_origins: tuple[str, ...]
    mcp_enabled: bool
    mcp_server_url: str
    mcp_tool_allowlist: tuple[str, ...]
    trust_forwarded_for: bool
    admin_ui_enabled: bool


def get_settings() -> Settings:
    config_path = Path(os.getenv("MODEL_CONFIG_PATH", str(ROOT / "config" / "models.json")))
    if not config_path.is_absolute():
        config_path = (ROOT / config_path).resolve()
    return Settings(
        llama_base_url=os.getenv("LLAMA_BASE_URL", "http://127.0.0.1:8080").rstrip("/"),
        api_key=os.getenv("ORCHESTRATOR_API_KEY", ""),
        admin_api_key=os.getenv("ORCHESTRATOR_ADMIN_API_KEY", ""),
        trust_forwarded_for=_bool("TRUST_FORWARDED_FOR"),
        admin_ui_enabled=_bool("ADMIN_UI_ENABLED", True),
        request_timeout=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "300")),
        model_config_path=config_path,
        log_level=os.getenv("ORCHESTRATOR_LOG_LEVEL", "INFO").upper(),
        cors_origins=_csv("ORCHESTRATOR_CORS_ORIGINS"),
        mcp_enabled=_bool("MCP_ENABLED"),
        mcp_server_url=os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8765/mcp"),
        mcp_tool_allowlist=_csv("MCP_TOOL_ALLOWLIST"),
    )


REQUIRED_CONFIG_KEYS = ("models", "virtual_models", "routing", "orchestration")


def validate_model_config(config: dict[str, Any]) -> None:
    if not isinstance(config, dict):
        raise ValueError("Config must be a JSON object")
    if not config.get("models") or not config.get("virtual_models"):
        raise ValueError("Config must define non-empty models and virtual_models")
    missing = [key for key in REQUIRED_CONFIG_KEYS if key not in config]
    if missing:
        raise ValueError(f"Config is missing required keys: {', '.join(missing)}")
    for key in ("models", "virtual_models", "routing", "orchestration"):
        if not isinstance(config[key], dict):
            raise ValueError(f"Config key '{key}' must be an object")


def load_model_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        config = json.load(file)
    validate_model_config(config)
    return config


def save_model_config(path: Path, config: dict[str, Any]) -> None:
    validate_model_config(config)
    payload = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
    # Prefer an atomic temp-write + replace so a crash mid-write can never leave a
    # truncated config on disk. This fails when the target is a bind-mounted single
    # file on a read-only rootfs (the Docker deployment), so fall back to an in-place
    # write there. The dry-run validation in the caller already guards content quality.
    tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}-{uuid4().hex}")
    try:
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        path.write_text(payload, encoding="utf-8")
