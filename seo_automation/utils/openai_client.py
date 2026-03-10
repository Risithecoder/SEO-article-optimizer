"""
utils/openai_client.py — Thin wrapper around the OpenAI API.

Provides helper functions for chat completions with automatic retry,
exponential backoff, and JSON response parsing.
"""

import json
import time
import logging
from typing import Any, Dict, Optional

from openai import OpenAI, APIError, RateLimitError, APIConnectionError

from ..config import config

logger = logging.getLogger(__name__)

# Initialise client once
_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    """Lazy-initialise the OpenAI client."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.openai_api_key)
    return _client


def chat_completion(
    system_prompt: str,
    user_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    retries: int = 3,
) -> str:
    """
    Send a chat completion request and return the assistant's reply.

    Retries up to `retries` times with exponential backoff on transient
    errors (rate-limit, connection, API errors).
    """
    client = _get_client()
    temp = temperature if temperature is not None else config.openai_temperature
    tokens = max_tokens if max_tokens is not None else config.openai_max_tokens

    for attempt in range(1, retries + 1):
        try:
            response = client.chat.completions.create(
                model=config.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temp,
                max_tokens=tokens,
            )
            return response.choices[0].message.content.strip()

        except (RateLimitError, APIConnectionError, APIError) as exc:
            wait = 2 ** attempt
            logger.warning(
                "OpenAI API error (attempt %d/%d): %s — retrying in %ds",
                attempt, retries, exc, wait,
            )
            if attempt == retries:
                raise
            time.sleep(wait)

    return ""  # unreachable but keeps type checkers happy


def chat_completion_json(
    system_prompt: str,
    user_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Send a chat completion request and parse the reply as JSON.

    The system prompt should instruct the model to return valid JSON.
    Falls back to an empty dict if parsing fails.
    """
    raw = chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # Strip markdown code fences if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first and last lines (```json and ```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON from OpenAI response:\n%s", raw[:500])
        return {}
