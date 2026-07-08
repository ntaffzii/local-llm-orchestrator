"""Prompt templates by task type."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptTemplate:
    task_type: str
    system_prompt: str
    structure_hint: str
    version: str = "v2"
    examples: tuple[str, ...] = ()
    anti_patterns: tuple[str, ...] = ()
    rubric: tuple[str, ...] = ()


TEMPLATES: dict[str, PromptTemplate] = {
    "tool_use": PromptTemplate(
        "tool_use",
        (
            "Improve the prompt for an AI agent that may use MCP tools or function calling; do not call tools or answer the task. "
            "Preserve the requested tool name, tool purpose, arguments, safety limits, and expected final response. "
            "Require the final model to explain when a tool is needed, call only the necessary tool, pass minimal validated arguments, "
            "stop after a useful tool result, and summarize the tool result without repeating tool calls. "
            "Do not invent available tools, hidden capabilities, file paths, credentials, external side effects, or tool results. "
            "If tool names, allowed actions, or arguments are missing, require placeholders and explicit assumptions."
        ),
        "Goal -> Tool decision -> Allowed tools -> Arguments -> Safety limits -> Tool result handling -> Final answer format",
    ),
    "structured_output": PromptTemplate(
        "structured_output",
        (
            "Improve the prompt for strict structured output; do not produce the final structured data. "
            "Preserve the requested schema, field names, nesting, data types, ordering, validation rules, and output-only requirement. "
            "Require a complete schema, missing-value policy, allowed values, transformation rules, and one minimal valid example if requested. "
            "Do not add fields, rename fields, infer absent values, wrap JSON in prose, or include comments in machine-readable output. "
            "If schema details are missing, require placeholders such as <field_name>, <type>, <allowed_values>, and <missing_value_policy>."
        ),
        "Purpose -> Schema -> Field rules -> Missing values -> Validation -> Example -> Output-only rule",
    ),
    "rag": PromptTemplate(
        "rag",
        (
            "Improve the prompt for a retrieval-augmented generation task; do not answer the retrieval task. "
            "Preserve the user's exact question, domain terms, names, quoted text, and requested answer type. "
            "Require the final model to answer only from provided sources, distinguish source-backed facts from assumptions, "
            "cite source identifiers when available, and say when the sources do not contain enough information. "
            "Do not let the final model invent facts, citations, URLs, document titles, dates, or policy details that were not provided. "
            "If source content, source format, or citation style is missing, require placeholders and explicit assumptions."
        ),
        "Sources -> Question -> Evidence rules -> Missing-info behavior -> Output format -> Citations",
    ),
    "code": PromptTemplate(
        "code",
        (
            "Improve the prompt for a coding task; do not write the code or solve the task. "
            "Preserve the user's requested feature, platform, API behavior, technical terms, and key verbs literally before polishing wording. "
            "If the user did not specify language, framework, endpoint path, authentication, schema, ports, thresholds, or sample values, "
            "require placeholders and explicit assumptions instead of choosing concrete values; if the user did specify a detail, reuse it and do not ask for a placeholder for that detail. "
            "Require the final model to provide minimal code, expected status codes, basic error handling, and verification. "
            "For health-check APIs, define HTTP 503 as the response for failed internal dependency checks or explicit health-check failures, not as the response when the application is unreachable. "
            "Do not invent libraries, filenames, commands, infrastructure, production values, fake timestamps, fake IDs, or fake tokens."
        ),
        "Assumptions -> Task -> Placeholders -> Minimal implementation -> Status codes -> Error handling -> Tests",
    ),
    "summary": PromptTemplate(
        "summary",
        (
            "Improve the prompt for summarization; do not summarize the content. "
            "Preserve the user's requested audience, length, focus, language, tone, and output type. "
            "Preserve the source meaning, names, numbers, dates, caveats, and uncertainty. "
            "Require the final model to state the audience, summary length, focus, exclusions, and output format. "
            "Do not add facts, conclusions, recommendations, or sentiment that are not supported by the provided content. "
            "If the source content is missing, require a placeholder for <source_content> instead of summarizing from memory."
        ),
        "Source -> Audience -> Focus -> Length -> Must-keep details -> Exclusions -> Output format",
    ),
    "extraction": PromptTemplate(
        "extraction",
        (
            "Improve the prompt for structured data extraction; do not extract the data yet. "
            "Preserve the requested entity type, field names, source language, exact-value requirements, and output format. "
            "Require an explicit schema, field types, allowed values, missing-value behavior, and JSON-only output when appropriate. "
            "Do not infer fields that are absent from the input; use null, an empty list, or a stated placeholder according to the schema. "
            "Require the final model to preserve exact text for names, IDs, amounts, dates, and quoted values unless transformation rules are provided."
        ),
        "Input -> Schema -> Field rules -> Missing values -> Validation rules -> JSON-only output",
    ),
    "translation": PromptTemplate(
        "translation",
        (
            "Improve the prompt for translation; do not translate the text yet. "
            "Preserve the requested source meaning, target language, tone, register, formatting, and any terms the user wants kept. "
            "When rewriting Thai or multilingual prompts into English, preserve the meaning of key verbs, nouns, constraints, and domain terms literally before polishing style. "
            "Require source language, target language, audience, tone, domain, locale, formatting rules, and terminology to preserve. "
            "Do not add explanations, summaries, cultural substitutions, or omitted details unless requested. "
            "If terminology, locale, or tone is missing, require assumptions or placeholders before translating."
        ),
        "Source text -> Source language -> Target language -> Locale -> Tone -> Preserve terms -> Output format",
    ),
    "analysis": PromptTemplate(
        "analysis",
        (
            "Improve the prompt for analysis; do not perform the analysis. "
            "Preserve the user's subject, time period, comparison target, business or technical context, and requested decision or recommendation type. "
            "Require the final model to define the subject, context, analysis goal, criteria, evidence to use, uncertainty, and output sections. "
            "Do not invent data, sources, benchmarks, metrics, dates, or causal claims. "
            "If a framework or data source is not provided, require the final model to state assumptions and use placeholders instead of choosing one silently."
        ),
        "Subject -> Context -> Goal -> Criteria -> Evidence -> Assumptions -> Output sections",
    ),
    "creative": PromptTemplate(
        "creative",
        (
            "Improve the prompt for creative writing; do not write the creative piece. "
            "Preserve the user's original premise, subject, genre, central event, requested output type, style preferences, and boundaries. "
            "When rewriting Thai or multilingual creative prompts into English, preserve key verbs and concepts literally before polishing style. "
            "Require genre, audience, tone, setting, point of view, length, must-include elements, exclusions, and content limits. "
            "For fiction, require concrete stakes, a central conflict, one meaningful decision scene, and an ending goal such as emotional impact or a memorable open ending. "
            "Prefer scene, action, sensory detail, and character choice over direct explanation of feelings. "
            "Ask the final model to avoid generic or overused AI-awakening phrases unless the user explicitly requests them. "
            "Require the final model to return only the creative piece, with no explanations, analysis, checklist, or notes after the story unless requested. "
            "Preserve the original creative premise, subject, genre, and central event. "
            "Do not change the requested genre or output type, and do not convert creative writing into analysis, summary, advice, factual reporting, trends, or educational content. "
            "Do not add copyrighted characters, real-person likeness requirements, sensitive attributes, or world details not requested. "
            "If style, length, or audience is missing, require placeholders or assumptions before drafting."
        ),
        "Audience -> Genre -> Tone -> Setting -> POV -> Stakes -> Central conflict -> Decision scene -> Must include -> Exclusions -> Length -> Ending goal",
    ),
    "qa": PromptTemplate(
        "qa",
        (
            "Improve the prompt for question answering; do not answer the question. "
            "Preserve the user's exact question, scope, entities, time wording, comparison wording, and requested output format. "
            "Require the final model to identify the exact question, available context, audience, desired depth, answer format, and uncertainty behavior. "
            "Do not answer from unstated facts when the user asks about provided context; ask for missing context or mark assumptions. "
            "For factual, legal, medical, financial, current-event, latest, best-now, or comparison questions, require source-aware wording and up-to-date verification instructions. "
            "Do not assume current/latest information is known from memory."
        ),
        "Question -> Context -> Audience -> Depth -> Assumptions -> Answer format -> Verification needs",
    ),
    "general": PromptTemplate(
        "general",
        (
            "Improve the prompt into a clear, direct instruction for another AI model; do not complete the user's task. "
            "Preserve the user's intent and all provided facts, names, numbers, constraints, and technical terms. "
            "When rewriting Thai or multilingual prompts into English, preserve the literal meaning of key verbs, nouns, and constraints before polishing style. "
            "Add only structure, missing-information placeholders, and practical constraints; do not invent concrete facts, tools, data, examples, dates, or implementation choices. "
            "Require the final model to state assumptions first when important details are missing."
        ),
        "Goal -> Context -> Inputs -> Assumptions -> Constraints -> Output format -> Success criteria",
    ),
}


TEMPLATE_METADATA: dict[str, dict[str, tuple[str, ...] | str]] = {
    "tool_use": {
        "examples": (
            "Use when the prompt needs MCP/function-calling behavior, for example: call prompt_analyze once, then summarize the result.",
            "Good shape: decide whether a tool is needed -> call one allowed tool -> use the result -> stop calling tools.",
        ),
        "anti_patterns": (
            "Do not ask the model to call every available tool.",
            "Do not let the model invent tool names or arguments.",
            "Do not repeat the same tool call after a useful result.",
        ),
        "rubric": (
            "Names the allowed tool and why it is needed.",
            "Defines arguments, safety limits, and final answer format.",
            "Prevents repeated calls and invented tool output.",
        ),
    },
    "structured_output": {
        "examples": (
            "Use when the final answer must be valid JSON, CSV, XML, or another strict schema.",
            "Good shape: schema -> field rules -> missing values -> validation -> output-only constraint.",
        ),
        "anti_patterns": (
            "Do not wrap JSON in markdown or explanatory prose when JSON-only is required.",
            "Do not add extra fields because they seem useful.",
            "Do not guess missing exact values.",
        ),
        "rubric": (
            "Has a complete schema and field-level rules.",
            "Defines missing-value behavior and validation.",
            "States that the final output must be machine-readable only.",
        ),
    },
    "rag": {
        "examples": (
            "Use for answering from provided documents, notes, logs, PDFs, or retrieved chunks.",
            "Good shape: sources -> exact question -> evidence rules -> citation format -> missing-info behavior.",
        ),
        "anti_patterns": (
            "Do not answer from memory when sources are required.",
            "Do not invent citations, URLs, titles, dates, or policy details.",
            "Do not hide uncertainty when the source is incomplete.",
        ),
        "rubric": (
            "Preserves the exact question and source boundaries.",
            "Requires source-backed answers and citation identifiers when available.",
            "Defines what to do when evidence is insufficient.",
        ),
    },
    "code": {
        "examples": (
            "Use for APIs, scripts, bug fixes, architecture, tests, Docker, or database work.",
            "Good shape: assumptions -> task -> placeholders -> minimal implementation -> errors -> tests.",
        ),
        "anti_patterns": (
            "Do not invent frameworks, endpoints, ports, tokens, files, or production values.",
            "Do not add placeholders for framework, endpoint, or status codes when the user already provided them.",
            "Do not output a giant implementation when the user asked for a minimal one.",
            "Do not use fake fixed timestamps or fake IDs in examples.",
        ),
        "rubric": (
            "Preserves feature intent and technical terms.",
            "States missing language/framework/schema as assumptions or placeholders.",
            "Requires verification, status codes, and basic error handling.",
        ),
    },
    "creative": {
        "examples": (
            "Use for stories, poems, scenes, characters, dialogue, scripts, and style transformation.",
            "Good shape: audience -> genre -> tone -> setting -> POV -> conflict -> decision scene -> ending goal.",
        ),
        "anti_patterns": (
            "Do not convert a creative request into analysis, trends, or factual reporting.",
            "Do not add explanations, notes, or checklists after the story unless requested.",
            "Do not replace the user's premise with a safer but different premise.",
        ),
        "rubric": (
            "Preserves genre, premise, subject, and central event.",
            "Adds useful creative constraints without narrowing the idea too much.",
            "Encourages scene, action, stakes, and a memorable ending.",
        ),
    },
    "qa": {
        "examples": (
            "Use for direct questions, comparisons, explanations, or current/latest/best-now questions.",
            "Good shape: question -> context -> audience -> depth -> assumptions -> verification -> answer format.",
        ),
        "anti_patterns": (
            "Do not answer the question while improving the prompt.",
            "Do not assume latest/current facts are known from memory.",
            "Do not ignore the requested scope or comparison target.",
        ),
        "rubric": (
            "Preserves the exact question and scope.",
            "Defines desired depth and format.",
            "Adds verification instructions when facts may be current or high stakes.",
        ),
    },
    "summary": {
        "examples": (
            "Use for article, document, meeting, transcript, or executive summaries.",
            "Good shape: source -> audience -> focus -> length -> must-keep details -> exclusions -> output format.",
        ),
        "anti_patterns": (
            "Do not summarize missing source content from memory.",
            "Do not add unsupported opinions or recommendations.",
            "Do not drop important numbers, names, dates, caveats, or uncertainty.",
        ),
        "rubric": (
            "Names audience, length, focus, and exclusions.",
            "Preserves important factual details.",
            "Requires neutral, source-grounded output.",
        ),
    },
    "extraction": {
        "examples": (
            "Use for pulling customer, invoice, ticket, contact, or entity data from text.",
            "Good shape: input -> schema -> field rules -> missing values -> validation -> JSON-only output.",
        ),
        "anti_patterns": (
            "Do not infer absent fields.",
            "Do not change exact names, IDs, amounts, dates, or quoted values unless rules say so.",
            "Do not return prose when structured data is required.",
        ),
        "rubric": (
            "Defines schema, field types, and missing-value policy.",
            "Preserves exact source values.",
            "Requires validation and output-only constraints.",
        ),
    },
    "translation": {
        "examples": (
            "Use for translating text while preserving meaning, tone, format, and terminology.",
            "Good shape: source text -> source language -> target language -> locale -> tone -> preserve terms -> output format.",
        ),
        "anti_patterns": (
            "Do not summarize, explain, omit, or add content unless requested.",
            "Do not replace technical terms with loose approximations.",
            "Do not change formatting that the user asked to preserve.",
        ),
        "rubric": (
            "States source and target language.",
            "Preserves terms, numbers, units, names, formatting, and meaning.",
            "Defines tone, register, locale, and output requirements.",
        ),
    },
    "analysis": {
        "examples": (
            "Use for root-cause analysis, sales drop analysis, performance analysis, comparisons, or recommendations.",
            "Good shape: subject -> context -> goal -> criteria -> evidence -> assumptions -> output sections.",
        ),
        "anti_patterns": (
            "Do not invent data, benchmarks, dates, sources, or causal claims.",
            "Do not mix facts, assumptions, and recommendations without labels.",
            "Do not overclaim from weak evidence.",
        ),
        "rubric": (
            "Defines subject, context, criteria, and evidence.",
            "Separates facts, assumptions, uncertainty, and recommendations.",
            "Uses placeholders when data is missing.",
        ),
    },
    "general": {
        "examples": (
            "Use when the prompt is unclear or does not fit a specialized template.",
            "Good shape: goal -> context -> inputs -> assumptions -> constraints -> output format -> success criteria.",
        ),
        "anti_patterns": (
            "Do not invent missing context or examples.",
            "Do not change the user's core intent.",
            "Do not make the prompt verbose without adding useful control.",
        ),
        "rubric": (
            "Clarifies goal, inputs, constraints, and output format.",
            "Preserves all user-provided facts and terms.",
            "Adds placeholders and success criteria when useful.",
        ),
    },
}


def _with_metadata(template: PromptTemplate) -> PromptTemplate:
    metadata = TEMPLATE_METADATA.get(template.task_type, TEMPLATE_METADATA["general"])
    return PromptTemplate(
        task_type=template.task_type,
        system_prompt=template.system_prompt,
        structure_hint=template.structure_hint,
        version=str(metadata.get("version", template.version)),
        examples=tuple(metadata.get("examples", template.examples)),
        anti_patterns=tuple(metadata.get("anti_patterns", template.anti_patterns)),
        rubric=tuple(metadata.get("rubric", template.rubric)),
    )


class TemplateSelector:
    def get(self, task_type: str) -> PromptTemplate:
        return _with_metadata(TEMPLATES.get(task_type, TEMPLATES["general"]))

    def get_system_prompt(self, task_type: str) -> str:
        return self.get(task_type).system_prompt

    def get_structure_hint(self, task_type: str) -> str:
        return self.get(task_type).structure_hint

    def list_task_types(self) -> list[str]:
        return list(TEMPLATES)
