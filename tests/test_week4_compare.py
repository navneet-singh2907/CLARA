"""Week 4 baseline-vs-improved report tests."""

import copy
import json

from loan_pipeline.eval.week4_compare import generate_week4_improvement_report
from loan_pipeline.eval.week4_experiment import run_week4_baseline_experiment


def test_week4_improvement_report_writes_delta_table(tmp_path) -> None:
    baseline_path = tmp_path / "baseline.json"
    improved_path = tmp_path / "improved.json"
    output_path = tmp_path / "delta.md"
    baseline_report_path = tmp_path / "baseline.md"

    baseline = run_week4_baseline_experiment(
        output_path=baseline_path,
        report_path=baseline_report_path,
    )
    improved = copy.deepcopy(baseline)
    improved["summary"]["accuracy"]["overall"]["risk_band_accuracy"] = 1.0
    improved["summary"]["failure_counts"] = {}
    improved["summary"]["latency_ms"]["p50"] = (
        baseline["summary"]["latency_ms"]["p50"] - 250
    )

    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    improved_path.write_text(json.dumps(improved), encoding="utf-8")

    generated = generate_week4_improvement_report(
        baseline_path=baseline_path,
        improved_path=improved_path,
        output_path=output_path,
    )
    report = generated.read_text(encoding="utf-8")

    assert generated == output_path
    assert "CLARA Week 4 Improvement Delta Report" in report
    assert "Delta Table" in report
    assert "Risk band accuracy" in report
    assert "Failure Movement" in report
