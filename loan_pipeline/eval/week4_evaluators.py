"""Week 4 evaluator helpers for CLARA Eval Lab."""

from dataclasses import asdict
from typing import Any

from loan_pipeline.eval.failure_attribution import attribute_failure
from loan_pipeline.eval.metrics import GoldLabel, score_case
from loan_pipeline.graph.orchestrator import run_pipeline_with_state
from loan_pipeline.graph.state import LoanCase, ReviewPacket

EXPECTED_TRAJECTORY = [
    "term_extractor",
    "schema_validator",
    "compliance_checker",
    "credit_risk_scorer",
    "review_synthesizer",
]


def evaluate_case(loan_case: LoanCase, gold: GoldLabel) -> dict[str, Any]:
    state = run_pipeline_with_state(loan_case)
    packet = state["review_packet"]
    if packet is None:
        raise RuntimeError(f"CLARA did not produce a review packet for {loan_case.case_id}.")

    exact_scores = exact_match_scores(loan_case, packet, gold)
    trajectory = trajectory_score(state["execution_trace"])
    trust = trust_risk_flags(packet)
    failure_attribution = attribute_failure(
        loan_case=loan_case,
        packet=packet,
        gold=gold,
        exact_match=exact_scores,
        execution_trace=state["execution_trace"],
    )
    return {
        "case_id": loan_case.case_id,
        "tier": gold.tier,
        "exact_match": exact_scores,
        "trajectory": trajectory,
        "trust_risk": trust,
        "failure_attribution": failure_attribution,
        "packet": _packet_summary(packet),
    }


def exact_match_scores(
    loan_case: LoanCase,
    packet: ReviewPacket,
    gold: GoldLabel,
) -> dict[str, bool]:
    score = score_case(loan_case, packet, gold)
    return {
        "term_extraction_correct": score.term_extraction_correct,
        "compliance_correct": score.compliance_correct,
        "risk_correct": score.risk_correct,
        "escalation_correct": score.escalation_correct,
        "outcome_correct": score.outcome_correct,
    }


def trajectory_score(execution_trace) -> dict[str, Any]:
    observed_nodes = [entry.node for entry in execution_trace]
    missing_nodes = [node for node in EXPECTED_TRAJECTORY if node not in observed_nodes]
    has_parallel_review = any(
        entry.parallel_group == "specialist_review" for entry in execution_trace
    )
    all_success = all(entry.status == "SUCCESS" for entry in execution_trace)
    return {
        "trajectory_correct": not missing_nodes and has_parallel_review and all_success,
        "observed_nodes": observed_nodes,
        "missing_nodes": missing_nodes,
        "parallel_specialist_review_seen": has_parallel_review,
        "all_nodes_successful": all_success,
    }


def trust_risk_flags(packet: ReviewPacket) -> dict[str, Any]:
    flags = []
    if packet.contradictions:
        flags.append("agent_disagreement")
    if packet.risk.confidence < 0.75:
        flags.append("low_risk_confidence")
    if packet.extracted_terms.confidence < 0.80:
        flags.append("low_extraction_confidence")
    if packet.escalation_required:
        flags.append("human_review_required")
    return {
        "should_not_auto_approve": bool(flags),
        "flags": flags,
    }


def _packet_summary(packet: ReviewPacket) -> dict[str, Any]:
    return {
        "case_id": packet.case_id,
        "outcome": packet.recommended_outcome,
        "risk_band": packet.risk.band,
        "risk_confidence": packet.risk.confidence,
        "compliance_status": packet.compliance.status,
        "term_confidence": packet.extracted_terms.confidence,
        "escalation_required": packet.escalation_required,
        "contradiction_count": len(packet.contradictions),
        "counterfactual_count": len(packet.counterfactuals),
        "human_review_notes": list(packet.human_review_notes),
        "compliance_findings": [asdict(finding) for finding in packet.compliance.findings],
    }
