"""Week 4 report generator tests."""

import json

from loan_pipeline.eval.week4_experiment import run_week4_baseline_experiment
from loan_pipeline.eval.week4_report import generate_week4_baseline_report


def test_week4_report_generator_writes_submission_markdown(tmp_path) -> None:
    baseline_path = tmp_path / "baseline.json"
    baseline_report_path = tmp_path / "baseline_raw.md"
    output_path = tmp_path / "week4_report.md"
    artifact = run_week4_baseline_experiment(
        output_path=baseline_path,
        report_path=baseline_report_path,
    )
    baseline_path.write_text(json.dumps(artifact), encoding="utf-8")

    generated = generate_week4_baseline_report(
        baseline_path=baseline_path,
        output_path=output_path,
    )
    report = generated.read_text(encoding="utf-8")

    assert generated == output_path
    assert "CLARA Week 4 Baseline Evaluation Report" in report
    assert "Failure Analysis" in report
    assert "Recommended Improvement Target" in report
    assert "LangSmith dataset ID" in report
