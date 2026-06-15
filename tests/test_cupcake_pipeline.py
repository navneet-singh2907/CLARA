"""Cupcake MVP tests."""

from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.graph.orchestrator import run_pipeline, run_pipeline_with_state
from loan_pipeline.graph.state import LoanCase


def get_sample_case(case_id: str) -> LoanCase:
    for loan_case in load_sba_demo_cases():
        if loan_case.case_id == case_id:
            return loan_case
    raise ValueError(f"Unknown sample case: {case_id}")


def test_clean_case_reaches_approve_or_conditional_review() -> None:
    packet = run_pipeline(get_sample_case("CLEAN-001"))

    assert packet.case_id == "CLEAN-001"
    assert packet.risk.band == "LOW"
    assert packet.compliance.status == "PASS"
    assert packet.recommended_outcome == "APPROVE"
    assert not packet.escalation_required


def test_adversarial_case_escalates() -> None:
    packet = run_pipeline(get_sample_case("ADV-001"))

    assert packet.case_id == "ADV-001"
    assert packet.risk.band == "HIGH"
    assert packet.compliance.status == "FAIL"
    assert packet.recommended_outcome == "ESCALATE"
    assert packet.escalation_required
    assert packet.human_review_notes


def test_ambiguous_case_requires_conditional_review() -> None:
    packet = run_pipeline(get_sample_case("AMB-001"))

    assert packet.case_id == "AMB-001"
    assert packet.compliance.status == "FAIL"
    assert packet.recommended_outcome == "ESCALATE"
    assert "Extraction confidence is below target threshold." in packet.human_review_notes


def test_validation_errors_force_human_review() -> None:
    invalid_case = LoanCase(
        case_id="INVALID-001",
        borrower_name="",
        industry="Unknown",
        naics_code="000000",
        loan_amount=0,
        sba_guaranteed_amount=0,
        term_months=0,
        jobs_supported=0,
        borrower_credit_score=700,
        years_in_business=3,
        prior_default=False,
    )

    packet = run_pipeline(invalid_case)

    assert packet.recommended_outcome != "APPROVE"
    assert packet.escalation_required
    assert "Loan amount must be greater than zero." in packet.human_review_notes
    assert "Loan term must be greater than zero months." in packet.human_review_notes
    assert "Borrower name is required." in packet.human_review_notes


def test_pipeline_exposes_intermediate_state() -> None:
    state = run_pipeline_with_state(get_sample_case("AMB-001"))

    assert state["extracted_terms"] is not None
    assert state["compliance"] is not None
    assert state["risk"] is not None
    assert state["review_packet"] is not None
