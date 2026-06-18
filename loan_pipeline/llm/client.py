"""LangChain client helpers used only when LLM agent mode is enabled."""

import json
from dataclasses import asdict, replace
from typing import Any

from loan_pipeline.config import Settings, get_settings
from loan_pipeline.graph.state import ComplianceResult, ExtractedTerms, LoanCase, RiskResult
from loan_pipeline.llm.prompts import (
    COMPLIANCE_RATIONALE_PROMPT,
    RISK_RATIONALE_PROMPT,
    TERM_EXTRACTION_PROMPT,
)


def extract_terms_with_llm(loan_case: LoanCase) -> ExtractedTerms:
    settings = _require_llm_settings()
    payload = _invoke_json_prompt(
        settings=settings,
        prompt=TERM_EXTRACTION_PROMPT.format(loan_case_json=json.dumps(asdict(loan_case), indent=2)),
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
            float(payload["years_in_business"]) if payload.get("years_in_business") is not None else None
        ),
        prior_default=bool(payload["prior_default"]),
        missing_documents=list(payload.get("missing_documents") or []),
        confidence=float(payload["confidence"]),
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
    )
    rationale = str(payload.get("rationale", "")).strip()
    if not rationale:
        return risk
    return replace(risk, rationale=rationale)


def _require_llm_settings() -> Settings:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("USE_LLM_AGENTS=true requires OPENAI_API_KEY.")
    return settings


def _invoke_json_prompt(settings: Settings, prompt: str) -> dict[str, Any]:
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        temperature=settings.llm_temperature,
    )
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    if not isinstance(content, str):
        content = str(content)
    return _parse_json_content(content)


def _parse_json_content(content: str) -> dict[str, Any]:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError("LLM response must be valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("LLM response JSON must be an object.")
    return payload
