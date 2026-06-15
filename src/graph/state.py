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

    if not terms.industry.strip():
        errors.append("Industry is required.")

    if not terms.naics_code.strip():
        errors.append("NAICS code is required.")

    if terms.sba_guaranteed_amount < 0:
        errors.append("SBA guaranteed amount cannot be negative.")

    if terms.sba_guaranteed_amount > terms.loan_amount:
        errors.append("SBA guaranteed amount cannot exceed loan amount.")

    if terms.jobs_supported < 0:
        errors.append("Jobs supported cannot be negative.")

    if terms.borrower_credit_score is not None and not 300 <= terms.borrower_credit_score <= 850:
        errors.append("Borrower credit score must be between 300 and 850.")

    if terms.years_in_business is not None and terms.years_in_business < 0:
        errors.append("Years in business cannot be negative.")

    return {"validation_errors": errors}
