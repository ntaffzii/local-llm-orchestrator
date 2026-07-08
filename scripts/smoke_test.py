import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SmokeClient:
    def __init__(self, base_url: str, api_key: str, timeout: int) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def request(self, method: str, path: str, payload: dict | None = None, auth: bool = True) -> tuple[int, object]:
        headers = {}
        data = None
        if auth:
            headers["Authorization"] = "Bearer " + self.api_key
        if payload is not None:
            headers["Content-Type"] = "application/json; charset=utf-8"
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(self.base_url + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                return response.status, json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(body)
            except json.JSONDecodeError:
                detail = body
            return exc.code, detail


def load_api_key(env_file: Path) -> str:
    text = env_file.read_text(encoding="utf-8-sig")
    match = re.search(r"^\s*ORCHESTRATOR_API_KEY\s*=\s*(.+?)\s*$", text, re.M)
    if not match:
        raise RuntimeError(f"ORCHESTRATOR_API_KEY was not found in {env_file}")
    return match.group(1)


def print_result(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}")
    if detail:
        print(f"       {detail}")
    return ok


def chat(client: SmokeClient, model: str, prompt: str, max_tokens: int) -> tuple[int, object, float]:
    start = time.perf_counter()
    status, data = client.request(
        "POST",
        "/v1/chat/completions",
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "max_tokens": max_tokens,
        },
    )
    return status, data, time.perf_counter() - start


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the running Local LLM Orchestrator.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8090")
    parser.add_argument("--env-file", default=str(ROOT / ".env.docker"))
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--max-tokens", type=int, default=96)
    parser.add_argument("--full", action="store_true", help="Also test main/coding/improved model flows.")
    parser.add_argument("--mcp", action="store_true", help="Also call /mcp/tools.")
    parser.add_argument("--reload", action="store_true", help="Also call /admin/reload.")
    args = parser.parse_args()

    api_key = load_api_key(Path(args.env_file))
    client = SmokeClient(args.base_url, api_key, args.timeout)
    failures = 0

    status, data = client.request("GET", "/health", auth=False)
    failures += not print_result("public /health", status == 200 and data.get("status") == "ok", f"status={status}")

    status, data = client.request("GET", "/ready")
    failures += not print_result(
        "authenticated /ready",
        status == 200 and data.get("status") == "ready",
        f"status={status} body={data}",
    )

    status, data = client.request("GET", "/v1/models")
    model_ids = {item.get("id") for item in data.get("data", [])} if isinstance(data, dict) else set()
    expected = {"auto", "main-llm", "main-llm-improved", "coding", "coding-improved", "prompt"}
    failures += not print_result(
        "model registry /v1/models",
        status == 200 and expected <= model_ids,
        f"status={status} models={sorted(model_ids)}",
    )

    status, data = client.request("GET", "/admin/config")
    prompt_system = data.get("prompt_improver", {}).get("system_prompt", "") if isinstance(data, dict) else ""
    failures += not print_result(
        "admin config",
        status == 200 and "English prompt" in prompt_system,
        f"status={status}",
    )

    if args.reload:
        status, data = client.request("POST", "/admin/reload", {})
        failures += not print_result("admin reload", status == 200 and data.get("success") is True, f"status={status}")

    if args.mcp:
        status, data = client.request("GET", "/mcp/tools")
        failures += not print_result("mcp tools endpoint", status == 200 and "enabled" in data, f"status={status} body={data}")

    thai_prompt = "ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server"
    status, data = client.request(
        "POST",
        "/prompt/improve",
        {"prompt": thai_prompt, "model": "prompt", "temperature": 0.05, "max_tokens": 700},
    )
    improved = data.get("improved_prompt", "") if isinstance(data, dict) else ""
    original = data.get("original_prompt", "") if isinstance(data, dict) else ""
    ascii_ratio = sum(1 for char in improved if ord(char) < 128) / max(len(improved), 1)
    failures += not print_result(
        "LFM2.5 prompt improver Thai -> English",
        status == 200 and original == thai_prompt and ascii_ratio > 0.85,
        f"status={status} original={original!r} improved={improved!r}",
    )

    if args.full:
        tests = [
            ("main-llm", "Answer in one sentence: what is a health check API?"),
            ("main-llm-improved", "ช่วยเขียน api ง่ายๆ สำหรับเช็คสถานะ server"),
            ("coding", "Write a minimal health check endpoint example. Keep it short."),
            ("coding-improved", "ช่วยเขียน endpoint health check แบบสั้น"),
            ("auto", "debug this Python API health check function"),
        ]
        for model, prompt in tests:
            status, data, elapsed = chat(client, model, prompt, args.max_tokens)
            content = ""
            if isinstance(data, dict):
                choices = data.get("choices") or []
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
            failures += not print_result(
                f"chat model {model}",
                status == 200 and bool(content.strip()),
                f"status={status} elapsed={elapsed:.1f}s content={content[:180]!r}",
            )

    print()
    if failures:
        print(f"Smoke test completed with {failures} failure(s).")
        return 1
    print("Smoke test completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
