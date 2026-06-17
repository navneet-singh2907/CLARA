"""Repeated-run drift detection tests."""

from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.eval.drift import fingerprint_review_packet, run_drift_study
from loan_pipeline.graph.orchestrator import run_pipeline


def test_packet_fingerprint_is_stable_for_same_case() -> None:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases()}

    first = fingerprint_review_packet(run_pipeline(cases["ADV-001"]))
    second = fingerprint_review_packet(run_pipeline(cases["ADV-001"]))

    assert first == second


def test_drift_study_reports_stable_deterministic_runs() -> None:
    result = run_drift_study(repeats=3, case_ids=["CLEAN-001", "AMB-002", "ADV-001"])

    assert result["cases"] == 3
    assert result["repeats"] == 3
    assert result["stable_cases"] == 3
    assert result["drifting_cases"] == 0
    assert result["stability_rate"] == 1.0
    assert all(row["variant_count"] == 1 for row in result["rows"])
