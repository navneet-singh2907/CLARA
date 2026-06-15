"""LangGraph runtime tests."""

from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.graph.orchestrator import build_review_graph


def test_review_graph_compiles_and_invokes() -> None:
    graph = build_review_graph()
    case = load_sba_demo_cases()[0]

    state = graph.invoke(
        {
            "loan_case": case,
            "extracted_terms": None,
            "validation_errors": [],
            "compliance": None,
            "risk": None,
            "review_packet": None,
            "agent_errors": [],
        }
    )

    assert state["extracted_terms"] is not None
    assert state["compliance"] is not None
    assert state["risk"] is not None
    assert state["review_packet"] is not None
    assert state["agent_errors"] == []

