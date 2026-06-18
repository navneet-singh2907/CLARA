"""Inter-rater agreement scaffold for judge model evaluation."""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable

from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.eval.judge import (
    JUDGE_DIMENSIONS,
    JudgeScore,
    run_configured_primary_judge,
    run_configured_secondary_judge,
)
from loan_pipeline.eval.metrics import GoldLabel
from loan_pipeline.eval.run_eval import load_gold_labels
from loan_pipeline.graph.orchestrator import run_pipeline
from loan_pipeline.graph.state import LoanCase

ProgressCallback = Callable[[int, int, str], None]


@dataclass(frozen=True)
class JudgePairScore:
    case_id: str
    tier: str
    primary: JudgeScore
    secondary: JudgeScore


def _score_one_case(loan_case: LoanCase, label: GoldLabel) -> JudgePairScore:
    packet = run_pipeline(loan_case)
    return JudgePairScore(
        case_id=loan_case.case_id,
        tier=label.tier,
        primary=run_configured_primary_judge(loan_case, packet, label),
        secondary=run_configured_secondary_judge(loan_case, packet, label),
    )


def run_inter_rater_report(
    case_limit: int | None = None,
    case_ids: list[str] | None = None,
    max_workers: int = 8,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases()}
    labels = load_gold_labels()
    if case_ids is not None:
        labels_by_id = {label.case_id: label for label in labels}
        labels = [labels_by_id[case_id] for case_id in case_ids if case_id in labels_by_id]
    if case_limit is not None:
        labels = labels[:case_limit]
    label_order = {label.case_id: index for index, label in enumerate(labels)}

    pair_scores: list[JudgePairScore] = []
    errors: list[str] = []
    total_cases = len(labels)
    completed_cases = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_score_one_case, cases[label.case_id], label): label
            for label in labels
        }
        for future in as_completed(futures):
            label = futures[future]
            try:
                pair_scores.append(future.result())
            except Exception as exc:
                errors.append(f"{label.case_id}: {exc}")
            completed_cases += 1
            if progress_callback:
                progress_callback(completed_cases, total_cases, label.case_id)

    pair_scores.sort(key=lambda score: label_order[score.case_id])
    result = summarize_inter_rater_agreement(pair_scores)
    if errors:
        result["errors"] = errors
    return result


def summarize_inter_rater_agreement(pair_scores: list[JudgePairScore]) -> dict[str, Any]:
    comparisons = []
    disagreement_cases = []
    case_rows = []
    dimension_deltas = {dimension: [] for dimension in JUDGE_DIMENSIONS}

    for pair_score in pair_scores:
        case_deltas = {
            dimension: abs(
                getattr(pair_score.primary, dimension) - getattr(pair_score.secondary, dimension)
            )
            for dimension in JUDGE_DIMENSIONS
        }
        comparisons.extend(case_deltas.values())

        for dimension, delta in case_deltas.items():
            dimension_deltas[dimension].append(delta)

        if any(delta > 0 for delta in case_deltas.values()):
            disagreement_cases.append(
                {
                    "case_id": pair_score.case_id,
                    "tier": pair_score.tier,
                    "dimension_deltas": case_deltas,
                    "manual_spot_check_required": any(delta > 0 for delta in case_deltas.values()),
                }
            )
        case_rows.append(
            {
                "case_id": pair_score.case_id,
                "tier": pair_score.tier,
                "primary_overall": pair_score.primary.overall_score,
                "secondary_overall": pair_score.secondary.overall_score,
                "primary_failure_category": pair_score.primary.major_failure_category,
                "secondary_failure_category": pair_score.secondary.major_failure_category,
                "primary_rationale": pair_score.primary.rationale,
                "secondary_rationale": pair_score.secondary.rationale,
                "dimension_deltas": case_deltas,
            }
        )

    total = len(comparisons)
    exact_agreement = _ratio(delta == 0 for delta in comparisons)
    within_one_point_agreement = _ratio(delta <= 1 for delta in comparisons)
    average_score_delta = round(sum(comparisons) / total, 4) if total else 0.0
    highest_disagreement_dimension = max(
        dimension_deltas,
        key=lambda dimension: sum(dimension_deltas[dimension]),
    )

    return {
        "cases": len(pair_scores),
        "dimensions_per_case": len(JUDGE_DIMENSIONS),
        "primary_judge_summary": summarize_judge_scores([pair.primary for pair in pair_scores]),
        "secondary_judge_summary": summarize_judge_scores([pair.secondary for pair in pair_scores]),
        "exact_agreement": exact_agreement,
        "within_one_point_agreement": within_one_point_agreement,
        "average_score_delta": average_score_delta,
        "highest_disagreement_dimension": highest_disagreement_dimension,
        "disagreement_case_count": len(disagreement_cases),
        "case_rows": case_rows,
        "manual_spot_check_cases": [
            case["case_id"] for case in disagreement_cases if case["manual_spot_check_required"]
        ],
        "disagreement_cases": disagreement_cases,
    }


def _ratio(values) -> float:
    items = list(values)
    if not items:
        return 0.0
    return round(sum(1 for item in items if item) / len(items), 4)


def summarize_judge_scores(scores: list[JudgeScore]) -> dict[str, float]:
    if not scores:
        return {}
    fields = [*JUDGE_DIMENSIONS, "overall_score"]
    return {
        field: round(sum(getattr(score, field) for score in scores) / len(scores), 4)
        for field in fields
    }


if __name__ == "__main__":
    print(json.dumps(run_inter_rater_report(), indent=2))
