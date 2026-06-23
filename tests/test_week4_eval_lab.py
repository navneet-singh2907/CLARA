"""Week 4 CLARA Eval Lab dataset and evaluator tests."""

import json

from loan_pipeline.config import WEEK4_GOLD_SET_JSON, WEEK4_SBA_LOANS_CSV, load_sba_demo_cases
from loan_pipeline.eval.run_eval import load_gold_labels, run_eval
from loan_pipeline.eval.week4_dataset import build_week4_dataset_records, export_week4_dataset_jsonl
from loan_pipeline.eval.week4_evaluators import evaluate_case
from loan_pipeline.eval.week4_experiment import run_week4_baseline_experiment


def test_week4_dataset_has_50_cases_with_required_split() -> None:
    labels = load_gold_labels(WEEK4_GOLD_SET_JSON)
    cases = load_sba_demo_cases(WEEK4_SBA_LOANS_CSV)

    assert len(labels) == 50
    assert len(cases) == 50
    assert sum(1 for label in labels if label.tier == "clean") == 10
    assert sum(1 for label in labels if label.tier == "ambiguous") == 10
    assert sum(1 for label in labels if label.tier == "edge") == 10
    assert sum(1 for label in labels if label.tier == "known_failure") == 5
    assert sum(1 for label in labels if label.tier == "adversarial") == 15


def test_week4_langsmith_jsonl_export_shape(tmp_path) -> None:
    output_path = tmp_path / "week4_dataset.jsonl"

    exported = export_week4_dataset_jsonl(output_path)
    rows = [json.loads(line) for line in exported.read_text(encoding="utf-8").splitlines()]

    assert exported == output_path
    assert len(rows) == 50
    assert rows[0]["inputs"]["review_policy"] == "sba_reviewer"
    assert "expected_outcome" in rows[0]["outputs"]
    assert rows[0]["metadata"]["scenario_type"] == "happy_path"


def test_week4_records_are_langsmith_ready() -> None:
    records = build_week4_dataset_records()

    assert len(records) == 50
    assert all({"inputs", "outputs", "metadata"}.issubset(record) for record in records)
    assert any(record["metadata"]["scenario_type"] == "known_failure" for record in records)


def test_week4_eval_summary_includes_new_tiers() -> None:
    result = run_eval(gold_path=WEEK4_GOLD_SET_JSON, cases_path=WEEK4_SBA_LOANS_CSV)

    assert result["summary"]["overall"]["cases"] == 50
    assert result["summary"]["by_tier"]["edge"]["cases"] == 10
    assert result["summary"]["by_tier"]["known_failure"]["cases"] == 5


def test_week4_trajectory_evaluator_checks_graph_path() -> None:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases(WEEK4_SBA_LOANS_CSV)}
    labels = {label.case_id: label for label in load_gold_labels(WEEK4_GOLD_SET_JSON)}

    result = evaluate_case(cases["EDGE-001"], labels["EDGE-001"])

    assert result["trajectory"]["trajectory_correct"] is True
    assert result["trajectory"]["parallel_specialist_review_seen"] is True
    assert result["trust_risk"]["should_not_auto_approve"] is True


def test_week4_baseline_experiment_writes_local_artifacts(tmp_path) -> None:
    output_path = tmp_path / "baseline.json"
    report_path = tmp_path / "baseline.md"

    artifact = run_week4_baseline_experiment(output_path=output_path, report_path=report_path)

    assert output_path.exists()
    assert report_path.exists()
    assert artifact["experiment"]["case_count"] == 50
    assert artifact["summary"]["accuracy"]["overall"]["cases"] == 50
    assert "trajectory_correct_rate" in artifact["summary"]
    assert "CLARA Week 4 Baseline Evaluation" in report_path.read_text(encoding="utf-8")
