"""Streamlit dashboard helper tests."""

from loan_pipeline.ui.app import money, pct


def test_dashboard_formatters() -> None:
    assert pct(0.9533) == "95.33%"
    assert money(185000) == "$185,000"

