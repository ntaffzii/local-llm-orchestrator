from pathlib import Path

from services.orchestrator.config import load_model_config
from services.orchestrator.registry import ModelRegistry
from services.orchestrator.router import RequestRouter
from services.orchestrator.schemas import ChatMessage


CONFIG = load_model_config(Path(__file__).parents[1] / "config" / "models.json")


def test_virtual_models_are_exposed():
    registry = ModelRegistry(CONFIG)
    model_ids = {item["id"] for item in registry.openai_models()["data"]}
    assert {"auto", "main-llm", "main-llm-improved", "coding", "vision", "prompt"} <= model_ids


def test_auto_routes_code_to_coder():
    router = RequestRouter(ModelRegistry(CONFIG))
    messages = [ChatMessage(role="user", content="Please debug this Python function")]
    assert router.route("auto", messages).target == "qwen-coder"


def test_auto_routes_images_to_vision():
    router = RequestRouter(ModelRegistry(CONFIG))
    messages = [
        ChatMessage(
            role="user",
            content=[
                {"type": "text", "text": "Describe this"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,AA=="}},
            ],
        )
    ]
    assert router.route("auto", messages).target == "vision-model"


def test_short_auto_prompt_is_improved():
    router = RequestRouter(ModelRegistry(CONFIG))
    messages = [ChatMessage(role="user", content="Build an API")]
    assert router.should_improve("auto", messages) is True

