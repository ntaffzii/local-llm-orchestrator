"""Prompt consulting utilities."""

from __future__ import annotations

from typing import Any

from .analyzer import AnalysisResult, PromptAnalyzer
from .templates import PromptTemplate, TemplateSelector


LANGUAGE_GUIDANCE = {
    "thai": "Keep the user's original meaning, but write the improved prompt in clear English unless the final task requires Thai output.",
    "mixed": "Keep technical terms as written, normalize the instruction language, and avoid mixing languages without purpose.",
    "english": "Keep the prompt in English and preserve the user's original technical terms.",
    "unknown": "Choose the language explicitly before using the prompt.",
}

OUTPUT_GUIDANCE = {
    "tool_use": "Use a tool-aware instruction: decide if a tool is needed, call only one necessary allowed tool, then summarize the result.",
    "structured_output": "Use a strict schema and output-only rule, especially for JSON, CSV, XML, or validation-sensitive output.",
    "rag": "Use source-grounded answer sections with citations or source IDs when available.",
    "code": "Use assumptions, minimal implementation, status/error behavior, and a small verification example.",
    "creative": "Use creative constraints such as genre, tone, setting, POV, conflict, decision scene, and ending goal.",
    "qa": "Use exact-question answering with scope, depth, assumptions, and verification needs.",
    "summary": "Use audience, length, focus, must-keep details, exclusions, and source-boundary rules.",
    "extraction": "Use schema, field rules, missing-value policy, validation, and JSON-only output.",
    "translation": "Use source/target language, locale, tone, terminology, and formatting preservation rules.",
    "analysis": "Use facts, assumptions, evidence, uncertainty, criteria, and recommendations as separate sections.",
    "general": "Use goal, context, inputs, assumptions, constraints, output format, and success criteria.",
}

TASK_USE = {
    "tool_use": "Use this when the model must decide whether to call MCP tools or function-calling tools.",
    "structured_output": "Use this when the final answer must follow a strict machine-readable format.",
    "rag": "Use this when the answer must come from provided documents or retrieved sources.",
    "code": "Use this for implementation, API, debugging, scripts, Docker, tests, or technical build tasks.",
    "creative": "Use this for stories, poems, scenes, dialogue, scripts, or creative style control.",
    "qa": "Use this for direct questions, explanations, comparisons, and latest/best-now questions.",
    "summary": "Use this for summarizing articles, documents, transcripts, or notes.",
    "extraction": "Use this for extracting entities or records from text into structured data.",
    "translation": "Use this for translating text while preserving meaning, tone, terms, and formatting.",
    "analysis": "Use this for diagnosing causes, comparing options, evaluating evidence, or making recommendations.",
    "general": "Use this when the request is unclear or does not fit a specialized template.",
}


def consult_prompt(prompt: str, preferred_language: str | None = None) -> dict[str, Any]:
    """Return deterministic expert guidance for improving a prompt."""

    analysis = PromptAnalyzer().analyze(prompt)
    template = TemplateSelector().get(analysis.task_type)
    language = preferred_language or _recommended_prompt_language(analysis)

    return {
        "success": bool(prompt.strip()),
        "original_prompt": prompt,
        "detected": {
            "language": analysis.language,
            "task_type": analysis.task_type,
            "quality_score": analysis.quality_score,
            "word_count": analysis.word_count,
            "has_context": analysis.has_context,
            "has_examples": analysis.has_examples,
            "has_output_format": analysis.has_output_format,
            "has_constraints": analysis.has_constraints,
            "issues": analysis.issues,
            "suggestions": analysis.suggestions,
        },
        "recommendation": {
            "role": "Prompt consultant",
            "intended_use": TASK_USE.get(analysis.task_type, TASK_USE["general"]),
            "recommended_prompt_language": language,
            "language_guidance": LANGUAGE_GUIDANCE.get(analysis.language, LANGUAGE_GUIDANCE["unknown"]),
            "how_to_write": _how_to_write(template, analysis),
            "output_guidance": OUTPUT_GUIDANCE.get(analysis.task_type, OUTPUT_GUIDANCE["general"]),
            "next_action": "Use /prompt/improve or the prompt model after filling the important missing details.",
        },
        "template": {
            "task_type": template.task_type,
            "version": template.version,
            "structure_hint": template.structure_hint,
            "examples": list(template.examples),
            "anti_patterns": list(template.anti_patterns),
            "rubric": list(template.rubric),
        },
        "questions_to_ask_first": _questions_to_ask_first(analysis),
    }


def _recommended_prompt_language(analysis: AnalysisResult) -> str:
    if analysis.language in {"thai", "mixed"}:
        return "English prompt for the model, with Thai output only if the user wants Thai final content."
    return "English"


def _how_to_write(template: PromptTemplate, analysis: AnalysisResult) -> list[str]:
    steps = [
        f"Start from this structure: {template.structure_hint}.",
        "Preserve the user's original intent, facts, names, constraints, and technical terms.",
        "Use placeholders for missing details instead of inventing concrete values.",
    ]
    if analysis.task_type == "creative":
        steps.append("Keep the original premise and genre; add creative control without changing the story idea.")
    if analysis.task_type == "tool_use":
        steps.append("Name the exact allowed tool and instruct the model to stop after a useful result.")
    if analysis.task_type == "code":
        steps.append("Ask for a minimal implementation, expected behavior, error handling, and one verification command.")
    if analysis.task_type == "structured_output":
        steps.append("Define a schema and require output-only machine-readable data.")
    if analysis.issues:
        steps.append("Fix the detected issues before sending the prompt to the final model.")
    return steps


def _questions_to_ask_first(analysis: AnalysisResult) -> list[str]:
    questions: list[str] = []
    if not analysis.has_context and analysis.task_type not in {"translation", "creative", "structured_output"}:
        questions.append("What context or background should the model know?")
    if not analysis.has_output_format:
        questions.append("What output format should the model return?")
    if not analysis.has_constraints:
        questions.append("What must the model include or avoid?")
    if analysis.task_type == "code":
        questions.extend(
            [
                "Which language, framework, endpoint path, and runtime should be used?",
                "What status codes, response schema, and error cases are required?",
            ]
        )
    elif analysis.task_type == "tool_use":
        questions.extend(
            [
                "Which MCP tool names are allowed?",
                "What arguments may the model pass to the tool?",
            ]
        )
    elif analysis.task_type == "creative":
        questions.extend(
            [
                "What length, tone, point of view, and ending style do you want?",
                "Are there any themes, characters, or content boundaries to include or avoid?",
            ]
        )
    elif analysis.task_type == "structured_output":
        questions.extend(
            [
                "What exact schema and field types should be used?",
                "How should missing or uncertain values be represented?",
            ]
        )
    return _dedupe(questions)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
