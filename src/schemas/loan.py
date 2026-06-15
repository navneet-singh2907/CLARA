"""Core data contracts for the Cupcake MVP."""

from dataclasses import dataclass, field
from typing import Any, Literal

RiskBand = Literal["LOW", "MEDIUM", "HIGH"]
ReviewOutcome = Literal["APPROVE", "CONDITIONAL_REVIEW", "ESCALATE", "REJECT"]


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


@dataclass(frozen=True)
class RiskResult:
    score: int
    band: RiskBand
    confidence: float
    primary_risk_factors: list[str]
    mitigating_factors: list[str]
    rationale: str


@dataclass(frozen=True)
class ReviewPacket:
    case_id: str
    recommended_outcome: ReviewOutcome
    escalation_required: bool
    summary: str
    extracted_terms: ExtractedTerms
    compliance: ComplianceResult
    risk: RiskResult
    human_review_notes: list[str]


GraphState = dict[str, Any]

