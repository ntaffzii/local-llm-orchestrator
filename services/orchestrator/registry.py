from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelSelection:
    requested: str
    target: str
    improve_prompt: bool | str
    use_tools: bool | str
    defaults: dict[str, Any]
    capabilities: frozenset[str]


class ModelRegistry:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.models = config["models"]
        self.virtual_models = config["virtual_models"]

    def selection(self, requested: str) -> ModelSelection:
        policy = self.virtual_models.get(requested)
        if policy:
            target = policy["route"]
            if target == "auto":
                target = "auto"
            details = self.models.get(target, {})
            return ModelSelection(
                requested=requested,
                target=target,
                improve_prompt=policy.get("improve_prompt", False),
                use_tools=policy.get("tools", False),
                defaults=details.get("defaults", {}),
                capabilities=frozenset(details.get("capabilities", [])),
            )
        details = self.models.get(requested)
        if not details or not details.get("enabled", True):
            raise KeyError(requested)
        return ModelSelection(
            requested=requested,
            target=requested,
            improve_prompt=False,
            use_tools=False,
            defaults=details.get("defaults", {}),
            capabilities=frozenset(details.get("capabilities", [])),
        )

    def target_selection(self, requested: str, target: str) -> ModelSelection:
        base = self.selection(requested)
        details = self.models[target]
        return ModelSelection(
            requested=base.requested,
            target=target,
            improve_prompt=base.improve_prompt,
            use_tools=base.use_tools,
            defaults=details.get("defaults", {}),
            capabilities=frozenset(details.get("capabilities", [])),
        )

    def openai_models(self) -> dict[str, Any]:
        data = []
        for model_id, details in self.models.items():
            if details.get("enabled", True):
                data.append(self._model_item(model_id, details, virtual=False))
        for model_id, policy in self.virtual_models.items():
            data.append(self._model_item(model_id, policy, virtual=True))
        return {"object": "list", "data": data}

    @staticmethod
    def _model_item(model_id: str, details: dict[str, Any], virtual: bool) -> dict[str, Any]:
        return {
            "id": model_id,
            "object": "model",
            "created": 0,
            "owned_by": "local-orchestrator",
            "name": details.get("display_name", model_id),
            "virtual": virtual,
        }
