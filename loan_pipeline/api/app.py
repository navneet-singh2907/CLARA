"""FastAPI entrypoint for SSE streaming endpoints."""

import hashlib
import io
import re
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from loan_pipeline.api.rate_limit import enforce_rate_limit
from loan_pipeline.api.streaming import (
    error_payload,
    stream_evaluation_events,
    stream_judge_agreement_events,
    stream_live_drift_events,
    stream_review_events,
)
from loan_pipeline.config import (
    WEEK4_GOLD_SET_JSON,
    WEEK4_SBA_LOANS_CSV,
    get_settings,
    load_sba_demo_cases,
    offline_evaluation_context,
)
from loan_pipeline.eval.ablation import run_ablation_study, summarize_ablation_table
from loan_pipeline.eval.drift import run_drift_study
from loan_pipeline.eval.inter_rater import run_inter_rater_report, run_packet_inter_rater_report
from loan_pipeline.eval.report import generate_evaluation_report
from loan_pipeline.eval.report_pdf import build_evaluation_report_pdf
from loan_pipeline.eval.run_eval import run_eval
from loan_pipeline.graph.orchestrator import run_pipeline
from loan_pipeline.graph.state import LoanCase, ReviewPolicy
from loan_pipeline.llm.client import parse_document_to_loan_case
from loan_pipeline.review.pdf_export import build_review_packet_pdf

app = FastAPI(
    title="CLARA API",
    version="0.1.0",
    description="SSE endpoints for observing CLARA loan review agents and evaluation runs.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class AuditEntryPayload(BaseModel):
    target: str
    decision: str
    reviewer: str
    rationale: str
    createdAt: str


class LoanCasePayload(BaseModel):
    case_id: str
    borrower_name: str
    industry: str
    naics_code: str
    loan_amount: float
    sba_guaranteed_amount: float
    term_months: int
    jobs_supported: int
    borrower_credit_score: int | None = None
    years_in_business: float | None = None
    prior_default: bool = False
    missing_documents: list[str] = Field(default_factory=list)
    notes: str = ""
    difficulty_tier: str = "uploaded"


class ReviewPdfRequest(BaseModel):
    case_id: str | None = None
    policy: ReviewPolicy = "sba_reviewer"
    loan_case: LoanCasePayload | None = None
    audit_entries: list[AuditEntryPayload] = Field(default_factory=list)

CASE_ID_QUERY = Query(..., description="Gold-set case ID, for example ADV-001.")
POLICY_QUERY = Query("sba_reviewer", description="Reviewer policy profile.")
DOCUMENT_FILE = File(...)
DOCUMENT_POLICY = Form("sba_reviewer")
MAX_UPLOAD_BYTES = 10_000_000
REQUIRED_UPLOAD_FIELDS = {
    "borrower_name": "borrower/company name",
    "loan_amount": "loan amount",
    "term_months": "loan term",
    "jobs_supported": "jobs supported",
}


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <title>CLARA API</title>
        <style>
          body { font-family: Arial, sans-serif; max-width: 880px; margin: 48px auto; line-height: 1.5; }
          code, pre { background: #f4f4f4; border-radius: 6px; padding: 2px 6px; }
          pre { padding: 12px; overflow-x: auto; }
          a { color: #b91c1c; }
        </style>
      </head>
      <body>
        <h1>CLARA API</h1>
        <p>Credit Loan Analysis & Review Agent backend for streaming LangGraph loan-review events with Server-Sent Events.</p>
        <h2>Quick Checks</h2>
        <ul>
          <li><a href="/health">/health</a></li>
          <li><a href="/cases">/cases</a></li>
          <li><a href="/docs">/docs</a></li>
        </ul>
        <h2>SSE Test</h2>
        <p>Use this in PowerShell so you can see events arrive live:</p>
        <pre>curl.exe -N "http://127.0.0.1:8000/review/stream?case_id=ADV-001&amp;policy=sba_reviewer"</pre>
      </body>
    </html>
    """


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readiness")
def readiness() -> dict[str, Any]:
    settings = get_settings()
    cases = load_sba_demo_cases(WEEK4_SBA_LOANS_CSV)
    live_llm_available = settings.use_llm_agents and bool(settings.llm_api_key)
    primary_judge_available = bool(settings.primary_judge_model)
    secondary_judge_available = bool(settings.secondary_judge_model)
    difficulty_tiers = {
        tier: sum(1 for loan_case in cases if loan_case.difficulty_tier == tier)
        for tier in sorted({loan_case.difficulty_tier for loan_case in cases})
    }
    return {
        "api": "connected",
        "app": "CLARA",
        "gold_set_cases": len(cases),
        "difficulty_tiers": difficulty_tiers,
        "llm_mode": settings.use_llm_agents,
        "live_llm_available": live_llm_available,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.openai_model,
        "llm_temperature": settings.llm_temperature if live_llm_available else None,
        "primary_judge": settings.primary_judge_model or "local deterministic judge",
        "secondary_judge": settings.secondary_judge_model or "local strict judge",
        "live_judges_available": primary_judge_available and secondary_judge_available,
        "langsmith_tracing": settings.langsmith_tracing,
        "langsmith_project": settings.langsmith_project,
        "live_drift_available": live_llm_available,
        "rate_limits": {
            "window_seconds": settings.rate_limit_window_seconds,
            "review_requests": settings.rate_limit_review_requests,
            "upload_requests": settings.rate_limit_upload_requests,
            "expensive_requests": settings.rate_limit_expensive_requests,
            "demo_key_bypass": bool(settings.demo_api_key),
        },
    }


@app.get("/cases")
def cases() -> list[dict[str, str]]:
    return [
        {
            "case_id": loan_case.case_id,
            "borrower_name": loan_case.borrower_name,
            "tier": loan_case.difficulty_tier,
        }
        for loan_case in load_sba_demo_cases(WEEK4_SBA_LOANS_CSV)
    ]


@app.get("/review/stream")
def review_stream(
    request: Request,
    case_id: str = CASE_ID_QUERY,
    policy: ReviewPolicy = POLICY_QUERY,
) -> StreamingResponse:
    enforce_rate_limit(request, "review")
    return StreamingResponse(
        stream_review_events(case_id=case_id, review_policy=policy),
        media_type="text/event-stream",
    )


@app.post("/review/pdf")
def review_pdf(payload: ReviewPdfRequest, request: Request) -> Response:
    enforce_rate_limit(request, "review")
    if payload.loan_case:
        loan_case = _loan_case_from_payload(payload.loan_case)
    else:
        cases_by_id = {
            loan_case.case_id: loan_case for loan_case in load_sba_demo_cases(WEEK4_SBA_LOANS_CSV)
        }
        loan_case = cases_by_id.get(payload.case_id or "")
        if loan_case is None:
            return Response(f"Unknown case_id: {payload.case_id}", status_code=404)

    packet = run_pipeline(loan_case, review_policy=payload.policy)
    audit_log = [_audit_entry_to_pdf_row(entry) for entry in payload.audit_entries]
    pdf_bytes = build_review_packet_pdf(packet, audit_log=audit_log)
    headers = {
        "Content-Disposition": f'attachment; filename="loan_review_packet_{loan_case.case_id}.pdf"'
    }
    return Response(pdf_bytes, media_type="application/pdf", headers=headers)


@app.post("/review/document")
async def review_document(
    request: Request,
    file: UploadFile = DOCUMENT_FILE,
    policy: ReviewPolicy = DOCUMENT_POLICY,
) -> dict[str, Any]:
    enforce_rate_limit(request, "upload")
    document_text = await _extract_upload_text(file)
    if not document_text.strip():
        raise HTTPException(status_code=400, detail="Uploaded document did not contain extractable text.")

    loan_case = _parse_uploaded_loan_case(document_text)
    try:
        packet = run_pipeline(loan_case, review_policy=policy)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=error_payload(
                exc,
                endpoint="/review/document",
                file_name=file.filename,
                case_id=loan_case.case_id,
            ),
        ) from exc
    return {
        "file_name": file.filename,
        "characters_extracted": len(document_text),
        "loan_case": _loan_case_to_payload(loan_case),
        "case": _loan_case_summary(loan_case),
        "audit_targets": _review_packet_audit_targets(packet),
        "packet": {
            "case_id": packet.case_id,
            "outcome": packet.recommended_outcome,
            "risk": packet.risk.band,
            "compliance": packet.compliance.status,
            "escalation_required": packet.escalation_required,
            "summary": packet.summary,
            "risk_rationale": packet.risk.rationale,
            "compliance_findings": [asdict(finding) for finding in packet.compliance.findings],
            "counterfactuals": [asdict(item) for item in packet.counterfactuals],
            "contradictions": [asdict(item) for item in packet.contradictions],
        },
    }


@app.get("/evaluation/stream")
def evaluation_stream(request: Request) -> StreamingResponse:
    enforce_rate_limit(request, "expensive")
    return StreamingResponse(stream_evaluation_events(), media_type="text/event-stream")


@app.get("/evaluation")
def evaluation(request: Request) -> dict:
    enforce_rate_limit(request, "expensive")
    with offline_evaluation_context():
        return run_eval(gold_path=WEEK4_GOLD_SET_JSON, cases_path=WEEK4_SBA_LOANS_CSV)


@app.get("/ablation")
def ablation(request: Request) -> list[dict]:
    enforce_rate_limit(request, "expensive")
    with offline_evaluation_context():
        return summarize_ablation_table(
            run_ablation_study(gold_path=WEEK4_GOLD_SET_JSON, cases_path=WEEK4_SBA_LOANS_CSV)
        )


@app.get("/drift")
def drift(repeats: int = Query(5, ge=2, le=10)) -> dict:
    with offline_evaluation_context():
        return run_drift_study(repeats=repeats, cases_path=WEEK4_SBA_LOANS_CSV)


@app.get("/drift/live/stream")
def live_drift_stream(
    request: Request,
    case_id: str = CASE_ID_QUERY,
    policy: ReviewPolicy = POLICY_QUERY,
    repeats: int = Query(3, ge=2, le=5),
) -> StreamingResponse:
    enforce_rate_limit(request, "expensive")
    return StreamingResponse(
        stream_live_drift_events(case_id=case_id, review_policy=policy, repeats=repeats),
        media_type="text/event-stream",
    )


@app.get("/judge-agreement/stream")
def judge_agreement_stream(request: Request) -> StreamingResponse:
    enforce_rate_limit(request, "expensive")
    return StreamingResponse(stream_judge_agreement_events(), media_type="text/event-stream")


@app.get("/judge-agreement")
def judge_agreement(request: Request) -> dict:
    enforce_rate_limit(request, "expensive")
    return run_inter_rater_report(gold_path=WEEK4_GOLD_SET_JSON, cases_path=WEEK4_SBA_LOANS_CSV)


@app.post("/judge-agreement/packet")
async def judge_agreement_packet(request: Request, file: UploadFile = DOCUMENT_FILE) -> dict[str, Any]:
    enforce_rate_limit(request, "upload")
    packet_text = await _extract_upload_text(file)
    if not packet_text.strip():
        raise HTTPException(status_code=400, detail="Uploaded packet did not contain extractable text.")
    try:
        return run_packet_inter_rater_report(
            packet_text=packet_text,
            artifact_name=file.filename or "uploaded_packet.pdf",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=error_payload(
                exc,
                endpoint="/judge-agreement/packet",
                file_name=file.filename,
            ),
        ) from exc


@app.get("/report")
def report(request: Request) -> Response:
    enforce_rate_limit(request, "expensive")
    with offline_evaluation_context():
        report_text = generate_evaluation_report()
    return Response(report_text, media_type="text/markdown")


@app.get("/report/pdf")
def report_pdf(request: Request) -> Response:
    enforce_rate_limit(request, "expensive")
    with offline_evaluation_context():
        pdf_bytes = build_evaluation_report_pdf()
    headers = {"Content-Disposition": 'attachment; filename="evaluation_report.pdf"'}
    return Response(pdf_bytes, media_type="application/pdf", headers=headers)


def _audit_entry_to_pdf_row(entry: AuditEntryPayload) -> dict[str, Any]:
    return {
        "target_type": "UI_OVERRIDE",
        "target_id": entry.target,
        "override_decision": entry.decision,
        "rationale": entry.rationale,
        "reviewer": entry.reviewer,
        "created_at": entry.createdAt,
    }


def _loan_case_from_payload(payload: LoanCasePayload) -> LoanCase:
    return LoanCase(**payload.model_dump())


def _loan_case_to_payload(loan_case: LoanCase) -> dict[str, Any]:
    return asdict(loan_case)


def _loan_case_summary(loan_case: LoanCase) -> dict[str, Any]:
    return {
        "case_id": loan_case.case_id,
        "borrower_name": loan_case.borrower_name,
        "industry": loan_case.industry,
        "loan_amount": loan_case.loan_amount,
        "term_months": loan_case.term_months,
        "credit_score": loan_case.borrower_credit_score,
        "missing_documents": loan_case.missing_documents,
    }


def _review_packet_audit_targets(packet) -> list[str]:
    targets = [
        f"Outcome - {packet.recommended_outcome}",
        f"Risk band - {packet.risk.band}",
        f"Compliance status - {packet.compliance.status}",
    ]
    targets.extend(
        f"Compliance {finding.rule_id} - {finding.severity}"
        for finding in packet.compliance.findings
    )
    targets.extend(
        f"Contradiction {index} - {item.title}"
        for index, item in enumerate(packet.contradictions, start=1)
    )
    targets.extend(
        f"Counterfactual {index} - {item.title}"
        for index, item in enumerate(packet.counterfactuals, start=1)
    )
    return targets


async def _extract_upload_text(file: UploadFile) -> str:
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded file is too large. Maximum supported size is {MAX_UPLOAD_BYTES // 1_000_000} MB.",
        )
    file_name = (file.filename or "").lower()
    if file_name.endswith(".pdf") or file.content_type == "application/pdf":
        import pdfplumber

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    return content.decode("utf-8", errors="ignore")


def _parse_uploaded_loan_case(document_text: str) -> LoanCase:
    try:
        return _validate_uploaded_loan_case(parse_document_to_loan_case(document_text))
    except HTTPException:
        raise
    except Exception:
        return _parse_uploaded_loan_case_fallback(document_text)


def _parse_uploaded_loan_case_fallback(document_text: str) -> LoanCase:
    case_id = "DOC-" + hashlib.sha256(document_text.encode()).hexdigest()[:8].upper()
    borrower = _match_text(document_text, r"(?:borrower|business|company)\s*[:\-]\s*([^\n]+)")
    industry = _match_text(document_text, r"industry\s*[:\-]\s*([^\n]+)")
    naics = _match_text(document_text, r"naics\s*[:\-]\s*(\d{6})") or "000000"
    loan_amount = _match_money(document_text, r"loan(?: amount)?\s*[:\-]\s*\$?([\d,]+(?:\.\d+)?)")
    guaranteed = _match_money(
        document_text,
        r"(?:sba guarantee|guaranteed amount)\s*[:\-]\s*\$?([\d,]+(?:\.\d+)?)",
    )
    term = _match_int(document_text, r"term\s*[:\-]\s*(\d+)")
    jobs = _match_int(document_text, r"jobs(?: supported)?\s*[:\-]\s*(\d+)")
    credit_score = _match_int(document_text, r"credit score\s*[:\-]\s*(\d+)")
    years = _match_float(document_text, r"years in business\s*[:\-]\s*(\d+(?:\.\d+)?)")
    prior_default = bool(re.search(r"prior default\s*[:\-]\s*(true|yes)", document_text, re.I))
    missing_raw = _match_text(document_text, r"missing documents\s*[:\-]\s*([^\n]+)")
    missing_documents = [
        item.strip()
        for item in re.split(r"[,|]", missing_raw or "")
        if item.strip() and item.strip().lower() != "none"
    ]

    return _validate_uploaded_loan_case(LoanCase(
        case_id=case_id,
        borrower_name=borrower or "Uploaded Borrower",
        industry=industry or "Uploaded loan application",
        naics_code=naics,
        loan_amount=loan_amount,
        sba_guaranteed_amount=guaranteed,
        term_months=term,
        jobs_supported=jobs,
        borrower_credit_score=credit_score,
        years_in_business=years,
        prior_default=prior_default,
        missing_documents=missing_documents,
        notes="Parsed from uploaded document with deterministic fallback extraction.",
        difficulty_tier="uploaded",
    ))


def _validate_uploaded_loan_case(loan_case: LoanCase) -> LoanCase:
    missing_fields = []
    if not loan_case.borrower_name.strip() or loan_case.borrower_name in {
        "Unknown Borrower",
        "Uploaded Borrower",
    }:
        missing_fields.append(REQUIRED_UPLOAD_FIELDS["borrower_name"])
    if loan_case.loan_amount <= 0:
        missing_fields.append(REQUIRED_UPLOAD_FIELDS["loan_amount"])
    if loan_case.term_months <= 0:
        missing_fields.append(REQUIRED_UPLOAD_FIELDS["term_months"])
    if loan_case.jobs_supported < 0:
        missing_fields.append(REQUIRED_UPLOAD_FIELDS["jobs_supported"])

    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Uploaded loan document is missing required structured fields.",
                "missing_fields": missing_fields,
            },
        )
    return loan_case


def _match_text(text: str, pattern: str) -> str:
    match = re.search(pattern, text, re.I)
    return match.group(1).strip() if match else ""


def _match_money(text: str, pattern: str) -> float:
    value = _match_text(text, pattern).replace(",", "")
    return float(value) if value else 0.0


def _match_int(text: str, pattern: str) -> int:
    value = _match_text(text, pattern)
    return int(value) if value else 0


def _match_float(text: str, pattern: str) -> float | None:
    value = _match_text(text, pattern)
    return float(value) if value else None
