from __future__ import annotations

import json
from typing import Any

from .registry import ModelRegistry, ModelSelection
from .schemas import ChatMessage


class RequestRouter:
    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry
        self.routing = registry.config["routing"]

    def route(self, requested: str, messages: list[ChatMessage]) -> ModelSelection:
        selection = self.registry.selection(requested)
        if selection.target != "auto":
            return selection
        target = self._auto_target(messages)
        return self.registry.target_selection(requested, target)

    def should_improve(self, policy: bool | str, messages: list[ChatMessage]) -> bool:
        if isinstance(policy, bool):
            return policy
        text = self.last_user_text(messages)
        words = len(text.split())
        has_structure = any(marker in text.lower() for marker in ("format", "json", "ข้อกำหนด", "รูปแบบ", "must"))
        return bool(text) and words < int(self.routing.get("short_prompt_words", 10)) and not has_structure

    def should_use_tools(self, policy: bool | str, messages: list[ChatMessage]) -> bool:
        if isinstance(policy, bool):
            return policy
        text = self.last_user_text(messages).lower()
        return any(keyword.lower() in text for keyword in self.routing.get("tool_keywords", []))

    def _auto_target(self, messages: list[ChatMessage]) -> str:
        if self.has_image(messages):
            return self.routing["vision_model"]
        text = self.last_user_text(messages).lower()
        if any(keyword.lower() in text for keyword in self.routing.get("coding_keywords", [])):
            return self.routing["coding_model"]
        return self.routing["default_model"]

    @staticmethod
    def last_user_text(messages: list[ChatMessage]) -> str:
        for message in reversed(messages):
            if message.role == "user":
                if isinstance(message.content, str):
                    return message.content
                return json.dumps(message.content, ensure_ascii=False)
        return ""

    @staticmethod
    def has_image(messages: list[ChatMessage]) -> bool:
        for message in messages:
            if isinstance(message.content, list):
                for part in message.content:
                    if isinstance(part, dict) and part.get("type") in {"image", "image_url", "input_image"}:
                        return True
        return False
