"""LLM-as-judge scaffolding tests."""

import json

from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.eval.judge import build_judge_prompt, parse_judge_response, run_local_judge
from loan_pipeline.eval.run_eval import load_gold_labels
from loan_pipeline.graph.orchestrator import run_pipeline


def test_build_judge_prompt_contains_required_sections() -> None:
    loan_case = load_sba_demo_cases()[0]
    gold = load_gold_labels()[0]
    packet = run_pipeline(loan_case)

    prompt = build_judge_prompt(loan_case, packet, gold)

    assert "Source loan record:" in prompt
    assert "Agent output:" in prompt
    assert "Gold answer:" in prompt
    assert "Return JSON only" in prompt


def test_parse_judge_response_accepts_valid_json() -> None:
    score = parse_judge_response(
        json.dumps(
            {
                "faithfulness": 5,
                "completeness": 4,
                "risk_calibration": 5,
                "compliance_accuracy": 5,
                "explainability": 4,
                "overall_score": 5,
                "major_failure_category": "None",
                "rationale": "Grounded and useful.",
            }
        )
    )

    assert score.faithfulness == 5
    assert score.major_failure_category == "None"


def test_parse_judge_response_rejects_invalid_score() -> None:
    try:
        parse_judge_response(
            json.dumps(
                {
                    "faithfulness": 6,
                    "completeness": 4,
                    "risk_calibration": 5,
                    "compliance_accuracy": 5,
                    "explainability": 4,
                    "overall_score": 5,
                    "major_failure_category": "None",
                    "rationale": "Invalid score.",
                }
            )
        )
    except ValueError:
        return

    raise AssertionError("Invalid judge score should raise ValueError.")


def test_local_judge_flags_known_risk_calibration_failure() -> None:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases()}
    labels = {label.case_id: label for label in load_gold_labels()}
    loan_case = cases["ADV-003"]
    packet = run_pipeline(loan_case)

    score = run_local_judge(loan_case, packet, labels["ADV-003"])

    assert score.risk_calibration == 2
    assert score.major_failure_category == "Risk Calibration Failure"
