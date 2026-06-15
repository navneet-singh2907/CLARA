"""Graph node names and edge topology for the review pipeline."""

START = "loan_case"
TERM_EXTRACTOR = "term_extractor"
VALIDATOR = "schema_validator"
COMPLIANCE_CHECKER = "compliance_checker"
CREDIT_RISK_SCORER = "credit_risk_scorer"
SYNTHESIZER = "review_synthesizer"
END = "human_review_packet"

PIPELINE_EDGES = [
    (START, TERM_EXTRACTOR),
    (TERM_EXTRACTOR, VALIDATOR),
    (VALIDATOR, COMPLIANCE_CHECKER),
    (VALIDATOR, CREDIT_RISK_SCORER),
    (COMPLIANCE_CHECKER, SYNTHESIZER),
    (CREDIT_RISK_SCORER, SYNTHESIZER),
    (SYNTHESIZER, END),
]
