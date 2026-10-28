"""
Gemini client built on the official ``google-genai`` Python SDK.

The assessment and interview services only need one operation: send a prompt
and receive parsed JSON. This module keeps that small interface while using the
official SDK for transport, retries and error handling.

Security:
* The API key is read from ``GEMINI_API_KEY`` and is never logged.
* The client only returns parsed JSON; it does not execute model output.

Reliability:
* The configured model is verified with ``models.get`` before the first
  generation request (and the result is cached per client instance).
* SDK/HTTP failures are mapped to the shared LLM exception types so the API
  layer can return consistent status codes.
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Set

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

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

_RATE_LIMIT_CODES = {429}
_RATE_LIMIT_STATUSES = {"RESOURCE_EXHAUSTED"}
_AUTH_CODES = {401, 403}
_AUTH_STATUSES = {"UNAUTHENTICATED", "PERMISSION_DENIED"}
_TIMEOUT_CODES = {408, 504}
_TIMEOUT_STATUSES = {"DEADLINE_EXCEEDED", "TIMEOUT"}
_BLOCKED_FINISH_REASONS = {"SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT", "RECITATION"}


def _normalise_base_url(base_url: Optional[str]) -> Optional[str]:
    """
    Convert a REST-style base URL into the value expected by the SDK.

    Older deployments may still set
    ``GEMINI_API_BASE_URL=https://generativelanguage.googleapis.com/v1beta``.
    The SDK appends its own API version, so the trailing version segment is
    removed.
    """
    if not base_url:
        return None
    cleaned = base_url.strip().rstrip("/")
    for suffix in ("/v1beta", "/v1alpha", "/v1"):
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)]
            break
    return cleaned or None


class GeminiClient(BaseLLMClient):
    """Synchronous Gemini client backed by the official ``google-genai`` SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        client: Optional[Any] = None,
        validate_model: bool = True,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.timeout = timeout if timeout is not None else settings.GEMINI_TIMEOUT_SECONDS
        self.max_output_tokens = (
            max_output_tokens
            if max_output_tokens is not None
            else settings.GEMINI_MAX_OUTPUT_TOKENS
        )
        self.temperature = (
            temperature if temperature is not None else settings.GEMINI_TEMPERATURE
        )
        self.base_url = _normalise_base_url(
            base_url if base_url is not None else settings.GEMINI_API_BASE_URL
        )
        self.validate_model = validate_model

        # ``client`` allows callers/tests to inject an already-built SDK client.
        self._client = client
        self._validated_models: Set[str] = set()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    # ------------------------------------------------------------------ #
    # SDK client / model verification                                     #
    # ------------------------------------------------------------------ #
    def _get_client(self) -> Any:
        """Build (once) and return the official SDK client."""
        if self._client is None:
            http_options = genai_types.HttpOptions(
                timeout=int(self.timeout * 1000),
                base_url=self.base_url,
            )
            self._client = genai.Client(
                api_key=self.api_key,
                http_options=http_options,
            )
        return self._client

    def verify_model(self) -> None:
        """
        Confirm that ``GEMINI_MODEL`` is available to the configured API key.

        Raises:
            LLMConfigurationError: missing key or unsupported model.
            LLMTimeoutError: the model lookup timed out.
            LLMAPIError: the model lookup failed for another reason.
        """
        if not self.is_configured:
            raise LLMConfigurationError(
                "GEMINI_API_KEY is not configured. Set it in the backend environment "
                "to enable Gemini generation, or set LLM_PROVIDER=deepseek and "
                "configure DEEPSEEK_API_KEY."
            )

        if not self.validate_model or self.model in self._validated_models:
            return

        client = self._get_client()
        try:
            client.models.get(model=self.model)
        except genai_errors.APIError as exc:
            raise self._map_api_error(exc) from exc
        except (httpx.TimeoutException, TimeoutError) as exc:
            logger.warning("Gemini model lookup timed out after %.1fs", self.timeout)
            raise LLMTimeoutError(
                f"Gemini model lookup timed out after {self.timeout:.0f} seconds."
            ) from exc
        except httpx.RequestError as exc:
            logger.warning(
                "Gemini model lookup transport failure: %s", type(exc).__name__
            )
            raise LLMAPIError("Could not reach the Gemini API.") from exc

        self._validated_models.add(self.model)

    @staticmethod
    def _is_not_found(exc: genai_errors.APIError) -> bool:
        code = getattr(exc, "code", None)
        status = (getattr(exc, "status", None) or "").upper()
        message = (getattr(exc, "message", None) or "").lower()
        return (
            code == 404
            or status == "NOT_FOUND"
            or "not found" in message
            or "not supported" in message
        )

    def _map_api_error(self, exc: genai_errors.APIError) -> LLMError:
        """Map an SDK API error to the shared LLM exception hierarchy."""
        code = getattr(exc, "code", None)
        status = (getattr(exc, "status", None) or "").upper()
        # Never include the API key or full response body in logs/messages.
        logger.warning(
            "Gemini API error code=%s status=%s", code, status or "unknown"
        )

        if self._is_not_found(exc):
            return LLMConfigurationError(
                f"Gemini model {self.model!r} is not available for "
                "generateContent. Update GEMINI_MODEL to a supported model "
                "(for example 'gemini-flash-lite-latest' or "
                "'gemini-flash-latest')."
            )
        if code in _RATE_LIMIT_CODES or status in _RATE_LIMIT_STATUSES:
            return LLMAPIError(
                "Gemini API rate limit exceeded. Retry later or check the project "
                "quota and billing settings."
            )
        if code in _TIMEOUT_CODES or status in _TIMEOUT_STATUSES:
            return LLMTimeoutError(
                "Gemini API timed out before completing the request. Retry, or "
                "increase GEMINI_TIMEOUT_SECONDS for large prompts."
            )
        if code in _AUTH_CODES or status in _AUTH_STATUSES:
            return LLMConfigurationError(
                "Gemini API rejected the credentials. Check GEMINI_API_KEY and "
                "that the Generative Language API is enabled for the project."
            )
        label = code or status or "unknown"
        return LLMAPIError(
            f"Gemini API returned an error ({label}). Check the API key, quota "
            "and model configuration."
        )

    # ------------------------------------------------------------------ #
    # Generation                                                          #
    # ------------------------------------------------------------------ #
    def generate_json(self, prompt: str) -> Any:
        """
        Send a prompt to Gemini and return the parsed JSON response.

        Raises:
            LLMConfigurationError: missing API key or unsupported model.
            LLMTimeoutError: request timed out.
            LLMAPIError: API/rate-limit/transport failure.
            LLMResponseError: response contained no valid JSON.
        """
        self.verify_model()
        client = self._get_client()

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_output_tokens,
                    response_mime_type="application/json",
                ),
            )
        except genai_errors.APIError as exc:
            raise self._map_api_error(exc) from exc
        except (httpx.TimeoutException, TimeoutError) as exc:
            logger.warning("Gemini request timed out after %.1fs", self.timeout)
            raise LLMTimeoutError(
                f"Gemini request timed out after {self.timeout:.0f} seconds."
            ) from exc
        except httpx.RequestError as exc:
            logger.warning("Gemini transport failure: %s", type(exc).__name__)
            raise LLMAPIError("Could not reach the Gemini API.") from exc

        text = self._extract_text(response)
        return extract_json(text, provider="Gemini")

    @staticmethod
    def _extract_text(response: Any) -> str:
        """Extract candidate text and reject blocked or empty responses."""
        feedback = getattr(response, "prompt_feedback", None)
        block_reason = getattr(feedback, "block_reason", None)
        if block_reason:
            raise LLMResponseError(f"Gemini blocked the prompt: {block_reason}")

        try:
            text = response.text
        except Exception:  # SDK raises when no text part exists
            text = None

        if not text:
            candidates = getattr(response, "candidates", None) or []
            first = candidates[0] if candidates else None
            finish_reason = getattr(first, "finish_reason", None)
            if finish_reason and str(finish_reason).upper() in _BLOCKED_FINISH_REASONS:
                raise LLMResponseError(
                    f"Gemini stopped generating content: {finish_reason}"
                )
            content = getattr(first, "content", None)
            parts = getattr(content, "parts", None) or []
            text = "".join(
                part.text for part in parts if getattr(part, "text", None)
            )

        if not text or not str(text).strip():
            raise LLMResponseError("Gemini returned an empty candidate response.")

        return str(text)
