"""Week 4 baseline-vs-improved comparison report generation."""

import json
from pathlib import Path
from typing import Any

from loan_pipeline.eval.failure_attribution import primary_attribution
from loan_pipeline.eval.week4_historical_baseline import (
    DEFAULT_HISTORICAL_BASELINE_PATH,
    load_or_create_week4_historical_baseline,
)

DEFAULT_IMPROVED_PATH = Path("output") / "week4" / "clara_week4_improved.json"
DEFAULT_IMPROVEMENT_REPORT_PATH = Path("docs") / "week4_improvement_report.md"


def generate_week4_improvement_report(
    baseline_path: Path = DEFAULT_HISTORICAL_BASELINE_PATH,
    improved_path: Path = DEFAULT_IMPROVED_PATH,
    output_path: Path = DEFAULT_IMPROVEMENT_REPORT_PATH,
) -> Path:
    """Write a markdown delta report comparing two Week 4 experiment artifacts."""
    baseline = _load_artifact(baseline_path, "baseline")
    improved = _load_artifact(improved_path, "improved")
    report = render_week4_improvement_report(baseline, improved)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return output_path


def render_week4_improvement_report(
    baseline: dict[str, Any],
    improved: dict[str, Any],
) -> str:
    metric_rows = _metric_rows(baseline, improved)
    failure_delta = _failure_delta(baseline, improved)

    lines = [
        "# CLARA Week 4 Improvement Delta Report",
        "",
        "## What Changed",
        "",
        (
            "This report compares a Week 4 baseline run against a targeted improved run "
            "on the same 50-case golden dataset. The purpose is to show one measured "
            "engineering change at a time, not to claim a vague overall improvement."
        ),
        "",
        "## Hypothesis",
        "",
        (
            "If CLARA separates missing-document compliance blockers from credit-risk "
            "repayment severity more explicitly, then risk/compliance calibration should "
            "improve on adversarial and known-failure cases without weakening escalation."
        ),
        "",
        "## Delta Table",
        "",
        "| Metric | Baseline | Improved | Delta | Direction |",
        "| --- | ---: | ---: | ---: | --- |",
    ]

    for row in metric_rows:
        lines.append(
            "| "
            f"{row['label']} | "
            f"{row['baseline']} | "
            f"{row['improved']} | "
            f"{row['delta']} | "
            f"{row['direction']} |"
        )

    lines.extend(
        [
            "",
            "## Failure Movement",
            "",
            "| Bucket | Count | Cases |",
            "| --- | ---: | --- |",
            f"| Resolved baseline failures | {len(failure_delta['resolved'])} | {_case_list(failure_delta['resolved'])} |",
            f"| New failures introduced | {len(failure_delta['introduced'])} | {_case_list(failure_delta['introduced'])} |",
            f"| Persisting failures | {len(failure_delta['persisting'])} | {_case_list(failure_delta['persisting'])} |",
            "",
            "## Resolved Failure Attribution",
            "",
            "| Case | Original responsible agent | Failure mode | Expected | Actual |",
            "| --- | --- | --- | --- | --- |",
        ]
    )

    for row in _resolved_failure_rows(baseline, failure_delta["resolved"]):
        lines.append(
            "| "
            f"{row['case_id']} | "
            f"{row['responsible_agent']} | "
            f"{row['failure_mode']} | "
            f"{row['expected']} | "
            f"{row['actual']} |"
        )

    lines.extend(
        [
            "",
            "## Failure Clusters",
            "",
            "| Cluster | Baseline | Improved | Delta |",
            "| --- | ---: | ---: | ---: |",
        ]
    )

    for cluster in sorted(
        set(baseline["summary"]["failure_counts"]) | set(improved["summary"]["failure_counts"])
    ):
        before = baseline["summary"]["failure_counts"].get(cluster, 0)
        after = improved["summary"]["failure_counts"].get(cluster, 0)
        lines.append(f"| {cluster} | {before} | {after} | {after - before:+d} |")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            _interpret_metric_rows(metric_rows),
            "",
            "## Reproducibility",
            "",
            "Run the same workflow after each targeted change:",
            "",
            "```powershell",
            ".\\.venv\\Scripts\\python.exe scripts\\week4_run_baseline.py --live --log-langsmith --output-path output\\week4\\clara_week4_improved.json --report-path output\\week4\\clara_week4_improved_report.md --langsmith-run-name \"CLARA Week 4 Improved - Risk Calibration\"",
            ".\\.venv\\Scripts\\python.exe scripts\\week4_compare_runs.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _load_artifact(path: Path, label: str) -> dict[str, Any]:
    if label == "baseline" and path == DEFAULT_HISTORICAL_BASELINE_PATH and not path.exists():
        return load_or_create_week4_historical_baseline(source_path=DEFAULT_IMPROVED_PATH)
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {label} artifact at {path}. Run the Week 4 experiment first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_rows(
    baseline: dict[str, Any],
    improved: dict[str, Any],
) -> list[dict[str, str]]:
    metrics = [
        ("Final outcome accuracy", ("accuracy", "overall", "final_outcome_accuracy"), True),
        ("Compliance accuracy", ("accuracy", "overall", "compliance_status_accuracy"), True),
        ("Risk band accuracy", ("accuracy", "overall", "risk_band_accuracy"), True),
        ("Escalation accuracy", ("accuracy", "overall", "escalation_accuracy"), True),
        ("Trajectory correctness", ("trajectory_correct_rate",), True),
        (
            "Known-failure risk accuracy",
            ("accuracy", "by_tier", "known_failure", "risk_band_accuracy"),
            True,
        ),
        (
            "Adversarial compliance accuracy",
            ("accuracy", "by_tier", "adversarial", "compliance_status_accuracy"),
            True,
        ),
        ("Total failures", ("failure_total",), False),
        ("p50 latency", ("latency_ms", "p50"), False),
    ]

    rows = []
    for label, path, higher_is_better in metrics:
        before = _metric_value(baseline["summary"], path)
        after = _metric_value(improved["summary"], path)
        rows.append(_metric_row(label, before, after, higher_is_better, path[-1]))
    return rows


def _metric_value(summary: dict[str, Any], path: tuple[str, ...]) -> float:
    if path == ("failure_total",):
        return float(sum(summary["failure_counts"].values()))
    current: Any = summary
    for key in path:
        current = current[key]
    return float(current)


def _metric_row(
    label: str,
    before: float,
    after: float,
    higher_is_better: bool,
    metric_key: str,
) -> dict[str, str]:
    diff = after - before
    if metric_key == "p50":
        direction = _direction(diff, higher_is_better)
        return {
            "label": label,
            "baseline": _seconds(before),
            "improved": _seconds(after),
            "delta": _seconds_delta(diff),
            "direction": direction,
        }

    if label == "Total failures":
        direction = _direction(diff, higher_is_better)
        return {
            "label": label,
            "baseline": str(round(before)),
            "improved": str(round(after)),
            "delta": f"{diff:+.0f}",
            "direction": direction,
        }

    direction = _direction(diff, higher_is_better)
    return {
        "label": label,
        "baseline": _pct(before),
        "improved": _pct(after),
        "delta": f"{diff * 100:+.2f} pp",
        "direction": direction,
    }


def _direction(diff: float, higher_is_better: bool) -> str:
    if abs(diff) < 0.000001:
        return "unchanged"
    helped = diff > 0 if higher_is_better else diff < 0
    return "improved" if helped else "regressed"


def _failure_delta(
    baseline: dict[str, Any],
    improved: dict[str, Any],
) -> dict[str, list[str]]:
    before = _failed_case_ids(baseline["results"])
    after = _failed_case_ids(improved["results"])
    return {
        "resolved": sorted(before - after),
        "introduced": sorted(after - before),
        "persisting": sorted(before & after),
    }


def _resolved_failure_rows(
    baseline: dict[str, Any],
    resolved_case_ids: list[str],
) -> list[dict[str, str]]:
    resolved = set(resolved_case_ids)
    rows = []
    for result in baseline["results"]:
        if result["case_id"] not in resolved:
            continue
        attribution = primary_attribution(result)
        rows.append(
            {
                "case_id": result["case_id"],
                "responsible_agent": attribution["responsible_agent"],
                "failure_mode": attribution["failure_mode"],
                "expected": attribution["expected"],
                "actual": attribution["actual"],
            }
        )
    return rows


def _failed_case_ids(results: list[dict[str, Any]]) -> set[str]:
    return {
        result["case_id"]
        for result in results
        if not all(result["exact_match"].values())
    }


def _interpret_metric_rows(rows: list[dict[str, str]]) -> str:
    improved = [row["label"] for row in rows if row["direction"] == "improved"]
    regressed = [row["label"] for row in rows if row["direction"] == "regressed"]
    if improved and not regressed:
        return f"The targeted change improved {', '.join(improved)} with no tracked regressions."
    if improved and regressed:
        return (
            f"The targeted change improved {', '.join(improved)}, but regressed "
            f"{', '.join(regressed)}. This should be treated as a trade-off, not a clean win."
        )
    if regressed:
        return f"The targeted change regressed {', '.join(regressed)} and should be revised."
    return "The targeted change did not move the tracked metrics."


def _case_list(case_ids: list[str]) -> str:
    return ", ".join(case_ids) if case_ids else "none"


def _pct(value: float) -> str:
    return f"{value:.2%}"


def _seconds(ms: float) -> str:
    return f"{ms / 1000:.2f}s"


def _seconds_delta(ms: float) -> str:
    return f"{ms / 1000:+.2f}s"
