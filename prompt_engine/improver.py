"""Prompt improvement engine with optional OpenAI-compatible local model."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .analyzer import AnalysisResult
from .templates import TemplateSelector


@dataclass
class ImproveResult:
    original_prompt: str
    improved_prompt: str
    task_type: str
    quality_before: int
    quality_after: int
    changes_summary: list[str] = field(default_factory=list)
    structure_hint: str = ""
    model_used: str = "rule-based"
    success: bool = True
    error: str | None = None


class PromptImprover:
    """Improve prompts with a local LLM when configured, otherwise use rules."""

    def __init__(
        self,
        api_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout: int = 45,
        use_fallback: bool = True,
    ) -> None:
        self.api_url = api_url or os.getenv("PROMPT_IMPROVER_API_URL", "")
        self.model = model or os.getenv("PROMPT_IMPROVER_MODEL", "local-model")
        self.api_key = api_key or os.getenv("PROMPT_IMPROVER_API_KEY", "")
        self.timeout = timeout
        self.use_fallback = use_fallback
        self.selector = TemplateSelector()

    async def improve(self, original_prompt: str, analysis: AnalysisResult) -> ImproveResult:
        template = self.selector.get(analysis.task_type)
        error: str | None = None

        if self.api_url:
            try:
                improved = await self._call_llm(original_prompt, analysis)
                model_used = self.model
            except Exception as exc:
                if not self.use_fallback:
                    return ImproveResult(
                        original_prompt=original_prompt,
                        improved_prompt=original_prompt,
                        task_type=analysis.task_type,
                        quality_before=analysis.quality_score,
                        quality_after=analysis.quality_score,
                        success=False,
                        error=str(exc),
                    )
                improved = self._rule_based_improve(original_prompt, analysis)
                model_used = "rule-based"
                error = f"model unavailable; used fallback: {exc}"
        else:
            improved = self._rule_based_improve(original_prompt, analysis)
            model_used = "rule-based"

        quality_after = min(100, max(analysis.quality_score + 15, analysis.quality_score + (100 - analysis.quality_score) // 2))
        return ImproveResult(
            original_prompt=original_prompt,
            improved_prompt=improved,
            task_type=analysis.task_type,
            quality_before=analysis.quality_score,
            quality_after=quality_after,
            changes_summary=self._summarize_changes(analysis),
            structure_hint=template.structure_hint,
            model_used=model_used,
            success=True,
            error=error,
        )

    async def _call_llm(self, original_prompt: str, analysis: AnalysisResult) -> str:
        import httpx

        template = self.selector.get(analysis.task_type)
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload = {
            "model": self.model,
            "temperature": 0.05,
            "max_tokens": 1200,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        template.system_prompt
                        + " Return only the improved English prompt. "
                        + "Do not invent endpoint paths, URLs, auth schemes, parameters, response fields, timestamps, sample values, libraries, deployment details, or business rules."
                    ),
                },
                {"role": "user", "content": self._build_user_message(original_prompt, analysis)},
            ],
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.api_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    def _build_user_message(self, original_prompt: str, analysis: AnalysisResult) -> str:
        issues = "\n".join(f"- {issue}" for issue in analysis.issues) or "- none"
        suggestions = "\n".join(f"- {suggestion}" for suggestion in analysis.suggestions) or "- none"
        return f"""Original prompt:
{original_prompt}

Analysis:
- Language: {analysis.language}
- Task type: {analysis.task_type}
- Quality score: {analysis.quality_score}/100
- Issues:
{issues}
- Suggestions:
{suggestions}

Rewrite the prompt in English only. Preserve user intent and technical terms.
Preserve the literal meaning of key verbs, nouns, constraints, domain terms, and requested output types before polishing style.
Do not invent missing concrete details; use placeholders or ask the final model to state assumptions first.
For API/code tasks, require a minimal implementation, proposed response shape marked as an assumption, status codes, error handling, and a small test example.
Tell the final model not to use hard-coded fake dates or fake production values."""

    def _rule_based_improve(self, original_prompt: str, analysis: AnalysisResult) -> str:
        template = self.selector.get(analysis.task_type)
        sections = [
            "Role: An AI assistant that answers clearly, verifies important claims, and avoids unsupported guesses",
            f"Task type: {analysis.task_type}",
            f"Task:\n{original_prompt.strip()}",
        ]
        if not analysis.has_context:
            sections.append("Context: <add relevant background or state assumptions first>")
        if not analysis.has_output_format:
            sections.append(f"Output format: {self._default_format(analysis.task_type)}")
        if not analysis.has_constraints:
            sections.append(
                "Constraints:\n"
                "- Be specific.\n"
                "- Do not invent missing details.\n"
                "- Use placeholders for unknown inputs, sources, schemas, formats, examples, dates, metrics, tools, and domain-specific details."
            )
        if analysis.task_type == "code":
            sections.append(
                "Code/API guardrails:\n"
                "- Preserve the requested feature, API behavior, technical terms, and key verbs.\n"
                "- State assumptions before the implementation.\n"
                "- Use placeholders only for details that are missing; do not add placeholders for framework, endpoint path, or status codes when the user already provided them.\n"
                "- Suggested placeholders for missing details: <framework>, <endpoint_path>, <auth_scheme>, <response_schema>, and <current_utc_iso_timestamp>.\n"
                "- Mark any proposed response schema as an assumption.\n"
                "- For health-check APIs, define HTTP 503 as the response for failed internal dependency checks or explicit health-check failures, not for a completely unreachable application.\n"
                "- Do not use hard-coded fake timestamps, fake IDs, fake tokens, or fake production values.\n"
                "- Do not choose concrete framework names, endpoint paths, ports, OS commands, or load thresholds unless the user provided them.\n"
                "- Use placeholders in examples instead of concrete fake values.\n"
                "- Include a small test example only after the assumptions."
            )
        elif analysis.task_type == "rag":
            sections.append(
                "RAG guardrails:\n"
                "- Preserve the exact question, domain terms, names, and quoted text.\n"
                "- Answer only from provided sources.\n"
                "- Cite source identifiers when available.\n"
                "- Say when the sources do not contain enough information.\n"
                "- Do not invent citations, URLs, document titles, or policy details."
            )
        elif analysis.task_type == "summary":
            sections.append(
                "Summary guardrails:\n"
                "- Preserve the requested audience, focus, language, tone, and output type.\n"
                "- Preserve names, numbers, dates, caveats, and uncertainty.\n"
                "- Do not add facts, recommendations, or sentiment not present in the source.\n"
                "- Use <source_content>, <audience>, and <length> placeholders when missing."
            )
        elif analysis.task_type == "extraction":
            sections.append(
                "Extraction guardrails:\n"
                "- Preserve requested entity type, field names, source language, and exact-value requirements.\n"
                "- Define an exact schema with field types.\n"
                "- Specify missing-value behavior.\n"
                "- Preserve exact text for names, IDs, amounts, dates, and quoted values.\n"
                "- Return JSON only when requested."
            )
        elif analysis.task_type == "translation":
            sections.append(
                "Translation guardrails:\n"
                "- Preserve key verbs, nouns, constraints, domain terms, formatting, and meaning before polishing style.\n"
                "- Preserve meaning, formatting, names, terms, numbers, and units.\n"
                "- Do not summarize, explain, omit, or add content unless requested.\n"
                "- Use <target_language>, <locale>, and <tone> placeholders when missing."
            )
        elif analysis.task_type == "analysis":
            sections.append(
                "Analysis guardrails:\n"
                "- Preserve subject, time period, comparison target, context, and requested recommendation type.\n"
                "- Define criteria and evidence before conclusions.\n"
                "- Separate facts, assumptions, and recommendations.\n"
                "- Do not invent data, benchmarks, metrics, sources, or causal claims."
            )
        elif analysis.task_type == "creative":
            sections.append(
                "Creative guardrails:\n"
                "- Preserve key verbs and concepts literally before polishing style.\n"
                "- Preserve the original creative premise, subject, genre, and central event.\n"
                "- Preserve requested genre, tone, audience, and content boundaries.\n"
                "- Include concrete stakes, a central conflict, one meaningful decision scene, and a memorable ending goal.\n"
                "- Prefer scene, action, sensory detail, and character choice over direct explanation of feelings.\n"
                "- Avoid generic AI-awakening phrases unless the user explicitly requests them.\n"
                "- Return only the creative piece; do not add explanations, analysis, checklist, or notes after the story unless requested.\n"
                "- Do not convert creative writing into analysis, summary, advice, factual reporting, trends, or educational content.\n"
                "- Use placeholders for missing style, length, point of view, and setting.\n"
                "- Do not introduce copyrighted characters, real-person likeness requirements, or sensitive details unless provided."
            )
        elif analysis.task_type == "qa":
            sections.append(
                "Q&A guardrails:\n"
                "- Preserve the exact question, scope, entities, time wording, and comparison wording.\n"
                "- Answer the exact question asked.\n"
                "- Use only provided context when the task is context-bound.\n"
                "- State uncertainty or missing context before answering.\n"
                "- Require up-to-date verification for latest, best-now, current, legal, medical, financial, or comparison claims.\n"
                "- Do not assume current/latest information is known from memory."
            )
        sections.append(f"Recommended structure: {template.structure_hint}")
        sections.append("Rewrite this as an English prompt for the final model.")
        return "\n\n".join(sections).strip()

    def _default_format(self, task_type: str) -> str:
        if task_type == "extraction":
            return "JSON only"
        if task_type == "summary":
            return "3-5 bullet points"
        if task_type == "analysis":
            return "sections with evidence and conclusion"
        if task_type == "code":
            return "complete code block plus short verification notes"
        return "clear sections"

    def _summarize_changes(self, analysis: AnalysisResult) -> list[str]:
        changes = []
        if not analysis.has_context:
            changes.append("added context or assumptions placeholder")
        if not analysis.has_output_format:
            changes.append("added output format")
        if not analysis.has_constraints:
            changes.append("added conservative constraints")
        if not analysis.has_examples and analysis.task_type in {"code", "extraction"}:
            changes.append("suggested examples or tests")
        return changes or ["tightened clarity and specificity"]
