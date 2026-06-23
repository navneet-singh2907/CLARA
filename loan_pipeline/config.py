"""Project configuration and local data helpers."""

import csv
import os
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv

from loan_pipeline.graph.state import LoanCase

PROJECT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PROJECT_ROOT.parent
SBA_LOANS_CSV = PROJECT_ROOT / "data" / "sba_loans.csv"
WEEK4_SBA_LOANS_CSV = PROJECT_ROOT / "data" / "week4_sba_loans.csv"
GOLD_SET_JSON = PROJECT_ROOT / "eval" / "gold_set.json"
WEEK4_GOLD_SET_JSON = PROJECT_ROOT / "eval" / "week4_gold_set.json"

load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    app_env: str
    use_llm_agents: bool
    openai_api_key: str | None
    openai_model: str
    llm_api_key: str | None
    llm_base_url: str | None
    llm_provider: str
    llm_temperature: float
    primary_judge_model: str | None
    secondary_judge_model: str | None
    judge_temperature: float
    langsmith_tracing: bool
    langsmith_project: str
    demo_api_key: str | None
    rate_limit_window_seconds: int
    rate_limit_review_requests: int
    rate_limit_expensive_requests: int
    rate_limit_upload_requests: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    nebius_api_key = os.getenv("NEBIUS_API_KEY") or None
    openai_api_key = os.getenv("OPENAI_API_KEY") or None
    llm_base_url = os.getenv("LLM_BASE_URL") or os.getenv("NEBIUS_BASE_URL") or None
    llm_provider = os.getenv("LLM_PROVIDER") or ("nebius" if nebius_api_key else "openai")

    return Settings(
        app_env=os.getenv("APP_ENV", "local"),
        use_llm_agents=_env_bool("USE_LLM_AGENTS", default=False),
        openai_api_key=openai_api_key,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        llm_api_key=os.getenv("LLM_API_KEY") or nebius_api_key or openai_api_key,
        llm_base_url=llm_base_url,
        llm_provider=llm_provider,
        llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.2")),
        primary_judge_model=os.getenv("PRIMARY_JUDGE_MODEL") or None,
        secondary_judge_model=os.getenv("SECONDARY_JUDGE_MODEL") or None,
        judge_temperature=float(os.getenv("JUDGE_TEMPERATURE", "0.2")),
        langsmith_tracing=_env_bool("LANGSMITH_TRACING", default=False)
        or _env_bool("LANGCHAIN_TRACING_V2", default=False),
        langsmith_project=os.getenv("LANGSMITH_PROJECT", "loan-review-pipeline"),
        demo_api_key=os.getenv("CLARA_DEMO_KEY") or None,
        rate_limit_window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "3600")),
        rate_limit_review_requests=int(os.getenv("RATE_LIMIT_REVIEW_REQUESTS", "10")),
        rate_limit_expensive_requests=int(os.getenv("RATE_LIMIT_EXPENSIVE_REQUESTS", "3")),
        rate_limit_upload_requests=int(os.getenv("RATE_LIMIT_UPLOAD_REQUESTS", "5")),
    )


def reset_settings_cache() -> None:
    get_settings.cache_clear()


@contextmanager
def offline_evaluation_context() -> Iterator[None]:
    """Temporarily disable live model/tracing calls for reproducible batch artifacts."""
    env_names = [
        "USE_LLM_AGENTS",
        "PRIMARY_JUDGE_MODEL",
        "SECONDARY_JUDGE_MODEL",
        "LANGSMITH_TRACING",
        "LANGCHAIN_TRACING_V2",
    ]
    previous_values = {name: os.environ.get(name) for name in env_names}
    os.environ["USE_LLM_AGENTS"] = "false"
    os.environ["PRIMARY_JUDGE_MODEL"] = ""
    os.environ["SECONDARY_JUDGE_MODEL"] = ""
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    reset_settings_cache()
    try:
        yield
    finally:
        for name, value in previous_values.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        reset_settings_cache()


def load_sba_demo_cases(path: Path = SBA_LOANS_CSV) -> list[LoanCase]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        rows = csv.DictReader(csv_file)
        return [_row_to_loan_case(row) for row in rows]


def _row_to_loan_case(row: dict[str, str]) -> LoanCase:
    credit_score = row["borrower_credit_score"].strip()
    years_in_business = row["years_in_business"].strip()
    missing_documents = row["missing_documents"].strip()

    return LoanCase(
        case_id=row["case_id"],
        borrower_name=row["borrower_name"],
        industry=row["industry"],
        naics_code=row["naics_code"],
        loan_amount=float(row["loan_amount"]),
        sba_guaranteed_amount=float(row["sba_guaranteed_amount"]),
        term_months=int(row["term_months"]),
        jobs_supported=int(row["jobs_supported"]),
        borrower_credit_score=int(credit_score) if credit_score else None,
        years_in_business=float(years_in_business) if years_in_business else None,
        prior_default=row["prior_default"].lower() == "true",
        missing_documents=missing_documents.split("|") if missing_documents else [],
        notes=row["notes"],
        difficulty_tier=row["difficulty_tier"],
    )


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}
