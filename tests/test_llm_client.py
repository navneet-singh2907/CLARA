"""LLM client robustness tests."""

import sys
from types import ModuleType
from typing import Any

import pytest

from loan_pipeline.config import Settings
from loan_pipeline.llm.client import (
    LLM_TIMEOUT_SECONDS,
    LLMResponseError,
    _coerce_confidence,
    _invoke_json_prompt,
    _parse_json_content,
)


def test_coerce_confidence_accepts_numeric_and_labels() -> None:
    assert _coerce_confidence(0.87, default=0.8) == 0.87
    assert _coerce_confidence("medium", default=0.8) == 0.75
    assert _coerce_confidence("high", default=0.8) == 0.9
    assert _coerce_confidence("92", default=0.8) == 0.92
    assert _coerce_confidence("not sure", default=0.8) == 0.8


def test_invalid_json_error_includes_agent_context() -> None:
    with pytest.raises(LLMResponseError) as exc_info:
        _parse_json_content(
            "Sure, here is the answer instead of JSON.",
            agent_name="credit_risk_scorer",
            case_id="ADV2-003",
            operation="add_risk_rationale",
            provider="nebius",
            model="Qwen/Qwen3-235B-A22B-Instruct-2507",
            temperature=0.2,
        )

    error = exc_info.value
    assert error.agent_name == "credit_risk_scorer"
    assert error.case_id == "ADV2-003"
    assert error.operation == "add_risk_rationale"
    assert error.provider == "nebius"
    assert error.model == "Qwen/Qwen3-235B-A22B-Instruct-2507"
    assert "Response is not valid JSON" in str(error)
    assert error.response_preview == "Sure, here is the answer instead of JSON."


def test_non_object_json_error_includes_agent_context() -> None:
    with pytest.raises(LLMResponseError) as exc_info:
        _parse_json_content(
            '["not", "an", "object"]',
            agent_name="term_extractor",
            case_id="CLEAN-001",
            operation="extract_terms",
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.0,
        )

    assert exc_info.value.agent_name == "term_extractor"
    assert exc_info.value.case_id == "CLEAN-001"
    assert "Response JSON must be an object" in str(exc_info.value)


def test_llm_invocation_error_includes_context_and_timeout(monkeypatch) -> None:
    captured_kwargs: dict[str, Any] = {}

    class FailingChatOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            captured_kwargs.update(kwargs)

        def invoke(self, prompt: str) -> object:
            raise TimeoutError(f"Timed out while handling {prompt}")

    fake_module = ModuleType("langchain_openai")
    fake_module.ChatOpenAI = FailingChatOpenAI
    monkeypatch.setitem(sys.modules, "langchain_openai", fake_module)

    with pytest.raises(LLMResponseError) as exc_info:
        _invoke_json_prompt(
            settings=_test_settings(),
            prompt="score this case",
            agent_name="compliance_checker",
            case_id="AMB-003",
            operation="add_compliance_note",
        )

    assert captured_kwargs["timeout"] == LLM_TIMEOUT_SECONDS
    assert exc_info.value.agent_name == "compliance_checker"
    assert exc_info.value.case_id == "AMB-003"
    assert exc_info.value.provider == "nebius"
    assert exc_info.value.model == "Qwen/Qwen3-235B-A22B-Instruct-2507"
    assert "LLM call failed" in str(exc_info.value)


def _test_settings() -> Settings:
    return Settings(
        app_env="test",
        use_llm_agents=True,
        openai_api_key=None,
        openai_model="Qwen/Qwen3-235B-A22B-Instruct-2507",
        llm_api_key="test-key",
        llm_base_url="https://api.tokenfactory.nebius.com/v1/",
        llm_provider="nebius",
        llm_temperature=0.2,
        primary_judge_model=None,
        secondary_judge_model=None,
        judge_temperature=0.2,
        langsmith_tracing=False,
        langsmith_project="test",
        demo_api_key=None,
        rate_limit_window_seconds=3600,
        rate_limit_review_requests=100,
        rate_limit_expensive_requests=100,
        rate_limit_upload_requests=100,
    )
