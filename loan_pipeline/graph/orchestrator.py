"""Loan review orchestrator."""

from loan_pipeline.agents.compliance_checker import run_compliance_checker
from loan_pipeline.agents.credit_risk_scorer import run_credit_risk_scorer
from loan_pipeline.agents.term_extractor import extract_terms
from loan_pipeline.graph.state import (
    ComplianceResult,
    ExtractedTerms,
    GraphState,
    LoanCase,
    ReviewPacket,
    RiskResult,
    initial_state,
    validate_terms_node,
)


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


def synthesize_review_packet(
    terms: ExtractedTerms,
    compliance: ComplianceResult,
    risk: RiskResult,
    validation_errors: list[str],
) -> ReviewPacket:
    human_review_notes: list[str] = []

    if validation_errors:
        human_review_notes.extend(validation_errors)

    if compliance.status == "FAIL":
        human_review_notes.append("Compliance blocker or high-severity finding requires review.")

    if risk.band == "HIGH":
        human_review_notes.append("High credit risk requires loan officer review.")

    if terms.confidence < 0.80:
        human_review_notes.append("Extraction confidence is below target threshold.")

    escalation_required = bool(human_review_notes)

    if validation_errors or compliance.status == "FAIL" or risk.band == "HIGH":
        recommended_outcome = "ESCALATE"
    elif compliance.status == "REVIEW" or risk.band == "MEDIUM":
        recommended_outcome = "CONDITIONAL_REVIEW"
    else:
        recommended_outcome = "APPROVE"

    summary = (
        f"{terms.borrower_name} is classified as {risk.band} risk with compliance status "
        f"{compliance.status}. Recommended outcome: {recommended_outcome}."
    )

    return ReviewPacket(
        case_id=terms.case_id,
        recommended_outcome=recommended_outcome,
        escalation_required=escalation_required,
        summary=summary,
        extracted_terms=terms,
        compliance=compliance,
        risk=risk,
        human_review_notes=human_review_notes,
    )

