"""Test isolation for local developer environment variables."""

import pytest

from loan_pipeline.api.rate_limit import reset_rate_limits
from loan_pipeline.config import reset_settings_cache


@pytest.fixture(autouse=True)
def disable_live_external_calls(monkeypatch):
    """Keep tests offline even when the developer .env enables live demo mode."""
    monkeypatch.setenv("USE_LLM_AGENTS", "false")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("NEBIUS_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PRIMARY_JUDGE_MODEL", raising=False)
    monkeypatch.delenv("SECONDARY_JUDGE_MODEL", raising=False)
    monkeypatch.delenv("CLARA_DEMO_KEY", raising=False)
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "3600")
    monkeypatch.setenv("RATE_LIMIT_REVIEW_REQUESTS", "100")
    monkeypatch.setenv("RATE_LIMIT_EXPENSIVE_REQUESTS", "100")
    monkeypatch.setenv("RATE_LIMIT_UPLOAD_REQUESTS", "100")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    reset_rate_limits()
    reset_settings_cache()
    yield
    reset_rate_limits()
    reset_settings_cache()
