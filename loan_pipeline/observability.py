"""Optional LangSmith tracing helpers."""

import os
from collections.abc import Callable
from typing import Any, TypeVar

from langsmith import traceable

T = TypeVar("T")


def langsmith_tracing_enabled() -> bool:
    return _env_bool("LANGSMITH_TRACING") or _env_bool("LANGCHAIN_TRACING_V2")


def trace_call(
    *,
    name: str,
    run_type: str,
    func: Callable[..., T],
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> T:
    if not langsmith_tracing_enabled():
        return func(*args, **(kwargs or {}))

    traced = traceable(
        name=name,
        run_type=run_type,
        metadata=metadata,
        tags=tags,
    )(func)
    return traced(*args, **(kwargs or {}))


def _env_bool(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}
