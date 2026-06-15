"""Inter-rater agreement tests."""

from loan_pipeline.eval.inter_rater import run_inter_rater_report


def test_inter_rater_report_scores_30_cases() -> None:
    report = run_inter_rater_report()

    assert report["cases"] == 30
    assert report["dimensions_per_case"] == 5
    assert 0 <= report["exact_agreement"] <= 1
    assert 0 <= report["within_one_point_agreement"] <= 1


def test_inter_rater_report_identifies_disagreement_cases() -> None:
    report = run_inter_rater_report()

    assert report["disagreement_case_count"] > 0
    assert report["highest_disagreement_dimension"] in {
        "faithfulness",
        "completeness",
        "risk_calibration",
        "compliance_accuracy",
        "explainability",
    }


def test_inter_rater_report_marks_manual_spot_checks() -> None:
    report = run_inter_rater_report()

    assert "manual_spot_check_cases" in report
    assert isinstance(report["manual_spot_check_cases"], list)
    assert len(report["manual_spot_check_cases"]) == report["disagreement_case_count"]
