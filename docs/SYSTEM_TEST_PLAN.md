# System Test Plan

## Current Test Matrix

Use this section as the active test checklist for the current system. The older
sections below still contain detailed commands and troubleshooting notes.

| Area | What to test | How to test | Pass criteria |
|---|---|---|---|
| Docker stack | Required containers are running. | `docker compose --env-file .env.docker -f compose.yaml -f compose.cuda.yaml -f compose.mcp.yaml ps` | `llama-router`, `orchestrator`, and `mcp-tools` are up. |
| Orchestrator health | FastAPI is alive. | `GET /health` | Returns `status=ok`. |
| Orchestrator ready | Orchestrator can reach llama.cpp. | `GET /ready` with API key | Returns `status=ready`. |
| Models list | Physical and virtual models are exposed. | `GET /v1/models` | Includes `prompt`, `prompt-consultant`, `coding`, `coding-improved`, and `main-llm-tools`. |
| Prompt consultant | Deterministic prompt planning works without LLM tokens. | `POST /prompt/consult` or chat model `prompt-consultant` | Detects task type, gives questions/rubric, and chat mode has `usage.total_tokens=0`. |
| Prompt improve | LFM2.5 rewrites prompts. | `POST /prompt/improve` with `model=prompt` | Returns `success=true`, `model=lfm2.5-prompt`, and an English `improved_prompt`. |
| Code/API regression | Health-check prompt keeps user-provided details. | FastAPI `/health` prompt through `/prompt/improve` | Keeps `Python FastAPI`, `/health`, `200`, `503`; does not add `<framework>` or `<endpoint_path>`. |
| Direct model chat | A main/coding model can answer normally. | `POST /v1/chat/completions` with `model=coding` | Returns code/content and normal token usage. |
| Improved virtual model | Workflow can rewrite then call final model. | `POST /orchestrate/chat` with `model=coding-improved` | Final answer comes back after prompt improvement. |
| MCP discovery | Orchestrator can list MCP tools. | `GET /mcp/tools` | `enabled=true`, `available_tools>=tools`, includes `prompt_consult`. |
| MCP direct call | Deterministic MCP calls work. | `POST /mcp/call` with `prompt_analyze`, `prompt_consult`, or `prompt_improve_rule_based` | `is_error=false` and tool output is JSON/text. |
| MCP model tool use | Tool-enabled model can call MCP tools without looping forever. | `POST /orchestrate/chat` with `main-llm-tools`, `use_tools=true` | Response includes final answer and, when tools are used, top-level `tool_trace`. |
| Admin UI | Browser console can run main workflows. | `http://127.0.0.1:8090/admin/ui` | Connect succeeds; Playground works for `Prompt improve`, `prompt-consultant`, `Chat completion`, `Orchestrate chat`, and Tools tab presets/toggles. |
| Logs | No repeated backend failure. | `docker logs --tail 200 ...` | No repeated `Tool loop exceeded`, `llama_unavailable`, or MCP 421/503 errors. |

## Test Order

Run tests in this order when validating a new build:

```text
1. Docker stack
2. /health and /ready
3. /v1/models
4. /prompt/consult
5. /prompt/improve
6. FastAPI /health prompt regression
7. /v1/chat/completions with coding
8. /mcp/tools
9. /mcp/call prompt_consult
10. /orchestrate/chat with main-llm-tools
11. Admin UI smoke test
12. Logs
```

## Active Prompt Test Cases

### TC-PROMPT-001: Prompt Consultant

Purpose: Confirm that `prompt-consultant` explains how to write the prompt
without calling LFM2.5.

Input:

```text
ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server
```

Expected:

```text
detected.task_type = code
recommendation.role = Prompt consultant
template.rubric is not empty
questions_to_ask_first is not empty
usage.total_tokens = 0 when called through /v1/chat/completions
```

### TC-PROMPT-002: Prompt Improve

Purpose: Confirm that `lfm2.5-prompt` rewrites the user prompt.

Input:

```text
ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server
```

Expected:

```text
success = true
provider = local
model = lfm2.5-prompt
improved_prompt is English
improved_prompt does not answer with final code
```

### TC-PROMPT-003: FastAPI Health Check Regression

Purpose: Confirm that prompt post-clean preserves details the user already
provided and does not add redundant placeholders.

Input:

```text
ช่วยเขียน API สำหรับเช็คสถานะ server ด้วย Python FastAPI
ต้องการ endpoint /health
ให้ตอบเป็นโค้ด Python แบบ minimal
response เป็น JSON
ต้องมี status code 200 และ 503
ใส่ error handling เบื้องต้น
และมี curl command สำหรับทดสอบ
```

Expected:

```text
HAS_FRAMEWORK_PLACEHOLDER=False
HAS_ENDPOINT_PLACEHOLDER=False
HAS_HEALTH_ENDPOINT=True
HAS_200=True
HAS_503=True
```

Quality checks:

```text
- The improved prompt keeps Python FastAPI.
- The improved prompt keeps /health.
- The improved prompt keeps 200 and 503.
- The improved prompt does not add <framework>.
- The improved prompt does not add <endpoint_path>.
- If it explains 503, it should describe an internal dependency or explicit health-check failure, not a completely unreachable app.
```

### TC-MCP-001: MCP Tool Discovery

Purpose: Confirm that Docker orchestrator reaches the MCP tools container.

Expected:

```text
enabled = true
tool_allowlist is not empty
available_tools count >= tools count
tool list includes prompt_analyze
tool list includes prompt_consult
tool list includes prompt_improve_rule_based
```

### TC-MCP-001B: Admin UI Tool Manager

Purpose: Confirm that the browser UI can enable/disable MCP tools without
manually typing every tool name.

Steps:

```text
1. Open http://127.0.0.1:8090/admin/ui.
2. Enter ORCHESTRATOR_API_KEY and click Connect.
3. Open Tools.
4. Click Refresh tools.
5. Search for prompt.
6. Apply Prompt workflow preset.
7. Confirm the allowlist textarea contains only prompt_* tools.
8. Click Save selection.
9. Return to Tools, apply Recommended core, and Save selection to restore the
   safe default tool set.
```

Expected:

```text
available count shows discovered MCP tools
enabled tools count changes when presets or checkboxes change
Save selection calls PATCH /admin/mcp/tools with set_tools
after save, /mcp/tools reflects the new allowlist
```

### TC-MCP-002: MCP Prompt Consult

Purpose: Confirm that MCP can run the prompt consultant deterministically.

Call:

```text
POST /mcp/call
name = prompt_consult
arguments.prompt = ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server
arguments.preferred_language = English
```

Expected:

```text
is_error = false
content[0].text contains detected.task_type = code
content[0].text contains recommendation.role = Prompt consultant
```

### TC-MCP-003: Tool-Enabled Chat

Purpose: Confirm that `main-llm-tools` can use MCP tools and return a final
answer without getting stuck in a tool loop.

Natural-language input:

```text
ช่วยดูและปรับ prompt นี้ให้ใช้งานได้ดีขึ้น:
"ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server"
```

Expected tool choice:

```text
prompt_consult -> prompt_improve_rule_based
```

Expected:

```text
HTTP status is 200
choices[0].message.content is present
tool_trace is present when the model used tools
tool_trace should include prompt_consult for prompt-analysis requests
tool_trace should include prompt_improve_rule_based when the user asks to improve the prompt
final answer summarizes tools used, detected task type, quality score, missing details, and improved prompt
final answer does not write the final API/code/schema unless the user explicitly asks to execute the improved prompt
No Internal Server Error from Tool loop exceeded
```

### TC-MCP-004: Skill/Workflow Selection

Purpose: Confirm that skill/workflow selection does not get mixed with prompt
improvement unless the user asks for prompt improvement.

Natural-language input:

```text
ช่วยเลือก skill/workflow ที่เหมาะกับงานนี้:
ผมอยากสร้าง agent สำหรับช่วย review code และเปิด PR
```

Expected tool behavior:

```text
route_request
optional: list_toolsets
```

Expected final answer:

```text
- If route_request returns no workflows, skills, or toolsets, say that no registered MCP skill/workflow/toolset matched.
- Do not say there is no SKILL.md unless the model explicitly searched for SKILL.md files.
- Do not call prompt_consult or prompt_improve_rule_based unless the user also asked to improve the prompt.
- Do not repeatedly call route_request with rewritten prompts.
```

## Active Acceptance Criteria

The current build passes when all of these are true:

```text
- /health returns ok.
- /ready returns ready.
- /v1/models includes prompt-consultant.
- /prompt/consult returns deterministic consultation JSON.
- prompt-consultant chat returns usage.total_tokens = 0.
- /prompt/improve returns an improved prompt from lfm2.5-prompt.
- FastAPI /health prompt regression passes all HAS_* checks.
- /mcp/tools returns 15 allowed tools.
- /mcp/tools includes prompt_consult.
- /mcp/call prompt_consult returns task_type=code for the health API prompt.
- /orchestrate/chat with main-llm-tools does not fail with Tool loop exceeded.
- Admin UI can connect and run Prompt improve, prompt-consultant, and Chat completion.
```

เอกสารนี้ใช้สำหรับทดสอบระบบ `local-llm-orchestrator` แบบครบชุด ตั้งแต่ Docker, llama.cpp, Orchestrator API, Admin UI, Prompt Improver, MCP tools, และโมเดลที่ใช้งานจริง

ระบบชุดปัจจุบันประกอบด้วย 3 container หลัก:

```text
local-llm-llama-router-1   = llama.cpp model router
local-llm-orchestrator-1   = FastAPI OpenAI-compatible API gateway
local-llm-mcp-tools-1      = MCP tools server built from ../mcp-tools
```

## 1. เป้าหมายการทดสอบ

ใช้เอกสารนี้เพื่อตอบคำถามเหล่านี้:

- Docker stack เปิดครบหรือไม่
- Orchestrator API พร้อมใช้งานหรือไม่
- llama.cpp router ติดต่อได้หรือไม่
- โมเดลในระบบถูก list และเรียกใช้งานได้หรือไม่
- `lfm2.5-prompt` ปรับ prompt ได้จริงหรือไม่
- `qwen-coder` หรือ model coding ตอบงานเขียนโค้ดได้จริงหรือไม่
- MCP tools ต่อผ่าน Docker network ได้จริงหรือไม่
- Admin UI ใช้ connect, reload, playground, tools ได้หรือไม่
- ถ้าเกิด error จะดู log และแยกสาเหตุอย่างไร

## 2. โครงสร้างที่ต้องเข้าใจ

ไฟล์ Docker หลักอยู่ใน repo นี้:

```text
local-llm-orchestrator/
  compose.yaml
  compose.cuda.yaml
  compose.mcp.yaml
  .env.docker
```

ไฟล์ `compose.mcp.yaml` build MCP image จากอีกโฟลเดอร์:

```text
E:\Dev\Projects\project-work\agents-llm-github\mcp-tools
```

ใน `compose.mcp.yaml` มีค่า:

```yaml
build:
  context: ../mcp-tools
```

ดังนั้นเวลาเปิดด้วย compose ชุดใหม่ Docker จะรัน MCP tools จาก source ของ `mcp-tools` แล้วต่อเข้ากับ Orchestrator ผ่าน Docker service name:

```text
http://mcp-tools:8765/mcp
```

ไม่ควรใช้ `host.docker.internal:8765` สำหรับ flow นี้ เพราะเคยเจอปัญหา Windows/Docker route และ Host header แล้ว

## 3. คำสั่งเริ่มระบบ

เปิด PowerShell แล้วเข้าโฟลเดอร์:

```powershell
cd "E:\Dev\Projects\project-work\agents-llm-github\local-llm-orchestrator"
```

เปิดระบบแบบ CUDA + MCP:

```powershell
docker compose --env-file .env.docker -f compose.yaml -f compose.cuda.yaml -f compose.mcp.yaml up -d --build
```

ถ้าไม่ใช้ CUDA:

```powershell
docker compose --env-file .env.docker -f compose.yaml -f compose.mcp.yaml up -d --build
```

## 4. เช็ค container

```powershell
docker compose --env-file .env.docker -f compose.yaml -f compose.cuda.yaml -f compose.mcp.yaml ps
```

ผลลัพธ์ที่คาดหวัง:

```text
local-llm-llama-router-1   Up / healthy
local-llm-orchestrator-1   Up / healthy
local-llm-mcp-tools-1      Up
```

ถ้าต้องการดู container ทุกตัวในเครื่อง:

```powershell
docker ps
docker ps -a
```

ถ้าต้องการดูเฉพาะชุดนี้:

```powershell
docker ps -a --filter "name=local-llm"
```

## 5. ตั้งค่า API key ใน PowerShell

รันครั้งเดียวใน PowerShell session นั้น:

```powershell
$keyLine = Get-Content .env.docker | Where-Object { $_ -match '^ORCHESTRATOR_API_KEY=' } | Select-Object -First 1
$key = ($keyLine -split '=', 2)[1].Trim()
$headers = @{ Authorization = "Bearer $key" }
$headersJson = @{ Authorization = "Bearer $key"; "Content-Type" = "application/json" }
```

ถ้าคำสั่งนี้ error ให้เช็คก่อนว่าอยู่ในโฟลเดอร์ `local-llm-orchestrator` แล้ว:

```powershell
Get-Location
```

## 6. ทดสอบ health และ ready

Health endpoint ไม่ต้องใช้ API key:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8090/health"
```

ผลลัพธ์ที่คาดหวัง:

```text
status OK
```

Ready endpoint ใช้เช็คว่า Orchestrator ต่อ llama.cpp ได้:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8090/ready" -Headers $headers | ConvertTo-Json -Depth 10
```

ผลลัพธ์ที่คาดหวัง:

```json
{
  "status": "ready",
  "llama_cpp": {
    "status": "ok"
  },
  "mcp_enabled": true
}
```

ถ้า `llama_cpp` ไม่ ok ให้ดู log:

```powershell
docker logs --tail 120 local-llm-llama-router-1
docker logs --tail 120 local-llm-orchestrator-1
```

## 7. ทดสอบ list models

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8090/v1/models" -Headers $headers | ConvertTo-Json -Depth 20
```

ควรเห็น virtual models เช่น:

```text
auto
main-llm
main-llm-improved
main-llm-tools
coding
coding-improved
vision
prompt
```

และ physical models เช่น:

```text
lfm2.5-prompt
gemma4-e2b
qwen-tools
qwen-coder
vision-model
```

## 8. ทดสอบ Prompt Improver

Endpoint นี้ใช้ `lfm2.5-prompt` เพื่อปรับ prompt ไม่ใช่การตอบคำถามสุดท้าย

```powershell
$body = @{
  prompt = "ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server"
  model = "prompt"
  temperature = 0.05
  max_tokens = 500
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8090/prompt/improve" `
  -Headers $headersJson `
  -Body ([Text.Encoding]::UTF8.GetBytes($body)) |
  ConvertTo-Json -Depth 20
```

ผลลัพธ์ที่คาดหวัง:

```json
{
  "success": true,
  "provider": "local",
  "model": "lfm2.5-prompt",
  "original_prompt": "...",
  "improved_prompt": "..."
}
```

สิ่งที่ควรดูใน `improved_prompt`:

- เป็นภาษาอังกฤษ
- ไม่ตอบเป็น code ทันที
- ไม่แต่ง endpoint, auth, parameter, timestamp หรือ schema แบบมั่ว
- ถ้าข้อมูลขาด ควรสั่งให้ final model ระบุ assumptions ก่อน
- สำหรับงาน API ควรพูดเรื่อง minimal implementation, proposed response shape, status codes, error handling, test example

## 9. ทดสอบ Chat Completion แบบถามโมเดลตรง

ใช้ `coding` เพื่อทดสอบ `qwen-coder`:

```powershell
$body = @{
  model = "coding"
  messages = @(
    @{
      role = "user"
      content = "Write a minimal FastAPI /health endpoint. Do not use hard-coded fake timestamps."
    }
  )
  stream = $false
  max_tokens = 800
  temperature = 0.2
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8090/v1/chat/completions" `
  -Headers $headersJson `
  -Body ([Text.Encoding]::UTF8.GetBytes($body)) |
  ConvertTo-Json -Depth 20
```

ผลลัพธ์ที่คาดหวัง:

```text
choices[0].message.content มี code FastAPI
finish_reason เป็น stop หรือ length
usage มี prompt_tokens, completion_tokens, total_tokens
timings มี predicted_per_second
```

ถ้า `finish_reason = length`:

- เพิ่ม `max_tokens` เป็น `1200` หรือ `1600`
- หรือระบุให้ตอบสั้นลง

ถ้าได้ timestamp ปลอม เช่น `2023-10-27T10:00:00`:

- prompt ยังไม่ strict พอ
- ให้เพิ่มข้อความ `Do not use hard-coded fake timestamps`
- ควรใช้ `datetime.now(timezone.utc).isoformat()` หรืออธิบายเป็น assumption

## 10. ทดสอบ improved virtual model

ใช้ `coding-improved` เพื่อให้ระบบปรับ prompt ก่อนเข้า coding model:

```powershell
$body = @{
  model = "coding-improved"
  messages = @(
    @{
      role = "user"
      content = "ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server"
    }
  )
  stream = $false
  max_tokens = 900
  temperature = 0.2
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8090/orchestrate/chat" `
  -Headers $headersJson `
  -Body ([Text.Encoding]::UTF8.GetBytes($body)) |
  ConvertTo-Json -Depth 20
```

ผลลัพธ์ที่คาดหวัง:

- Orchestrator เรียก prompt improver ก่อน
- ส่ง prompt ที่ดีขึ้นให้ coding model
- ได้คำตอบเป็น code หรือคำแนะนำ final

หมายเหตุ: endpoint `/orchestrate/chat` อาจช้ากว่า `/v1/chat/completions` เพราะมี workflow เพิ่ม

## 11. ทดสอบ MCP tools discovery

```powershell
$r = Invoke-RestMethod -Uri "http://127.0.0.1:8090/mcp/tools" -Headers $headers
"tools=$($r.tools.Count)"
$r.tools | ForEach-Object { $_.function.name }
```

ผลลัพธ์ที่คาดหวังหลัง setup ล่าสุด:

```text
tools=14
list_files
read_file
load_skill
load_workflow
route_request
build_agent_context
list_toolsets
get_toolset
prompt_analyze
prompt_improve_rule_based
prompt_history_save
prompt_history_search
prompt_history_stats
prompt_history_export_markdown
```

ถ้าได้ `mcp_unavailable`:

1. เช็คว่า container MCP รันอยู่:

```powershell
docker ps --filter "name=local-llm-mcp-tools"
```

2. เช็ค log:

```powershell
docker logs --tail 120 local-llm-mcp-tools-1
docker logs --tail 120 local-llm-orchestrator-1
```

3. เช็ค `.env.docker` ต้องเป็น:

```env
MCP_SERVER_URL=http://mcp-tools:8765/mcp
MCP_ENABLED=true
```

4. Restart แบบมี `compose.mcp.yaml`:

```powershell
docker compose --env-file .env.docker -f compose.yaml -f compose.cuda.yaml -f compose.mcp.yaml up -d --build
```

## 12. ทดสอบ MCP call โดยตรง

ทดสอบ `prompt_analyze`:

```powershell
$body = @{
  name = "prompt_analyze"
  arguments = @{
    prompt = "Create a simple health check API for a server"
    task_type = "code"
  }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8090/mcp/call" `
  -Headers $headersJson `
  -Body $body |
  ConvertTo-Json -Depth 20
```

ผลลัพธ์ที่คาดหวัง:

```json
{
  "is_error": false,
  "content": [
    {
      "type": "text",
      "text": "{ ... \"task_type\": \"code\" ... }"
    }
  ]
}
```

ทดสอบ `prompt_improve_rule_based`:

```powershell
$body = @{
  name = "prompt_improve_rule_based"
  arguments = @{
    prompt = "Create a simple health check API for a server"
    task_type = "code"
    save_history = $true
    tags = @("system-test", "api")
  }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8090/mcp/call" `
  -Headers $headersJson `
  -Body $body |
  ConvertTo-Json -Depth 20
```

ผลลัพธ์ที่คาดหวัง:

- `is_error = false`
- มี improved prompt แบบ rule-based
- มีการบันทึก history ถ้า `save_history = true`

## 13. ทดสอบ Orchestrate Chat แบบใช้ tools

โหมดนี้ให้โมเดลตัดสินใจว่าจะเรียก MCP tools หรือไม่ จึงช้ากว่า test อื่น

```powershell
$body = @{
  model = "main-llm-tools"
  messages = @(
    @{
      role = "user"
      content = "Analyze this prompt once and improve it briefly: Create a health check API"
    }
  )
  improve_prompt = $false
  use_tools = $true
  stream = $false
  max_tokens = 500
  temperature = 0.1
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8090/orchestrate/chat" `
  -Headers $headersJson `
  -Body ([Text.Encoding]::UTF8.GetBytes($body)) `
  -TimeoutSec 180 |
  ConvertTo-Json -Depth 20
```

ผลลัพธ์ที่คาดหวัง:

- ไม่ควรได้ `Tool loop exceeded ...` เป็น 500 แล้ว
- ถ้า MCP ใช้ไม่ได้ ระบบควร fallback ตอบโดยไม่ใช้ tools
- ถ้า tool loop ครบรอบ ระบบควรบังคับจบรอบและให้โมเดลสรุปผลแทนการโยน Internal Server Error

ถ้าช้ามาก:

- ลด `max_tokens`
- ใช้ `/mcp/call` โดยตรงสำหรับทดสอบ tool
- ใช้ `Chat completion` สำหรับทดสอบโมเดล
- ใช้ `Orchestrate chat + tools` เฉพาะทดสอบ workflow จริง

## 14. ทดสอบ Admin UI

เปิดหน้าเว็บ:

```powershell
start http://127.0.0.1:8090/admin/ui
```

ขั้นตอน:

1. ใส่ `ORCHESTRATOR_API_KEY`
2. กด `Connect`
3. เช็คด้านบนควรเห็น:

```text
Orchestrator: OK
llama.cpp: Ready
Models: 13 หรือใกล้เคียงตาม config
MCP: On
```

ในแท็บ `Playground`:

### Prompt improve

```text
Mode: Prompt improve
Model: prompt
Max tokens: 500
Prompt: ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server
```

คาดหวัง:

- ได้ JSON มี `success: true`
- ได้ `improved_prompt` เป็นอังกฤษ

### Chat completion

```text
Mode: Chat completion
Model: coding
Max tokens: 800
Prompt: Write a minimal FastAPI /health endpoint. Do not use hard-coded fake timestamps.
```

คาดหวัง:

- ได้ code จากโมเดล
- ไม่จำเป็นต้องใช้ MCP

### Orchestrate chat

```text
Mode: Orchestrate chat
Model: coding-improved
Improve prompt: enabled หรือ model default
Use tools: disabled
```

คาดหวัง:

- ได้คำตอบ final หลังผ่าน prompt improvement

### Tools tab

กด refresh/list tools แล้วควรเห็น tools 14 ตัว

## 15. Smoke test script

ถ้ามี Python environment พร้อม:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test.py --mcp --reload
```

ถ้า `.venv` ไม่มี dependency บางตัว ให้ใช้ manual test ในเอกสารนี้แทน เพราะคำสั่งส่วนใหญ่ใช้ HTTP ผ่าน PowerShell และ Docker โดยตรง

## 16. วิธีดู log

Orchestrator:

```powershell
docker logs --tail 200 local-llm-orchestrator-1
```

llama.cpp:

```powershell
docker logs --tail 200 local-llm-llama-router-1
```

MCP tools:

```powershell
docker logs --tail 200 local-llm-mcp-tools-1
```

ดู log แบบ live:

```powershell
docker logs -f local-llm-orchestrator-1
```

## 17. Error ที่พบบ่อย

### PowerShell ใช้ `cd /d` ไม่ได้

`cd /d` เป็นคำสั่งของ CMD ไม่ใช่ PowerShell

ใช้:

```powershell
cd "E:\Dev\Projects\project-work\agents-llm-github\local-llm-orchestrator"
```

### ตัวแปร `$key` หายเมื่อใช้ `powershell -Command`

ถ้าอยู่ใน PowerShell อยู่แล้ว ไม่ต้องเรียก `powershell -Command` ซ้ำ

ให้รันเป็นหลายบรรทัด:

```powershell
$keyLine = Get-Content .env.docker | Where-Object { $_ -match '^ORCHESTRATOR_API_KEY=' } | Select-Object -First 1
$key = ($keyLine -split '=', 2)[1].Trim()
```

### ภาษาไทยกลายเป็น `????` หรือ `à¸...`

หลีกเลี่ยงการส่ง prompt ไทยแบบ inline ใน CMD

ใน PowerShell ให้ส่ง body เป็น UTF-8 bytes:

```powershell
-Body ([Text.Encoding]::UTF8.GetBytes($body))
```

หรือใช้ script:

```powershell
.\.venv\Scripts\python.exe scripts\test_prompt_improve.py --prompt-file scripts\prompts\health-api-th.txt
```

### `/mcp/tools` ได้ `mcp_unavailable`

เช็คว่าใช้ compose เสริม:

```powershell
docker compose --env-file .env.docker -f compose.yaml -f compose.cuda.yaml -f compose.mcp.yaml ps
```

เช็ค `.env.docker`:

```env
MCP_ENABLED=true
MCP_SERVER_URL=http://mcp-tools:8765/mcp
```

### `Tool loop exceeded`

ระบบปัจจุบันแก้แล้ว ไม่ควรกลายเป็น 500

ถ้ายังเจอ ให้ rebuild:

```powershell
docker compose --env-file .env.docker -f compose.yaml -f compose.cuda.yaml -f compose.mcp.yaml up -d --build orchestrator
```

### `finish_reason = length`

โมเดลตอบยาวเกิน `max_tokens`

แก้โดย:

```text
เพิ่ม max_tokens
หรือสั่งให้ตอบ concise
```

### `llama_unavailable`

แปลว่า Orchestrator ติดต่อ llama.cpp ไม่ได้

เช็ค:

```powershell
docker logs --tail 200 local-llm-llama-router-1
docker compose --env-file .env.docker -f compose.yaml -f compose.cuda.yaml -f compose.mcp.yaml ps
```

## 18. Acceptance Criteria

ถือว่าระบบผ่าน test ถ้า:

- `docker compose ps` เห็น 3 container หลัก
- `/ready` ได้ `status = ready`
- `/v1/models` เห็น virtual และ physical models
- `/prompt/improve` ได้ `success = true` และ improved prompt เป็นอังกฤษ
- `/v1/chat/completions` ด้วย `coding` ได้คำตอบจากโมเดล
- `/mcp/tools` ได้ `tools=14` หรือจำนวนตาม allowlist ล่าสุด
- `/mcp/call prompt_analyze` ได้ `is_error=false`
- Admin UI connect ได้ และ Playground รันได้อย่างน้อย 2 โหมด: `Prompt improve` และ `Chat completion`
- Log ไม่มี 500 ซ้ำจาก `Tool loop exceeded`

## 19. ชุดคำสั่งทดสอบเร็ว

ใช้เมื่ออยากเช็คระบบแบบเร็ว:

```powershell
cd "E:\Dev\Projects\project-work\agents-llm-github\local-llm-orchestrator"

docker compose --env-file .env.docker -f compose.yaml -f compose.cuda.yaml -f compose.mcp.yaml ps

$keyLine = Get-Content .env.docker | Where-Object { $_ -match '^ORCHESTRATOR_API_KEY=' } | Select-Object -First 1
$key = ($keyLine -split '=', 2)[1].Trim()
$headers = @{ Authorization = "Bearer $key" }
$headersJson = @{ Authorization = "Bearer $key"; "Content-Type" = "application/json" }

Invoke-RestMethod -Uri "http://127.0.0.1:8090/ready" -Headers $headers | ConvertTo-Json -Depth 10

$r = Invoke-RestMethod -Uri "http://127.0.0.1:8090/mcp/tools" -Headers $headers
"tools=$($r.tools.Count)"
$r.tools | ForEach-Object { $_.function.name }

$body = @{
  name = "prompt_analyze"
  arguments = @{
    prompt = "Create a simple health check API for a server"
    task_type = "code"
  }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8090/mcp/call" -Headers $headersJson -Body $body | ConvertTo-Json -Depth 20
```
