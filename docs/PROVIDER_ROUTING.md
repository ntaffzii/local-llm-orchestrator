# Provider Routing and Prompt Improvement

เอกสารนี้อธิบายวิธีใช้ `local-llm` แบบให้ local model ทำหน้าที่ปรับ prompt และให้ main model เปลี่ยน provider ได้ตาม config หรือ request

## หลักการ

ระบบแยกงานออกเป็น 2 ชั้น:

```text
raw user prompt
  -> prompt improver provider/model
  -> improved prompt
  -> main provider/model
  -> final answer
```

`prompt_improver` ใช้สำหรับ rewrite prompt เท่านั้น ไม่ตอบงานจริง ส่วน `virtual_models` เป็นชื่อที่ client เลือกใช้ เช่น `main-llm-improved` แล้วระบบจะดูว่า virtual model นั้นต้องส่ง final request ไป provider/model ไหน

## การรองรับ Prompt ภาษาไทย

`prompt_improver` ตามค่า default (`lfm2.5-prompt`) เป็นโมเดลเล็ก (1.2B) ที่ไม่แม่นเรื่องภาษาไทยพอที่จะ "แปล + ปรับ prompt" พร้อมกันในขั้นตอนเดียว ระบบจึงตรวจ prompt ก่อนว่ามีอักษรไทย (Unicode range `U+0E00`–`U+0E7F`, เช็คแบบ regex ธรรมดา ไม่เรียกโมเดล ไม่มีต้นทุน) แล้วแยก flow เป็น 2 แบบ:

```text
Prompt เป็นภาษาไทย:
  raw Thai prompt
    -> answer model/provider (แปลไทย -> อังกฤษ)
    -> English prompt
    -> prompt improver provider/model (ปรับ prompt เป็นภาษาอังกฤษล้วน)
    -> improved prompt + คำสั่ง "Respond in Thai."
    -> answer model/provider (ตอบจริง เป็นภาษาไทย)

Prompt เป็นภาษาอังกฤษ (หรือภาษาอื่นที่ไม่ใช่ไทย):
  raw prompt
    -> prompt improver provider/model
    -> improved prompt
    -> answer model/provider
    -> final answer
```

จุดสำคัญ:

- การแปลไทย -> อังกฤษ ใช้ **โมเดลเดียวกับที่จะตอบคำถามจริง** (เช่น `gemma4-e2b` ผ่าน provider `main`) ไม่ใช่ `lfm2.5-prompt` เพราะโมเดลใหญ่กว่ารองรับภาษาไทยได้ดีกว่าอยู่แล้ว และไม่ต้องเพิ่มโมเดล/provider ใหม่
- ไม่มีขั้นตอน "แปลคำตอบกลับเป็นไทย" แยกต่างหาก — คำสั่งให้ตอบเป็นไทยจะถูกแนบไปกับ prompt ที่ปรับปรุงแล้วในการเรียกโมเดลตอบจริงรอบเดียวกันเลย รวมทั้งหมด **3 รอบการเรียกโมเดล** (แปล → ปรับ prompt → ตอบ) แทนที่จะเป็น 4 รอบถ้าแยกขั้นตอนแปลคำตอบออกมาต่างหาก
- สิทธิ์การใช้โมเดล (`scopes.models` ของ API key) ตรวจกับโมเดลที่ใช้แปลด้วย เพราะใช้ selection เดียวกับโมเดลตอบจริงที่ผ่านการตรวจ scope แล้ว จึงไม่เปิดช่องให้ key ที่ถูกจำกัดสิทธิ์ไปเรียกโมเดลอื่นผ่านขั้นตอนแปล
- ถ้า prompt ไม่มีอักษรไทยเลย พฤติกรรมเดิมทุกอย่างไม่เปลี่ยน (ไม่มีรอบแปลเพิ่ม)

โค้ดอยู่ที่ `services/orchestrator/prompt_service.py` (`contains_thai`, `translate_to_english`) และ `services/orchestrator/service.py::_rewrite_last_user`

## ตั้งค่า Provider

แก้ไฟล์ `config/models.json`:

```json
"providers": {
  "local": {
    "type": "openai-compatible",
    "base_url": "http://127.0.0.1:8080",
    "api_key_env": ""
  },
  "lmstudio": {
    "type": "openai-compatible",
    "base_url": "http://127.0.0.1:1234/v1",
    "api_key_env": ""
  },
  "openrouter": {
    "type": "openai-compatible",
    "base_url": "https://openrouter.ai/api/v1",
    "api_key_env": "OPENROUTER_API_KEY"
  }
}
```

ทุก provider ต้องเป็น OpenAI-compatible endpoint. ถ้า `base_url` ลงท้ายด้วย `/v1` ได้ ระบบจะจัด path ให้เอง

## ตั้งค่า Prompt Improver

ให้ prompt improver อยู่ local ได้ แม้ final answer จะส่งไป provider อื่น:

```json
"prompt_improver": {
  "provider": "local",
  "model": "prompt",
  "system_prompt": "Rewrite the user's prompt for another AI model. Preserve its language, intent, facts, and constraints. Improve clarity and add an output format only when useful. Do not execute or answer the task. Return only the rewritten prompt.",
  "temperature": 0.15,
  "max_tokens": 800
}
```

ค่า `model: "prompt"` คือ virtual model ที่ map ไปยัง `lfm2.5-prompt` ใน `virtual_models`

## เปลี่ยน Main Provider

ถ้าต้องการให้ `main-llm-improved` ปรับ prompt ด้วย local model แต่ส่งคำตอบจริงไป OpenRouter:

```json
"main-llm-improved": {
  "provider": "openrouter",
  "model": "openai/gpt-4.1-mini",
  "improve_prompt": true,
  "tools": false
}
```

ถ้าต้องการส่งไป LM Studio:

```json
"main-llm-improved": {
  "provider": "lmstudio",
  "model": "qwen2.5-coder-7b-instruct",
  "improve_prompt": true,
  "tools": false
}
```

ถ้าต้องการกลับมาใช้ local:

```json
"main-llm-improved": {
  "provider": "local",
  "model": "gemma4-e2b",
  "improve_prompt": true,
  "tools": false
}
```

## ตั้งค่า API Key

ถ้า provider มี `api_key_env` ให้ตั้ง environment variable ชื่อนั้นก่อนเริ่ม service:

```powershell
$env:OPENROUTER_API_KEY="your-openrouter-key"
```

สำหรับ `local`, `lmstudio`, หรือ `ollama` ที่ไม่ต้องใช้ key ให้ตั้ง `api_key_env` เป็นค่าว่าง

## Reload Config

หลังแก้ `config/models.json` ให้ reload orchestrator:

```powershell
$key = $env:ORCHESTRATOR_API_KEY
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8090/admin/reload" `
  -Headers @{Authorization = "Bearer $key"}
```

ถ้าแก้ `config/models.ini` หรือเปลี่ยนไฟล์ GGUF ต้อง restart llama.cpp/local service แทน

## ใช้ผ่าน Web Admin UI

เปิดหน้า admin:

```text
http://127.0.0.1:8090/admin/ui
```

วิธีใช้:

1. ใส่ค่า `ORCHESTRATOR_API_KEY`
2. กด `Load config`
3. เลือก `Virtual model` เช่น `main-llm-improved`
4. เลือก `Main provider` เช่น `local`, `lmstudio`, หรือ `openrouter`
5. ใส่ `Main model id` เช่น `gemma4-e2b` หรือ `openai/gpt-4.1-mini`
6. ตั้ง `Improve prompt` เป็น `true`, `false`, หรือ `auto`
7. ตั้ง `Tools` เป็น `true`, `false`, หรือ `auto`
8. กด `Save virtual model`

เมื่อกด save ระบบจะ:

```text
update config/models.json
-> reload orchestrator components
-> ใช้งาน config ใหม่ทันที
```

ถ้าต้องการเปลี่ยนตัวปรับ prompt ให้แก้ส่วน `Prompt Improver` ในหน้าเดียวกัน แล้วกด `Save prompt improver`

ถ้าต้องการปรับ MCP tools ให้ใช้ส่วน `MCP Tools`:

1. ตั้ง `MCP enabled`
2. ใส่ allowlist แบบหนึ่ง tool ต่อหนึ่งบรรทัด
3. กด `Save MCP tools`

ระบบจะเรียก `PATCH /admin/mcp/tools`, เขียน `config/models.json`, แล้ว reload components ให้ทันที

หน้า `/admin/ui` เปิดได้โดยไม่ต้อง login แต่การโหลดและบันทึก config ทุกครั้งต้องใช้ `ORCHESTRATOR_API_KEY` ผ่าน protected admin API

## ใช้แบบ Prompt-only

ใช้ endpoint นี้เมื่อผู้ใช้ต้องการแค่ prompt ที่ดีขึ้น แล้วจะนำไปใช้กับ provider อื่นเอง:

```powershell
$key = $env:ORCHESTRATOR_API_KEY
$body = @{
  prompt = "ช่วยทำ api"
  model = "prompt"
  temperature = 0.15
  max_tokens = 800
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8090/prompt/improve" `
  -Headers @{Authorization = "Bearer $key"; "Content-Type" = "application/json"} `
  -Body $body
```

response จะมี `improved_prompt`:

```json
{
  "success": true,
  "provider": "local",
  "model": "lfm2.5-prompt",
  "original_prompt": "ช่วยทำ api",
  "improved_prompt": "..."
}
```

## ใช้แบบปรับ Prompt แล้วส่งต่อ

ใช้ `main-llm-improved` ผ่าน OpenAI-compatible endpoint:

```powershell
$key = $env:ORCHESTRATOR_API_KEY
$body = @{
  model = "main-llm-improved"
  messages = @(
    @{role = "user"; content = "ช่วยทำ api"}
  )
  stream = $false
} | ConvertTo-Json -Depth 10

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8090/v1/chat/completions" `
  -Headers @{Authorization = "Bearer $key"; "Content-Type" = "application/json"} `
  -Body $body
```

flow ที่เกิดขึ้น:

```text
user prompt
  -> prompt_improver.provider/model
  -> rewritten prompt
  -> main-llm-improved.provider/model
  -> final answer
```

## ใช้กับ Open WebUI หรือ GoModel

ตั้ง provider เป็น OpenAI-compatible:

```text
Base URL: http://127.0.0.1:8090/v1
API Key:  ORCHESTRATOR_API_KEY
Model:    main-llm-improved
```

ถ้าอยากเปลี่ยน main provider ให้แก้ `main-llm-improved` ใน `config/models.json` แล้ว reload config. ฝั่ง Open WebUI/GoModel ยังเลือก model เดิมได้

## ตัวอย่าง Pattern ที่แนะนำ

Prompt improver local, final answer remote:

```json
"prompt_improver": {
  "provider": "local",
  "model": "prompt"
},
"virtual_models": {
  "main-llm-improved": {
    "provider": "openrouter",
    "model": "openai/gpt-4.1-mini",
    "improve_prompt": true,
    "tools": false
  }
}
```

Prompt improver local, final answer local:

```json
"virtual_models": {
  "main-llm-improved": {
    "provider": "local",
    "model": "gemma4-e2b",
    "improve_prompt": true,
    "tools": false
  }
}
```

Prompt-only, no final answer:

```text
POST /prompt/improve
```

## Troubleshooting

- ถ้า remote provider ตอบ `401` ให้ตรวจ environment variable ตาม `api_key_env`
- ถ้า LM Studio/Ollama ตอบ `404` ให้ตรวจ `base_url` และชื่อ model ที่ server นั้น expose จริง
- ถ้าแก้ `models.json` แล้วไม่เปลี่ยน ให้เรียก `POST /admin/reload`
- ถ้าเลือก `main-llm-improved` แล้ว final answer ยังออก local ให้ตรวจว่า virtual model นั้นมี `"provider": "openrouter"` หรือ provider ที่ต้องการแล้ว
