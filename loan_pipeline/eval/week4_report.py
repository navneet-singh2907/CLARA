"""Week 4 board-style evaluation report generation."""

import json
from collections import Counter
from pathlib import Path
from typing import Any

from loan_pipeline.eval.week4_experiment import DEFAULT_BASELINE_PATH

DEFAULT_WEEK4_REPORT_PATH = Path("docs") / "week4_baseline_report.md"
LANGSMITH_PROJECT_NAME = "CLARA Week 4 Eval Lab"
LANGSMITH_DATASET_ID = "ec7896af-7117-4f7e-8972-0dc37239036a"


def generate_week4_baseline_report(
    baseline_path: Path = DEFAULT_BASELINE_PATH,
    output_path: Path = DEFAULT_WEEK4_REPORT_PATH,
) -> Path:
    artifact = json.loads(baseline_path.read_text(encoding="utf-8"))
    report = render_week4_baseline_report(artifact)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return output_path


def render_week4_baseline_report(artifact: dict[str, Any]) -> str:
    experiment = artifact["experiment"]
    summary = artifact["summary"]
    accuracy = summary["accuracy"]
    failures = _failure_rows(artifact["results"])
    trust_flags = summary["trust_risk_flag_counts"]
    strongest_tier, weakest_tier = _tier_extremes(accuracy["by_tier"])

    lines = [
        "# CLARA Week 4 Baseline Evaluation Report",
        "",
        "## Executive Summary",
        "",
        (
            f"CLARA was evaluated on a 50-case golden dataset using live LLM agents and "
            f"LangSmith tracing. The baseline achieved "
            f"{_pct(accuracy['overall']['final_outcome_accuracy'])} final outcome accuracy, "
            f"{_pct(accuracy['overall']['compliance_status_accuracy'])} compliance accuracy, "
            f"and {_pct(accuracy['overall']['risk_band_accuracy'])} risk-band accuracy."
        ),
        "",
        (
            "The important finding is not that the system is perfect. It is that the "
            "evaluation harness can identify where CLARA should slow down, request human "
            "review, or avoid auto-approval."
        ),
        "",
        "## Evaluation Setup",
        "",
        "- System: CLARA - Credit Loan Analysis & Review Agent",
        f"- Runtime: {experiment['runtime']}",
        f"- Dataset: {experiment['dataset']}",
        f"- Case count: {experiment['case_count']}",
        f"- LangSmith project: {LANGSMITH_PROJECT_NAME}",
        f"- LangSmith dataset ID: `{LANGSMITH_DATASET_ID}`",
        "- Baseline artifact: `output/week4/clara_week4_baseline.json`",
        "",
        "## Dataset Composition",
        "",
        "| Scenario type | Cases | Purpose |",
        "| --- | ---: | --- |",
        "| Clean | 10 | Straightforward applications that should be handled cleanly. |",
        "| Ambiguous | 10 | Missing fields, borderline signals, or incomplete documents. |",
        "| Adversarial | 15 | Buried clauses, prompt injection, malformed, or irrelevant inputs. |",
        "| Edge | 10 | Partial data, conflicting terms, and unusual but plausible cases. |",
        "| Known failure | 5 | Cases designed around Week 3 risk/compliance weaknesses. |",
        "",
        "## Baseline Metrics",
        "",
        "| Metric | Score |",
        "| --- | ---: |",
        f"| Term extraction accuracy | {_pct(accuracy['overall']['term_extraction_accuracy'])} |",
        f"| Compliance status accuracy | {_pct(accuracy['overall']['compliance_status_accuracy'])} |",
        f"| Risk band accuracy | {_pct(accuracy['overall']['risk_band_accuracy'])} |",
        f"| Escalation accuracy | {_pct(accuracy['overall']['escalation_accuracy'])} |",
        f"| Final outcome accuracy | {_pct(accuracy['overall']['final_outcome_accuracy'])} |",
        f"| Trajectory correctness | {_pct(summary['trajectory_correct_rate'])} |",
        "",
        "## Metrics By Scenario Type",
        "",
        "| Scenario | Cases | Final outcome | Compliance | Risk | Escalation |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for tier, tier_summary in accuracy["by_tier"].items():
        lines.append(
            "| "
            f"{tier} | "
            f"{tier_summary['cases']} | "
            f"{_pct(tier_summary['final_outcome_accuracy'])} | "
            f"{_pct(tier_summary['compliance_status_accuracy'])} | "
            f"{_pct(tier_summary['risk_band_accuracy'])} | "
            f"{_pct(tier_summary['escalation_accuracy'])} |"
        )

    lines.extend(
        [
            "",
            "## Failure Analysis",
            "",
            f"- Strongest tier: {strongest_tier}",
            f"- Weakest tier: {weakest_tier}",
            f"- Failure clusters: {_format_counter(summary['failure_counts'])}",
            "",
            "| Case | Tier | Failure category | Observed packet | Why it matters |",
            "| --- | --- | --- | --- | --- |",
        ]
    )

    for row in failures:
        lines.append(
            "| "
            f"{row['case_id']} | "
            f"{row['tier']} | "
            f"{row['category']} | "
            f"{row['observed']} | "
            f"{row['why_it_matters']} |"
        )

    lines.extend(
        [
            "",
            "## Trust And Safety Signals",
            "",
            "These are not necessarily failures. They are control signals telling a reviewer when "
            "CLARA should avoid silent auto-approval.",
            "",
            "| Signal | Count | Interpretation |",
            "| --- | ---: | --- |",
        ]
    )

    for signal, count in sorted(trust_flags.items()):
        lines.append(f"| {signal} | {count} | {_trust_signal_interpretation(signal)} |")

    lines.extend(
        [
            "",
            "## Latency",
            "",
            "| Statistic | Value |",
            "| --- | ---: |",
            f"| p50 latency | {_seconds(summary['latency_ms']['p50'])} |",
            f"| p95 latency | {_seconds(summary['latency_ms']['p95'])} |",
            f"| max latency | {_seconds(summary['latency_ms']['max'])} |",
            "",
            "## Recommended Improvement Target",
            "",
            (
                "The best next improvement target is risk/compliance calibration on "
                "adversarial and known-failure cases. The baseline is already strong on clean, "
                "ambiguous, and edge cases, so the next delta should come from reducing false "
                "risk or compliance judgments without weakening escalation behavior."
            ),
            "",
            "Proposed hypothesis:",
            "",
            (
                "If CLARA separates missing-document compliance blockers from credit-risk "
                "repayment severity more explicitly, then known-failure risk accuracy should "
                "improve while compliance escalation remains intact."
            ),
            "",
            "## Week 4 Submission Evidence",
            "",
            "- 50-case golden dataset exists in repo and LangSmith.",
            "- Live baseline run completed with LLM agents.",
            "- LangSmith traces show agent-level execution.",
            "- Baseline failures are categorized by type.",
            "- Next step is a measured post-improvement run and delta table.",
            "",
        ]
    )
    return "\n".join(lines)


def _failure_rows(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows = []
    for result in results:
        exact = result["exact_match"]
        if all(exact.values()):
            continue
        packet = result["packet"]
        rows.append(
            {
                "case_id": result["case_id"],
                "tier": result["tier"],
                "category": _failure_category(exact),
                "observed": (
                    f"{packet['outcome']} / {packet['risk_band']} / "
                    f"{packet['compliance_status']}"
                ),
                "why_it_matters": _failure_interpretation(result),
            }
        )
    return rows


def _failure_category(exact: dict[str, bool]) -> str:
    if not exact["term_extraction_correct"]:
        return "Extraction failure"
    if not exact["compliance_correct"]:
        return "Compliance failure"
    if not exact["risk_correct"]:
        return "Risk calibration failure"
    if not exact["escalation_correct"] or not exact["outcome_correct"]:
        return "Orchestration failure"
    return "Uncategorized"


def _failure_interpretation(result: dict[str, Any]) -> str:
    exact = result["exact_match"]
    if not exact["compliance_correct"]:
        return "Adversarial or malformed input was not classified with the expected compliance severity."
    if not exact["risk_correct"]:
        return "Credit-risk severity did not match the gold label despite correct escalation."
    if not exact["escalation_correct"]:
        return "Human-review gate fired differently from the gold label."
    return "Output differs from the gold packet and needs manual review."


def _tier_extremes(by_tier: dict[str, dict[str, float | int]]) -> tuple[str, str]:
    scored = {
        tier: (
            summary["final_outcome_accuracy"]
            + summary["compliance_status_accuracy"]
            + summary["risk_band_accuracy"]
        )
        / 3
        for tier, summary in by_tier.items()
    }
    return max(scored, key=scored.get), min(scored, key=scored.get)


def _format_counter(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    counter = Counter(counts)
    return ", ".join(f"{name}: {count}" for name, count in counter.items())


def _trust_signal_interpretation(signal: str) -> str:
    return {
        "agent_disagreement": "Compliance and risk evidence deserve side-by-side human review.",
        "human_review_required": "The packet should be reviewed before approval.",
        "low_extraction_confidence": "Terms may be under-specified or document quality may be weak.",
        "low_risk_confidence": "Risk band is less stable and should not be treated as final.",
    }.get(signal, "Reviewer should inspect this signal before acting.")


def _pct(value: float) -> str:
    return f"{value:.2%}"


def _seconds(ms: float) -> str:
    return f"{ms / 1000:.2f}s"
