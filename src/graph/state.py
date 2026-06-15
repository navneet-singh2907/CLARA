"""Graph state helpers for the Cupcake MVP."""

from src.schemas.loan import GraphState, LoanCase


def initial_state(loan_case: LoanCase) -> GraphState:
    return {
        "loan_case": loan_case,
        "extracted_terms": None,
        "validation_errors": [],
        "compliance": None,
        "risk": None,
        "review_packet": None,
        "agent_errors": [],
    }


def validate_terms_node(state: GraphState) -> GraphState:
    terms = state["extracted_terms"]
    errors: list[str] = []

    if terms.loan_amount <= 0:
        errors.append("Loan amount must be greater than zero.")

    if terms.term_months <= 0:
        errors.append("Loan term must be greater than zero months.")

    if not terms.borrower_name.strip():
        errors.append("Borrower name is required.")

    return {"validation_errors": errors}

