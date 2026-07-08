# Prompt Engine and MCP Prompt Tools

This document explains the current prompt-improvement flow used by
`local-llm-orchestrator` and the matching prompt tools served by `mcp-tools`.
For the external repositories that inspired the design, see
[Prompt Reference Sources and Local Adaptation](PROMPT_REFERENCES.md).

## Current Flow

Prompt improvement is designed to let the local LLM rewrite the prompt, while
the prompt templates and rule-based engine act as guardrails.

```text
User prompt
  -> PromptAnalyzer
  -> task template selection
  -> rule-based draft
  -> LFM2.5 prompt model
  -> post-check guardrails
  -> post-clean for redundant placeholders and task drift
  -> improved_prompt
```

The LLM is still the writer of the final improved prompt. The templates do not
replace the model; they keep the model from changing the user's task, inventing
missing details, or drifting into another genre or output type.

The final post-clean step fixes common small-model drift after LFM2.5 rewrites
the prompt. For example, if the user already provided `Python FastAPI` and
`/health`, the final prompt should not add `<framework>` or `<endpoint_path>`
placeholders for those same details.

## Prompt Consultant Flow

The prompt consultant is a planning layer before prompt improvement. It is for
questions like: what is this prompt for, which template should be used, what
language should the prompt use, and what details should the user add first?

```text
User prompt
  -> PromptAnalyzer
  -> TemplateSelector
  -> template examples, anti-patterns, and rubric
  -> consultation JSON
```

Use it when you want expert guidance before rewriting the prompt:

```text
Mode: Chat completion
Model: prompt-consultant
```

or call the deterministic endpoint:

```text
POST /prompt/consult
```

`prompt-consultant` does not generate the final answer and does not call MCP
tools. It returns guidance such as:

```text
detected task type
recommended prompt language
intended use
how to write the prompt
output guidance
questions to ask first
template examples
anti-patterns
rubric
```

## Files

Local orchestrator:

```text
prompt_engine/analyzer.py
prompt_engine/consultant.py
prompt_engine/templates.py
prompt_engine/improver.py
services/orchestrator/prompt_service.py
services/orchestrator/service.py
```

MCP tools project:

```text
E:\Dev\Projects\project-work\agents-llm-github\mcp-tools\prompt_engine\analyzer.py
E:\Dev\Projects\project-work\agents-llm-github\mcp-tools\prompt_engine\consultant.py
E:\Dev\Projects\project-work\agents-llm-github\mcp-tools\prompt_engine\templates.py
E:\Dev\Projects\project-work\agents-llm-github\mcp-tools\prompt_engine\improver.py
E:\Dev\Projects\project-work\agents-llm-github\mcp-tools\tools\prompt_improver.py
```

Keep the prompt engine files in sync between the two projects when prompt
behavior changes:

```powershell
Copy-Item -LiteralPath prompt_engine\analyzer.py -Destination E:\Dev\Projects\project-work\agents-llm-github\mcp-tools\prompt_engine\analyzer.py -Force
Copy-Item -LiteralPath prompt_engine\consultant.py -Destination E:\Dev\Projects\project-work\agents-llm-github\mcp-tools\prompt_engine\consultant.py -Force
Copy-Item -LiteralPath prompt_engine\templates.py -Destination E:\Dev\Projects\project-work\agents-llm-github\mcp-tools\prompt_engine\templates.py -Force
Copy-Item -LiteralPath prompt_engine\improver.py -Destination E:\Dev\Projects\project-work\agents-llm-github\mcp-tools\prompt_engine\improver.py -Force
```

## Template Behavior

All task templates now follow these rules:

- Improve the prompt only; do not answer the user's task.
- Preserve the user's task type, domain, requested output, and intent.
- Preserve key verbs, nouns, constraints, domain terms, and output type before
  polishing style.
- Use placeholders for missing values instead of inventing concrete details.
- Use placeholders only for details that are actually missing.
- Reuse concrete details the user already provided.
- Require assumptions when important details are missing.

Task-specific templates:

| Task type | Main behavior |
|---|---|
| `tool_use` | Prompt an agent to decide whether to call MCP/function tools, call only necessary tools, and stop after useful results. |
| `structured_output` | Require strict schemas, field rules, validation, missing-value behavior, and output-only machine-readable responses. |
| `rag` | Answer only from provided sources, cite source IDs, and say when sources are insufficient. |
| `code` | Preserve requested behavior, avoid invented implementation details, include minimal implementation, status codes, error handling, and tests. |
| `summary` | Preserve source meaning, names, numbers, dates, caveats, and uncertainty. |
| `extraction` | Require explicit schema, field types, missing-value behavior, and JSON-only output when appropriate. |
| `translation` | Preserve meaning, formatting, names, terms, numbers, units, tone, and locale. |
| `analysis` | Require subject, goal, criteria, evidence, uncertainty, and clear sections. |
| `creative` | Preserve premise and genre, require stakes/conflict/decision scene, and avoid generic AI-awakening phrasing. |
| `qa` | Preserve the exact question and require up-to-date verification for latest/current/best-now/comparison claims. |
| `general` | Add structure and constraints without inventing missing facts or tools. |

Every template now also has:

```text
examples
anti_patterns
rubric
```

These fields are used by `prompt-consultant` so it can explain when to use the
template, what to avoid, and how to judge whether the improved prompt is good.

## Code/API Prompt Rules

Code/API prompt improvement has extra safeguards because small local prompt
models can overuse placeholders or blur HTTP behavior.

Current code/API guardrails:

```text
- Preserve concrete framework names, endpoint paths, status codes, and technical terms when the user provides them.
- Do not add <framework> when the user already provided FastAPI, Flask, Express, or another framework.
- Do not add <endpoint_path> when the user already provided a path such as /health.
- Do not drop user-provided HTTP status codes such as 200 or 503.
- Use placeholders only for truly missing details, such as <auth_scheme> or <response_schema>.
- Remove undefined references such as "assumptions defined earlier" when those assumptions are not in the improved prompt.
- Clean awkward placeholder artifacts such as <curl> or <status_code>.
```

Health-check APIs have one extra rule:

```text
HTTP 503 means an internal dependency check or explicit health-check function failed.
Do not describe 503 as the response when the application is completely unreachable,
because an unreachable application cannot return its own HTTP response.
```

Example input:

```text
ช่วยเขียน API สำหรับเช็คสถานะ server ด้วย Python FastAPI
ต้องการ endpoint /health
ให้ตอบเป็นโค้ด Python แบบ minimal
response เป็น JSON
ต้องมี status code 200 และ 503
ใส่ error handling เบื้องต้น
และมี curl command สำหรับทดสอบ
```

Expected improved prompt behavior:

```text
- Keeps Python FastAPI.
- Keeps /health.
- Keeps status codes 200 and 503.
- Includes minimal implementation, JSON response, error handling, and curl test.
- Does not add <framework> or <endpoint_path>.
- Explains 503 as an internal dependency or explicit health-check failure.
```

## Creative Template Rules

The creative template was tightened because short story prompts were producing
usable but generic AI-awakening stories.

The current creative guardrails require:

```text
- Preserve key verbs and concepts literally before polishing style.
- Preserve the original creative premise, subject, genre, and central event.
- Preserve requested genre, tone, audience, and content boundaries.
- Include concrete stakes, a central conflict, one meaningful decision scene, and a memorable ending goal.
- Prefer scene, action, sensory detail, and character choice over direct explanation of feelings.
- Avoid generic AI-awakening phrases unless the user explicitly requests them.
- Do not convert creative writing into analysis, summary, advice, factual reporting, trends, or educational content.
```

Example input:

```text
ช่วยเขียนเรื่องสั้นไซไฟภาษาไทยเกี่ยวกับ AI ที่ตื่นขึ้นมา ให้มีความกดดัน มีมนุษย์หนึ่งคนเกี่ยวข้อง และมีฉากตัดสินใจสำคัญตอนท้าย
```

Expected improved prompt should mention ideas like:

```text
central conflict
human character
pivotal decision scene
stakes
sensory details
character choices
memorable ending goal
avoid generic or overused phrases
```

## Admin UI Usage

Use this for direct LFM2.5 prompt rewriting:

```text
Mode: Prompt improve
Model: prompt
Use tools: model default
Improve prompt: model default
```

Use this for prompt consulting before rewriting:

```text
Mode: Chat completion
Model: prompt-consultant
Use tools: model default
Improve prompt: model default
```

Use this for MCP tool workflow testing:

```text
Mode: Orchestrate chat
Model: main-llm-tools
Use tools: true
Improve prompt: false
```

The tool-enabled model is now guided to choose prompt tools from natural
language. The user does not need to name exact tools for common prompt work.

Natural prompt examples:

```text
ช่วยดู prompt นี้ให้หน่อยว่าดีไหม:
"ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server"
```

Expected tool behavior:

```text
prompt_consult
```

```text
ช่วยดูและปรับ prompt นี้ให้ใช้งานได้ดีขึ้น:
"ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server"
```

Expected tool behavior:

```text
prompt_consult -> prompt_improve_rule_based
```

Expected final answer behavior:

```text
- Mention the tools used.
- Mention detected task type and quality score.
- Mention the top missing details.
- Return the improved prompt from prompt_improve_rule_based.
- Do not write the final API/code/schema unless the user explicitly asks to execute the improved prompt.
```

The model may still choose fewer tools if the request only asks for analysis.
Use explicit tool names only when testing a deterministic path.

When testing MCP tools, start with explicit instructions such as:

```text
Call the MCP tool prompt_improve_rule_based exactly once for this prompt:
"ช่วยเขียนเรื่องสั้นแนวไซไฟเกี่ยวกับ AI ที่ตื่นขึ้นมา".
Return a concise summary of the tool result.
```

For deterministic MCP prompt consulting, call `prompt_consult` through
`/mcp/call`. This returns the same type of template guidance as
`/prompt/consult`, but from the MCP tools server.

## PowerShell Test Commands

Set the API key variables:

```powershell
cd "E:\Dev\Projects\project-work\agents-llm-github\local-llm-orchestrator"

$keyLine = Get-Content .env.docker | Where-Object { $_ -match '^ORCHESTRATOR_API_KEY=' } | Select-Object -First 1
$key = ($keyLine -split '=', 2)[1].Trim()
$headers = @{ Authorization = "Bearer $key" }
$headersJson = @{ Authorization = "Bearer $key"; "Content-Type" = "application/json; charset=utf-8" }
```

Test direct prompt improvement:

```powershell
$body = @{
  prompt = "ช่วยเขียนเรื่องสั้นไซไฟภาษาไทยเกี่ยวกับ AI ที่ตื่นขึ้นมา ให้มีความกดดัน มีมนุษย์หนึ่งคนเกี่ยวข้อง และมีฉากตัดสินใจสำคัญตอนท้าย"
  model = "prompt"
  temperature = 0.15
  max_tokens = 900
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8090/prompt/improve" `
  -Headers $headersJson `
  -Body ([Text.Encoding]::UTF8.GetBytes($body)) |
  ConvertTo-Json -Depth 20
```

Test direct prompt improvement for a FastAPI health-check API:

```powershell
$prompt = @'
ช่วยเขียน API สำหรับเช็คสถานะ server ด้วย Python FastAPI
ต้องการ endpoint /health
ให้ตอบเป็นโค้ด Python แบบ minimal
response เป็น JSON
ต้องมี status code 200 และ 503
ใส่ error handling เบื้องต้น
และมี curl command สำหรับทดสอบ
'@.Trim()

$body = @{
  prompt = $prompt
  model = "prompt"
  temperature = 0.05
  max_tokens = 800
} | ConvertTo-Json -Depth 10

$r = Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8090/prompt/improve" `
  -Headers $headersJson `
  -Body ([Text.Encoding]::UTF8.GetBytes($body)) `
  -TimeoutSec 180

$r.improved_prompt
"HAS_FRAMEWORK_PLACEHOLDER=" + ($r.improved_prompt -match "<framework>|placeholder for FastAPI")
"HAS_ENDPOINT_PLACEHOLDER=" + ($r.improved_prompt -match "<endpoint_path>|endpoint path,")
"HAS_HEALTH_ENDPOINT=" + ($r.improved_prompt -match "/health")
"HAS_200=" + ($r.improved_prompt -match "200")
"HAS_503=" + ($r.improved_prompt -match "503")
```

Expected check result:

```text
HAS_FRAMEWORK_PLACEHOLDER=False
HAS_ENDPOINT_PLACEHOLDER=False
HAS_HEALTH_ENDPOINT=True
HAS_200=True
HAS_503=True
```

Test prompt consultant:

```powershell
$body = @{
  prompt = "ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server"
  preferred_language = "English"
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8090/prompt/consult" `
  -Headers $headersJson `
  -Body ([Text.Encoding]::UTF8.GetBytes($body)) |
  ConvertTo-Json -Depth 20
```

Test prompt consultant from the OpenAI-compatible chat endpoint:

```powershell
$body = @{
  model = "prompt-consultant"
  messages = @(
    @{ role = "user"; content = "ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server" }
  )
  stream = $false
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8090/v1/chat/completions" `
  -Headers $headersJson `
  -Body ([Text.Encoding]::UTF8.GetBytes($body)) |
  ConvertTo-Json -Depth 20
```

Test MCP rule-based prompt tool directly:

```powershell
$body = @{
  name = "prompt_improve_rule_based"
  arguments = @{
    prompt = "ช่วยเขียนเรื่องสั้นไซไฟภาษาไทยเกี่ยวกับ AI ที่ตื่นขึ้นมา ให้มีความกดดัน มีมนุษย์หนึ่งคนเกี่ยวข้อง และมีฉากตัดสินใจสำคัญตอนท้าย"
    save_history = $false
  }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8090/mcp/call" `
  -Headers $headersJson `
  -Body ([Text.Encoding]::UTF8.GetBytes($body)) |
  ConvertTo-Json -Depth 20
```

Test MCP prompt consultant directly:

```powershell
$body = @{
  name = "prompt_consult"
  arguments = @{
    prompt = "ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server"
    preferred_language = "English"
  }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8090/mcp/call" `
  -Headers $headersJson `
  -Body ([Text.Encoding]::UTF8.GetBytes($body)) |
  ConvertTo-Json -Depth 20
```

Test orchestrated MCP tool use:

```powershell
$body = @{
  model = "main-llm-tools"
  messages = @(
    @{
      role = "user"
      content = "Call the MCP tool prompt_improve_rule_based exactly once for this prompt: ช่วยเขียนเรื่องสั้นแนวไซไฟเกี่ยวกับ AI ที่ตื่นขึ้นมา. Return a concise summary of the tool result."
    }
  )
  use_tools = $true
  improve_prompt = $false
  stream = $false
  max_tokens = 800
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8090/orchestrate/chat" `
  -Headers $headersJson `
  -Body ([Text.Encoding]::UTF8.GetBytes($body)) `
  -TimeoutSec 180 |
  ConvertTo-Json -Depth 20
```

## Rebuild After Prompt Engine Changes

Rebuild both services after changing local and MCP prompt engine files:

```powershell
docker compose --env-file .env.docker -f compose.yaml -f compose.cuda.yaml -f compose.mcp.yaml up -d --build orchestrator mcp-tools
```

## Verification

Run local compile checks:

```powershell
.\.venv\Scripts\python.exe -m py_compile prompt_engine\analyzer.py prompt_engine\consultant.py prompt_engine\templates.py prompt_engine\improver.py services\orchestrator\prompt_service.py services\orchestrator\service.py services\orchestrator\main.py services\orchestrator\schemas.py
```

Run MCP prompt tests:

```powershell
cd "E:\Dev\Projects\project-work\agents-llm-github\mcp-tools"
.\.venv\Scripts\python.exe -m unittest tests.test_prompt_improver -v
```

Expected result:

```text
Ran 4 tests
OK
```

## Known Notes

- `/prompt/improve` does not call MCP tools. It uses the local prompt model plus
  the local prompt engine.
- `/prompt/improve` now post-cleans code/API prompts so provided details such
  as `FastAPI`, `/health`, `200`, and `503` are preserved and not replaced by
  redundant placeholders.
- `Orchestrate chat` with `main-llm-tools` and `Use tools=true` is the path for
  testing model-decided MCP tool use.
- `/mcp/call` is the best path for deterministic MCP tool testing.
- Tool-enabled orchestration responses include `tool_trace`, which lists the
  MCP tools actually called, their arguments, error state, and a short result
  preview.
- llama.cpp/Qwen chat templates require system messages to appear at the
  beginning of the conversation. Tool-loop final notices are sent as user
  messages to avoid `System message must be at the beginning` errors.
