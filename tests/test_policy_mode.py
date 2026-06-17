"""Reviewer policy mode tests."""

from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.graph.orchestrator import run_pipeline, run_pipeline_with_state
from loan_pipeline.review.policies import POLICY_PROFILES


def test_default_policy_is_sba_reviewer() -> None:
    case = load_sba_demo_cases()[0]
    packet = run_pipeline(case)

    assert packet.review_policy == "sba_reviewer"


def test_same_case_can_have_different_policy_outputs() -> None:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases()}
    case = cases["AMB-001"]

    packets = {
        policy: run_pipeline(case, review_policy=policy)
        for policy in POLICY_PROFILES
    }
    risk_bands = {packet.risk.band for packet in packets.values()}

    assert len(risk_bands) > 1
    assert packets["bank_underwriter"].risk.band == "HIGH"
    assert packets["sba_reviewer"].risk.band == "MEDIUM"
    assert packets["cdfi_lender"].risk.band == "LOW"


def test_graph_state_records_review_policy() -> None:
    case = load_sba_demo_cases()[0]
    state = run_pipeline_with_state(case, review_policy="cdfi_lender")

    assert state["review_policy"] == "cdfi_lender"
    assert state["review_packet"] is not None
    assert state["review_packet"].review_policy == "cdfi_lender"
