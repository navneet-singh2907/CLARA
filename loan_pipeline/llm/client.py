"""LangChain client helpers used only when LLM agent mode is enabled."""

import hashlib
import json
from dataclasses import asdict, replace
from typing import Any

from pydantic import SecretStr

from loan_pipeline.config import Settings, get_settings
from loan_pipeline.graph.state import ComplianceResult, ExtractedTerms, LoanCase, RiskResult
from loan_pipeline.llm.prompts import (
    COMPLIANCE_RATIONALE_PROMPT,
    DOCUMENT_PARSE_PROMPT,
    RISK_RATIONALE_PROMPT,
    TERM_EXTRACTION_PROMPT,
)

LLM_TIMEOUT_SECONDS = 30.0
LLM_RESPONSE_PREVIEW_CHARS = 500


class LLMResponseError(Exception):
    """Raised when an LLM returns a response that cannot be parsed or used.

    Carries structured context so callers and log aggregators can pinpoint
    exactly which agent, case, and provider produced the bad response.
    """

    def __init__(
        self,
        message: str,
        *,
        agent_name: str,
        case_id: str | None = None,
        operation: str,
        provider: str,
        model: str,
        temperature: float,
        response_preview: str | None = None,
    ) -> None:
        self.agent_name = agent_name
        self.case_id = case_id
        self.operation = operation
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.response_preview = response_preview
        super().__init__(
            f"[{agent_name}|{operation}|case={case_id}|{provider}/{model}] {message}"
            + (f" | response_preview={response_preview!r}" if response_preview else "")
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "case_id": self.case_id,
            "operation": self.operation,
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "response_preview": self.response_preview,
            "message": str(self),
        }


def extract_terms_with_llm(loan_case: LoanCase) -> ExtractedTerms:
    settings = _require_llm_settings()
    payload = _invoke_json_prompt(
        settings=settings,
        prompt=TERM_EXTRACTION_PROMPT.format(
            loan_case_json=json.dumps(asdict(loan_case), indent=2)
        ),
        agent_name="term_extractor",
        case_id=loan_case.case_id,
        operation="extract_terms",
    )
    return ExtractedTerms(
        case_id=str(payload["case_id"]),
        borrower_name=str(payload["borrower_name"]),
        industry=str(payload["industry"]),
        naics_code=str(payload["naics_code"]),
        loan_amount=float(payload["loan_amount"]),
        sba_guaranteed_amount=float(payload["sba_guaranteed_amount"]),
        guarantee_ratio=round(float(payload["guarantee_ratio"]), 4),
        term_months=int(payload["term_months"]),
        jobs_supported=int(payload["jobs_supported"]),
        borrower_credit_score=(
            int(payload["borrower_credit_score"])
            if payload.get("borrower_credit_score") is not None
            else None
        ),
        years_in_business=(
            float(payload["years_in_business"])
            if payload.get("years_in_business") is not None
            else None
        ),
        prior_default=bool(payload["prior_default"]),
        missing_documents=list(payload.get("missing_documents") or []),
        confidence=_coerce_confidence(payload.get("confidence"), default=0.80),
        warnings=list(payload.get("warnings") or []),
    )


def add_llm_compliance_note(terms: ExtractedTerms, compliance: ComplianceResult) -> ComplianceResult:
    settings = _require_llm_settings()
    payload = _invoke_json_prompt(
        settings=settings,
        prompt=COMPLIANCE_RATIONALE_PROMPT.format(
            terms_json=json.dumps(asdict(terms), indent=2),
            compliance_json=json.dumps(asdict(compliance), indent=2),
        ),
        agent_name="compliance_checker",
        case_id=terms.case_id,
        operation="add_compliance_note",
    )
    reviewer_note = str(payload.get("reviewer_note", "")).strip()
    if not reviewer_note:
        return compliance
    return replace(
        compliance,
        confidence=max(compliance.confidence, 0.90),
        reviewer_note=reviewer_note,
    )


def add_llm_risk_rationale(terms: ExtractedTerms, risk: RiskResult) -> RiskResult:
    settings = _require_llm_settings()
    payload = _invoke_json_prompt(
        settings=settings,
        prompt=RISK_RATIONALE_PROMPT.format(
            terms_json=json.dumps(asdict(terms), indent=2),
            risk_json=json.dumps(asdict(risk), indent=2),
        ),
        agent_name="credit_risk_scorer",
        case_id=terms.case_id,
        operation="add_risk_rationale",
    )
    rationale = str(payload.get("rationale", "")).strip()
    if not rationale:
        return risk
    return replace(risk, rationale=rationale)


def parse_document_to_loan_case(document_text: str) -> LoanCase:
    settings = _require_llm_settings()
    payload = _invoke_json_prompt(
        settings=settings,
        prompt=DOCUMENT_PARSE_PROMPT.format(document_text=document_text.strip()),
        agent_name="document_parser",
        case_id=None,
        operation="parse_document",
    )
    case_id = "DOC-" + hashlib.sha256(document_text.encode()).hexdigest()[:8].upper()
    credit_score = payload.get("borrower_credit_score")
    years = payload.get("years_in_business")
    missing = payload.get("missing_documents") or []
    return LoanCase(
        case_id=case_id,
        borrower_name=str(payload.get("borrower_name") or "Unknown Borrower"),
        industry=str(payload.get("industry") or ""),
        naics_code=str(payload.get("naics_code") or ""),
        loan_amount=float(payload.get("loan_amount") or 0),
        sba_guaranteed_amount=float(payload.get("sba_guaranteed_amount") or 0),
        term_months=int(payload.get("term_months") or 0),
        jobs_supported=int(payload.get("jobs_supported") or 0),
        borrower_credit_score=int(credit_score) if credit_score is not None else None,
        years_in_business=float(years) if years is not None else None,
        prior_default=bool(payload.get("prior_default", False)),
        missing_documents=[str(d) for d in missing],
        notes=str(payload.get("notes") or ""),
        difficulty_tier="unknown",
    )


def _require_llm_settings() -> Settings:
    settings = get_settings()
    if not settings.llm_api_key:
        raise RuntimeError(
            "USE_LLM_AGENTS=true requires LLM_API_KEY, NEBIUS_API_KEY, or OPENAI_API_KEY."
        )
    return settings


def _invoke_json_prompt(
    settings: Settings,
    prompt: str,
    *,
    agent_name: str,
    case_id: str | None = None,
    operation: str,
) -> dict[str, Any]:
    from langchain_openai import ChatOpenAI

    provider = settings.llm_provider
    model = settings.openai_model
    temperature = settings.llm_temperature
    api_key = settings.llm_api_key
    if api_key is None:
        raise RuntimeError(
            "USE_LLM_AGENTS=true requires LLM_API_KEY, NEBIUS_API_KEY, or OPENAI_API_KEY."
        )

    llm = ChatOpenAI(
        api_key=SecretStr(api_key),
        base_url=settings.llm_base_url,
        model=model,
        temperature=temperature,
        timeout=LLM_TIMEOUT_SECONDS,
    )

    try:
        response = llm.invoke(prompt)
    except Exception as exc:
        raise LLMResponseError(
            "LLM call failed.",
            agent_name=agent_name,
            case_id=case_id,
            operation=operation,
            provider=provider,
            model=model,
            temperature=temperature,
        ) from exc

    content = response.content if hasattr(response, "content") else str(response)
    if not isinstance(content, str):
        content = str(content)

    return _parse_json_content(
        content,
        agent_name=agent_name,
        case_id=case_id,
        operation=operation,
        provider=provider,
        model=model,
        temperature=temperature,
    )


def _parse_json_content(
    content: str,
    *,
    agent_name: str,
    case_id: str | None,
    operation: str,
    provider: str,
    model: str,
    temperature: float,
) -> dict[str, Any]:
    preview = content[:LLM_RESPONSE_PREVIEW_CHARS].replace("\n", " ")

    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LLMResponseError(
            "Response is not valid JSON.",
            agent_name=agent_name,
            case_id=case_id,
            operation=operation,
            provider=provider,
            model=model,
            temperature=temperature,
            response_preview=preview,
        ) from exc
    if not isinstance(payload, dict):
        raise LLMResponseError(
            f"Response JSON must be an object, got {type(payload).__name__}.",
            agent_name=agent_name,
            case_id=case_id,
            operation=operation,
            provider=provider,
            model=model,
            temperature=temperature,
            response_preview=preview,
        )
    return payload


def _coerce_confidence(value: Any, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip().lower()
        label_scores = {
            "very high": 0.95,
            "high": 0.90,
            "medium": 0.75,
            "moderate": 0.75,
            "low": 0.55,
            "very low": 0.35,
        }
        if normalized in label_scores:
            return label_scores[normalized]
        value = normalized
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return default
    if confidence > 1:
        confidence = confidence / 100
    return min(max(confidence, 0.0), 1.0)
