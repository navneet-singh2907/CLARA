"""Evaluation metrics for the loan review pipeline."""

from dataclasses import dataclass

from loan_pipeline.graph.state import LoanCase, ReviewPacket


@dataclass(frozen=True)
class GoldLabel:
    case_id: str
    tier: str
    expected_compliance_status: str
    expected_risk_band: str
    expected_escalation: bool
    expected_outcome: str


@dataclass(frozen=True)
class CaseScore:
    case_id: str
    tier: str
    term_extraction_correct: bool
    compliance_correct: bool
    risk_correct: bool
    escalation_correct: bool
    outcome_correct: bool


def score_case(loan_case: LoanCase, packet: ReviewPacket, gold: GoldLabel) -> CaseScore:
    return CaseScore(
        case_id=loan_case.case_id,
        tier=gold.tier,
        term_extraction_correct=_terms_match_case(loan_case, packet),
        compliance_correct=packet.compliance.status == gold.expected_compliance_status,
        risk_correct=packet.risk.band == gold.expected_risk_band,
        escalation_correct=packet.escalation_required == gold.expected_escalation,
        outcome_correct=packet.recommended_outcome == gold.expected_outcome,
    )


def summarize_scores(scores: list[CaseScore]) -> dict[str, object]:
    return {
        "overall": _summarize_group(scores),
        "by_tier": {
            tier: _summarize_group([score for score in scores if score.tier == tier])
            for tier in ["clean", "ambiguous", "adversarial"]
        },
    }


def _summarize_group(scores: list[CaseScore]) -> dict[str, float | int]:
    if not scores:
        return {
            "cases": 0,
            "term_extraction_accuracy": 0.0,
            "compliance_status_accuracy": 0.0,
            "risk_band_accuracy": 0.0,
            "escalation_accuracy": 0.0,
            "final_outcome_accuracy": 0.0,
        }

    return {
        "cases": len(scores),
        "term_extraction_accuracy": _mean(score.term_extraction_correct for score in scores),
        "compliance_status_accuracy": _mean(score.compliance_correct for score in scores),
        "risk_band_accuracy": _mean(score.risk_correct for score in scores),
        "escalation_accuracy": _mean(score.escalation_correct for score in scores),
        "final_outcome_accuracy": _mean(score.outcome_correct for score in scores),
    }


def _terms_match_case(loan_case: LoanCase, packet: ReviewPacket) -> bool:
    terms = packet.extracted_terms
    return (
        terms.case_id == loan_case.case_id
        and terms.borrower_name == loan_case.borrower_name
        and terms.loan_amount == loan_case.loan_amount
        and terms.sba_guaranteed_amount == loan_case.sba_guaranteed_amount
        and terms.term_months == loan_case.term_months
        and terms.naics_code == loan_case.naics_code
    )


def _mean(values) -> float:
    items = list(values)
    return round(sum(1 for item in items if item) / len(items), 4)

