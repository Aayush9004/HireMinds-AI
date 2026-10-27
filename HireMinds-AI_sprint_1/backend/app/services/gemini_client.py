"""
Minimal Gemini REST client for Phase 8 assessment generation.

Why REST instead of an SDK?
---------------------------
The backend already depends on ``httpx``. A small, typed REST client avoids
adding another vendor SDK and makes timeouts, HTTP failures and malformed
responses explicit and testable.

Security:
* The API key is read from ``GEMINI_API_KEY`` and is never logged.
* The client only returns parsed JSON; it does not execute model output.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.services.llm_client import (
    BaseLLMClient,
    LLMAPIError,
    LLMConfigurationError,
    LLMError,
    LLMResponseError,
    LLMTimeoutError,
    extract_json,
)

logger = logging.getLogger(__name__)

# Backwards-compatible names. Phase 8 originally exposed Gemini-specific
# exception classes; they are aliases of the shared LLM exceptions so callers
# can catch either the provider-specific or the generic type.
GeminiError = LLMError
GeminiConfigurationError = LLMConfigurationError
GeminiTimeoutError = LLMTimeoutError
GeminiAPIError = LLMAPIError
GeminiResponseError = LLMResponseError


class GeminiClient(BaseLLMClient):
    """Small synchronous client for Gemini's generateContent endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.base_url = (base_url or settings.GEMINI_API_BASE_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.GEMINI_TIMEOUT_SECONDS
        self.max_output_tokens = (
            max_output_tokens
            if max_output_tokens is not None
            else settings.GEMINI_MAX_OUTPUT_TOKENS
        )
        self.temperature = (
            temperature if temperature is not None else settings.GEMINI_TEMPERATURE
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def generate_json(self, prompt: str) -> Any:
        """
        Send a prompt to Gemini and return the parsed JSON response.

        Raises:
            LLMConfigurationError: missing API key.
            LLMTimeoutError: request timed out.
            LLMAPIError: non-2xx HTTP response or transport failure.
            LLMResponseError: response contained no valid JSON.
        """
        if not self.is_configured:
            raise LLMConfigurationError(
                "GEMINI_API_KEY is not configured. Set it in the backend environment "
                "to enable assessment generation, or set LLM_PROVIDER=deepseek and "
                "configure DEEPSEEK_API_KEY."
            )

        url = f"{self.base_url}/models/{self.model}:generateContent"
        payload: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_output_tokens,
                "responseMimeType": "application/json",
            },
        }

        try:
            response = httpx.post(
                url,
                params={"key": self.api_key},
                json=payload,
                timeout=self.timeout,
            )
        except httpx.TimeoutException as exc:
            logger.warning("Gemini request timed out after %.1fs", self.timeout)
            raise LLMTimeoutError(
                f"Gemini request timed out after {self.timeout:.0f} seconds."
            ) from exc
        except httpx.RequestError as exc:
            logger.warning("Gemini transport failure: %s", type(exc).__name__)
            raise LLMAPIError("Could not reach the Gemini API.") from exc

        if response.status_code >= 400:
            # Do not include the API key or full response body in logs.
            logger.warning("Gemini returned HTTP %s", response.status_code)
            raise LLMAPIError(
                f"Gemini API returned HTTP {response.status_code}. "
                "Check the API key, quota and model configuration."
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMResponseError("Gemini returned a non-JSON HTTP response.") from exc

        if isinstance(data, dict) and (data.get("promptFeedback") or {}).get("blockReason"):
            reason = data["promptFeedback"]["blockReason"]
            raise LLMResponseError(f"Gemini blocked the prompt: {reason}")

        candidates = data.get("candidates") if isinstance(data, dict) else None
        if not isinstance(candidates, list) or not candidates:
            raise LLMResponseError("Gemini returned no candidates.")

        first_candidate = candidates[0] if isinstance(candidates[0], dict) else {}
        content = first_candidate.get("content") or {}
        parts = content.get("parts") or []
        text = "".join(
            part.get("text", "")
            for part in parts
            if isinstance(part, dict)
        )
        if not text.strip():
            raise LLMResponseError("Gemini returned an empty candidate response.")

        return extract_json(text, provider="Gemini")
