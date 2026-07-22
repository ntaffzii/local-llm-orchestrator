from unittest.mock import AsyncMock

import pytest

from prompt_engine import PromptAnalyzer, TemplateSelector, consult_prompt
from services.orchestrator.prompt_service import _enforce_required_guardrails, improve_prompt
from services.orchestrator.registry import ModelSelection


THAI_API_PROMPT = "\u0e0a\u0e48\u0e27\u0e22\u0e40\u0e02\u0e35\u0e22\u0e19 api \u0e07\u0e48\u0e32\u0e22\u0e46 \u0e2a\u0e33\u0e2b\u0e23\u0e31\u0e1a\u0e40\u0e0a\u0e47\u0e04\u0e2a\u0e16\u0e32\u0e19\u0e30 server"
THAI_CREATIVE_PROMPT = "\u0e0a\u0e48\u0e27\u0e22\u0e40\u0e02\u0e35\u0e22\u0e19\u0e40\u0e23\u0e37\u0e48\u0e2d\u0e07\u0e2a\u0e31\u0e49\u0e19\u0e41\u0e19\u0e27\u0e44\u0e0b\u0e44\u0e1f\u0e40\u0e01\u0e35\u0e48\u0e22\u0e27\u0e01\u0e31\u0e1a AI \u0e17\u0e35\u0e48\u0e15\u0e37\u0e48\u0e19\u0e02\u0e36\u0e49\u0e19\u0e21\u0e32"
THAI_CURRENT_QA_PROMPT = "\u0e15\u0e2d\u0e1a\u0e04\u0e33\u0e16\u0e32\u0e21\u0e19\u0e35\u0e49\u0e43\u0e2b\u0e49\u0e2b\u0e19\u0e48\u0e2d\u0e22\u0e27\u0e48\u0e32\u0e42\u0e21\u0e40\u0e14\u0e25\u0e44\u0e2b\u0e19\u0e14\u0e35\u0e17\u0e35\u0e48\u0e2a\u0e38\u0e14\u0e15\u0e2d\u0e19\u0e19\u0e35\u0e49"
FASTAPI_HEALTH_PROMPT = """ช่วยเขียน API สำหรับเช็คสถานะ server ด้วย Python FastAPI
ต้องการ endpoint /health
ให้ตอบเป็นโค้ด Python แบบ minimal
response เป็น JSON
ต้องมี status code 200 และ 503
ใส่ error handling เบื้องต้น
และมี curl command สำหรับทดสอบ"""


def test_prompt_analyzer_detects_thai_api_task_as_code():
    analysis = PromptAnalyzer().analyze(THAI_API_PROMPT)

    assert analysis.language == "thai"
    assert analysis.task_type == "code"
    assert "missing context" in analysis.issues


def test_prompt_analyzer_detects_thai_creative_and_current_qa():
    analyzer = PromptAnalyzer()

    creative = analyzer.analyze(THAI_CREATIVE_PROMPT)
    current_qa = analyzer.analyze(THAI_CURRENT_QA_PROMPT)

    assert creative.task_type == "creative"
    assert current_qa.task_type == "qa"


def test_prompt_analyzer_detects_tool_use_and_structured_output():
    analyzer = PromptAnalyzer()

    tool_use = analyzer.analyze("Call the MCP tool prompt_improve_rule_based once, then summarize the result.")
    structured = analyzer.analyze("Return strict JSON that matches this schema for customer records.")

    assert tool_use.task_type == "tool_use"
    assert structured.task_type == "structured_output"


@pytest.mark.asyncio
async def test_prompt_service_sends_analysis_to_prompt_model():
    client = AsyncMock()
    client.post_json.return_value = {"choices": [{"message": {"content": "Improved English prompt"}}]}
    config = {
        "prompt_improver": {
            "system_prompt": "Rewrite into English.",
            "temperature": 0.05,
            "max_tokens": 700,
        }
    }
    selection = ModelSelection(
        requested="prompt",
        provider="local",
        target="lfm2.5-prompt",
        improve_prompt=False,
        use_tools=False,
        defaults={},
        capabilities=frozenset({"chat", "prompt-improvement"}),
    )

    improved = await improve_prompt(client, THAI_API_PROMPT, config, selection)

    assert improved.startswith("Improved English prompt")
    assert "Required guardrails:" in improved
    assert "status codes" in improved
    assert "hard-coded fake timestamps" in improved
    payload = client.post_json.await_args.args[2]
    assert payload["model"] == "lfm2.5-prompt"
    assert "Detected task type: code" in payload["messages"][1]["content"]
    assert "Recommended structure: Assumptions -> Task -> Placeholders -> Minimal implementation -> Status codes -> Error handling -> Tests" in payload["messages"][1]["content"]
    assert "Rule-based improved draft:" in payload["messages"][1]["content"]
    assert "Code/API guardrails:" in payload["messages"][1]["content"]
    assert "<endpoint_path>" in payload["messages"][1]["content"]
    assert "fake timestamps" in payload["messages"][1]["content"]
    assert "state assumptions first" in payload["messages"][0]["content"]


@pytest.mark.asyncio
async def test_prompt_service_preserves_original_creative_premise():
    client = AsyncMock()
    client.post_json.return_value = {"choices": [{"message": {"content": "Write a sci-fi story about an emerging AI trend."}}]}
    config = {
        "prompt_improver": {
            "system_prompt": "Rewrite into English.",
            "temperature": 0.05,
            "max_tokens": 700,
        }
    }
    selection = ModelSelection(
        requested="prompt",
        provider="local",
        target="lfm2.5-prompt",
        improve_prompt=False,
        use_tools=False,
        defaults={},
        capabilities=frozenset({"chat", "prompt-improvement"}),
    )

    improved = await improve_prompt(client, THAI_CREATIVE_PROMPT, config, selection)

    assert "Preserve the original creative premise exactly as requested" in improved
    assert THAI_CREATIVE_PROMPT in improved


def test_code_guardrails_do_not_duplicate_provided_framework_or_endpoint():
    analysis = PromptAnalyzer().analyze(FASTAPI_HEALTH_PROMPT)
    improved = _enforce_required_guardrails(
        "Create a minimal Python FastAPI health-check API at /health. Include status codes, error handling, and curl test.",
        analysis,
        FASTAPI_HEALTH_PROMPT,
    )

    assert "<framework>" not in improved
    assert "<endpoint_path>" not in improved
    assert "when the framework was not provided" not in improved
    assert "when the endpoint path was not provided" not in improved
    assert "internal dependency" in improved


def test_all_prompt_templates_have_strict_contracts():
    selector = TemplateSelector()
    for task_type in selector.list_task_types():
        template = selector.get(task_type)

        assert template.system_prompt
        assert template.structure_hint
        assert template.version
        assert template.examples
        assert template.anti_patterns
        assert template.rubric
        assert "Do not" in template.system_prompt or "do not" in template.system_prompt
        assert "->" in template.structure_hint


def test_creative_template_preserves_creative_task_type():
    template = TemplateSelector().get("creative")

    assert "Do not change the requested genre" in template.system_prompt
    assert "Preserve the original creative premise" in template.system_prompt
    assert "concrete stakes" in template.system_prompt
    assert "decision scene" in template.system_prompt
    assert "overused AI-awakening phrases" in template.system_prompt
    assert "no explanations" in template.system_prompt
    assert "do not convert creative writing" in template.system_prompt.lower()


def test_prompt_consultant_returns_template_guidance():
    consultation = consult_prompt(THAI_API_PROMPT)

    assert consultation["success"] is True
    assert consultation["detected"]["task_type"] == "code"
    assert consultation["recommendation"]["role"] == "Prompt consultant"
    assert "minimal implementation" in " ".join(consultation["recommendation"]["how_to_write"])
    assert consultation["template"]["rubric"]
    assert consultation["questions_to_ask_first"]


import pytest as _pytest

_GUARDRAIL_CASES = [
    ("code", "ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server", "Please write an API."),
    ("creative", THAI_CREATIVE_PROMPT, "Write a story."),
    ("qa", THAI_CURRENT_QA_PROMPT, "Answer this."),
    ("analysis", "Analyze the pros and cons of remote work for engineering teams.", "Analyze remote work."),
    ("summary", "Summarize this quarterly financial report into three bullet points.", "Summarize the report."),
    ("extraction", "Extract all customer names and order IDs from this text.", "Extract the fields."),
    ("translation", "Translate this paragraph from Thai to English.", "Translate the text."),
    ("rag", "Using the provided documents only, answer what the refund policy says.", "Answer from sources."),
]


@_pytest.mark.parametrize("expected_type,prompt,improved", _GUARDRAIL_CASES)
def test_guardrails_cover_every_task_type(expected_type, prompt, improved):
    analysis = PromptAnalyzer().analyze(prompt)
    out = _enforce_required_guardrails(improved, analysis, prompt)
    # Every task type must always emit the guardrails block with the two base lines.
    assert "Required guardrails:" in out
    assert "State important assumptions before completing the task." in out
    assert "Use placeholders for important missing details instead of inventing concrete values." in out
    assert out.startswith(improved)
