"""
Optional live Gemini API tests.

These tests make real network calls and are therefore skipped by default.
Enable them explicitly after configuring ``GEMINI_API_KEY``:

    RUN_LIVE_LLM_TESTS=1 PYTHONPATH=. ./venv/bin/pytest tests/test_gemini_live.py -q

The API key is read from the environment by ``GeminiClient`` and is never
printed by these tests.
"""
from __future__ import annotations

import os

import pytest

from app.core.config import settings
from app.services.gemini_client import GeminiClient


def _live_tests_enabled() -> bool:
    flag = os.getenv("RUN_LIVE_LLM_TESTS", "").strip().lower()
    return flag in {"1", "true", "yes", "on"} and bool(
        (settings.GEMINI_API_KEY or "").strip()
    )


pytestmark = pytest.mark.skipif(
    not _live_tests_enabled(),
    reason=(
        "Live Gemini tests are opt-in: set RUN_LIVE_LLM_TESTS=1 and configure "
        "GEMINI_API_KEY."
    ),
)


def test_live_configured_model_is_supported():
    """The model named by GEMINI_MODEL must exist for the configured key."""
    GeminiClient().verify_model()


def test_live_generation_returns_json():
    """A real generation request returns parsed JSON."""
    result = GeminiClient().generate_json(
        'Return ONLY this JSON object and nothing else: {"status": "ok"}'
    )
    assert isinstance(result, dict)
    assert result.get("status") == "ok"
