"""Edge-case stress tests for malformed loan applications."""

from src.graph.orchestrator import run_pipeline
from src.schemas.loan import LoanCase


def test_guarantee_cannot_exceed_loan_amount() -> None:
    case = LoanCase(
        case_id="EDGE-OVER-GUARANTEE",
        borrower_name="Mismatch Metals LLC",
        industry="Metal fabrication",
        naics_code="332999",
        loan_amount=100000,
        sba_guaranteed_amount=125000,
        term_months=60,
        jobs_supported=8,
        borrower_credit_score=710,
        years_in_business=4,
        prior_default=False,
    )

    packet = run_pipeline(case)

    assert packet.recommended_outcome == "ESCALATE"
    assert packet.escalation_required
    assert "SBA guaranteed amount cannot exceed loan amount." in packet.human_review_notes


def test_impossible_credit_score_escalates() -> None:
    case = LoanCase(
        case_id="EDGE-BAD-CREDIT",
        borrower_name="Impossible Score Services",
        industry="Professional services",
        naics_code="541611",
        loan_amount=90000,
        sba_guaranteed_amount=67500,
        term_months=72,
        jobs_supported=5,
        borrower_credit_score=912,
        years_in_business=3,
        prior_default=False,
    )

    packet = run_pipeline(case)

    assert packet.recommended_outcome == "ESCALATE"
    assert "Borrower credit score must be between 300 and 850." in packet.human_review_notes


def test_negative_business_history_and_jobs_escalate() -> None:
    case = LoanCase(
        case_id="EDGE-NEGATIVE-FIELDS",
        borrower_name="Backdated Ventures",
        industry="Consulting",
        naics_code="541618",
        loan_amount=50000,
        sba_guaranteed_amount=25000,
        term_months=24,
        jobs_supported=-2,
        borrower_credit_score=680,
        years_in_business=-1,
        prior_default=False,
    )

    packet = run_pipeline(case)

    assert packet.recommended_outcome == "ESCALATE"
    assert "Jobs supported cannot be negative." in packet.human_review_notes
    assert "Years in business cannot be negative." in packet.human_review_notes


def test_missing_classification_fields_escalate() -> None:
    case = LoanCase(
        case_id="EDGE-MISSING-CLASSIFICATION",
        borrower_name="Sparse Application LLC",
        industry="",
        naics_code="",
        loan_amount=75000,
        sba_guaranteed_amount=56250,
        term_months=48,
        jobs_supported=3,
        borrower_credit_score=690,
        years_in_business=2,
        prior_default=False,
    )

    packet = run_pipeline(case)

    assert packet.recommended_outcome == "ESCALATE"
    assert "Industry is required." in packet.human_review_notes
    assert "NAICS code is required." in packet.human_review_notes

