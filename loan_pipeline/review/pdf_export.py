"""PDF export for loan review packets."""

from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from loan_pipeline.graph.state import ReviewPacket
from loan_pipeline.review.policies import POLICY_PROFILES


def build_review_packet_pdf(packet: ReviewPacket, audit_log: list[dict[str, Any]] | None = None) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title=f"Loan Review Packet - {packet.case_id}",
    )

    styles = _styles()
    story = [
        Paragraph("CLARA Loan Review Packet", styles["Title"]),
        Paragraph(f"Case ID: {packet.case_id}", styles["Meta"]),
        Paragraph(f"Reviewer Policy: {POLICY_PROFILES[packet.review_policy].label}", styles["Meta"]),
        Spacer(1, 0.16 * inch),
        _summary_table(packet),
        Spacer(1, 0.18 * inch),
        Paragraph("Executive Summary", styles["Heading2"]),
        Paragraph(packet.summary, styles["Body"]),
        Spacer(1, 0.14 * inch),
    ]

    story.extend(_bullet_section("Human Review Notes", packet.human_review_notes, styles))
    story.extend(_terms_section(packet, styles))
    story.extend(_compliance_section(packet, styles))
    story.extend(_risk_section(packet, styles))
    story.extend(_contradiction_section(packet, styles))
    story.extend(_counterfactual_section(packet, styles))
    story.extend(_audit_section(audit_log or [asdict(entry) for entry in packet.audit_log], styles))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def write_review_packet_pdf(
    packet: ReviewPacket,
    path: Path,
    audit_log: list[dict[str, Any]] | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_review_packet_pdf(packet, audit_log=audit_log))
    return path


def _styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "PacketTitle",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1f2937"),
            spaceAfter=4,
        ),
        "Meta": ParagraphStyle(
            "PacketMeta",
            parent=sample["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#4b5563"),
        ),
        "Heading2": ParagraphStyle(
            "PacketHeading2",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#111827"),
            spaceBefore=8,
            spaceAfter=6,
        ),
        "Body": ParagraphStyle(
            "PacketBody",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#1f2937"),
        ),
        "Small": ParagraphStyle(
            "PacketSmall",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#374151"),
        ),
    }


def _summary_table(packet: ReviewPacket) -> Table:
    rows = [
        ["Recommended Outcome", packet.recommended_outcome, "Escalation", "Yes" if packet.escalation_required else "No"],
        ["Compliance", packet.compliance.status, "Risk Band", packet.risk.band],
        ["Risk Score", str(packet.risk.score), "Risk Confidence", f"{packet.risk.confidence:.2f}"],
    ]
    return _table(rows, col_widths=[1.65 * inch, 1.4 * inch, 1.3 * inch, 1.45 * inch])


def _terms_section(packet: ReviewPacket, styles: dict[str, ParagraphStyle]) -> list[Any]:
    terms = packet.extracted_terms
    rows = [
        ["Borrower", terms.borrower_name, "Industry", terms.industry],
        ["NAICS", terms.naics_code, "Loan Amount", _money(terms.loan_amount)],
        ["SBA Guarantee", _money(terms.sba_guaranteed_amount), "Guarantee Ratio", f"{terms.guarantee_ratio:.1%}"],
        ["Term", f"{terms.term_months} months", "Jobs Supported", str(terms.jobs_supported)],
        ["Credit Score", str(terms.borrower_credit_score or "Missing"), "Years in Business", str(terms.years_in_business or "Missing")],
    ]
    return [Paragraph("Extracted Terms", styles["Heading2"]), _table(rows)]


def _compliance_section(packet: ReviewPacket, styles: dict[str, ParagraphStyle]) -> list[Any]:
    story: list[Any] = [Paragraph("Compliance Findings", styles["Heading2"])]
    if not packet.compliance.findings:
        story.append(Paragraph("No compliance findings.", styles["Body"]))
        return story

    rows = [["Rule", "Severity", "Description", "Evidence"]]
    for finding in packet.compliance.findings:
        rows.append([finding.rule_id, finding.severity, finding.description, finding.evidence])
    story.append(_table(rows, header=True, col_widths=[0.8 * inch, 0.75 * inch, 2.35 * inch, 1.9 * inch]))
    return story


def _risk_section(packet: ReviewPacket, styles: dict[str, ParagraphStyle]) -> list[Any]:
    risk = packet.risk
    story = [
        Paragraph("Credit Risk Scoring", styles["Heading2"]),
        Paragraph(risk.rationale, styles["Body"]),
    ]
    story.extend(_bullet_section("Primary Risk Factors", risk.primary_risk_factors, styles))
    story.extend(_bullet_section("Mitigating Factors", risk.mitigating_factors, styles))
    return story


def _contradiction_section(packet: ReviewPacket, styles: dict[str, ParagraphStyle]) -> list[Any]:
    if not packet.contradictions:
        return [
            KeepTogether(
                [
                    Paragraph("Agent Contradictions", styles["Heading2"]),
                    Paragraph("No agent contradictions detected.", styles["Body"]),
                ]
            )
        ]

    story: list[Any] = []
    for item in packet.contradictions:
        rows = [
            ["Severity", item.severity],
            ["Issue", item.title],
            ["Compliance Position", item.compliance_position],
            ["Risk Position", item.risk_position],
            ["Reviewer Prompt", item.reviewer_prompt],
        ]
        story.append(
            KeepTogether(
                [
                    Paragraph("Agent Contradictions", styles["Heading2"]),
                    _table(rows, col_widths=[1.25 * inch, 4.55 * inch]),
                ]
            )
        )
        story.append(Spacer(1, 0.08 * inch))
    return story


def _counterfactual_section(packet: ReviewPacket, styles: dict[str, ParagraphStyle]) -> list[Any]:
    if not packet.counterfactuals:
        return [
            KeepTogether(
                [
                    Paragraph("Counterfactual Explanations", styles["Heading2"]),
                    Paragraph("No counterfactual explanations generated.", styles["Body"]),
                ]
            )
        ]

    rows = [["Type", "Current State", "Suggested Change", "Expected Effect"]]
    for item in packet.counterfactuals:
        rows.append([item.type, item.current_state, item.suggested_change, item.expected_effect])
    return [
        KeepTogether(
            [
                Paragraph("Counterfactual Explanations", styles["Heading2"]),
                _table(rows, header=True, col_widths=[0.95 * inch, 1.55 * inch, 1.65 * inch, 1.65 * inch]),
            ]
        )
    ]


def _audit_section(audit_log: list[dict[str, Any]], styles: dict[str, ParagraphStyle]) -> list[Any]:
    story: list[Any] = [PageBreak(), Paragraph("Human Override Audit Log", styles["Heading2"])]
    if not audit_log:
        story.append(Paragraph("No human override entries recorded.", styles["Body"]))
        return story

    rows = [["Target", "Decision", "Reviewer", "Rationale", "Timestamp"]]
    for entry in audit_log:
        rows.append(
            [
                f"{entry['target_type']}:{entry['target_id']}",
                entry["override_decision"],
                entry["reviewer"],
                entry["rationale"],
                entry["created_at"],
            ]
        )
    story.append(_table(rows, header=True, col_widths=[1.15 * inch, 1.15 * inch, 1.0 * inch, 1.65 * inch, 0.85 * inch]))
    return story


def _bullet_section(
    title: str,
    values: list[str],
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    story: list[Any] = [Paragraph(title, styles["Heading2"])]
    if not values:
        story.append(Paragraph("None.", styles["Body"]))
        return story

    for value in values:
        story.append(Paragraph(f"- {value}", styles["Body"]))
    return story


def _table(rows: list[list[Any]], header: bool = False, col_widths: list[float] | None = None) -> Table:
    paragraph_rows = [
        [_cell(value, bold=header and row_index == 0) for value in row]
        for row_index, row in enumerate(rows)
    ]
    table = Table(paragraph_rows, colWidths=col_widths, hAlign="LEFT", repeatRows=1 if header else 0)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6") if header else colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _cell(value: Any, bold: bool = False) -> Paragraph:
    text = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    font = "Helvetica-Bold" if bold else "Helvetica"
    style = ParagraphStyle("TableCell", fontName=font, fontSize=7.6, leading=9.5)
    return Paragraph(text, style)


def _money(value: float) -> str:
    return f"${value:,.0f}"


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawString(0.55 * inch, 0.35 * inch, "Generated by CLARA")
    canvas.drawRightString(7.95 * inch, 0.35 * inch, f"Page {doc.page}")
    canvas.restoreState()
