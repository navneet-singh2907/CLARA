"""Confidence calibration tests."""

from loan_pipeline.eval.calibration import CalibrationPoint, summarize_confidence_calibration
from loan_pipeline.eval.run_eval import run_eval


def test_summarize_confidence_calibration_reports_ece() -> None:
    summary = summarize_confidence_calibration(
        [
            CalibrationPoint("A", "clean", 0.8, True),
            CalibrationPoint("B", "clean", 0.8, False),
            CalibrationPoint("C", "clean", 0.6, True),
        ],
        bins=((0.0, 0.7), (0.7, 0.9)),
    )

    assert summary["cases"] == 3
    assert summary["expected_calibration_error"] == 0.3333
    assert len(summary["buckets"]) == 2


def test_run_eval_includes_risk_confidence_calibration() -> None:
    result = run_eval()

    calibration = result["risk_confidence_calibration"]

    assert calibration["cases"] == 30
    assert calibration["expected_calibration_error"] >= 0
    assert calibration["buckets"]
