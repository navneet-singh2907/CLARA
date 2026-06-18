"""Test isolation for local developer environment variables."""

import pytest

from loan_pipeline.config import reset_settings_cache


@pytest.fixture(autouse=True)
def disable_live_external_calls(monkeypatch):
    """Keep tests offline even when the developer .env enables live demo mode."""
    monkeypatch.setenv("USE_LLM_AGENTS", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PRIMARY_JUDGE_MODEL", raising=False)
    monkeypatch.delenv("SECONDARY_JUDGE_MODEL", raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
    reset_settings_cache()
    yield
    reset_settings_cache()
