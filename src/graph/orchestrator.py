"""Cupcake MVP orchestrator.

The function is intentionally simple but mirrors the planned LangGraph DAG:
extract terms, validate state, run compliance and risk nodes, then synthesize a packet.
"""

from src.agents.compliance_checker import run_compliance_checker
from src.agents.credit_risk_scorer import run_credit_risk_scorer
from src.agents.term_extractor import extract_terms
from src.graph.state import initial_state, validate_terms_node
from src.reporting.synthesizer import synthesize_review_packet
from src.schemas.loan import GraphState, LoanCase, ReviewPacket


def run_pipeline(loan_case: LoanCase) -> ReviewPacket:
    state = run_pipeline_with_state(loan_case)
    return state["review_packet"]


def run_pipeline_with_state(loan_case: LoanCase) -> GraphState:
    state = initial_state(loan_case)

    terms = extract_terms(loan_case)
    state["extracted_terms"] = terms

    state.update(validate_terms_node(state))

    compliance = run_compliance_checker(terms)
    risk = run_credit_risk_scorer(terms)
    state["compliance"] = compliance
    state["risk"] = risk

    state["review_packet"] = synthesize_review_packet(
        terms=terms,
        compliance=compliance,
        risk=risk,
        validation_errors=state["validation_errors"],
    )

    return state

