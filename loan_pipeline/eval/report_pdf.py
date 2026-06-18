"""PDF rendering for the evaluation report."""

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from loan_pipeline.eval.report import generate_evaluation_report


def build_evaluation_report_pdf(report_text: str | None = None) -> bytes:
    text = report_text or generate_evaluation_report()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch,
        title="CLARA Evaluation Report",
    )

    styles = _styles()
    story: list[Any] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue

        if line.startswith("# "):
            if story:
                story.append(PageBreak())
            story.append(Paragraph(_clean(line[2:]), styles["Title"]))
            story.append(Spacer(1, 0.16 * inch))
            index += 1
            continue

        if line.startswith("## "):
            if story:
                story.append(Spacer(1, 0.12 * inch))
            story.append(Paragraph(_clean(line[3:]), styles["Heading2"]))
            index += 1
            continue

        if line.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            table = _markdown_table(table_lines)
            if table is not None:
                story.append(table)
                story.append(Spacer(1, 0.10 * inch))
            continue

        if line.startswith("- "):
            story.append(Paragraph(f"- {_clean(line[2:])}", styles["Bullet"]))
            index += 1
            continue

        story.append(Paragraph(_clean(line), styles["Body"]))
        index += 1

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def _markdown_table(lines: list[str]) -> Table | None:
    rows = [
        [cell.strip() for cell in line.strip("|").split("|")]
        for line in lines
        if not set(line.replace("|", "").strip()) <= {"-", ":"}
    ]
    if not rows:
        return None

    paragraph_rows = [
        [_cell(value, bold=row_index == 0) for value in row]
        for row_index, row in enumerate(rows)
    ]
    table = Table(paragraph_rows, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2f7")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c9d1dc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "EvaluationReportTitle",
            parent=sample["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#111827"),
            spaceAfter=8,
        ),
        "Heading2": ParagraphStyle(
            "EvaluationReportHeading2",
            parent=sample["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#1f2937"),
            spaceBefore=10,
            spaceAfter=6,
        ),
        "Body": ParagraphStyle(
            "EvaluationReportBody",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=8.7,
            leading=11.5,
            textColor=colors.HexColor("#374151"),
            spaceAfter=5,
        ),
        "Bullet": ParagraphStyle(
            "EvaluationReportBullet",
            parent=sample["BodyText"],
            fontName="Helvetica",
            fontSize=8.7,
            leading=11.5,
            leftIndent=10,
            textColor=colors.HexColor("#374151"),
            spaceAfter=4,
        ),
    }


def _cell(value: Any, bold: bool = False) -> Paragraph:
    style = ParagraphStyle(
        "EvaluationReportTableCell",
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=6.9,
        leading=8.4,
        textColor=colors.HexColor("#111827"),
    )
    return Paragraph(_clean(str(value)), style)


def _clean(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("`", "")
        .replace("**", "")
    )


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawString(0.55 * inch, 0.35 * inch, "Generated by CLARA")
    canvas.drawRightString(7.95 * inch, 0.35 * inch, f"Page {doc.page}")
    canvas.restoreState()
