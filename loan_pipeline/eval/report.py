"""Generate a Markdown evaluation report."""

from pathlib import Path
from typing import Any

from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.eval.ablation import run_ablation_study, summarize_ablation_table
from loan_pipeline.eval.drift import run_drift_study
from loan_pipeline.eval.inter_rater import run_inter_rater_report
from loan_pipeline.eval.run_eval import run_eval
from loan_pipeline.graph.orchestrator import run_pipeline_with_state

REPORT_PATH = Path("reports") / "evaluation_report.md"


def generate_evaluation_report() -> str:
    eval_result = run_eval()
    ablation_rows = summarize_ablation_table(run_ablation_study())
    drift_result = run_drift_study()
    inter_rater = run_inter_rater_report()

    sections = [
        "# Small Business Loan Review Pipeline Evaluation Report",
        _executive_summary(eval_result, inter_rater),
        _baseline_metrics(eval_result),
        _observability(),
        _parallel_execution_trace(),
        _ablation_table(ablation_rows),
        _failure_analysis(eval_result),
        _confidence_calibration(eval_result),
        _drift_detection(drift_result),
        _contradiction_analysis(eval_result),
        _counterfactual_analysis(eval_result),
        _human_override_governance(),
        _reviewer_policy_mode(),
        _judge_summary(eval_result),
        _inter_rater_summary(inter_rater),
        _manual_spot_checks(inter_rater),
        _v2_recommendations(eval_result, inter_rater),
    ]
    return "\n\n".join(sections) + "\n"


def write_evaluation_report(path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_evaluation_report(), encoding="utf-8")
    return path


def _executive_summary(eval_result: dict[str, Any], inter_rater: dict[str, Any]) -> str:
    overall = eval_result["summary"]["overall"]
    return "\n".join(
        [
            "## Executive Summary",
            "",
            "This report evaluates a LangGraph-based multi-agent small business loan review pipeline across a 30-case gold set.",
            "",
            f"- Gold set size: {overall['cases']} cases",
            "- Difficulty tiers: 10 clean, 10 ambiguous, 10 adversarial",
            f"- Final outcome accuracy: {_pct(overall['final_outcome_accuracy'])}",
            f"- Risk band accuracy: {_pct(overall['risk_band_accuracy'])}",
            f"- Inter-rater exact agreement: {_pct(inter_rater['exact_agreement'])}",
            f"- Manual spot-check cases: {len(inter_rater['manual_spot_check_cases'])}",
        ]
    )


def _baseline_metrics(eval_result: dict[str, Any]) -> str:
    summary = eval_result["summary"]
    lines = [
        "## Baseline Metrics",
        "",
        "| Tier | Cases | Term Extraction | Compliance | Risk Band | Escalation | Final Outcome |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        _metric_row("Overall", summary["overall"]),
    ]
    for tier in ["clean", "ambiguous", "adversarial"]:
        lines.append(_metric_row(tier.title(), summary["by_tier"][tier]))
    return "\n".join(lines)


def _observability() -> str:
    return "\n".join(
        [
            "## Observability",
            "",
            "LangSmith tracing is supported as an optional runtime mode. Set `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, and `LANGSMITH_PROJECT=loan-review-pipeline` to emit traces for the top-level loan review run, Term Extractor, Compliance Checker, Credit Risk Scorer, and Review Synthesizer.",
            "",
            "The dashboard also includes a local LangGraph execution trace, so the demo remains inspectable even when LangSmith credentials are not configured.",
        ]
    )


def _parallel_execution_trace() -> str:
    sample_case = load_sba_demo_cases()[0]
    state = run_pipeline_with_state(sample_case)
    trace_rows = state["execution_trace"]
    parallel_nodes = [
        entry.node
        for entry in trace_rows
        if entry.parallel_group == "specialist_review"
    ]

    lines = [
        "## Parallel Specialist Review Trace",
        "",
        "The graph fans out after schema validation so independent specialists can review the same extracted terms before synthesis.",
        "",
        f"- Sample case: {sample_case.case_id}",
        "- Parallel group: specialist_review",
        f"- Parallel nodes: {', '.join(parallel_nodes)}",
        "",
        "| Node | Stage | Parallel Group | Duration ms | Status |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for entry in trace_rows:
        lines.append(
            f"| {entry.node} | {entry.stage} | {entry.parallel_group or ''} | "
            f"{entry.duration_ms:.3f} | {entry.status} |"
        )
    return "\n".join(lines)


def _ablation_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "## Ablation Study",
        "",
        "| Configuration | Cases | Extraction | Compliance | Risk | Escalation | Final Outcome |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {configuration} | {cases} | {term} | {compliance} | {risk} | {escalation} | {outcome} |".format(
                configuration=row["configuration"],
                cases=row["cases"],
                term=_pct(row["term_extraction_accuracy"]),
                compliance=_pct(row["compliance_status_accuracy"]),
                risk=_pct(row["risk_band_accuracy"]),
                escalation=_pct(row["escalation_accuracy"]),
                outcome=_pct(row["final_outcome_accuracy"]),
            )
        )
    return "\n".join(lines)


def _failure_analysis(eval_result: dict[str, Any]) -> str:
    lines = [
        "## Failure Analysis",
        "",
        "| Failure Category | Count |",
        "| --- | ---: |",
    ]
    failure_counts = eval_result["failure_counts"]
    if failure_counts:
        for category, count in failure_counts.items():
            lines.append(f"| {category} | {count} |")
    else:
        lines.append("| None | 0 |")

    lines.extend(["", "| Case ID | Tier | Failure Category |", "| --- | --- | --- |"])
    for failure in eval_result["failures"]:
        lines.append(
            f"| {failure['case_id']} | {failure['tier']} | {failure['failure_category']} |"
        )
    return "\n".join(lines)


def _confidence_calibration(eval_result: dict[str, Any]) -> str:
    calibration = eval_result["risk_confidence_calibration"]
    lines = [
        "## Confidence Calibration",
        "",
        "This section compares the Credit Risk Scorer's stated confidence against observed risk-band accuracy on the gold set.",
        "",
        f"- Expected calibration error: {_pct(calibration['expected_calibration_error'])}",
        "",
        "| Confidence Bucket | Cases | Average Confidence | Observed Accuracy | Gap | Case IDs |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for bucket in calibration["buckets"]:
        lines.append(
            "| {bucket} | {cases} | {confidence} | {accuracy} | {gap} | {case_ids} |".format(
                bucket=bucket["confidence_bucket"],
                cases=bucket["cases"],
                confidence=_pct(bucket["average_confidence"]),
                accuracy=_pct(bucket["observed_accuracy"]),
                gap=_pct(bucket["calibration_gap"]),
                case_ids=", ".join(bucket["case_ids"]),
            )
        )
    return "\n".join(lines)


def _drift_detection(drift_result: dict[str, Any]) -> str:
    tier_rows: dict[str, dict[str, int]] = {}
    for row in drift_result["rows"]:
        tier = row["tier"]
        tier_rows.setdefault(tier, {"cases": 0, "stable_cases": 0, "max_variants": 0})
        tier_rows[tier]["cases"] += 1
        tier_rows[tier]["stable_cases"] += 1 if row["stable"] else 0
        tier_rows[tier]["max_variants"] = max(tier_rows[tier]["max_variants"], row["variant_count"])

    lines = [
        "## Drift Detection",
        "",
        "Each gold-set case is run multiple times and material review outputs are fingerprinted to detect nondeterministic drift.",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Cases | {drift_result['cases']} |",
        f"| Runs per case | {drift_result['repeats']} |",
        f"| Stable cases | {drift_result['stable_cases']} |",
        f"| Drifting cases | {drift_result['drifting_cases']} |",
        f"| Stability rate | {_pct(drift_result['stability_rate'])} |",
        "",
        "| Tier | Cases | Stable Cases | Stability Rate | Max Variants |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for tier in ["clean", "ambiguous", "adversarial"]:
        tier_row = tier_rows.get(tier, {"cases": 0, "stable_cases": 0, "max_variants": 0})
        stability = tier_row["stable_cases"] / tier_row["cases"] if tier_row["cases"] else 0.0
        lines.append(
            f"| {tier.title()} | {tier_row['cases']} | {tier_row['stable_cases']} | "
            f"{_pct(stability)} | {tier_row['max_variants']} |"
        )
    return "\n".join(lines)


def _contradiction_analysis(eval_result: dict[str, Any]) -> str:
    contradiction_cases = [
        failure["case_id"]
        for failure in eval_result["failures"]
        if failure["failure_category"] == "Risk Calibration Failure"
    ]
    lines = [
        "## Agent Contradiction Analysis",
        "",
        "The orchestrator surfaces conflicts where compliance and credit-risk agents point in different decision directions.",
        "",
        "| Signal | Value |",
        "| --- | ---: |",
        f"| Risk calibration cases requiring adjudication | {len(contradiction_cases)} |",
    ]
    if contradiction_cases:
        lines.extend(["", "Demo candidates: " + ", ".join(contradiction_cases)])
    return "\n".join(lines)


def _counterfactual_analysis(eval_result: dict[str, Any]) -> str:
    failures = eval_result["failures"]
    lines = [
        "## Counterfactual Explanation Coverage",
        "",
        "Escalated and failed cases can produce actionable borrower or reviewer-facing counterfactuals such as supplying missing documents, improving credit evidence, or resolving prior default concerns.",
        "",
        "| Signal | Value |",
        "| --- | ---: |",
        f"| Evaluation failures with likely counterfactual review value | {len(failures)} |",
    ]
    if failures:
        lines.extend(["", "Counterfactual demo candidates: " + ", ".join(f["case_id"] for f in failures)])
    return "\n".join(lines)


def _human_override_governance() -> str:
    return "\n".join(
        [
            "## Human Override Governance",
            "",
            "The reviewer UI supports per-finding override audit entries. Each entry records the case, target type, target ID, original agent value, override decision, rationale, reviewer, and timestamp.",
            "",
            "| Control | Status |",
            "| --- | --- |",
            "| Per-finding target selection | Implemented |",
            "| Required human rationale | Implemented |",
            "| Reviewer identity field | Implemented |",
            "| Timestamped audit entry | Implemented |",
        ]
    )


def _reviewer_policy_mode() -> str:
    from loan_pipeline.review.policies import POLICY_PROFILES

    sample_case = next(case for case in load_sba_demo_cases() if case.case_id == "AMB-003")
    lines = [
        "## Reviewer Policy Mode",
        "",
        "The same loan application can be reviewed under different institutional policy profiles. These profiles are configurable review postures, not official legal rules.",
        "",
        f"Sample case: {sample_case.case_id}",
        "",
        "| Policy | Outcome | Compliance | Risk | Escalation |",
        "| --- | --- | --- | --- | --- |",
    ]
    for policy, profile in POLICY_PROFILES.items():
        packet = run_pipeline_with_state(sample_case, review_policy=policy)["review_packet"]
        if packet is None:
            continue
        lines.append(
            f"| {profile.label} | {packet.recommended_outcome} | {packet.compliance.status} | "
            f"{packet.risk.band} | {'Yes' if packet.escalation_required else 'No'} |"
        )
    return "\n".join(lines)


def _judge_summary(eval_result: dict[str, Any]) -> str:
    judge = eval_result["local_judge_summary"]
    lines = [
        "## Local Judge Summary",
        "",
        "| Dimension | Average Score |",
        "| --- | ---: |",
    ]
    for dimension, score in judge.items():
        lines.append(f"| {dimension} | {score:.4f} |")
    return "\n".join(lines)


def _inter_rater_summary(inter_rater: dict[str, Any]) -> str:
    return "\n".join(
        [
            "## Inter-Rater Agreement",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| Cases | {inter_rater['cases']} |",
            f"| Dimensions per case | {inter_rater['dimensions_per_case']} |",
            f"| Exact agreement | {_pct(inter_rater['exact_agreement'])} |",
            f"| Within-one-point agreement | {_pct(inter_rater['within_one_point_agreement'])} |",
            f"| Average score delta | {inter_rater['average_score_delta']:.4f} |",
            f"| Highest disagreement dimension | {inter_rater['highest_disagreement_dimension']} |",
            f"| Disagreement cases | {inter_rater['disagreement_case_count']} |",
        ]
    )


def _manual_spot_checks(inter_rater: dict[str, Any]) -> str:
    cases = inter_rater["manual_spot_check_cases"]
    if not cases:
        case_text = "None"
    else:
        case_text = ", ".join(cases)

    return "\n".join(
        [
            "## Manual Spot-Check Queue",
            "",
            "These cases should be manually reviewed because the primary and secondary judges disagreed.",
            "",
            case_text,
        ]
    )


def _v2_recommendations(eval_result: dict[str, Any], inter_rater: dict[str, Any]) -> str:
    recommendations = [
        "Add real model-backed judge providers after the local judge contract is stable.",
        "Calibrate the credit risk scorer against adversarial cases with known risk misses.",
        "Replace SBA-style seed rows with downloaded public SBA records and hand-adjudicated labels.",
    ]

    if eval_result["failure_counts"].get("Risk Calibration Failure", 0):
        recommendations.insert(0, "Prioritize v2 risk calibration for adversarial loan cases.")

    if inter_rater["manual_spot_check_cases"]:
        recommendations.append("Manually adjudicate judge disagreement cases before final submission.")

    lines = ["## V2 Recommendations", ""]
    lines.extend(f"- {recommendation}" for recommendation in recommendations)
    return "\n".join(lines)


def _metric_row(label: str, metrics: dict[str, Any]) -> str:
    return (
        f"| {label} | {metrics['cases']} | "
        f"{_pct(metrics['term_extraction_accuracy'])} | "
        f"{_pct(metrics['compliance_status_accuracy'])} | "
        f"{_pct(metrics['risk_band_accuracy'])} | "
        f"{_pct(metrics['escalation_accuracy'])} | "
        f"{_pct(metrics['final_outcome_accuracy'])} |"
    )


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%"


if __name__ == "__main__":
    print(write_evaluation_report())
