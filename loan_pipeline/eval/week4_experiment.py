"""Week 4 CLARA baseline experiment runner."""

import json
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Any

from loan_pipeline.config import (
    WEEK4_GOLD_SET_JSON,
    WEEK4_SBA_LOANS_CSV,
    load_sba_demo_cases,
    offline_evaluation_context,
)
from loan_pipeline.eval.metrics import summarize_scores
from loan_pipeline.eval.run_eval import categorize_failure, load_gold_labels
from loan_pipeline.eval.week4_evaluators import evaluate_case

DEFAULT_EXPERIMENT_DIR = Path("output") / "week4"
DEFAULT_BASELINE_PATH = DEFAULT_EXPERIMENT_DIR / "clara_week4_baseline.json"
DEFAULT_MARKDOWN_PATH = DEFAULT_EXPERIMENT_DIR / "clara_week4_baseline_report.md"


def run_week4_baseline_experiment(
    output_path: Path = DEFAULT_BASELINE_PATH,
    report_path: Path = DEFAULT_MARKDOWN_PATH,
    use_live_runtime: bool = False,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    """Run CLARA across the 50-case Week 4 set and write local artifacts."""
    if not use_live_runtime:
        with offline_evaluation_context():
            return _run_week4_baseline_experiment(
                output_path,
                report_path,
                use_live_runtime,
                progress_callback,
            )

    return _run_week4_baseline_experiment(
        output_path,
        report_path,
        use_live_runtime,
        progress_callback,
    )


def _run_week4_baseline_experiment(
    output_path: Path,
    report_path: Path,
    use_live_runtime: bool,
    progress_callback: Callable[[int, int, str], None] | None,
) -> dict[str, Any]:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases(WEEK4_SBA_LOANS_CSV)}
    labels = load_gold_labels(WEEK4_GOLD_SET_JSON)

    results = []
    latencies_ms = []
    total_cases = len(labels)
    for index, label in enumerate(labels, start=1):
        if progress_callback:
            progress_callback(index - 1, total_cases, label.case_id)
        loan_case = cases[label.case_id]
        started_at = perf_counter()
        result = evaluate_case(loan_case, label)
        latency_ms = round((perf_counter() - started_at) * 1000, 3)
        result["latency_ms"] = latency_ms
        result["gold"] = asdict(label)
        results.append(result)
        latencies_ms.append(latency_ms)
        _write_partial_results(output_path, results, total_cases, use_live_runtime)

    artifact = {
        "experiment": {
            "name": "CLARA Week 4 Baseline",
            "created_at": datetime.now(UTC).isoformat(),
            "dataset": "CLARA Week 4 Loan Review Eval",
            "case_count": len(results),
            "runtime": "live_llm" if use_live_runtime else "offline_reproducible",
            "description": (
                "Baseline CLARA run on the 50-case Week 4 golden dataset before "
                "targeted improvements."
            ),
        },
        "summary": _summarize_experiment(results, latencies_ms),
        "results": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    report_path.write_text(render_week4_baseline_markdown(artifact), encoding="utf-8")
    if progress_callback:
        progress_callback(total_cases, total_cases, "complete")
    return artifact


def _write_partial_results(
    output_path: Path,
    results: list[dict[str, Any]],
    total_cases: int,
    use_live_runtime: bool,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    partial_path = output_path.with_suffix(".partial.json")
    partial_payload = {
        "experiment": {
            "name": "CLARA Week 4 Baseline",
            "runtime": "live_llm" if use_live_runtime else "offline_reproducible",
            "completed_cases": len(results),
            "total_cases": total_cases,
            "updated_at": datetime.now(UTC).isoformat(),
        },
        "results": results,
    }
    partial_path.write_text(json.dumps(partial_payload, indent=2), encoding="utf-8")


def _summarize_experiment(
    results: list[dict[str, Any]],
    latencies_ms: list[float],
) -> dict[str, Any]:
    exact_scores = [_score_from_result(result) for result in results]
    failure_counts: Counter[str] = Counter()
    trust_flags: Counter[str] = Counter()
    trajectory_correct = 0

    for result, score in zip(results, exact_scores, strict=True):
        if result["trajectory"]["trajectory_correct"]:
            trajectory_correct += 1
        for flag in result["trust_risk"]["flags"]:
            trust_flags[flag] += 1
        if not all(
            [
                score.term_extraction_correct,
                score.compliance_correct,
                score.risk_correct,
                score.escalation_correct,
                score.outcome_correct,
            ]
        ):
            failure_counts[categorize_failure(score)] += 1

    return {
        "accuracy": summarize_scores(exact_scores),
        "trajectory_correct_rate": _rate(trajectory_correct, len(results)),
        "trust_risk_flag_counts": dict(trust_flags),
        "failure_counts": dict(failure_counts),
        "latency_ms": {
            "p50": round(median(latencies_ms), 3) if latencies_ms else 0.0,
            "p95": _percentile(latencies_ms, 95),
            "max": round(max(latencies_ms), 3) if latencies_ms else 0.0,
        },
    }


def _score_from_result(result: dict[str, Any]):
    from loan_pipeline.eval.metrics import CaseScore

    exact = result["exact_match"]
    return CaseScore(
        case_id=result["case_id"],
        tier=result["tier"],
        term_extraction_correct=exact["term_extraction_correct"],
        compliance_correct=exact["compliance_correct"],
        risk_correct=exact["risk_correct"],
        escalation_correct=exact["escalation_correct"],
        outcome_correct=exact["outcome_correct"],
    )


def render_week4_baseline_markdown(artifact: dict[str, Any]) -> str:
    summary = artifact["summary"]
    accuracy = summary["accuracy"]
    lines = [
        "# CLARA Week 4 Baseline Evaluation",
        "",
        f"Dataset: {artifact['experiment']['dataset']}",
        f"Cases: {artifact['experiment']['case_count']}",
        f"Created: {artifact['experiment']['created_at']}",
        "",
        "## Overall Accuracy",
        "",
        _metric_line("Term extraction", accuracy["overall"]["term_extraction_accuracy"]),
        _metric_line("Compliance status", accuracy["overall"]["compliance_status_accuracy"]),
        _metric_line("Risk band", accuracy["overall"]["risk_band_accuracy"]),
        _metric_line("Escalation", accuracy["overall"]["escalation_accuracy"]),
        _metric_line("Final outcome", accuracy["overall"]["final_outcome_accuracy"]),
        "",
        "## Accuracy By Scenario Type",
        "",
        "| Scenario | Cases | Final outcome | Compliance | Risk |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for tier, tier_summary in accuracy["by_tier"].items():
        lines.append(
            "| "
            f"{tier} | "
            f"{tier_summary['cases']} | "
            f"{tier_summary['final_outcome_accuracy']:.2%} | "
            f"{tier_summary['compliance_status_accuracy']:.2%} | "
            f"{tier_summary['risk_band_accuracy']:.2%} |"
        )

    lines.extend(
        [
            "",
            "## Trajectory And Trust Signals",
            "",
            f"- Trajectory correct rate: {summary['trajectory_correct_rate']:.2%}",
            f"- Trust risk flags: {summary['trust_risk_flag_counts'] or 'none'}",
            f"- Failure clusters: {summary['failure_counts'] or 'none'}",
            "",
            "## Latency",
            "",
            f"- p50: {summary['latency_ms']['p50']} ms",
            f"- p95: {summary['latency_ms']['p95']} ms",
            f"- max: {summary['latency_ms']['max']} ms",
        ]
    )
    return "\n".join(lines) + "\n"


def log_week4_experiment_to_langsmith(
    artifact: dict[str, Any],
    project_name: str = "CLARA Week 4 Eval Lab",
    run_name: str = "CLARA Week 4 Baseline",
) -> str:
    """Create a LangSmith experiment summary run when credentials are configured."""
    try:
        from langsmith import Client
    except ImportError as exc:
        raise RuntimeError("Install langsmith to log the Week 4 experiment.") from exc

    client = Client()
    client.create_run(
        name=run_name,
        inputs={"dataset": artifact["experiment"]["dataset"]},
        outputs=artifact["summary"],
        run_type="chain",
        project_name=project_name,
        tags=["clara", "week4", "baseline", "eval"],
        extra={
            "metadata": {
                "case_count": artifact["experiment"]["case_count"],
                "created_at": artifact["experiment"]["created_at"],
            }
        },
    )
    return project_name


def _metric_line(label: str, value: float) -> str:
    return f"- {label}: {value:.2%}"


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)


def _percentile(values: list[float], percentile: int) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = round((percentile / 100) * (len(sorted_values) - 1))
    return round(sorted_values[index], 3)
