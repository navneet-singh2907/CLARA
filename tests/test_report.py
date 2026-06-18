"""Evaluation report tests."""

from pathlib import Path

from loan_pipeline.eval.report import generate_evaluation_report, write_evaluation_report
from loan_pipeline.eval.report_pdf import build_evaluation_report_pdf


def test_generate_evaluation_report_contains_required_sections() -> None:
    report = generate_evaluation_report()

    assert "# CLARA Evaluation Report" in report
    assert "## Baseline Metrics" in report
    assert "## Observability" in report
    assert "## Parallel Specialist Review Trace" in report
    assert "## Ablation Study" in report
    assert "## Failure Analysis" in report
    assert "## Confidence Calibration" in report
    assert "## Drift Detection" in report
    assert "## Agent Contradiction Analysis" in report
    assert "## Counterfactual Explanation Coverage" in report
    assert "## Human Override Governance" in report
    assert "## Reviewer Policy Mode" in report
    assert "## Local Judge Summary" in report
    assert "## Inter-Rater Agreement" in report
    assert "## Manual Spot-Check Queue" in report
    assert "## V2 Recommendations" in report


def test_write_evaluation_report_creates_markdown_file(tmp_path: Path) -> None:
    output_path = tmp_path / "evaluation_report.md"

    written_path = write_evaluation_report(output_path)

    assert written_path == output_path
    assert output_path.exists()
    assert "Ablation Study" in output_path.read_text(encoding="utf-8")


def test_build_evaluation_report_pdf_creates_pdf_bytes() -> None:
    pdf_bytes = build_evaluation_report_pdf("# Test Report\n\n## Summary\n\n- One finding\n")

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1000

