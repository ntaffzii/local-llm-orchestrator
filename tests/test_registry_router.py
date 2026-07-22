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
    selection = router.route("auto", messages)
    assert selection.provider == "local"
    assert selection.target == "qwen-coder"


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


def test_physical_models_have_matching_llama_presets():
    import re

    ini_text = (Path(__file__).parents[1] / "config" / "models.ini").read_text(encoding="utf-8")
    ini_sections = {m.group(1) for m in re.finditer(r"^\[(.+)\]\s*$", ini_text, re.MULTILINE)}
    ini_sections.discard("*")
    physical_models = set(CONFIG["models"].keys())
    # Every physical model exposed by the orchestrator must have a llama.cpp preset,
    # so config/models.json and config/models.ini cannot silently drift apart.
    missing = physical_models - ini_sections
    assert not missing, f"models.json models without a models.ini preset: {sorted(missing)}"


def test_save_config_falls_back_to_in_place_write_when_replace_fails(tmp_path, monkeypatch):
    import os as _os
    from services.orchestrator import config as config_module

    target = tmp_path / "models.json"
    target.write_text("old", encoding="utf-8")

    def _boom(src, dst):
        raise OSError("Device or resource busy")

    # Simulate the Docker case where os.replace onto a bind-mounted file fails.
    monkeypatch.setattr(config_module.os, "replace", _boom)
    config_module.save_model_config(target, CONFIG)

    written = config_module.load_model_config(target)
    assert written["models"]
    # No temp files should be left behind.
    assert not list(tmp_path.glob("*.tmp-*"))
