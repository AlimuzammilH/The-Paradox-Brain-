"""Thin client for any OpenAI-compatible chat endpoint. Paradox never depends on one vendor."""
from __future__ import annotations

import json
import time
from typing import Any

import httpx

from . import config


class LLMError(RuntimeError):
    pass


def parse_json(text: str) -> Any:
    """Pull the first JSON object out of a model reply, tolerating code fences and chatter around it."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise LLMError(f"no JSON object in reply: {text[:200]!r}")
    return json.loads(text[start:end + 1])


class LLM:
    def __init__(self, url: str = config.LLM_URL, model: str = config.LLM_MODEL, key: str = config.LLM_KEY,
                 temperature: float = 0.5, timeout: float = 300):
        self.url, self.model, self.key = url.rstrip("/"), model, key
        self.temperature, self.timeout = temperature, timeout
        self.calls = 0
        self.seconds = 0.0

    def chat(self, messages: list[dict], json_mode: bool = False, temperature: float | None = None,
             max_tokens: int | None = None) -> str:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        if max_tokens:
            body["max_tokens"] = max_tokens
        t0 = time.time()
        try:
            r = httpx.post(f"{self.url}/chat/completions", json=body, timeout=self.timeout,
                           headers={"Authorization": f"Bearer {self.key}"})
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMError(f"language model unreachable at {self.url} ({e}). Is Ollama running?") from e
        finally:
            self.calls += 1
            self.seconds += time.time() - t0
        return r.json()["choices"][0]["message"]["content"].strip()

    def ask(self, system: str, user: str, temperature: float | None = None) -> str:
        return self.chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                         temperature=temperature)

    def ask_json(self, system: str, user: str, keys: list[str] | None = None,
                 temperature: float | None = None, retries: int = 2) -> dict:
        """Ask for a JSON object; retry when the reply is malformed or misses required keys."""
        last: Exception | None = None
        for attempt in range(retries + 1):
            try:
                text = self.chat([{"role": "system", "content": system + " Answer with JSON only."},
                                  {"role": "user", "content": user}], json_mode=True, temperature=temperature)
                data = parse_json(text)
                missing = [k for k in keys or [] if k not in data]
                if missing:
                    raise LLMError(f"missing keys {missing}")
                return data
            except (LLMError, json.JSONDecodeError) as e:
                if isinstance(e, LLMError) and "unreachable" in str(e):
                    raise
                last = e
        raise LLMError(f"model gave no usable JSON after {retries + 1} tries: {last}")
