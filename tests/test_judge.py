"""LLM-as-judge scaffolding tests."""

import json
import os

from loan_pipeline.config import load_sba_demo_cases, reset_settings_cache
from loan_pipeline.eval.judge import (
    build_judge_prompt,
    parse_judge_response,
    run_configured_primary_judge,
    run_local_judge,
)
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


def test_configured_primary_judge_falls_back_to_local_when_model_blank() -> None:
    old_model = os.environ.pop("PRIMARY_JUDGE_MODEL", None)
    try:
        reset_settings_cache()
        loan_case = load_sba_demo_cases()[0]
        gold = load_gold_labels()[0]
        packet = run_pipeline(loan_case)

        score = run_configured_primary_judge(loan_case, packet, gold)

        assert score.rationale.startswith("Local judge scaffold")
    finally:
        _restore_env("PRIMARY_JUDGE_MODEL", old_model)
        reset_settings_cache()


def test_configured_primary_judge_requires_api_key_when_model_set() -> None:
    old_model = os.environ.get("PRIMARY_JUDGE_MODEL")
    old_key = os.environ.pop("OPENAI_API_KEY", None)
    os.environ["PRIMARY_JUDGE_MODEL"] = "gpt-4o-mini"
    try:
        reset_settings_cache()
        loan_case = load_sba_demo_cases()[0]
        gold = load_gold_labels()[0]
        packet = run_pipeline(loan_case)

        try:
            run_configured_primary_judge(loan_case, packet, gold)
        except RuntimeError as exc:
            assert "OPENAI_API_KEY" in str(exc)
            return
        raise AssertionError("Live judge should require OPENAI_API_KEY.")
    finally:
        _restore_env("PRIMARY_JUDGE_MODEL", old_model)
        _restore_env("OPENAI_API_KEY", old_key)
        reset_settings_cache()


def _restore_env(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value
