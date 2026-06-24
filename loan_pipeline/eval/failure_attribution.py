"""Agent-level failure attribution for multi-agent evaluations."""

from dataclasses import asdict, dataclass
from typing import Any

from loan_pipeline.eval.metrics import GoldLabel
from loan_pipeline.graph.state import ExecutionTraceEntry, LoanCase, ReviewPacket


@dataclass(frozen=True)
class FailureAttribution:
    responsible_agent: str
    graph_node: str
    failure_mode: str
    expected: str
    actual: str
    downstream_impact: str


AGENT_LABELS = {
    "term_extractor": "Term Extractor Agent",
    "schema_validator": "Schema Validator",
    "compliance_checker": "Compliance Checker Agent",
    "credit_risk_scorer": "Credit Risk Scorer Agent",
    "review_synthesizer": "Review Synthesizer / Orchestrator",
}


def attribute_failure(
    loan_case: LoanCase,
    packet: ReviewPacket,
    gold: GoldLabel,
    exact_match: dict[str, bool],
    execution_trace: list[ExecutionTraceEntry],
) -> list[dict[str, str]]:
    """Attribute runtime and behavioral failures to the most relevant graph agent."""
    attributions = _runtime_attributions(execution_trace)
    attributions.extend(_behavioral_attributions(loan_case, packet, gold, exact_match))
    return [asdict(attribution) for attribution in attributions]


def attribute_result_failure(result: dict[str, Any]) -> list[dict[str, str]]:
    """Attribute failures from a persisted Week 4 result artifact."""
    if result.get("failure_attribution"):
        return result["failure_attribution"]

    exact = result["exact_match"]
    if all(exact.values()):
        return []

    packet = result["packet"]
    gold = result.get("gold", {})
    attributions = []

    if not exact["term_extraction_correct"]:
        attributions.append(
            _behavioral(
                responsible_agent="Term Extractor Agent",
                graph_node="term_extractor",
                expected="Extracted terms should match the loan case source fields.",
                actual="One or more extracted terms differed from the source case.",
                downstream_impact=(
                    "Downstream compliance, risk, and synthesis decisions may be grounded "
                    "on incorrect terms."
                ),
            )
        )

    if not exact["compliance_correct"]:
        attributions.append(
            _behavioral(
                responsible_agent="Compliance Checker Agent",
                graph_node="compliance_checker",
                expected=f"Compliance status {gold.get('expected_compliance_status', 'unknown')}",
                actual=f"Compliance status {packet.get('compliance_status', 'unknown')}",
                downstream_impact=(
                    "The review synthesizer may choose the wrong review path because the "
                    "compliance status is misclassified."
                ),
            )
        )

    if not exact["risk_correct"]:
        attributions.append(
            _behavioral(
                responsible_agent="Credit Risk Scorer Agent",
                graph_node="credit_risk_scorer",
                expected=f"Risk band {gold.get('expected_risk_band', 'unknown')}",
                actual=f"Risk band {packet.get('risk_band', 'unknown')}",
                downstream_impact=(
                    "The final packet may understate or overstate repayment severity and "
                    "counterfactual guidance."
                ),
            )
        )

    if (
        exact["term_extraction_correct"]
        and exact["compliance_correct"]
        and exact["risk_correct"]
        and (not exact["escalation_correct"] or not exact["outcome_correct"])
    ):
        attributions.append(
            _behavioral(
                responsible_agent="Review Synthesizer / Orchestrator",
                graph_node="review_synthesizer",
                expected=(
                    f"Outcome {gold.get('expected_outcome', 'unknown')}; "
                    f"escalation {gold.get('expected_escalation', 'unknown')}"
                ),
                actual=(
                    f"Outcome {packet.get('outcome', 'unknown')}; "
                    f"escalation {packet.get('escalation_required', 'unknown')}"
                ),
                downstream_impact=(
                    "Specialist agents were correct, but the orchestration gate produced "
                    "the wrong action for the human reviewer."
                ),
            )
        )

    return [asdict(attribution) for attribution in attributions]


def primary_attribution(result: dict[str, Any]) -> dict[str, str]:
    attributions = attribute_result_failure(result)
    if attributions:
        return attributions[0]
    return {
        "responsible_agent": "None",
        "graph_node": "none",
        "failure_mode": "none",
        "expected": "All tracked fields matched.",
        "actual": "All tracked fields matched.",
        "downstream_impact": "No failure attribution required.",
    }


def _runtime_attributions(
    execution_trace: list[ExecutionTraceEntry],
) -> list[FailureAttribution]:
    attributions = []
    for entry in execution_trace:
        if entry.status != "ERROR":
            continue
        attributions.append(
            FailureAttribution(
                responsible_agent=AGENT_LABELS.get(entry.node, entry.node),
                graph_node=entry.node,
                failure_mode="runtime_error",
                expected=f"{entry.node} should complete successfully.",
                actual=f"{entry.node} returned ERROR during {entry.stage}.",
                downstream_impact=(
                    "The graph cannot fully trust downstream state because an upstream "
                    "agent failed at runtime."
                ),
            )
        )
    return attributions


def _behavioral_attributions(
    loan_case: LoanCase,
    packet: ReviewPacket,
    gold: GoldLabel,
    exact_match: dict[str, bool],
) -> list[FailureAttribution]:
    result = {
        "exact_match": exact_match,
        "packet": {
            "outcome": packet.recommended_outcome,
            "risk_band": packet.risk.band,
            "compliance_status": packet.compliance.status,
            "escalation_required": packet.escalation_required,
        },
        "gold": asdict(gold),
    }
    if loan_case.case_id != packet.case_id:
        result["exact_match"] = {**exact_match, "term_extraction_correct": False}
    return [
        FailureAttribution(**attribution)
        for attribution in attribute_result_failure(result)
    ]


def _behavioral(
    *,
    responsible_agent: str,
    graph_node: str,
    expected: str,
    actual: str,
    downstream_impact: str,
) -> FailureAttribution:
    return FailureAttribution(
        responsible_agent=responsible_agent,
        graph_node=graph_node,
        failure_mode="behavioral_misclassification",
        expected=expected,
        actual=actual,
        downstream_impact=downstream_impact,
    )
