"""Credit risk scorer agent wrapper."""

from src.rules.risk_features import score_credit_risk
from src.schemas.loan import ExtractedTerms, RiskResult


def run_credit_risk_scorer(terms: ExtractedTerms) -> RiskResult:
    return score_credit_risk(terms)

