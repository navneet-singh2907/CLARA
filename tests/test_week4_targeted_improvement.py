"""Tests for Week 4 eval-driven calibration changes."""

from loan_pipeline.agents.compliance_checker import run_compliance_checker_deterministic
from loan_pipeline.agents.credit_risk_scorer import run_credit_risk_scorer_deterministic
from loan_pipeline.config import WEEK4_SBA_LOANS_CSV, load_sba_demo_cases
from loan_pipeline.graph.orchestrator import run_pipeline, synthesize_review_packet
from loan_pipeline.graph.state import ComplianceResult, ExtractedTerms, RiskResult


def _week4_case(case_id: str):
    return {
        loan_case.case_id: loan_case
        for loan_case in load_sba_demo_cases(WEEK4_SBA_LOANS_CSV)
    }[case_id]


def test_irrelevant_non_loan_input_is_not_mislabeled_as_kyc_failure() -> None:
    packet = run_pipeline(_week4_case("ADV2-003"))

    assert packet.compliance.status == "PASS"
    assert packet.risk.band == "MEDIUM"
    assert packet.recommended_outcome == "ESCALATE"
    assert packet.escalation_required


def test_missing_customer_contracts_raise_medium_risk_for_young_large_request() -> None:
    packet = run_pipeline(_week4_case("KF-003"))

    assert packet.compliance.status == "FAIL"
    assert packet.risk.band == "MEDIUM"
    assert packet.recommended_outcome == "ESCALATE"


def test_low_confidence_alone_does_not_force_clean_approval_to_escalate() -> None:
    terms = ExtractedTerms(
        case_id="AMB-LIVE-LIKE",
        borrower_name="Fairview Fitness Studio",
        industry="Fitness center",
        naics_code="713940",
        loan_amount=420000,
        sba_guaranteed_amount=357000,
        guarantee_ratio=0.85,
        term_months=120,
        jobs_supported=10,
        borrower_credit_score=681,
        years_in_business=1.5,
        prior_default=False,
        missing_documents=[],
        confidence=0.75,
    )
    compliance = run_compliance_checker_deterministic(terms)
    risk = run_credit_risk_scorer_deterministic(terms)

    packet = synthesize_review_packet(
        terms=terms,
        compliance=compliance,
        risk=risk,
        validation_errors=[],
    )

    assert packet.recommended_outcome == "APPROVE"
    assert not packet.escalation_required
    assert "Extraction confidence is below target threshold." not in packet.human_review_notes


def test_materially_low_confidence_still_forces_human_review() -> None:
    terms = ExtractedTerms(
        case_id="ADV-INTAKE",
        borrower_name="Unrelated Weather Report",
        industry="Nonspecific business",
        naics_code="000000",
        loan_amount=150000,
        sba_guaranteed_amount=112500,
        guarantee_ratio=0.75,
        term_months=60,
        jobs_supported=0,
        borrower_credit_score=None,
        years_in_business=None,
        prior_default=False,
        missing_documents=[],
        confidence=0.40,
    )
    compliance = ComplianceResult(status="PASS", findings=[], confidence=0.95)
    risk = RiskResult(
        score=3,
        band="MEDIUM",
        confidence=0.70,
        primary_risk_factors=["Credit score is missing.", "Years in business is missing."],
        mitigating_factors=[],
        rationale="Missing core underwriting fields.",
    )

    packet = synthesize_review_packet(
        terms=terms,
        compliance=compliance,
        risk=risk,
        validation_errors=[],
    )

    assert packet.recommended_outcome == "ESCALATE"
    assert packet.escalation_required
    assert "Extraction confidence is below target threshold." in packet.human_review_notes
