"""Counterfactual explanation tests."""

from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.graph.orchestrator import run_pipeline
from loan_pipeline.review.counterfactuals import generate_counterfactuals


def test_counterfactuals_identify_missing_documents() -> None:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases()}
    packet = run_pipeline(cases["AMB-002"])

    titles = {counterfactual.title for counterfactual in packet.counterfactuals}

    assert "Supply missing required documents." in titles
    assert "Provide borrower credit evidence." in titles


def test_counterfactuals_identify_prior_default_and_low_credit() -> None:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases()}
    packet = run_pipeline(cases["ADV-001"])

    titles = {counterfactual.title for counterfactual in packet.counterfactuals}

    assert "Improve borrower credit score." in titles
    assert "Resolve prior default concern." in titles


def test_generate_counterfactuals_returns_empty_for_clean_case() -> None:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases()}
    packet = run_pipeline(cases["CLEAN-001"])

    counterfactuals = generate_counterfactuals(
        packet.extracted_terms,
        packet.compliance,
        packet.risk,
    )

    assert counterfactuals == []

