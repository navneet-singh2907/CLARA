"""Optional LangChain LLM mode tests."""

import os

from loan_pipeline.agents.credit_risk_scorer import run_credit_risk_scorer
from loan_pipeline.agents.term_extractor import extract_terms
from loan_pipeline.config import get_settings, load_sba_demo_cases, reset_settings_cache


def test_llm_mode_defaults_off() -> None:
    old_value = os.environ.pop("USE_LLM_AGENTS", None)
    try:
        reset_settings_cache()
        assert not get_settings().use_llm_agents
    finally:
        if old_value is not None:
            os.environ["USE_LLM_AGENTS"] = old_value
        reset_settings_cache()


def test_deterministic_agents_run_without_api_key_when_llm_mode_off() -> None:
    old_flag = os.environ.get("USE_LLM_AGENTS")
    old_key = os.environ.pop("OPENAI_API_KEY", None)
    os.environ["USE_LLM_AGENTS"] = "false"

    try:
        reset_settings_cache()
        loan_case = load_sba_demo_cases()[0]
        terms = extract_terms(loan_case)
        risk = run_credit_risk_scorer(terms)

        assert terms.case_id == loan_case.case_id
        assert risk.band == "LOW"
    finally:
        _restore_env("USE_LLM_AGENTS", old_flag)
        _restore_env("OPENAI_API_KEY", old_key)
        reset_settings_cache()


def test_llm_mode_requires_api_key() -> None:
    old_flag = os.environ.get("USE_LLM_AGENTS")
    old_key = os.environ.pop("OPENAI_API_KEY", None)
    os.environ["USE_LLM_AGENTS"] = "true"

    try:
        reset_settings_cache()
        loan_case = load_sba_demo_cases()[0]
        try:
            extract_terms(loan_case)
        except RuntimeError as exc:
            assert "OPENAI_API_KEY" in str(exc)
            return
        raise AssertionError("LLM mode should require OPENAI_API_KEY.")
    finally:
        _restore_env("USE_LLM_AGENTS", old_flag)
        _restore_env("OPENAI_API_KEY", old_key)
        reset_settings_cache()


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value

