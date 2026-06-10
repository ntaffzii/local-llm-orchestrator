from __future__ import annotations

from typing import Any

from .llama_client import LlamaClient


async def improve_prompt(
    client: LlamaClient,
    prompt: str,
    model_config: dict[str, Any],
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    settings = model_config["prompt_improver"]
    target = model or model_config["routing"]["prompt_model"]
    payload = {
        "model": target,
        "messages": [
            {"role": "system", "content": settings["system_prompt"]},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature if temperature is not None else settings["temperature"],
        "max_tokens": max_tokens if max_tokens is not None else settings["max_tokens"],
        "stream": False,
    }
    response = await client.post_json("/v1/chat/completions", payload)
    return response["choices"][0]["message"]["content"].strip()
