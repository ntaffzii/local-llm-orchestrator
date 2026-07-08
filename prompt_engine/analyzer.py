"""Rule-based prompt analysis."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


TASK_TYPES = (
    "tool_use",
    "structured_output",
    "rag",
    "code",
    "creative",
    "qa",
    "summary",
    "extraction",
    "translation",
    "analysis",
    "general",
)

TASK_KEYWORDS: dict[str, list[str]] = {
    "tool_use": [
        "mcp",
        "mcp tool",
        "tool call",
        "call tool",
        "use tools",
        "function calling",
        "prompt_improve_rule_based",
        "prompt_analyze",
        "route_request",
    ],
    "structured_output": [
        "json schema",
        "strict json",
        "json-only",
        "output schema",
        "schema",
        "structured output",
        "valid json",
        "csv",
        "xml",
    ],
    "rag": [
        "\u0e08\u0e32\u0e01\u0e40\u0e2d\u0e01\u0e2a\u0e32\u0e23",
        "\u0e08\u0e32\u0e01\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25",
        "\u0e40\u0e2d\u0e01\u0e2a\u0e32\u0e23\u0e17\u0e35\u0e48\u0e43\u0e2b\u0e49",
        "context",
        "based on",
        "from the document",
        "according to",
        "provided sources",
    ],
    "code": [
        "\u0e40\u0e02\u0e35\u0e22\u0e19\u0e42\u0e04\u0e49\u0e14",
        "\u0e40\u0e02\u0e35\u0e22\u0e19\u0e42\u0e1b\u0e23\u0e41\u0e01\u0e23\u0e21",
        "\u0e41\u0e01\u0e49\u0e1a\u0e31\u0e4a\u0e01",
        "\u0e1f\u0e31\u0e07\u0e01\u0e4c\u0e0a\u0e31\u0e19",
        "\u0e40\u0e0a\u0e47\u0e04\u0e2a\u0e16\u0e32\u0e19\u0e30 server",
        "api",
        "endpoint",
        "python",
        "javascript",
        "typescript",
        "write code",
        "debug",
        "implement",
    ],
    "creative": [
        "\u0e41\u0e15\u0e48\u0e07\u0e40\u0e23\u0e37\u0e48\u0e2d\u0e07",
        "\u0e40\u0e23\u0e37\u0e48\u0e2d\u0e07\u0e2a\u0e31\u0e49\u0e19",
        "\u0e19\u0e34\u0e22\u0e32\u0e22",
        "\u0e01\u0e25\u0e2d\u0e19",
        "\u0e44\u0e0b\u0e44\u0e1f",
        "\u0e15\u0e37\u0e48\u0e19\u0e02\u0e36\u0e49\u0e19\u0e21\u0e32",
        "creative",
        "story",
        "short story",
        "fiction",
        "poem",
        "compose",
    ],
    "summary": ["\u0e2a\u0e23\u0e38\u0e1b", "\u0e22\u0e48\u0e2d", "summarize", "summary", "tldr", "brief"],
    "extraction": [
        "\u0e14\u0e36\u0e07\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25",
        "\u0e41\u0e22\u0e01\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25",
        "json",
        "yaml",
        "extract",
        "parse",
        "structured",
    ],
    "translation": [
        "\u0e41\u0e1b\u0e25",
        "\u0e20\u0e32\u0e29\u0e32\u0e2d\u0e31\u0e07\u0e01\u0e24\u0e29",
        "\u0e20\u0e32\u0e29\u0e32\u0e44\u0e17\u0e22",
        "translate",
        "english",
        "thai",
    ],
    "analysis": [
        "\u0e27\u0e34\u0e40\u0e04\u0e23\u0e32\u0e30\u0e2b\u0e4c",
        "\u0e40\u0e1b\u0e23\u0e35\u0e22\u0e1a\u0e40\u0e17\u0e35\u0e22\u0e1a",
        "\u0e1b\u0e23\u0e30\u0e40\u0e21\u0e34\u0e19",
        "\u0e17\u0e33\u0e44\u0e21",
        "\u0e2a\u0e32\u0e40\u0e2b\u0e15\u0e38",
        "analyze",
        "compare",
        "evaluate",
    ],
    "qa": [
        "\u0e04\u0e37\u0e2d\u0e2d\u0e30\u0e44\u0e23",
        "\u0e2d\u0e18\u0e34\u0e1a\u0e32\u0e22",
        "\u0e44\u0e2b\u0e19",
        "\u0e14\u0e35\u0e17\u0e35\u0e48\u0e2a\u0e38\u0e14",
        "\u0e25\u0e48\u0e32\u0e2a\u0e38\u0e14",
        "\u0e15\u0e2d\u0e19\u0e19\u0e35\u0e49",
        "what is",
        "which",
        "best",
        "latest",
        "now",
        "explain",
        "how does",
        "why",
    ],
}

CONTEXT_SIGNALS = ["\u0e1a\u0e23\u0e34\u0e1a\u0e17", "context", "background", "project", "\u0e23\u0e30\u0e1a\u0e1a", "details"]
EXAMPLE_SIGNALS = ["\u0e15\u0e31\u0e27\u0e2d\u0e22\u0e48\u0e32\u0e07", "example", "for instance", "e.g.", "sample"]
FORMAT_SIGNALS = ["\u0e23\u0e39\u0e1b\u0e41\u0e1a\u0e1a", "format", "json", "yaml", "bullet", "table", "\u0e2b\u0e31\u0e27\u0e02\u0e49\u0e2d", "list"]
CONSTRAINT_SIGNALS = ["\u0e2b\u0e49\u0e32\u0e21", "\u0e15\u0e49\u0e2d\u0e07", "\u0e44\u0e21\u0e48\u0e40\u0e01\u0e34\u0e19", "must", "should not", "only", "limit", "within"]


@dataclass
class AnalysisResult:
    language: str = "unknown"
    task_type: str = "general"
    quality_score: int = 0
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    word_count: int = 0
    has_context: bool = False
    has_examples: bool = False
    has_output_format: bool = False
    has_constraints: bool = False


class PromptAnalyzer:
    """Analyze a prompt before improvement."""

    def analyze(self, prompt: str) -> AnalysisResult:
        text = prompt.strip()
        result = AnalysisResult()
        if not text:
            result.issues.append("prompt is empty")
            result.suggestions.append("add the task, context, output format, and constraints")
            return result

        lower = text.lower()
        result.word_count = len(text.split())
        result.language = self._detect_language(text)
        result.task_type = self._detect_task_type(lower)
        result.has_context = any(signal in lower for signal in CONTEXT_SIGNALS)
        result.has_examples = any(signal in lower for signal in EXAMPLE_SIGNALS)
        result.has_output_format = any(signal in lower for signal in FORMAT_SIGNALS)
        result.has_constraints = any(signal in lower for signal in CONSTRAINT_SIGNALS)
        result.issues, result.suggestions = self._evaluate(result)
        result.quality_score = self._score(result)
        return result

    def _detect_language(self, text: str) -> str:
        thai_chars = len(re.findall(r"[\u0E00-\u0E7F]", text))
        ascii_words = len(re.findall(r"[a-zA-Z]+", text))
        total = max(1, len(text))
        if thai_chars / total > 0.45:
            return "thai"
        if thai_chars and ascii_words:
            return "mixed"
        return "english"

    def _detect_task_type(self, lower_text: str) -> str:
        scores = {task_type: 0 for task_type in TASK_TYPES}
        for task_type, keywords in TASK_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in lower_text:
                    scores[task_type] += 1
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "general"

    def _evaluate(self, result: AnalysisResult) -> tuple[list[str], list[str]]:
        issues: list[str] = []
        suggestions: list[str] = []

        if result.word_count < 8:
            issues.append("prompt is too short")
            suggestions.append("add context, target audience, and expected output")
        if not result.has_context and result.task_type not in {"translation", "creative", "structured_output"}:
            issues.append("missing context")
            suggestions.append("state the background or situation")
        if not result.has_output_format and result.task_type in {"summary", "extraction", "rag", "analysis", "code", "tool_use"}:
            issues.append("missing output format")
            suggestions.append("specify bullets, JSON, table, code block, or section headings")
        if not result.has_examples and result.task_type in {"code", "extraction"}:
            issues.append("missing examples")
            suggestions.append("include input/output examples or a minimal test case")
        if not result.has_constraints:
            issues.append("missing constraints")
            suggestions.append("add limits, exclusions, or must-have requirements")
        if result.language == "mixed":
            issues.append("mixed language may confuse the model")
            suggestions.append("preserve technical terms, but keep the rewritten prompt in English")

        return issues, suggestions

    def _score(self, result: AnalysisResult) -> int:
        score = 35
        score += 15 if result.has_context else 0
        score += 15 if result.has_examples else 0
        score += 15 if result.has_output_format else 0
        score += 10 if result.has_constraints else 0
        score += 5 if 8 <= result.word_count <= 250 else 0
        score -= len(result.issues) * 7
        return max(0, min(100, score))
