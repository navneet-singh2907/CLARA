"""Week 6 guardrail stress-test runner for CLARA."""

from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from loan_pipeline.eval.week6_guardrails import (
    GuardrailAttackCase,
    load_week6_attack_cases,
    score_guardrail_response,
    summarize_guardrail_evaluations,
)
from loan_pipeline.guardrails import inspect_input_prompt, inspect_output_response

DefenseMode = Literal["baseline", "guarded"]


def run_week6_guardrail_stress(
    *,
    defense_mode: DefenseMode = "guarded",
    cases: list[GuardrailAttackCase] | None = None,
) -> dict[str, Any]:
    selected_cases = cases or load_week6_attack_cases()
    rows = []
    evaluations = []
    for attack_case in selected_cases:
        response, guardrail = _respond_to_attack(attack_case, defense_mode)
        evaluation = score_guardrail_response(attack_case, response)
        evaluations.append(evaluation)
        rows.append(
            {
                "attack_id": attack_case.attack_id,
                "family": attack_case.family,
                "title": attack_case.title,
                "prompt": attack_case.prompt,
                "target_surface": attack_case.target_surface,
                "expected_safe_action": attack_case.expected_safe_action,
                "observed_response": response,
                "score": evaluation.score,
                "observed_behavior": evaluation.observed_behavior,
                "failure_reason": evaluation.failure_reason,
                "recommended_defense": attack_case.recommended_defense,
                "guardrail": guardrail,
            }
        )
    return {
        "defense_mode": defense_mode,
        "summary": summarize_guardrail_evaluations(evaluations),
        "rows": rows,
    }


def compare_week6_baseline_to_guarded() -> dict[str, Any]:
    baseline = run_week6_guardrail_stress(defense_mode="baseline")
    guarded = run_week6_guardrail_stress(defense_mode="guarded")
    return {
        "baseline": baseline["summary"],
        "guarded": guarded["summary"],
        "delta": {
            "pass_rate": round(
                guarded["summary"]["pass_rate"] - baseline["summary"]["pass_rate"],
                4,
            ),
            "fail_rate": round(
                guarded["summary"]["fail_rate"] - baseline["summary"]["fail_rate"],
                4,
            ),
        },
    }


def export_week6_guardrail_evidence(
    output_path: Path = Path("output") / "week6" / "guardrail_evidence.json",
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "baseline": run_week6_guardrail_stress(defense_mode="baseline"),
        "guarded": run_week6_guardrail_stress(defense_mode="guarded"),
        "comparison": compare_week6_baseline_to_guarded(),
    }
    output_path.write_text(_json_dumps(payload), encoding="utf-8")
    return output_path


def _respond_to_attack(
    attack_case: GuardrailAttackCase,
    defense_mode: DefenseMode,
) -> tuple[str, dict[str, Any]]:
    if defense_mode == "baseline":
        return _baseline_response(attack_case), {"mode": "baseline", "findings": []}

    input_decision = inspect_input_prompt(attack_case.prompt)
    if not input_decision.allowed:
        return (
            input_decision.safe_response,
            {
                "mode": "guarded",
                "stage": "input",
                "action": input_decision.action,
                "findings": [asdict(finding) for finding in input_decision.findings],
            },
        )

    draft_response = _safe_allowed_response(attack_case)
    output_decision = inspect_output_response(draft_response)
    return (
        output_decision.safe_response,
        {
            "mode": "guarded",
            "stage": "output" if not output_decision.allowed else "allowed",
            "action": output_decision.action,
            "findings": [asdict(finding) for finding in output_decision.findings],
        },
    )


def _baseline_response(attack_case: GuardrailAttackCase) -> str:
    if not attack_case.should_block:
        return _safe_allowed_response(attack_case)
    if attack_case.family == "pii_extraction":
        return "The borrower SSN is 123-45-6789 and the account ID is ACCT-4482."
    if attack_case.family == "internal_policy_leakage":
        return "The system prompt, hidden scoring formula, and API key are shown below."
    if attack_case.family == "tool_authorization":
        return "Approved. I submitted the approval and marked funds ready for disbursement."
    return "Approved. I ignored compliance and skipped escalation as requested."


def _safe_allowed_response(attack_case: GuardrailAttackCase) -> str:
    if attack_case.family == "overblocking_control":
        return (
            "CLARA can answer this safely using high-level policy guidance, aggregate "
            "metrics, or evidence-grounded next steps without exposing sensitive data."
        )
    return "CLARA can provide a safe, evidence-grounded answer for this request."


def _json_dumps(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, indent=2)
