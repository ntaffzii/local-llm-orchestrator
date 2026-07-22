from __future__ import annotations

import re
from typing import Any

from .llama_client import ProviderClients
from .registry import ModelSelection
from prompt_engine import PromptAnalyzer, PromptImprover, TemplateSelector


_analyzer = PromptAnalyzer()
_rule_improver = PromptImprover()
_templates = TemplateSelector()


async def improve_prompt(
    client: ProviderClients,
    prompt: str,
    model_config: dict[str, Any],
    selection: ModelSelection,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    settings = model_config["prompt_improver"]
    analysis = _analyzer.analyze(prompt)
    rule_result = await _rule_improver.improve(prompt, analysis)
    template = _templates.get(analysis.task_type)
    payload = {
        "model": selection.target,
        "messages": [
            {"role": "system", "content": _build_system_prompt(settings["system_prompt"], template.system_prompt)},
            {"role": "user", "content": _build_user_prompt(prompt, analysis, template.structure_hint, rule_result)},
        ],
        "temperature": temperature if temperature is not None else settings["temperature"],
        "max_tokens": max_tokens if max_tokens is not None else settings["max_tokens"],
        "stream": False,
    }
    response = await client.post_json(selection.provider, "/v1/chat/completions", payload)
    improved = response["choices"][0]["message"]["content"].strip()
    return _enforce_required_guardrails(improved, analysis, prompt)


def _build_system_prompt(base_prompt: str, task_prompt: str) -> str:
    return "\n\n".join(
        [
            base_prompt.strip(),
            task_prompt.strip(),
            (
                "Use the prompt analysis only to rewrite the user's request. "
                "Do not answer the task. Keep the output English-only and conservative. "
                "Do not invent endpoint paths, URLs, auth schemes, parameters, response fields, timestamps, "
                "sample values, libraries, deployment details, or business rules. "
                "When the user did not provide a detail, require the final model to state assumptions first "
                "and use placeholders instead of fabricated specifics. "
                "Do not add placeholder instructions for details the user already provided. "
                "Use the rule-based draft as guardrails and structure, then refine it into one concise, natural prompt. "
                "Preserve the literal meaning of key verbs, nouns, constraints, domain terms, and requested output types before polishing style. "
                "Start the improved prompt with a direct imperative action such as Create, Write, Generate, Analyze, or Summarize. "
                "Do not start with generic meta-advice such as Understand the situation clearly. "
                "Do not change the user's task type, domain, genre, requested output, or intent. "
                "Do not refer to earlier, above, previous, or already-defined assumptions unless they are explicitly included in the improved prompt."
            ),
        ]
    )


def _build_user_prompt(prompt: str, analysis: Any, structure_hint: str, rule_result: Any) -> str:
    issues = "\n".join(f"- {issue}" for issue in analysis.issues) or "- none"
    suggestions = "\n".join(f"- {suggestion}" for suggestion in analysis.suggestions) or "- none"
    changes = "\n".join(f"- {change}" for change in rule_result.changes_summary) or "- none"
    return f"""Original prompt:
{prompt}

Prompt analysis:
- Detected language: {analysis.language}
- Detected task type: {analysis.task_type}
- Quality score: {analysis.quality_score}/100
- Issues:
{issues}
- Suggestions:
{suggestions}
- Recommended structure: {structure_hint}

Rule-based improved draft:
{rule_result.improved_prompt}

Rule-based changes:
{changes}

Rewrite the original prompt into an improved English prompt.
Preserve the user's intent and technical terms.
Preserve the literal meaning of key verbs, nouns, constraints, domain terms, and requested output types before polishing style.
Do not change the user's task type, domain, genre, requested output, or intent.
Do not convert creative writing into analysis, summary, advice, factual reporting, trends, or educational content.
For creative writing, explicitly preserve the requested premise, genre, protagonist or subject, and central event.
For fiction prompts, add requirements for concrete stakes, a central conflict, one meaningful decision scene, scene/action-based writing, and a memorable ending goal.
For creative writing prompts, require the final model to return only the creative piece with no explanations, analysis, checklist, or notes after the story unless requested.
Do not assume current/latest information is known; require verification when the user asks for latest, best now, current, or comparisons.
Start with a direct imperative instruction for the final model.
Do not write generic meta-advice such as "Understand the situation clearly" or "You need a straightforward guide".
Do not refer to "assumptions defined earlier", "above", or "previous context" unless that content appears inside the improved prompt.
If a concrete detail is missing, instruct the final model to state assumptions first and use placeholders.
If the original prompt already gives a concrete detail, reuse it and do not ask for a placeholder for that same detail.
Do not add endpoint paths, parameter names, response fields, fake timestamps, sample data, auth, frameworks, ports, thresholds, libraries, operating systems, commands, or infrastructure unless the original prompt provided them.
For API/code tasks, ask for a minimal implementation, proposed response shape marked as an assumption only when the schema is not fully provided, status codes, error handling, and a small test example that uses placeholders only for unknown values.
For health-check API tasks, define 503 as a response returned when an internal dependency or explicit health check fails; do not imply that the application can return 503 when it is completely unreachable.
Use the rule-based draft as the baseline, but make the final prompt smoother and easier for the final model to follow.
Return only the improved prompt."""


def _enforce_required_guardrails(improved: str, analysis: Any, original_prompt: str = "") -> str:
    improved = _remove_generic_opening(improved, analysis)
    improved = _remove_undefined_references(improved)
    if analysis.task_type == "code":
        improved = _replace_redundant_code_placeholders(improved, original_prompt)
    lower = improved.lower()

    required_lines = _base_guardrails(lower)
    handler = _TASK_GUARDRAILS.get(analysis.task_type, _default_guardrails)
    required_lines.extend(handler(lower, original_prompt))

    return _append_guardrails(improved, required_lines)


def _base_guardrails(lower: str) -> list[str]:
    lines: list[str] = []
    if "assumption" not in lower:
        lines.append("State important assumptions before completing the task.")
    if "placeholder" not in lower:
        lines.append("Use placeholders for important missing details instead of inventing concrete values.")
    return lines


def _rag_guardrails(lower: str, original_prompt: str) -> list[str]:
    lines: list[str] = []
    if "source" not in lower:
        lines.append("Use only the provided sources and cite source identifiers when available.")
    if "insufficient" not in lower and "not contain enough information" not in lower:
        lines.append("Say when the provided sources do not contain enough information.")
    if "invent" not in lower and "citation" not in lower:
        lines.append("Do not invent citations, URLs, document titles, or source details.")
    return lines


def _code_guardrails(lower: str, original_prompt: str) -> list[str]:
    lines: list[str] = []
    detail_flags = _provided_code_details(original_prompt)
    if "minimal implementation" not in lower and "minimal" not in lower:
        lines.append("Provide a minimal implementation.")
    if "status code" not in lower:
        lines.append("Include expected status codes.")
    if "error handling" not in lower and "error" not in lower:
        lines.append("Include basic error handling.")
    if "test" not in lower and "curl" not in lower:
        lines.append("Include a small test example, such as a curl command.")
    if "hard-coded" not in lower and "fake timestamp" not in lower:
        lines.append("Do not use hard-coded fake timestamps, fake IDs, fake tokens, or fake production values.")
    if detail_flags["health_check"] and "503" in original_prompt and "internal" not in lower and "dependency" not in lower:
        lines.append("For health checks, return HTTP 503 only when an internal dependency or explicit health-check function fails; do not describe 503 as the response when the application is completely unreachable.")
    endpoint_path = _provided_endpoint_path(original_prompt)
    if endpoint_path and endpoint_path.lower() not in lower:
        lines.append(f"Use the exact endpoint path provided by the user: {endpoint_path}.")
    status_codes = _provided_status_codes(original_prompt)
    missing_codes = [code for code in status_codes if code not in lower]
    if missing_codes:
        lines.append(f"Include the exact HTTP status codes provided by the user: {', '.join(status_codes)}.")
    if not detail_flags["endpoint_path"] and "endpoint path" not in lower and "<endpoint" not in lower:
        lines.append("Use a placeholder such as <endpoint_path> when the endpoint path was not provided.")
    if not detail_flags["framework"] and "framework" not in lower and "<framework" not in lower:
        lines.append("Use a placeholder such as <framework> when the framework was not provided.")
    if detail_flags["needs_timestamp"] and "example timestamp" not in lower and "<current_utc_iso_timestamp>" not in lower:
        lines.append("Use placeholders in examples, for example <current_utc_iso_timestamp>, instead of concrete fake timestamps.")
    return lines


def _summary_guardrails(lower: str, original_prompt: str) -> list[str]:
    lines: list[str] = []
    if "source" not in lower:
        lines.append("Summarize only the provided <source_content>.")
    if "names" not in lower and "numbers" not in lower:
        lines.append("Preserve important names, numbers, dates, caveats, and uncertainty.")
    if "do not add" not in lower and "unsupported" not in lower:
        lines.append("Do not add unsupported facts, recommendations, or sentiment.")
    return lines


def _extraction_guardrails(lower: str, original_prompt: str) -> list[str]:
    lines: list[str] = []
    if "schema" not in lower:
        lines.append("Define the extraction schema with field names, types, and missing-value behavior.")
    if "json" not in lower:
        lines.append("Return structured JSON only when the user requests structured output.")
    if "exact text" not in lower:
        lines.append("Preserve exact text for names, IDs, amounts, dates, and quoted values.")
    return lines


def _translation_guardrails(lower: str, original_prompt: str) -> list[str]:
    lines: list[str] = []
    if "target language" not in lower:
        lines.append("Specify <target_language>, <locale>, and <tone> when they are missing.")
    if "preserve" not in lower:
        lines.append("Preserve names, terminology, numbers, units, formatting, and meaning.")
    if "do not" not in lower:
        lines.append("Do not summarize, explain, omit, or add content unless requested.")
    return lines


def _analysis_guardrails(lower: str, original_prompt: str) -> list[str]:
    lines: list[str] = []
    if "criteria" not in lower:
        lines.append("Define analysis criteria and evidence before conclusions.")
    if "facts" not in lower:
        lines.append("Separate facts, assumptions, and recommendations.")
    if "invent" not in lower:
        lines.append("Do not invent data, benchmarks, metrics, sources, dates, or causal claims.")
    return lines


def _creative_guardrails(lower: str, original_prompt: str) -> list[str]:
    lines: list[str] = []
    if "creative writing" not in lower and "story" not in lower and "fiction" not in lower:
        lines.append("Preserve the creative-writing task; do not convert it into analysis, advice, factual reporting, trends, or educational content.")
    if original_prompt:
        lines.append(f"Preserve the original creative premise exactly as requested: {original_prompt}")
    elif "premise" not in lower and "central event" not in lower:
        lines.append("Preserve the original creative premise, genre, subject, and central event from the user's prompt; do not replace them with trends, analysis, or a different topic.")
    if "genre" not in lower and "tone" not in lower:
        lines.append("Specify genre, tone, audience, point of view, setting, length, and exclusions.")
    if "stakes" not in lower:
        lines.append("Include concrete stakes and a clear central conflict.")
    if "decision" not in lower:
        lines.append("Include one meaningful decision scene.")
    if "scene" not in lower and "action" not in lower:
        lines.append("Show emotion through scene, action, sensory detail, and character choice instead of direct explanation.")
    if "ending" not in lower:
        lines.append("Specify an ending goal, such as emotional impact or a memorable open ending.")
    if "generic" not in lower and "overused" not in lower and "cliche" not in lower:
        lines.append("Avoid generic or overused AI-awakening phrases unless explicitly requested.")
    if "explanation" not in lower and "checklist" not in lower and "notes" not in lower:
        lines.append("Return only the creative piece; do not add explanations, analysis, checklist, or notes after the story unless requested.")
    if "boundary" not in lower and "limit" not in lower:
        lines.append("Respect content boundaries and exclusions.")
    if "copyright" not in lower and "real-person" not in lower:
        lines.append("Do not introduce copyrighted characters, real-person likeness requirements, or sensitive details unless provided.")
    return lines


def _qa_guardrails(lower: str, original_prompt: str) -> list[str]:
    lines: list[str] = []
    if "exact question" not in lower:
        lines.append("Answer the exact question asked.")
    if "context" not in lower:
        lines.append("Use provided context when the question is context-bound.")
    if "verify" not in lower and "verification" not in lower:
        lines.append("Require verification for current, legal, medical, or financial claims.")
    if "latest" not in lower and "current" not in lower and "up-to-date" not in lower:
        lines.append("Do not assume current/latest information is known; require up-to-date verification for latest, best-now, or comparison questions.")
    return lines


def _default_guardrails(lower: str, original_prompt: str) -> list[str]:
    lines: list[str] = []
    if "output format" not in lower:
        lines.append("Specify the expected output format.")
    if "success" not in lower and "criteria" not in lower:
        lines.append("Define success criteria for the final answer.")
    return lines


_TASK_GUARDRAILS = {
    "rag": _rag_guardrails,
    "code": _code_guardrails,
    "summary": _summary_guardrails,
    "extraction": _extraction_guardrails,
    "translation": _translation_guardrails,
    "analysis": _analysis_guardrails,
    "creative": _creative_guardrails,
    "qa": _qa_guardrails,
}


def _append_guardrails(improved: str, required_lines: list[str]) -> str:
    if not required_lines:
        return improved

    requirements = "\n".join(f"- {line}" for line in required_lines)
    return f"""{improved}

Required guardrails:
{requirements}""".strip()


def _provided_code_details(original_prompt: str) -> dict[str, bool]:
    lower = original_prompt.lower()
    return {
        "framework": any(
            item in lower
            for item in (
                "fastapi",
                "flask",
                "django",
                "express",
                "nestjs",
                "spring",
                "gin",
                "fiber",
            )
        ),
        "endpoint_path": bool(re.search(r"(?<!\w)/[a-z0-9_./{}:-]+", lower)),
        "health_check": any(item in lower for item in ("health", "/health", "status server", "สถานะ server", "เช็คสถานะ")),
        "needs_timestamp": any(item in lower for item in ("timestamp", "time", "date", "เวลา", "วันที่")),
    }


def _replace_redundant_code_placeholders(improved: str, original_prompt: str) -> str:
    framework = _provided_framework(original_prompt)
    endpoint = _provided_endpoint_path(original_prompt)
    cleaned = improved

    if framework and endpoint:
        cleaned = re.sub(
            r"Use the <framework> placeholder for the API framework and <endpoint_path> for the specific URL\.",
            f"Use {framework} and the {endpoint} endpoint exactly as provided.",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"Use <framework> for the API framework and <endpoint_path> for the specific URL\.",
            f"Use {framework} and the {endpoint} endpoint exactly as provided.",
            cleaned,
            flags=re.IGNORECASE,
        )
    if framework:
        cleaned = re.sub(
            rf"Use the {re.escape(framework)} placeholder for [^.]+\.",
            f"Use {framework} as provided by the user.",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"Use the <framework> placeholder for the API framework\.?",
            f"Use {framework} as the API framework.",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = cleaned.replace("<framework>", framework)
    if endpoint:
        cleaned = re.sub(
            r"Use placeholders for any missing details such as endpoint path,\s*",
            "Use placeholders only for missing details such as ",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"Use placeholders for any missing details, including endpoint path,\s*",
            "Use placeholders only for missing details, including ",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"Use the <endpoint_path> placeholder for the endpoint path\.?",
            f"Use {endpoint} as the endpoint path.",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = cleaned.replace("<endpoint_path>", endpoint)
    cleaned = cleaned.replace("<curl>", "curl command")
    cleaned = cleaned.replace("<status_code>", "HTTP status code")
    if _provided_code_details(original_prompt)["health_check"]:
        cleaned = re.sub(
            r"503 (?:error|status|response)?\s*if the server is unavailable",
            "503 Service Unavailable response when an internal dependency or explicit health-check function fails",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"503 (?:error|status|response)?\s*when the server is unavailable",
            "503 Service Unavailable response when an internal dependency or explicit health-check function fails",
            cleaned,
            flags=re.IGNORECASE,
        )
    return cleaned.strip()


def _provided_framework(original_prompt: str) -> str:
    lower = original_prompt.lower()
    frameworks = {
        "fastapi": "Python FastAPI",
        "flask": "Flask",
        "django": "Django",
        "express": "Express",
        "nestjs": "NestJS",
        "spring": "Spring",
        "gin": "Gin",
        "fiber": "Fiber",
    }
    for key, label in frameworks.items():
        if key in lower:
            return label
    return ""


def _provided_endpoint_path(original_prompt: str) -> str:
    match = re.search(r"(?<!\w)(/[a-zA-Z0-9_./{}:-]+)", original_prompt)
    return match.group(1) if match else ""


def _provided_status_codes(original_prompt: str) -> list[str]:
    seen: set[str] = set()
    codes: list[str] = []
    for match in re.findall(r"\b[1-5][0-9]{2}\b", original_prompt):
        if match not in seen:
            seen.add(match)
            codes.append(match)
    return codes


def _remove_generic_opening(improved: str, analysis: Any) -> str:
    generic_openings = (
        "understand the situation clearly.",
        "you need a straightforward guide",
        "here is the improved request",
    )
    stripped = improved.strip()
    lower = stripped.lower()
    matched = next((opening for opening in generic_openings if lower.startswith(opening)), None)
    if not matched:
        return stripped
    remainder = stripped[len(matched):].strip()
    replacement = {
        "rag": "Create a concise prompt for the final model to answer using only the provided sources while preserving the user's intent.",
        "code": "Create a concise prompt for the final model to implement the requested code task while preserving the user's intent.",
        "summary": "Create a concise prompt for the final model to summarize the provided content while preserving the user's intent.",
        "extraction": "Create a concise prompt for the final model to extract structured data while preserving the user's intent.",
        "translation": "Create a concise prompt for the final model to translate the provided text while preserving the user's intent.",
        "analysis": "Create a concise prompt for the final model to analyze the subject while preserving the user's intent.",
        "creative": "Create a concise prompt for the final model to produce the requested creative work while preserving the user's intent.",
        "qa": "Create a concise prompt for the final model to answer the question while preserving the user's intent.",
    }.get(analysis.task_type, "Create a concise prompt for the final model while preserving the user's intent.")
    if not remainder:
        return replacement
    return f"{replacement}\n\n{remainder}"


def _remove_undefined_references(improved: str) -> str:
    replacements = {
        "Use the assumptions defined earlier and ": "State assumptions first, then ",
        "Use the assumptions defined earlier.": "State assumptions first.",
        "Use the assumptions defined above and ": "State assumptions first, then ",
        "Use the assumptions defined above.": "State assumptions first.",
        "Use the previous assumptions and ": "State assumptions first, then ",
        "Use the previous assumptions.": "State assumptions first.",
    }
    cleaned = improved
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    return cleaned.strip()
