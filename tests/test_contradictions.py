"""Agent contradiction detection tests."""

from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.graph.orchestrator import run_pipeline
from loan_pipeline.graph.state import ComplianceFinding, ComplianceResult, RiskResult
from loan_pipeline.review.contradictions import detect_contradictions


def test_detects_compliance_fail_with_low_risk() -> None:
    compliance = ComplianceResult(
        status="FAIL",
        findings=[
            ComplianceFinding(
                rule_id="DOC-001",
                severity="HIGH",
                description="Required loan documentation is missing.",
                evidence="tax_returns",
            )
        ],
        confidence=0.9,
    )
    risk = RiskResult(
        score=1,
        band="LOW",
        confidence=0.8,
        primary_risk_factors=[],
        mitigating_factors=["Strong repayment profile."],
        rationale="Low credit risk.",
    )

    contradictions = detect_contradictions(compliance, risk)

    assert len(contradictions) == 1
    assert contradictions[0].severity == "HIGH"
    assert "Compliance blocker" in contradictions[0].title


def test_pipeline_surfaces_contradiction_in_review_packet() -> None:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases()}
    packet = run_pipeline(cases["AMB-002"])

    assert packet.recommended_outcome == "ESCALATE"
    assert packet.contradictions
    assert any("Agent contradiction detected" in note for note in packet.human_review_notes)
