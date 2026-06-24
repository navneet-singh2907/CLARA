"""LLM client robustness tests."""

from loan_pipeline.llm.client import _coerce_confidence


def test_coerce_confidence_accepts_numeric_and_labels() -> None:
    assert _coerce_confidence(0.87, default=0.8) == 0.87
    assert _coerce_confidence("medium", default=0.8) == 0.75
    assert _coerce_confidence("high", default=0.8) == 0.9
    assert _coerce_confidence("92", default=0.8) == 0.92
    assert _coerce_confidence("not sure", default=0.8) == 0.8
