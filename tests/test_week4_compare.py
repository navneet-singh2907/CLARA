"""Week 4 baseline-vs-improved report tests."""

import copy
import json

from loan_pipeline.eval.week4_compare import (
    generate_week4_improvement_report,
    render_week4_improvement_report,
)
from loan_pipeline.eval.week4_experiment import run_week4_baseline_experiment
from loan_pipeline.eval.week4_historical_baseline import (
    build_week4_historical_baseline_artifact,
)


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


def test_historical_baseline_preserves_documented_resolved_failures(tmp_path) -> None:
    current_path = tmp_path / "current.json"
    current_report_path = tmp_path / "current.md"

    current = run_week4_baseline_experiment(
        output_path=current_path,
        report_path=current_report_path,
    )
    baseline = build_week4_historical_baseline_artifact(current)
    report = render_week4_improvement_report(baseline, current)

    failed_case_ids = {
        result["case_id"]
        for result in baseline["results"]
        if not all(result["exact_match"].values())
    }

    assert failed_case_ids == {"AMB-003", "ADV2-003", "KF-003"}
    assert baseline["summary"]["failure_counts"] == {
        "Compliance Failure": 1,
        "Orchestration Failure": 1,
        "Risk Calibration Failure": 1,
    }
    assert baseline["summary"]["accuracy"]["overall"]["final_outcome_accuracy"] == 0.98
    assert "| Resolved baseline failures | 3 | ADV2-003, AMB-003, KF-003 |" in report
