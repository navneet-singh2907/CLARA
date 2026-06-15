"""Evaluation foundation tests."""

from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.eval.run_eval import load_gold_labels, run_eval


def test_gold_set_has_30_cases_split_by_tier() -> None:
    labels = load_gold_labels()

    assert len(labels) == 30
    assert sum(1 for label in labels if label.tier == "clean") == 10
    assert sum(1 for label in labels if label.tier == "ambiguous") == 10
    assert sum(1 for label in labels if label.tier == "adversarial") == 10


def test_sba_demo_data_has_30_cases_split_by_tier() -> None:
    cases = load_sba_demo_cases()

    assert len(cases) == 30
    assert sum(1 for case in cases if case.difficulty_tier == "clean") == 10
    assert sum(1 for case in cases if case.difficulty_tier == "ambiguous") == 10
    assert sum(1 for case in cases if case.difficulty_tier == "adversarial") == 10


def test_eval_runner_scores_all_cases() -> None:
    result = run_eval()

    assert result["summary"]["overall"]["cases"] == 30
    assert result["summary"]["by_tier"]["clean"]["cases"] == 10
    assert result["summary"]["by_tier"]["ambiguous"]["cases"] == 10
    assert result["summary"]["by_tier"]["adversarial"]["cases"] == 10
    assert "failure_counts" in result
