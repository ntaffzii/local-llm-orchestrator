from __future__ import annotations

import hashlib
import json
import secrets
import time
from pathlib import Path
from typing import Any

from .config import atomic_write_json


def _hash_key(raw: str) -> str:
    # Keys are high-entropy random tokens, so a single SHA-256 is sufficient -- there is
    # nothing to brute-force. We store only this hash, never the raw key.
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


_PUBLIC_FIELDS = ("id", "label", "prefix", "created_at", "last_used_at", "revoked")


class ApiKeyStore:
    """Manages issued inference API keys, persisted as hashes in a JSON file.

    The raw key is shown to the admin exactly once at creation; only its hash is kept,
    so a leak of the file cannot reveal any key. Keys can be revoked individually
    without affecting others.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._keys: list[dict[str, Any]] = self._load()

    def _load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return []
        keys = data.get("keys") if isinstance(data, dict) else None
        return keys if isinstance(keys, list) else []

    def _save(self) -> None:
        atomic_write_json(self.path, {"keys": self._keys})

    def has_keys(self) -> bool:
        return any(not key["revoked"] for key in self._keys)

    def create(self, label: str) -> tuple[dict[str, Any], str]:
        key_id = secrets.token_hex(4)
        raw = f"llmk_{key_id}_{secrets.token_urlsafe(32)}"
        record = {
            "id": key_id,
            "label": (label or "").strip() or "unnamed",
            "prefix": f"llmk_{key_id}",
            "hash": _hash_key(raw),
            "created_at": time.time(),
            "last_used_at": None,
            "revoked": False,
        }
        self._keys.append(record)
        self._save()
        return self._public(record), raw

    def list(self) -> list[dict[str, Any]]:
        return [self._public(key) for key in self._keys]

    def revoke(self, key_id: str) -> bool:
        for key in self._keys:
            if key["id"] == key_id and not key["revoked"]:
                key["revoked"] = True
                self._save()
                return True
        return False

    def verify(self, raw: str) -> dict[str, Any] | None:
        candidate = _hash_key(raw)
        for key in self._keys:
            if key["revoked"]:
                continue
            if secrets.compare_digest(key["hash"], candidate):
                # Track usage in memory only; it is persisted opportunistically on the
                # next create/revoke to avoid a disk write on every request.
                key["last_used_at"] = time.time()
                return self._public(key)
        return None

    @staticmethod
    def _public(key: dict[str, Any]) -> dict[str, Any]:
        return {field: key[field] for field in _PUBLIC_FIELDS}
