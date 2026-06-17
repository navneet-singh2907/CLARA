"""Human override audit log tests."""

from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.graph.orchestrator import run_pipeline
from loan_pipeline.review.audit import create_human_override
from loan_pipeline.ui.app import override_targets


def test_create_human_override_records_required_fields() -> None:
    entry = create_human_override(
        case_id="ADV-001",
        target_type="RISK",
        target_id="risk_band",
        original_value="HIGH",
        override_decision="Approve despite finding",
        rationale="Collateral and guarantor strength offset the model risk.",
        reviewer="Loan Officer A",
    )

    assert entry.case_id == "ADV-001"
    assert entry.target_type == "RISK"
    assert entry.target_id == "risk_band"
    assert entry.override_decision == "Approve despite finding"
    assert entry.rationale == "Collateral and guarantor strength offset the model risk."
    assert entry.reviewer == "Loan Officer A"
    assert entry.entry_id
    assert entry.created_at


def test_override_targets_include_outcome_risk_and_findings() -> None:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases()}
    packet = run_pipeline(cases["ADV-001"])

    targets = override_targets(packet)

    assert any(label.startswith("Outcome -") for label in targets)
    assert any(label.startswith("Risk band -") for label in targets)
    assert any(label.startswith("Compliance") for label in targets)
