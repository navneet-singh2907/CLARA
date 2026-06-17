"""LangGraph runtime tests."""

from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.graph.orchestrator import build_review_graph


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

