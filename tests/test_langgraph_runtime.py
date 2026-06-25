"""LangGraph runtime tests."""

import loan_pipeline.graph.orchestrator as orchestrator
from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.graph.orchestrator import build_review_graph, run_pipeline_with_state


def test_review_graph_compiles_and_invokes() -> None:
    graph = build_review_graph()
    case = load_sba_demo_cases()[0]

    state = graph.invoke(
        {
            "loan_case": case,
            "review_policy": "sba_reviewer",
            "extracted_terms": None,
            "validation_errors": [],
            "compliance": None,
            "risk": None,
            "contradictions": [],
            "counterfactuals": [],
            "review_packet": None,
            "agent_errors": [],
            "execution_trace": [],
        }
    )

    assert state["extracted_terms"] is not None
    assert state["compliance"] is not None
    assert state["risk"] is not None
    assert state["review_packet"] is not None
    assert state["agent_errors"] == []

    parallel_nodes = {
        entry.node
        for entry in state["execution_trace"]
        if entry.parallel_group == "specialist_review"
    }
    assert parallel_nodes == {"compliance_checker", "credit_risk_scorer"}


def test_compliance_agent_failure_escalates_with_review_packet(monkeypatch) -> None:
    def failing_compliance_agent(*args, **kwargs):
        raise RuntimeError("simulated compliance outage")

    monkeypatch.setattr(orchestrator, "run_compliance_checker", failing_compliance_agent)

    state = run_pipeline_with_state(load_sba_demo_cases()[0])
    packet = state["review_packet"]

    assert packet is not None
    assert packet.recommended_outcome == "ESCALATE"
    assert packet.escalation_required
    assert packet.compliance.status == "REVIEW"
    assert packet.compliance.findings[0].rule_id == "AGENT-ERROR"
    assert any("Compliance checker failed" in error for error in state["agent_errors"])
    assert any(
        entry.node == "compliance_checker" and entry.status == "ERROR"
        for entry in state["execution_trace"]
    )
    assert any("Agent failure:" in note for note in packet.human_review_notes)


def test_risk_agent_failure_escalates_with_review_packet(monkeypatch) -> None:
    def failing_risk_agent(*args, **kwargs):
        raise RuntimeError("simulated risk model timeout")

    monkeypatch.setattr(orchestrator, "run_credit_risk_scorer", failing_risk_agent)

    state = run_pipeline_with_state(load_sba_demo_cases()[0])
    packet = state["review_packet"]

    assert packet is not None
    assert packet.recommended_outcome == "ESCALATE"
    assert packet.escalation_required
    assert packet.risk.band == "HIGH"
    assert packet.risk.score == 5
    assert any("Credit risk scorer failed" in error for error in state["agent_errors"])
    assert any(
        entry.node == "credit_risk_scorer" and entry.status == "ERROR"
        for entry in state["execution_trace"]
    )
    assert "specialist agents failed" in packet.summary

