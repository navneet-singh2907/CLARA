"""Streamlit dashboard helper tests."""

from loan_pipeline.ui.app import ablation_chart_data, money, pct


def test_dashboard_formatters() -> None:
    assert pct(0.9533) == "95.33%"
    assert money(185000) == "$185,000"


def test_ablation_chart_data_uses_demo_labels() -> None:
    rows = [
        {
            "configuration": "full_pipeline",
            "term_extraction_accuracy": 1.0,
            "compliance_status_accuracy": 1.0,
            "risk_band_accuracy": 0.9,
            "escalation_accuracy": 1.0,
            "final_outcome_accuracy": 1.0,
        }
    ]

    chart_data = ablation_chart_data(rows)

    assert chart_data.loc[0, "Configuration"] == "Full Pipeline"
    assert chart_data.loc[0, "Final Outcome"] == 1.0

