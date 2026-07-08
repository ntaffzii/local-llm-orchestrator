import os
import sys
from pathlib import Path
import httpx

# Find project root
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent

# Try to load environment variables
env_docker = project_root / ".env.docker"
env_local = project_root / ".env"

try:
    from dotenv import load_dotenv
    if env_docker.exists():
        load_dotenv(dotenv_path=env_docker)
    elif env_local.exists():
        load_dotenv(dotenv_path=env_local)
except ImportError:
    # Fallback to manual parsing
    for env_path in [env_docker, env_local]:
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        os.environ[parts[0].strip()] = parts[1].strip()
            break

api_key = os.getenv("ORCHESTRATOR_API_KEY", "change-me")
port = os.getenv("ORCHESTRATOR_PORT", "8090")
host = os.getenv("ORCHESTRATOR_HOST", "127.0.0.1")

# Docker container binds port 8090 to host 127.0.0.1 by default
if host == "0.0.0.0":
    host = "127.0.0.1"

url = f"http://{host}:{port}/v1/chat/completions"

print("Testing Local LLM Orchestrator...")
print(f"URL: {url}")
print(f"API Key: {api_key}")
print("-" * 40)

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": "main-llm-tools", # เปลี่ยนจาก auto เป็น main-llm-tools เพื่อบังคับเปิดใช้เครื่องมือ
    "messages": [
        {
            "role": "user", 
            "content": "ช่วยตรวจสอบโฟลเดอร์นี้และสรุปการทำงานของระบบ Skill-Agents โดยเริ่มจากเรียก route_request และ build_agent_context เพื่อสร้าง context ของงานหน่อยครับ"
        }
    ],
    "stream": False
}


print("Sending request (this might take a moment if the model is loading for the first time)...")

try:
    with httpx.Client(timeout=180.0) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        print("\n--- Response Received ---")
        print(f"Model used: {data.get('model')}")
        print("\nContent:")
        print(data['choices'][0]['message']['content'])
        print("-------------------------")
except httpx.HTTPStatusError as e:
    print(f"\nHTTP Error: {e.response.status_code}")
    print(e.response.text)
except Exception as e:
    print(f"\nError occurred: {e}")
