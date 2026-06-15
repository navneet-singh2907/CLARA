"""Cupcake MVP tests."""

from src.data.sample_cases import get_sample_case
from src.graph.orchestrator import run_pipeline, run_pipeline_with_state


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


def test_pipeline_exposes_intermediate_state() -> None:
    state = run_pipeline_with_state(get_sample_case("AMB-001"))

    assert state["extracted_terms"] is not None
    assert state["compliance"] is not None
    assert state["risk"] is not None
    assert state["review_packet"] is not None

