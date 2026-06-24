"""Loan review orchestrator."""

from functools import lru_cache
from time import perf_counter

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
    ContradictionResult,
    CounterfactualResult,
    ExecutionTraceEntry,
    ExtractedTerms,
    GraphState,
    LoanCase,
    ReviewPacket,
    ReviewPolicy,
    RiskResult,
    initial_state,
    validate_terms_node,
)
from loan_pipeline.observability import trace_call
from loan_pipeline.review.contradictions import detect_contradictions
from loan_pipeline.review.counterfactuals import generate_counterfactuals


def run_pipeline(loan_case: LoanCase, review_policy: ReviewPolicy = "sba_reviewer") -> ReviewPacket:
    state = run_pipeline_with_state(loan_case, review_policy=review_policy)
    packet = state["review_packet"]
    if packet is None:
        raise RuntimeError("Pipeline completed without producing a review packet.")
    return packet


def run_pipeline_with_state(
    loan_case: LoanCase,
    review_policy: ReviewPolicy = "sba_reviewer",
) -> GraphState:
    return trace_call(
        name="CLARA Loan Review Pipeline",
        run_type="chain",
        func=_run_pipeline_with_state,
        args=(loan_case, review_policy),
        metadata={
            "case_id": loan_case.case_id,
            "tier": loan_case.difficulty_tier,
            "review_policy": review_policy,
        },
        tags=["loan-review", "langgraph"],
    )


def _run_pipeline_with_state(loan_case: LoanCase, review_policy: ReviewPolicy) -> GraphState:
    graph = build_review_graph()
    return graph.invoke(initial_state(loan_case, review_policy=review_policy))


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
    started_at = perf_counter()
    loan_case = state["loan_case"]
    terms = trace_call(
        name="Term Extractor Agent",
        run_type="chain",
        func=extract_terms,
        args=(loan_case,),
        metadata={"case_id": loan_case.case_id, "stage": "term_extraction"},
        tags=["agent", "term-extractor"],
    )
    return {
        "extracted_terms": terms,
        "execution_trace": [
            _trace_entry(
                node=TERM_EXTRACTOR,
                stage="term_extraction",
                parallel_group=None,
                started_at=started_at,
            )
        ],
    }


def compliance_checker_node(state: GraphState) -> GraphState:
    started_at = perf_counter()
    terms = state["extracted_terms"]
    review_policy = state["review_policy"]
    if terms is None:
        return {
            "agent_errors": [*state["agent_errors"], "Compliance checker missing terms."],
            "execution_trace": [
                _trace_entry(
                    node=COMPLIANCE_CHECKER,
                    stage="parallel_specialist_review",
                    parallel_group="specialist_review",
                    started_at=started_at,
                    status="ERROR",
                )
            ],
        }
    return {
        "compliance": trace_call(
            name="Compliance Checker Agent",
            run_type="chain",
            func=run_compliance_checker,
            args=(terms, review_policy),
            metadata={
                "case_id": terms.case_id,
                "stage": "parallel_specialist_review",
                "review_policy": review_policy,
            },
            tags=["agent", "compliance", "parallel-specialist-review"],
        ),
        "execution_trace": [
            _trace_entry(
                node=COMPLIANCE_CHECKER,
                stage="parallel_specialist_review",
                parallel_group="specialist_review",
                started_at=started_at,
            )
        ],
    }


def credit_risk_scorer_node(state: GraphState) -> GraphState:
    started_at = perf_counter()
    terms = state["extracted_terms"]
    review_policy = state["review_policy"]
    if terms is None:
        return {
            "agent_errors": [*state["agent_errors"], "Credit risk scorer missing terms."],
            "execution_trace": [
                _trace_entry(
                    node=CREDIT_RISK_SCORER,
                    stage="parallel_specialist_review",
                    parallel_group="specialist_review",
                    started_at=started_at,
                    status="ERROR",
                )
            ],
        }
    return {
        "risk": trace_call(
            name="Credit Risk Scorer Agent",
            run_type="chain",
            func=run_credit_risk_scorer,
            args=(terms, review_policy),
            metadata={
                "case_id": terms.case_id,
                "stage": "parallel_specialist_review",
                "review_policy": review_policy,
            },
            tags=["agent", "credit-risk", "parallel-specialist-review"],
        ),
        "execution_trace": [
            _trace_entry(
                node=CREDIT_RISK_SCORER,
                stage="parallel_specialist_review",
                parallel_group="specialist_review",
                started_at=started_at,
            )
        ],
    }


def synthesizer_node(state: GraphState) -> GraphState:
    started_at = perf_counter()
    terms = state["extracted_terms"]
    compliance = state["compliance"]
    risk = state["risk"]
    review_policy = state["review_policy"]

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
            ],
            "execution_trace": [
                _trace_entry(
                    node=SYNTHESIZER,
                    stage="synthesis",
                    parallel_group=None,
                    started_at=started_at,
                    status="ERROR",
                )
            ],
        }

    packet = trace_call(
        name="Review Synthesizer",
        run_type="chain",
        func=synthesize_review_packet,
        kwargs={
            "terms": terms,
            "compliance": compliance,
            "risk": risk,
            "validation_errors": state["validation_errors"],
            "review_policy": review_policy,
        },
        metadata={"case_id": terms.case_id, "stage": "synthesis", "review_policy": review_policy},
        tags=["synthesizer", "review-packet"],
    )

    return {
        "review_packet": packet,
        "contradictions": packet.contradictions,
        "counterfactuals": packet.counterfactuals,
        "execution_trace": [
            _trace_entry(
                node=SYNTHESIZER,
                stage="synthesis",
                parallel_group=None,
                started_at=started_at,
            )
        ],
    }


def _trace_entry(
    *,
    node: str,
    stage: str,
    parallel_group: str | None,
    started_at: float,
    status: str = "SUCCESS",
) -> ExecutionTraceEntry:
    return ExecutionTraceEntry(
        node=node,
        stage=stage,
        parallel_group=parallel_group,
        duration_ms=round((perf_counter() - started_at) * 1000, 3),
        status=status,
    )


def synthesize_review_packet(
    terms: ExtractedTerms,
    compliance: ComplianceResult,
    risk: RiskResult,
    validation_errors: list[str],
    review_policy: ReviewPolicy = "sba_reviewer",
) -> ReviewPacket:
    human_review_notes: list[str] = []
    contradictions = [
        ContradictionResult(
            severity=contradiction.severity,
            title=contradiction.title,
            compliance_position=contradiction.compliance_position,
            risk_position=contradiction.risk_position,
            reviewer_prompt=contradiction.reviewer_prompt,
        )
        for contradiction in detect_contradictions(compliance, risk)
    ]
    counterfactuals = [
        CounterfactualResult(
            type=counterfactual.type,
            title=counterfactual.title,
            current_state=counterfactual.current_state,
            suggested_change=counterfactual.suggested_change,
            expected_effect=counterfactual.expected_effect,
        )
        for counterfactual in generate_counterfactuals(terms, compliance, risk)
    ]

    if validation_errors:
        human_review_notes.extend(validation_errors)

    if compliance.status == "FAIL":
        human_review_notes.append("Compliance blocker or high-severity finding requires review.")

    if risk.band == "HIGH":
        human_review_notes.append("High credit risk requires loan officer review.")

    if _requires_extraction_confidence_review(terms):
        human_review_notes.append("Extraction confidence is below target threshold.")

    if contradictions:
        human_review_notes.append("Agent contradiction detected; human adjudication required.")

    escalation_required = bool(human_review_notes)

    if (
        validation_errors
        or contradictions
        or compliance.status == "FAIL"
        or risk.band == "HIGH"
        or terms.confidence < 0.60
        or _is_non_loan_or_irrelevant_input(terms)
    ):
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
        review_policy=review_policy,
        recommended_outcome=recommended_outcome,
        escalation_required=escalation_required,
        summary=summary,
        extracted_terms=terms,
        compliance=compliance,
        risk=risk,
        human_review_notes=human_review_notes,
        contradictions=contradictions,
        counterfactuals=counterfactuals,
    )


def _requires_extraction_confidence_review(terms: ExtractedTerms) -> bool:
    if terms.confidence >= 0.80:
        return False
    if terms.confidence < 0.60:
        return True
    return bool(
        terms.missing_documents
        or terms.borrower_credit_score is None
        or terms.years_in_business is None
    )


def _is_non_loan_or_irrelevant_input(terms: ExtractedTerms) -> bool:
    return (
        terms.naics_code == "000000"
        and not terms.missing_documents
        and not terms.prior_default
        and terms.borrower_credit_score is None
        and terms.years_in_business is None
    )
