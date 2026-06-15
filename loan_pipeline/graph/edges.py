"""Graph edge names for the review pipeline.

The Cupcake MVP runs these nodes directly. The next iteration will map this
same topology into a compiled LangGraph StateGraph.
"""

START = "loan_case"
TERM_EXTRACTOR = "term_extractor"
VALIDATOR = "schema_validator"
COMPLIANCE_CHECKER = "compliance_checker"
CREDIT_RISK_SCORER = "credit_risk_scorer"
ORCHESTRATOR = "orchestrator"
END = "human_review_packet"

PIPELINE_EDGES = [
    (START, TERM_EXTRACTOR),
    (TERM_EXTRACTOR, VALIDATOR),
    (VALIDATOR, COMPLIANCE_CHECKER),
    (VALIDATOR, CREDIT_RISK_SCORER),
    (COMPLIANCE_CHECKER, ORCHESTRATOR),
    (CREDIT_RISK_SCORER, ORCHESTRATOR),
    (ORCHESTRATOR, END),
]

