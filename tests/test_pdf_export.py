"""PDF export tests."""

from pathlib import Path

from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.graph.orchestrator import run_pipeline
from loan_pipeline.review.pdf_export import build_review_packet_pdf, write_review_packet_pdf


def test_build_review_packet_pdf_returns_pdf_bytes() -> None:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases()}
    packet = run_pipeline(cases["ADV-001"])

    pdf_bytes = build_review_packet_pdf(
        packet,
        audit_log=[
            {
                "target_type": "RISK",
                "target_id": "risk_band",
                "override_decision": "Request additional evidence",
                "reviewer": "Loan Officer A",
                "rationale": "Need guarantor support before final decision.",
                "created_at": "2026-06-17T00:00:00+00:00",
            }
        ],
    )

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 3000


def test_write_review_packet_pdf_creates_file(tmp_path: Path) -> None:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases()}
    packet = run_pipeline(cases["AMB-002"])
    output_path = tmp_path / "packet.pdf"

    written_path = write_review_packet_pdf(packet, output_path)

    assert written_path == output_path
    assert output_path.exists()
    assert output_path.read_bytes().startswith(b"%PDF")
