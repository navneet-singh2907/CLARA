"""Generate actionable counterfactual explanations for loan review outcomes."""

from dataclasses import dataclass
from typing import Literal

from loan_pipeline.graph.state import ComplianceResult, ExtractedTerms, RiskResult

CounterfactualType = Literal["DOCUMENTATION", "CREDIT", "OPERATING_HISTORY", "DEFAULT_HISTORY"]


@dataclass(frozen=True)
class CounterfactualExplanation:
    type: CounterfactualType
    title: str
    current_state: str
    suggested_change: str
    expected_effect: str


def generate_counterfactuals(
    terms: ExtractedTerms,
    compliance: ComplianceResult,
    risk: RiskResult,
) -> list[CounterfactualExplanation]:
    counterfactuals: list[CounterfactualExplanation] = []

    if terms.missing_documents:
        counterfactuals.append(
            CounterfactualExplanation(
                type="DOCUMENTATION",
                title="Supply missing required documents.",
                current_state=f"Missing documents: {', '.join(terms.missing_documents)}.",
                suggested_change="Submit all missing documentation before final underwriting.",
                expected_effect=(
                    "The compliance blocker would be eligible for re-review and may move "
                    "from FAIL to PASS if no other findings remain."
                ),
            )
        )

    if terms.borrower_credit_score is None:
        counterfactuals.append(
            CounterfactualExplanation(
                type="CREDIT",
                title="Provide borrower credit evidence.",
                current_state="Borrower credit score is missing.",
                suggested_change="Provide an owner credit report with a score at or above 680.",
                expected_effect=(
                    "The risk model would remove the missing-credit penalty and may reduce "
                    "the risk band if other risk factors are limited."
                ),
            )
        )
    elif terms.borrower_credit_score < 640:
        counterfactuals.append(
            CounterfactualExplanation(
                type="CREDIT",
                title="Improve borrower credit score.",
                current_state=f"Borrower credit score is {terms.borrower_credit_score}.",
                suggested_change="Improve or document credit strength to at least 680.",
                expected_effect=(
                    "The risk model would remove the sub-640 credit penalty and may reduce "
                    f"the current {risk.band} risk band."
                ),
            )
        )

    if terms.years_in_business is None:
        counterfactuals.append(
            CounterfactualExplanation(
                type="OPERATING_HISTORY",
                title="Document operating history.",
                current_state="Years in business is missing.",
                suggested_change="Provide formation records, tax filings, or operating history evidence.",
                expected_effect="The risk model would remove the missing operating-history penalty.",
            )
        )
    elif terms.years_in_business < 2:
        counterfactuals.append(
            CounterfactualExplanation(
                type="OPERATING_HISTORY",
                title="Offset short operating history.",
                current_state=f"Business operating history is {terms.years_in_business:.1f} years.",
                suggested_change=(
                    "Provide signed contracts, collateral support, or guarantor strength to "
                    "offset limited operating history."
                ),
                expected_effect=(
                    "The risk model would still note limited history, but the reviewer would "
                    "have specific mitigating evidence to consider."
                ),
            )
        )

    if terms.prior_default:
        counterfactuals.append(
            CounterfactualExplanation(
                type="DEFAULT_HISTORY",
                title="Resolve prior default concern.",
                current_state="Prior default is disclosed.",
                suggested_change="Provide default resolution, repayment, settlement, or cure documentation.",
                expected_effect=(
                    "The compliance and risk review could distinguish unresolved default risk "
                    "from a cured historical issue."
                ),
            )
        )

    return counterfactuals

