import json
import re
import sys
import urllib.request
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    prompt_file = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "scripts" / "prompts" / "health-api-th.txt"
    if not prompt_file.is_absolute():
        prompt_file = root / prompt_file

    env_text = (root / ".env.docker").read_text(encoding="utf-8-sig")
    match = re.search(r"^\s*ORCHESTRATOR_API_KEY\s*=\s*(.+?)\s*$", env_text, re.M)
    if not match:
        raise RuntimeError("ORCHESTRATOR_API_KEY was not found in .env.docker")

    prompt = prompt_file.read_text(encoding="utf-8").strip()
    body = json.dumps(
        {
            "prompt": prompt,
            "model": "prompt",
            "temperature": 0.1,
            "max_tokens": 900,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    request = urllib.request.Request(
        "http://127.0.0.1:8090/prompt/improve",
        data=body,
        method="POST",
        headers={
            "Authorization": "Bearer " + match.group(1),
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        data = json.loads(response.read().decode("utf-8"))

    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
