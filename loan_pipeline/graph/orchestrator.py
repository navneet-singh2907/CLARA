"""Loan review orchestrator."""

from functools import lru_cache

from langgraph.graph import END as LANGGRAPH_END
from langgraph.graph import START as LANGGRAPH_START
from langgraph.graph import StateGraph

from loan_pipeline.agents.compliance_checker import run_compliance_checker
from loan_pipeline.agents.credit_risk_scorer import run_credit_risk_scorer
from loan_pipeline.agents.term_extractor import extract_terms
from loan_pipeline.graph.edges import (
    COMPLIANCE_CHECKER,
    CREDIT_RISK_SCORER,
    SYNTHESIZER,
    TERM_EXTRACTOR,
    VALIDATOR,
)
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
    packet = state["review_packet"]
    if packet is None:
        raise RuntimeError("Pipeline completed without producing a review packet.")
    return packet


def run_pipeline_with_state(loan_case: LoanCase) -> GraphState:
    graph = build_review_graph()
    return graph.invoke(initial_state(loan_case))


@lru_cache(maxsize=1)
def build_review_graph():
    workflow = StateGraph(GraphState)

    workflow.add_node(TERM_EXTRACTOR, term_extractor_node)
    workflow.add_node(VALIDATOR, validate_terms_node)
    workflow.add_node(COMPLIANCE_CHECKER, compliance_checker_node)
    workflow.add_node(CREDIT_RISK_SCORER, credit_risk_scorer_node)
    workflow.add_node(SYNTHESIZER, synthesizer_node)

    workflow.add_edge(LANGGRAPH_START, TERM_EXTRACTOR)
    workflow.add_edge(TERM_EXTRACTOR, VALIDATOR)
    workflow.add_edge(VALIDATOR, COMPLIANCE_CHECKER)
    workflow.add_edge(VALIDATOR, CREDIT_RISK_SCORER)
    workflow.add_edge(COMPLIANCE_CHECKER, SYNTHESIZER)
    workflow.add_edge(CREDIT_RISK_SCORER, SYNTHESIZER)
    workflow.add_edge(SYNTHESIZER, LANGGRAPH_END)

    return workflow.compile()


def term_extractor_node(state: GraphState) -> GraphState:
    return {"extracted_terms": extract_terms(state["loan_case"])}


def compliance_checker_node(state: GraphState) -> GraphState:
    terms = state["extracted_terms"]
    if terms is None:
        return {"agent_errors": [*state["agent_errors"], "Compliance checker missing terms."]}
    return {"compliance": run_compliance_checker(terms)}


def credit_risk_scorer_node(state: GraphState) -> GraphState:
    terms = state["extracted_terms"]
    if terms is None:
        return {"agent_errors": [*state["agent_errors"], "Credit risk scorer missing terms."]}
    return {"risk": run_credit_risk_scorer(terms)}


def synthesizer_node(state: GraphState) -> GraphState:
    terms = state["extracted_terms"]
    compliance = state["compliance"]
    risk = state["risk"]

    missing_outputs = []
    if terms is None:
        missing_outputs.append("extracted_terms")
    if compliance is None:
        missing_outputs.append("compliance")
    if risk is None:
        missing_outputs.append("risk")

    if missing_outputs:
        return {
            "agent_errors": [
                *state["agent_errors"],
                f"Synthesizer missing required outputs: {', '.join(missing_outputs)}.",
            ]
        }

    return {
        "review_packet": synthesize_review_packet(
            terms=terms,
            compliance=compliance,
            risk=risk,
            validation_errors=state["validation_errors"],
        )
    }


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
