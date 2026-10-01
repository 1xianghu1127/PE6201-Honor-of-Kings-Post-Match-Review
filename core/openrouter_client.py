"""OpenRouter client with terminal-only API-key handling and usage capture."""

from __future__ import annotations

import getpass
import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any

import requests


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"
DEFAULT_TEXT_MODEL = DEFAULT_OPENROUTER_MODEL


def prompt_for_openrouter_api_key() -> str:
    """Read an API key from an interactive terminal and keep it in memory only."""
    existing = os.getenv("OPENROUTER_API_KEY", "").strip()
    if existing:
        return existing
    if not sys.stdin or not sys.stdin.isatty():
        raise RuntimeError(
            "OPENROUTER_API_KEY is unavailable and no interactive terminal was detected. "
            "Run the command from a terminal so the key can be entered securely."
        )
    api_key = getpass.getpass("OpenRouter API Key (input hidden): ").strip()
    if not api_key:
        raise RuntimeError("OpenRouter API Key cannot be empty.")
    os.environ["OPENROUTER_API_KEY"] = api_key
    return api_key


@dataclass
class OpenRouterResult:
    content: str
    model: str
    latency_seconds: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float | None
    raw: dict[str, Any]


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object, tolerating a fenced response."""
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("The model did not return a JSON object.")
        value = json.loads(candidate[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("The model response must be a JSON object.")
    return value


class OpenRouterClient:
    def __init__(self, api_key: str | None = None, timeout_seconds: int = 90):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.timeout_seconds = timeout_seconds

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float = 0.1,
        max_tokens: int = 900,
        response_format: dict[str, Any] | None = None,
        reasoning_effort: str | None = None,
    ) -> OpenRouterResult:
        if not self.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not available in this process. Start the webpage "
                "with start_app.ps1, or run the evaluation from an interactive terminal."
            )
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
            "usage": {"include": True},
        }
        if response_format:
            payload["response_format"] = response_format
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-OpenRouter-Title": "Honor of Kings Post-Match Review Assistant",
        }
        started = time.perf_counter()
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"OpenRouter request failed: {exc}") from exc
        latency = time.perf_counter() - started
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("OpenRouter returned no completion choice.")
        choice = choices[0]
        message = choice.get("message") or {}
        raw_content = message.get("content")
        if isinstance(raw_content, str):
            content = raw_content.strip()
        elif isinstance(raw_content, list):
            content = "".join(
                str(part.get("text") or "")
                for part in raw_content
                if isinstance(part, dict) and part.get("type") in {"text", "output_text"}
            ).strip()
        else:
            content = ""
        if not content:
            served_model = str(data.get("model") or model)
            finish_reason = choice.get("finish_reason") or choice.get("native_finish_reason") or "unknown"
            raise RuntimeError(
                "OpenRouter returned no text content "
                f"(served model: {served_model}; finish reason: {finish_reason}). "
                "Retry once; if it repeats, select another text model."
            )
        usage = data.get("usage") or {}
        cost = usage.get("cost")
        return OpenRouterResult(
            content=content,
            model=str(data.get("model") or model),
            latency_seconds=latency,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            total_tokens=int(usage.get("total_tokens") or 0),
            cost_usd=float(cost) if cost is not None else None,
            raw=data,
        )
