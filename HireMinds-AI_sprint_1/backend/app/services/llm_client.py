"""
Shared LLM client primitives for Phase 8 assessment generation.

The assessment service only needs one operation: send a prompt and receive
parsed JSON. Gemini and DeepSeek are implemented as interchangeable providers
behind that small interface.

Security:
* API keys are read from settings and are never logged.
* Model output is parsed as data only; it is never executed.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.core.config import settings

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class LLMError(Exception):
    """Base class for LLM integration failures."""


class LLMConfigurationError(LLMError):
    """Raised when the selected provider or its API key is not configured."""


class LLMTimeoutError(LLMError):
    """Raised when an LLM request exceeds the configured timeout."""


class LLMAPIError(LLMError):
    """Raised when an LLM provider returns a non-success HTTP response."""


class LLMResponseError(LLMError):
    """Raised when an LLM returns no usable JSON."""


def extract_json(text: str, provider: str = "LLM") -> Any:
    """
    Extract a JSON value from an LLM response.

    Handles plain JSON, fenced ```json blocks, and prose surrounding a JSON
    object/array. Raises ``LLMResponseError`` if no valid JSON is found.
    """
    if not text or not text.strip():
        raise LLMResponseError(f"{provider} returned an empty response.")

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = _FENCE_RE.sub("", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Find the first JSON object/array and attempt to decode from there.
    starts = [index for index in (cleaned.find("{"), cleaned.find("[")) if index >= 0]
    if not starts:
        raise LLMResponseError(f"{provider} response did not contain JSON.")

    start = min(starts)
    decoder = json.JSONDecoder()
    try:
        value, _ = decoder.raw_decode(cleaned[start:])
        return value
    except json.JSONDecodeError as exc:
        raise LLMResponseError(
            f"{provider} returned invalid JSON: {exc.msg}"
        ) from exc


class BaseLLMClient:
    """Minimal interface implemented by every assessment LLM provider."""

    model: str

    def generate_json(self, prompt: str) -> Any:  # pragma: no cover - interface
        raise NotImplementedError


def get_llm_client(
    provider: Optional[str] = None,
    **kwargs: Any,
) -> BaseLLMClient:
    """
    Build the configured LLM client.

    ``LLM_PROVIDER`` selects the provider. Supported values are ``gemini``
    (default) and ``deepseek``. Provider-specific keyword arguments are passed
    through to the client constructor.
    """
    selected = (provider or settings.LLM_PROVIDER or "gemini").strip().lower()

    if selected == "gemini":
        from app.services.gemini_client import GeminiClient

        return GeminiClient(**kwargs)

    if selected == "deepseek":
        from app.services.deepseek_client import DeepSeekClient

        return DeepSeekClient(**kwargs)

    raise LLMConfigurationError(
        f"Unsupported LLM_PROVIDER='{selected}'. "
        "Supported providers are 'gemini' and 'deepseek'."
    )
