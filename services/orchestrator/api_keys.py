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


_WILDCARD_WORDS = {"all", "*", "any"}


def _normalize_model_scope(models: list[str] | None) -> list[str]:
    # An empty scope already means "all models". Typing a wildcard word like "all"
    # is a natural, common mistake -- without this, it would be taken literally as a
    # model named "all" (which never exists), silently locking the key out of every
    # real model. Treat any such word as equivalent to leaving the field empty.
    cleaned = [m.strip() for m in (models or []) if m.strip()]
    if any(m.lower() in _WILDCARD_WORDS for m in cleaned):
        return []
    return cleaned




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

    @staticmethod
    def is_expired(key: dict[str, Any], now: float | None = None) -> bool:
        # Records written before expiry existed have no expires_at -> never expire.
        expires_at = key.get("expires_at")
        if not expires_at:
            return False
        return (now if now is not None else time.time()) >= float(expires_at)

    def is_configured(self) -> bool:
        """Whether key-based auth has ever been set up on this deployment.

        Deliberately counts revoked and expired records too. Callers use this to decide
        whether the service may run without authentication at all, and that must not
        depend on a key being *currently* valid: a deployment with no root key whose
        managed keys all expire (or get revoked) has to fail closed and reject
        everything, not fall open to anonymous callers at the moment its last
        credential lapses.
        """
        return bool(self._keys)

    def has_keys(self) -> bool:
        """Whether at least one key can authenticate right now."""
        return any(not key["revoked"] and not self.is_expired(key) for key in self._keys)

    def create(
        self,
        label: str,
        models: list[str] | None = None,
        rate_limit_per_min: int = 0,
        tools: list[str] | None = None,
        expires_in_days: int = 0,
    ) -> tuple[dict[str, Any], str]:
        key_id = secrets.token_hex(4)
        raw = f"llmk_{key_id}_{secrets.token_urlsafe(32)}"
        created_at = time.time()
        expires_in_days = max(0, int(expires_in_days or 0))
        record = {
            "id": key_id,
            "label": (label or "").strip() or "unnamed",
            "prefix": f"llmk_{key_id}",
            "hash": _hash_key(raw),
            "created_at": created_at,
            "last_used_at": None,
            "revoked": False,
            # None = never expires (the pre-existing behaviour, still the default);
            # a timestamp = verify() refuses the key from then on, without needing an
            # admin to remember to revoke it.
            "expires_at": created_at + expires_in_days * 86400 if expires_in_days else None,
            # scopes.models: allowlist of client-facing model names, empty = all.
            # scopes.tools: None = all tools, [] = no tools, [names] = only those.
            "scopes": {
                "models": _normalize_model_scope(models),
                "tools": None if tools is None else [t.strip() for t in tools if t.strip()],
            },
            "rate_limit_per_min": max(0, int(rate_limit_per_min or 0)),
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
        now = time.time()
        for key in self._keys:
            if key["revoked"] or self.is_expired(key, now):
                continue
            if secrets.compare_digest(key["hash"], candidate):
                # Track usage in memory only; it is persisted opportunistically on the
                # next create/revoke to avoid a disk write on every request.
                key["last_used_at"] = now
                return self._public(key)
        return None

    @classmethod
    def _public(cls, key: dict[str, Any]) -> dict[str, Any]:
        # Never includes the hash. Tolerant of records written before scopes/expiry existed.
        return {
            "id": key["id"],
            "label": key["label"],
            "prefix": key["prefix"],
            "created_at": key["created_at"],
            "last_used_at": key.get("last_used_at"),
            "revoked": key["revoked"],
            "expires_at": key.get("expires_at"),
            "expired": cls.is_expired(key),
            "scopes": {
                "models": (key.get("scopes") or {}).get("models") or [],
                "tools": (key.get("scopes") or {}).get("tools", None),
            },
            "rate_limit_per_min": int(key.get("rate_limit_per_min", 0) or 0),
        }
