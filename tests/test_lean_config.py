from pathlib import Path

from services.orchestrator.config import load_model_config
from services.orchestrator.registry import ModelRegistry
from services.orchestrator.router import RequestRouter
from services.orchestrator.schemas import ChatMessage


LEAN_CONFIG = load_model_config(Path(__file__).parents[1] / "config" / "models.main-prompt-only.json")


def test_lean_config_only_exposes_main_and_prompt():
    registry = ModelRegistry(LEAN_CONFIG)
    model_ids = {item["id"] for item in registry.openai_models()["data"]}
    # No coding/vision/tools model should ever be reachable from this config -- the
    # whole point is pinning inference to the two dedicated containers.
    assert model_ids == {
        "gemma4-e2b",
        "lfm2.5-prompt",
        "auto",
        "main-llm",
        "main-llm-improved",
        "main-llm-tools",
        "prompt",
        "prompt-consultant",
    }


def test_lean_config_auto_never_switches_away_from_main():
    router = RequestRouter(ModelRegistry(LEAN_CONFIG))
    coding_prompt = [ChatMessage(role="user", content="Please debug this Python function")]
    image_prompt = [
        ChatMessage(
            role="user",
            content=[
                {"type": "text", "text": "Describe this"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}},
            ],
        )
    ]
    # In the full config these route to qwen-coder / vision-model; here both must
    # resolve to the one loaded model so "auto" never triggers a container switch.
    assert router.route("auto", coding_prompt).target == "gemma4-e2b"
    assert router.route("auto", image_prompt).target == "gemma4-e2b"


def test_lean_config_main_and_prompt_use_dedicated_providers():
    registry = ModelRegistry(LEAN_CONFIG)
    assert registry.selection("main-llm").provider == "main"
    assert registry.selection("prompt").provider == "prompt"
    assert registry.selection("main-llm-tools").provider == "main"
