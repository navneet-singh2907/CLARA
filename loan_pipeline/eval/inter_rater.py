"""Inter-rater agreement scaffold for judge model evaluation."""

import json
from dataclasses import dataclass
from typing import Any

from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.eval.judge import (
    JUDGE_DIMENSIONS,
    JudgeScore,
    run_configured_primary_judge,
    run_configured_secondary_judge,
)
from loan_pipeline.eval.run_eval import load_gold_labels
from loan_pipeline.graph.orchestrator import run_pipeline


@dataclass(frozen=True)
class JudgePairScore:
    case_id: str
    tier: str
    primary: JudgeScore
    secondary: JudgeScore


def run_inter_rater_report() -> dict[str, Any]:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases()}
    labels = load_gold_labels()
    pair_scores: list[JudgePairScore] = []

    for label in labels:
        loan_case = cases[label.case_id]
        packet = run_pipeline(loan_case)
        pair_scores.append(
            JudgePairScore(
                case_id=loan_case.case_id,
                tier=label.tier,
                primary=run_configured_primary_judge(loan_case, packet, label),
                secondary=run_configured_secondary_judge(loan_case, packet, label),
            )
        )

    return summarize_inter_rater_agreement(pair_scores)


def summarize_inter_rater_agreement(pair_scores: list[JudgePairScore]) -> dict[str, Any]:
    comparisons = []
    disagreement_cases = []
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
        "exact_agreement": exact_agreement,
        "within_one_point_agreement": within_one_point_agreement,
        "average_score_delta": average_score_delta,
        "highest_disagreement_dimension": highest_disagreement_dimension,
        "disagreement_case_count": len(disagreement_cases),
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


if __name__ == "__main__":
    print(json.dumps(run_inter_rater_report(), indent=2))
