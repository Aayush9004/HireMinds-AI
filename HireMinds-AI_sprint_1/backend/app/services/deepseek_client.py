"""
DeepSeek REST client for Phase 8 assessment generation.

DeepSeek exposes an OpenAI-compatible chat-completions API, so this client is
small and dependency-free: it uses the existing ``httpx`` package.

Security:
* The API key is read from ``DEEPSEEK_API_KEY`` and is never logged.
* The client only returns parsed JSON; it does not execute model output.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.llm_client import (
    BaseLLMClient,
    LLMAPIError,
    LLMConfigurationError,
    LLMResponseError,
    LLMTimeoutError,
    extract_json,
)

logger = logging.getLogger(__name__)


class DeepSeekClient(BaseLLMClient):
    """Synchronous client for DeepSeek's OpenAI-compatible chat API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.DEEPSEEK_API_KEY
        self.model = model or settings.DEEPSEEK_MODEL
        self.base_url = (base_url or settings.DEEPSEEK_API_BASE_URL).rstrip("/")
        self.timeout = (
            timeout if timeout is not None else settings.DEEPSEEK_TIMEOUT_SECONDS
        )
        self.max_output_tokens = (
            max_output_tokens
            if max_output_tokens is not None
            else settings.DEEPSEEK_MAX_OUTPUT_TOKENS
        )
        self.temperature = (
            temperature if temperature is not None else settings.DEEPSEEK_TEMPERATURE
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _build_messages(self, prompt: str) -> List[Dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "You generate technical assessment questions. "
                    "Return only valid JSON and no commentary."
                ),
            },
            {"role": "user", "content": prompt},
        ]

    def generate_json(self, prompt: str) -> Any:
        """
        Send a prompt to DeepSeek and return the parsed JSON response.

        Raises:
            LLMConfigurationError: missing API key.
            LLMTimeoutError: request timed out.
            LLMAPIError: non-2xx HTTP response or transport failure.
            LLMResponseError: response contained no valid JSON.
        """
        if not self.is_configured:
            raise LLMConfigurationError(
                "DEEPSEEK_API_KEY is not configured. Set it in the backend "
                "environment to enable DeepSeek assessment generation."
            )

        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": self._build_messages(prompt),
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
            "response_format": {"type": "json_object"},
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = httpx.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
        except httpx.TimeoutException as exc:
            logger.warning("DeepSeek request timed out after %.1fs", self.timeout)
            raise LLMTimeoutError(
                f"DeepSeek request timed out after {self.timeout:.0f} seconds."
            ) from exc
        except httpx.RequestError as exc:
            logger.warning("DeepSeek transport failure: %s", type(exc).__name__)
            raise LLMAPIError("Could not reach the DeepSeek API.") from exc

        if response.status_code >= 400:
            # Do not include the API key or full response body in logs.
            logger.warning("DeepSeek returned HTTP %s", response.status_code)
            raise LLMAPIError(
                f"DeepSeek API returned HTTP {response.status_code}. "
                "Check the API key, quota and model configuration."
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMResponseError(
                "DeepSeek returned a non-JSON HTTP response."
            ) from exc

        if isinstance(data, dict) and data.get("error"):
            error = data["error"]
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise LLMAPIError(f"DeepSeek API error: {message}")

        choices = data.get("choices") if isinstance(data, dict) else None
        if not isinstance(choices, list) or not choices:
            raise LLMResponseError("DeepSeek returned no choices.")

        first_choice = choices[0] if isinstance(choices[0], dict) else {}
        message = first_choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            text = "".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict)
            )
        else:
            text = content or ""
        if not text.strip():
            raise LLMResponseError("DeepSeek returned an empty response.")

        return extract_json(text, provider="DeepSeek")
