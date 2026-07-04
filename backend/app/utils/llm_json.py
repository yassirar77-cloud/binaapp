"""Small async DeepSeek chat helper that returns parsed JSON (M1).

Separate from AIService._call_deepseek on purpose: the legacy caller is
tuned for 24k-token raw-HTML emission; brief/intent calls need JSON mode,
a system message, small token caps, and call-time env reads (so tests can
monkeypatch env and so the Render-pinned model ID is always honored).
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.MULTILINE)


class LLMJSONError(Exception):
    """DeepSeek JSON call failed (config, HTTP, or unparsable output)."""


async def call_deepseek_json(
    prompt: str,
    *,
    system: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 4000,
    timeout: float = 60.0,
    model: Optional[str] = None,
) -> dict:
    """One DeepSeek chat call in JSON mode; returns the parsed object.

    Model resolution: explicit arg > DEEPSEEK_MODEL env > 'deepseek-chat'.
    Raises LLMJSONError on any failure — callers decide fallback policy.
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise LLMJSONError("DEEPSEEK_API_KEY not configured")

    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    model_id = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model_id,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise LLMJSONError(f"DeepSeek request failed: {exc}") from exc

    try:
        content = data["choices"][0]["message"]["content"]
        finish_reason = data["choices"][0].get("finish_reason")
    except (KeyError, IndexError) as exc:
        raise LLMJSONError(f"unexpected DeepSeek response shape: {exc}") from exc

    if finish_reason == "length":
        raise LLMJSONError(f"DeepSeek JSON output truncated at max_tokens={max_tokens}")

    # JSON mode should return bare JSON, but strip fences defensively.
    cleaned = _FENCE_RE.sub("", content).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMJSONError(f"DeepSeek returned unparsable JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise LLMJSONError(f"expected JSON object, got {type(parsed).__name__}")
    return parsed
