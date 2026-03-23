"""Thin abstraction over the Anthropic API for structured LLM calls."""

from __future__ import annotations

import json
import os
import threading
import time
from typing import TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5-20251001"

T = TypeVar("T", bound=BaseModel)

_client: anthropic.Anthropic | None = None

# Simple rate limiter: max N requests per minute, thread-safe
_rate_lock = threading.Lock()
_request_times: list[float] = []
_MAX_RPM = 40  # stay under the 50/min limit with headroom


def _wait_for_rate_limit():
    """Block until we're under the rate limit."""
    with _rate_lock:
        now = time.time()
        # Prune timestamps older than 60s
        _request_times[:] = [t for t in _request_times if now - t < 60]
        if len(_request_times) >= _MAX_RPM:
            # Wait until the oldest request falls outside the window
            sleep_time = 60 - (now - _request_times[0]) + 0.1
            if sleep_time > 0:
                time.sleep(sleep_time)
        _request_times.append(time.time())


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key or api_key == "your-api-key-here":
            try:
                import streamlit as st
                api_key = st.secrets.get("ANTHROPIC_API_KEY")
            except Exception:
                pass
        if not api_key or api_key == "your-api-key-here":
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file or Streamlit secrets."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def call(
    system_prompt: str,
    user_message: str,
    model: str,
    output_schema: type[T],
    max_tokens: int = 4096,
) -> T:
    """Call the Anthropic API and parse the response into a Pydantic model.

    If parsing fails, retries once with the validation error as feedback.
    """
    schema_json = json.dumps(
        output_schema.model_json_schema(), indent=2
    )
    full_system = (
        f"{system_prompt}\n\n"
        f"You MUST respond with valid JSON matching this schema:\n"
        f"```json\n{schema_json}\n```\n"
        f"Return ONLY the JSON object, no markdown fences or extra text."
    )
    client = _get_client()

    def _attempt(msg: str) -> T:
        for attempt in range(4):  # up to 3 retries
            try:
                _wait_for_rate_limit()
                response = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=full_system,
                    messages=[{"role": "user", "content": msg}],
                )
                raw = response.content[0].text.strip()
                if raw.startswith("```"):
                    lines = raw.split("\n")
                    lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    raw = "\n".join(lines)
                return output_schema.model_validate_json(raw)
            except anthropic.APIStatusError as e:
                if e.status_code in (429, 529) and attempt < 3:
                    wait = (2 ** attempt) * 2  # 2s, 4s, 8s
                    import time
                    time.sleep(wait)
                    continue
                raise

    try:
        return _attempt(user_message)
    except (ValidationError, json.JSONDecodeError) as first_err:
        retry_msg = (
            f"{user_message}\n\n"
            f"Your previous response failed validation:\n{first_err}\n"
            f"Please fix the JSON and try again."
        )
        try:
            return _attempt(retry_msg)
        except (ValidationError, json.JSONDecodeError) as second_err:
            raise RuntimeError(
                f"LLM output failed validation after retry.\n"
                f"Error: {second_err}"
            ) from second_err


def call_streaming(
    system_prompt: str,
    user_message: str,
    model: str,
    max_tokens: int = 4096,
):
    """Stream a plain-text response from the Anthropic API. Yields text chunks."""
    client = _get_client()
    _wait_for_rate_limit()
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            yield text
