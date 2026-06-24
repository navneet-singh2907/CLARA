"""Agent-level failure attribution tests."""

from loan_pipeline.eval.failure_attribution import attribute_result_failure, primary_attribution
from loan_pipeline.graph.state import ExecutionTraceEntry


def _result_with_exact(**overrides):
    exact = {
        "term_extraction_correct": True,
        "compliance_correct": True,
        "risk_correct": True,
        "escalation_correct": True,
        "outcome_correct": True,
    }
    exact.update(overrides)
    return {
        "case_id": "CASE-001",
        "exact_match": exact,
        "packet": {
            "outcome": "CONDITIONAL_REVIEW",
            "risk_band": "MEDIUM",
            "compliance_status": "REVIEW",
            "escalation_required": True,
        },
        "gold": {
            "expected_outcome": "ESCALATE",
            "expected_risk_band": "HIGH",
            "expected_compliance_status": "FAIL",
            "expected_escalation": True,
        },
    }


def test_compliance_miss_maps_to_compliance_checker() -> None:
    attribution = primary_attribution(
        _result_with_exact(compliance_correct=False, outcome_correct=False)
    )

    assert attribution["responsible_agent"] == "Compliance Checker Agent"
    assert attribution["graph_node"] == "compliance_checker"
    assert attribution["failure_mode"] == "behavioral_misclassification"


def test_risk_miss_maps_to_credit_risk_scorer() -> None:
    attribution = primary_attribution(_result_with_exact(risk_correct=False))

    assert attribution["responsible_agent"] == "Credit Risk Scorer Agent"
    assert attribution["graph_node"] == "credit_risk_scorer"
    assert "Risk band HIGH" in attribution["expected"]


def test_specialists_correct_but_outcome_wrong_maps_to_synthesizer() -> None:
    attribution = primary_attribution(
        _result_with_exact(outcome_correct=False, escalation_correct=False)
    )

    assert attribution["responsible_agent"] == "Review Synthesizer / Orchestrator"
    assert attribution["graph_node"] == "review_synthesizer"
    assert "Specialist agents were correct" in attribution["downstream_impact"]


def test_runtime_error_maps_to_failed_graph_node() -> None:
    result = {
        "exact_match": {
            "term_extraction_correct": True,
            "compliance_correct": True,
            "risk_correct": True,
            "escalation_correct": True,
            "outcome_correct": True,
        },
        "packet": {},
        "gold": {},
    }
    trace = [
        ExecutionTraceEntry(
            node="term_extractor",
            stage="term_extraction",
            parallel_group=None,
            duration_ms=10,
            status="ERROR",
        )
    ]

    # Simulate persisted runtime attribution shape through direct result enrichment.
    result["failure_attribution"] = [
        {
            "responsible_agent": "Term Extractor Agent",
            "graph_node": trace[0].node,
            "failure_mode": "runtime_error",
            "expected": "term_extractor should complete successfully.",
            "actual": "term_extractor returned ERROR during term_extraction.",
            "downstream_impact": "The graph cannot fully trust downstream state.",
        }
    ]

    attribution = attribute_result_failure(result)[0]

    assert attribution["responsible_agent"] == "Term Extractor Agent"
    assert attribution["failure_mode"] == "runtime_error"
