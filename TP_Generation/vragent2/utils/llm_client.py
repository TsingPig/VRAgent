"""
LLM Client — Unified interface for calling OpenAI-compatible LLM APIs.

Extracted and refactored from GenerateTestPlanModified._call_llm_api().
Supports:
    - Single-turn and multi-turn conversations
    - Configurable model, temperature, retries
    - Response parsing (JSON extraction, think-tag stripping)
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional

import httpx
import openai

# Regex to strip <think>...</think> blocks (some reasoning models emit these)
_THINK_RE = re.compile(r"<\s*think\s*>.*?<\s*/\s*think\s*>", re.IGNORECASE | re.DOTALL)

# Local proxy for API access
_PROXY_URL = "http://127.0.0.1:15236"


class LLMClient:
    """Thin wrapper around the OpenAI chat-completions API."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        default_model: str = "gpt-4o",
        default_temperature: float = 0.0,
        max_retries: int = 5,
        retry_delay: float = 30.0,
        proxy_url: str = _PROXY_URL,
    ):
        self.default_model = default_model
        self.default_temperature = default_temperature
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Token usage accumulator: {caller: {prompt_tokens, completion_tokens, total_tokens, calls}}
        self._token_usage: Dict[str, Dict[str, int]] = {}

        http_client = httpx.Client(proxy=proxy_url) if proxy_url else None
        self._client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=http_client,
        )

    # ------------------------------------------------------------------
    # Core API call
    # ------------------------------------------------------------------

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_retries: Optional[int] = None,
        caller: Optional[str] = None,
    ) -> Optional[str]:
        """
        Send *messages* to the LLM and return the assistant reply as a string.

        *caller* is an optional tag (e.g. ``"planner"``, ``"verifier"``) used
        to attribute token usage.  Returns ``None`` on total failure after retries.
        """
        model = model or self.default_model
        temperature = temperature if temperature is not None else self.default_temperature
        retries = max_retries if max_retries is not None else self.max_retries

        for attempt in range(1, retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                )
                # Accumulate token usage
                self._accumulate_usage(response, caller or model)

                if response.choices:
                    return response.choices[0].message.content
                print("[LLM] Empty response from API")
                return None
            except Exception as exc:
                print(f"[LLM] Attempt {attempt}/{retries} failed: {exc}")
                if attempt < retries:
                    time.sleep(self.retry_delay)
        print("[LLM] All retries exhausted")
        return None

    # ------------------------------------------------------------------
    # Token usage tracking
    # ------------------------------------------------------------------

    def _accumulate_usage(self, response: Any, caller: str) -> None:
        """Extract token counts from the API response and accumulate."""
        usage = getattr(response, "usage", None)
        if not usage:
            return
        bucket = self._token_usage.setdefault(caller, {
            "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0,
        })
        bucket["prompt_tokens"] += getattr(usage, "prompt_tokens", 0) or 0
        bucket["completion_tokens"] += getattr(usage, "completion_tokens", 0) or 0
        bucket["total_tokens"] += getattr(usage, "total_tokens", 0) or 0
        bucket["calls"] += 1

    def get_token_usage(self) -> Dict[str, Dict[str, int]]:
        """Return accumulated token usage by caller, plus an ``_total`` key."""
        totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "calls": 0}
        for v in self._token_usage.values():
            for k in totals:
                totals[k] += v[k]
        result = dict(self._token_usage)
        result["_total"] = totals
        return result

    def reset_token_usage(self) -> None:
        """Clear accumulated stats (e.g. between iterations)."""
        self._token_usage.clear()

    # ------------------------------------------------------------------
    # Convenience: single-turn
    # ------------------------------------------------------------------

    def ask(self, prompt: str, **kwargs) -> Optional[str]:
        """Single-turn user→assistant call."""
        return self.chat([{"role": "user", "content": prompt}], **kwargs)


    # ------------------------------------------------------------------
    # Convenience: multi-turn with context management
    # ------------------------------------------------------------------

    def ask_with_context(
        self,
        prompt: str,
        context: List[Dict[str, str]],
        **kwargs,
    ) -> Optional[str]:
        """Append *prompt* to *context*, call LLM, and return the reply.

        *context* is **mutated** in-place (user + assistant messages appended).
        """
        context.append({"role": "user", "content": prompt})
        reply = self.chat(context, **kwargs)
        if reply:
            context.append({"role": "assistant", "content": reply})
        return reply

    # ------------------------------------------------------------------
    # Response parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def strip_think_tags(text: str) -> str:
        """Remove ``<think>…</think>`` blocks."""
        return _THINK_RE.sub("", text).strip()

    @staticmethod
    def extract_json(text: str) -> Optional[Dict[str, Any]]:
        """Try to pull a JSON object out of a fenced code block or raw text."""
        text = LLMClient.strip_think_tags(text)

        # Try ```json ... ``` first
        m = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # Fallback: find first { … }
        start = text.find("{")
        if start != -1:
            brace = 0
            for i, ch in enumerate(text[start:], start):
                if ch == "{":
                    brace += 1
                elif ch == "}":
                    brace -= 1
                    if brace == 0:
                        try:
                            return json.loads(text[start : i + 1])
                        except json.JSONDecodeError:
                            break
        return None

    @staticmethod
    def extract_test_plan(text: str) -> Optional[Dict[str, Any]]:
        """Extract a test-plan JSON (must contain ``taskUnits``) from LLM output."""
        parsed = LLMClient.extract_json(text)
        if parsed and "taskUnits" in parsed:
            return parsed
        # Last resort: check raw text
        if text and "taskUnits" in text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        return None
