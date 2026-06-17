"""LangSmith observability tests."""

import os

from loan_pipeline.config import get_settings, reset_settings_cache
from loan_pipeline.observability import langsmith_tracing_enabled, trace_call


def test_langsmith_tracing_defaults_off() -> None:
    old_tracing = os.environ.pop("LANGSMITH_TRACING", None)
    old_legacy = os.environ.pop("LANGCHAIN_TRACING_V2", None)
    try:
        reset_settings_cache()
        assert not langsmith_tracing_enabled()
        assert not get_settings().langsmith_tracing
    finally:
        _restore_env("LANGSMITH_TRACING", old_tracing)
        _restore_env("LANGCHAIN_TRACING_V2", old_legacy)
        reset_settings_cache()


def test_trace_call_runs_function_when_tracing_disabled() -> None:
    old_tracing = os.environ.pop("LANGSMITH_TRACING", None)
    old_legacy = os.environ.pop("LANGCHAIN_TRACING_V2", None)
    try:
        result = trace_call(
            name="Unit Test Trace",
            run_type="chain",
            func=lambda value: value + 1,
            args=(2,),
        )
        assert result == 3
    finally:
        _restore_env("LANGSMITH_TRACING", old_tracing)
        _restore_env("LANGCHAIN_TRACING_V2", old_legacy)


def test_settings_reads_langsmith_project() -> None:
    old_tracing = os.environ.get("LANGSMITH_TRACING")
    old_project = os.environ.get("LANGSMITH_PROJECT")
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = "loan-review-test"
    try:
        reset_settings_cache()
        settings = get_settings()
        assert settings.langsmith_tracing
        assert settings.langsmith_project == "loan-review-test"
    finally:
        _restore_env("LANGSMITH_TRACING", old_tracing)
        _restore_env("LANGSMITH_PROJECT", old_project)
        reset_settings_cache()


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
