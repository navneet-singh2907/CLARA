"""Credit Risk Scorer Agent."""

from loan_pipeline.config import get_settings
from loan_pipeline.graph.state import ExtractedTerms, ReviewPolicy, RiskResult
from loan_pipeline.llm.client import add_llm_risk_rationale
from loan_pipeline.review.policies import get_policy_profile


def run_credit_risk_scorer(
    terms: ExtractedTerms,
    review_policy: ReviewPolicy = "sba_reviewer",
) -> RiskResult:
    result = run_credit_risk_scorer_deterministic(terms, review_policy=review_policy)
    if get_settings().use_llm_agents:
        return add_llm_risk_rationale(terms, result)
    return result


def run_credit_risk_scorer_deterministic(
    terms: ExtractedTerms,
    review_policy: ReviewPolicy = "sba_reviewer",
) -> RiskResult:
    profile = get_policy_profile(review_policy)
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

    if profile.mission_impact_credit and terms.jobs_supported >= profile.mission_jobs_threshold:
        points -= profile.mission_impact_credit
        mitigating_factors.append(
            f"{profile.label} policy credits strong mission/job impact."
        )

    score = min(max(points, 1), 5)
    if score >= profile.high_risk_min_score:
        band = "HIGH"
    elif score >= profile.medium_risk_min_score:
        band = "MEDIUM"
    else:
        band = "LOW"

    confidence = 0.85
    if terms.borrower_credit_score is None or terms.years_in_business is None:
        confidence -= 0.15

    rationale = (
        f"Risk score {score}/5 based on credit profile, operating history, prior default, "
        f"loan size, job support, and {profile.label} tolerance."
    )

    return RiskResult(
        score=score,
        band=band,
        confidence=max(confidence, 0.50),
        primary_risk_factors=primary_risk_factors,
        mitigating_factors=mitigating_factors,
        rationale=rationale,
    )
