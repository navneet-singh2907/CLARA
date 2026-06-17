"""Shared graph state and loan review contracts."""

import operator
from dataclasses import dataclass, field
from time import perf_counter
from typing import Annotated, Literal, TypedDict

RiskBand = Literal["LOW", "MEDIUM", "HIGH"]
ReviewOutcome = Literal["APPROVE", "CONDITIONAL_REVIEW", "ESCALATE", "REJECT"]
ReviewPolicy = Literal["sba_reviewer", "bank_underwriter", "cdfi_lender"]


@dataclass(frozen=True)
class LoanCase:
    case_id: str
    borrower_name: str
    industry: str
    naics_code: str
    loan_amount: float
    sba_guaranteed_amount: float
    term_months: int
    jobs_supported: int
    borrower_credit_score: int | None
    years_in_business: float | None
    prior_default: bool
    missing_documents: list[str] = field(default_factory=list)
    notes: str = ""
    difficulty_tier: str = "clean"


@dataclass(frozen=True)
class ExtractedTerms:
    case_id: str
    borrower_name: str
    industry: str
    naics_code: str
    loan_amount: float
    sba_guaranteed_amount: float
    guarantee_ratio: float
    term_months: int
    jobs_supported: int
    borrower_credit_score: int | None
    years_in_business: float | None
    prior_default: bool
    missing_documents: list[str]
    confidence: float
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ComplianceFinding:
    rule_id: str
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    description: str
    evidence: str


@dataclass(frozen=True)
class ComplianceResult:
    status: Literal["PASS", "REVIEW", "FAIL"]
    findings: list[ComplianceFinding]
    confidence: float
    reviewer_note: str = ""


@dataclass(frozen=True)
class RiskResult:
    score: int
    band: RiskBand
    confidence: float
    primary_risk_factors: list[str]
    mitigating_factors: list[str]
    rationale: str


@dataclass(frozen=True)
class ContradictionResult:
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    title: str
    compliance_position: str
    risk_position: str
    reviewer_prompt: str


@dataclass(frozen=True)
class CounterfactualResult:
    type: Literal["DOCUMENTATION", "CREDIT", "OPERATING_HISTORY", "DEFAULT_HISTORY"]
    title: str
    current_state: str
    suggested_change: str
    expected_effect: str


@dataclass(frozen=True)
class HumanOverride:
    entry_id: str
    case_id: str
    target_type: Literal["COMPLIANCE", "RISK", "CONTRADICTION", "COUNTERFACTUAL", "OUTCOME"]
    target_id: str
    original_value: str
    override_decision: str
    rationale: str
    reviewer: str
    created_at: str


@dataclass(frozen=True)
class ExecutionTraceEntry:
    node: str
    stage: str
    parallel_group: str | None
    duration_ms: float
    status: Literal["SUCCESS", "ERROR"]


@dataclass(frozen=True)
class ReviewPacket:
    case_id: str
    review_policy: ReviewPolicy
    recommended_outcome: ReviewOutcome
    escalation_required: bool
    summary: str
    extracted_terms: ExtractedTerms
    compliance: ComplianceResult
    risk: RiskResult
    human_review_notes: list[str]
    contradictions: list[ContradictionResult] = field(default_factory=list)
    counterfactuals: list[CounterfactualResult] = field(default_factory=list)
    audit_log: list[HumanOverride] = field(default_factory=list)


class GraphState(TypedDict):
    loan_case: LoanCase
    review_policy: ReviewPolicy
    extracted_terms: ExtractedTerms | None
    validation_errors: list[str]
    compliance: ComplianceResult | None
    risk: RiskResult | None
    contradictions: list[ContradictionResult]
    counterfactuals: list[CounterfactualResult]
    review_packet: ReviewPacket | None
    agent_errors: list[str]
    execution_trace: Annotated[list[ExecutionTraceEntry], operator.add]


def initial_state(loan_case: LoanCase, review_policy: ReviewPolicy = "sba_reviewer") -> GraphState:
    return {
        "loan_case": loan_case,
        "review_policy": review_policy,
        "extracted_terms": None,
        "validation_errors": [],
        "compliance": None,
        "risk": None,
        "contradictions": [],
        "counterfactuals": [],
        "review_packet": None,
        "agent_errors": [],
        "execution_trace": [],
    }


def validate_terms_node(state: GraphState) -> GraphState:
    started_at = perf_counter()
    terms = state["extracted_terms"]
    errors: list[str] = []

    if terms.loan_amount <= 0:
        errors.append("Loan amount must be greater than zero.")

    if terms.term_months <= 0:
        errors.append("Loan term must be greater than zero months.")

    if not terms.borrower_name.strip():
        errors.append("Borrower name is required.")

    if not terms.industry.strip():
        errors.append("Industry is required.")

    if not terms.naics_code.strip():
        errors.append("NAICS code is required.")

    if terms.sba_guaranteed_amount < 0:
        errors.append("SBA guaranteed amount cannot be negative.")

    if terms.sba_guaranteed_amount > terms.loan_amount:
        errors.append("SBA guaranteed amount cannot exceed loan amount.")

    if terms.jobs_supported < 0:
        errors.append("Jobs supported cannot be negative.")

    if terms.borrower_credit_score is not None and not 300 <= terms.borrower_credit_score <= 850:
        errors.append("Borrower credit score must be between 300 and 850.")

    if terms.years_in_business is not None and terms.years_in_business < 0:
        errors.append("Years in business cannot be negative.")

    return {
        "validation_errors": errors,
        "execution_trace": [
            ExecutionTraceEntry(
                node="schema_validator",
                stage="validation",
                parallel_group=None,
                duration_ms=round((perf_counter() - started_at) * 1000, 3),
                status="SUCCESS" if not errors else "ERROR",
            )
        ],
    }
