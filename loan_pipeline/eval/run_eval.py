"""Run the 30-case evaluation harness."""

import json
from pathlib import Path
from typing import Any, Callable

from loan_pipeline.config import GOLD_SET_JSON, load_sba_demo_cases
from loan_pipeline.eval.calibration import risk_calibration_points, summarize_confidence_calibration
from loan_pipeline.eval.judge import run_configured_primary_judge
from loan_pipeline.eval.metrics import GoldLabel, score_case, summarize_scores
from loan_pipeline.graph.orchestrator import run_pipeline

ProgressCallback = Callable[[int, int, str], None]


def run_eval(
    gold_path: Path = GOLD_SET_JSON,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases()}
    gold_labels = load_gold_labels(gold_path)
    total_cases = len(gold_labels)

    scores = []
    judge_scores = []
    failures = []
    failure_counts: dict[str, int] = {}
    packets_by_case = {}
    for index, label in enumerate(gold_labels, start=1):
        if progress_callback:
            progress_callback(index - 1, total_cases, label.case_id)
        loan_case = cases[label.case_id]
        packet = run_pipeline(loan_case)
        packets_by_case[label.case_id] = packet
        score = score_case(loan_case, packet, label)
        scores.append(score)
        judge_scores.append(run_configured_primary_judge(loan_case, packet, label))

        if not all(
            [
                score.term_extraction_correct,
                score.compliance_correct,
                score.risk_correct,
                score.escalation_correct,
                score.outcome_correct,
            ]
        ):
            category = categorize_failure(score)
            failure_counts[category] = failure_counts.get(category, 0) + 1
            failures.append(
                {
                    "case_id": score.case_id,
                    "tier": score.tier,
                    "failure_category": category,
                    "term_extraction_correct": score.term_extraction_correct,
                    "compliance_correct": score.compliance_correct,
                    "risk_correct": score.risk_correct,
                    "escalation_correct": score.escalation_correct,
                    "outcome_correct": score.outcome_correct,
                }
            )

    if progress_callback:
        progress_callback(total_cases, total_cases, "complete")

    return {
        "summary": summarize_scores(scores),
        "risk_confidence_calibration": summarize_confidence_calibration(
            risk_calibration_points(packets_by_case, scores)
        ),
        "local_judge_summary": summarize_judge_scores(judge_scores),
        "failure_counts": failure_counts,
        "failures": failures,
    }


def load_gold_labels(path: Path = GOLD_SET_JSON) -> list[GoldLabel]:
    with path.open(encoding="utf-8") as gold_file:
        payload = json.load(gold_file)

    labels: list[GoldLabel] = []
    for tier, cases in payload["tiers"].items():
        for case in cases:
            labels.append(
                GoldLabel(
                    case_id=case["case_id"],
                    tier=tier,
                    expected_compliance_status=case["expected_compliance_status"],
                    expected_risk_band=case["expected_risk_band"],
                    expected_escalation=case["expected_escalation"],
                    expected_outcome=case["expected_outcome"],
                )
            )

    return labels


def categorize_failure(score) -> str:
    if not score.term_extraction_correct:
        return "Extraction Failure"
    if not score.compliance_correct:
        return "Compliance Failure"
    if not score.risk_correct:
        return "Risk Calibration Failure"
    if not score.escalation_correct or not score.outcome_correct:
        return "Orchestration Failure"
    return "Uncategorized Failure"


def summarize_judge_scores(judge_scores) -> dict[str, float]:
    if not judge_scores:
        return {}

    fields = [
        "faithfulness",
        "completeness",
        "risk_calibration",
        "compliance_accuracy",
        "explainability",
        "overall_score",
    ]
    return {
        field: round(sum(getattr(score, field) for score in judge_scores) / len(judge_scores), 4)
        for field in fields
    }


if __name__ == "__main__":
    print(json.dumps(run_eval(), indent=2))
