"""Ablation study tests."""

from loan_pipeline.eval.ablation import run_ablation_study, summarize_ablation_table


def test_ablation_study_runs_expected_configurations() -> None:
    results = run_ablation_study()

    assert set(results) == {
        "full_pipeline",
        "no_compliance_checker",
        "no_risk_scorer",
        "term_extractor_only",
        "single_agent_baseline_stub",
    }


def test_full_pipeline_beats_term_extractor_only_on_outcome_accuracy() -> None:
    results = run_ablation_study()

    assert (
        results["full_pipeline"]["final_outcome_accuracy"]
        > results["term_extractor_only"]["final_outcome_accuracy"]
    )


def test_ablation_table_is_report_ready() -> None:
    table = summarize_ablation_table(run_ablation_study())

    assert len(table) == 5
    assert "configuration" in table[0]
    assert "risk_band_accuracy" in table[0]

