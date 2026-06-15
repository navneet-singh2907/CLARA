"""Credit Risk Scorer Agent."""

from loan_pipeline.graph.state import ExtractedTerms, RiskResult


def run_credit_risk_scorer(terms: ExtractedTerms) -> RiskResult:
    points = 1
    primary_risk_factors: list[str] = []
    mitigating_factors: list[str] = []

    if terms.borrower_credit_score is None:
        points += 1
        primary_risk_factors.append("Credit score is missing.")
    elif terms.borrower_credit_score < 640:
        points += 2
        primary_risk_factors.append("Borrower credit score is below 640.")
    elif terms.borrower_credit_score >= 700:
        mitigating_factors.append("Borrower credit score is above 700.")

    if terms.years_in_business is None:
        points += 1
        primary_risk_factors.append("Years in business is missing.")
    elif terms.years_in_business < 2:
        points += 1
        primary_risk_factors.append("Business has less than two years operating history.")
    elif terms.years_in_business >= 5:
        mitigating_factors.append("Business has at least five years operating history.")

    if terms.prior_default:
        points += 2
        primary_risk_factors.append("Prior default is disclosed.")

    if terms.loan_amount >= 750000:
        points += 1
        primary_risk_factors.append("Loan amount is high for manual-review threshold.")

    if terms.jobs_supported >= 10:
        mitigating_factors.append("Application supports at least ten jobs.")

    score = min(points, 5)
    if score >= 4:
        band = "HIGH"
    elif score >= 3:
        band = "MEDIUM"
    else:
        band = "LOW"

    confidence = 0.85
    if terms.borrower_credit_score is None or terms.years_in_business is None:
        confidence -= 0.15

    rationale = (
        f"Risk score {score}/5 based on credit profile, operating history, prior default, "
        "loan size, and job support."
    )

    return RiskResult(
        score=score,
        band=band,
        confidence=max(confidence, 0.50),
        primary_risk_factors=primary_risk_factors,
        mitigating_factors=mitigating_factors,
        rationale=rationale,
    )

