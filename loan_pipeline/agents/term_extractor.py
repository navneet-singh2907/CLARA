"""Term Extractor Agent."""

from loan_pipeline.config import get_settings
from loan_pipeline.graph.state import ExtractedTerms, LoanCase
from loan_pipeline.llm.client import extract_terms_with_llm


def extract_terms(loan_case: LoanCase) -> ExtractedTerms:
    if get_settings().use_llm_agents:
        return extract_terms_with_llm(loan_case)

    return extract_terms_deterministic(loan_case)


def extract_terms_deterministic(loan_case: LoanCase) -> ExtractedTerms:
    warnings: list[str] = []
    confidence = 0.95

    if loan_case.borrower_credit_score is None:
        warnings.append("Borrower credit score is missing.")
        confidence -= 0.15

    if loan_case.years_in_business is None:
        warnings.append("Years in business is missing.")
        confidence -= 0.10

    if loan_case.missing_documents:
        confidence -= min(0.20, 0.05 * len(loan_case.missing_documents))

    guarantee_ratio = (
        loan_case.sba_guaranteed_amount / loan_case.loan_amount if loan_case.loan_amount else 0.0
    )

    return ExtractedTerms(
        case_id=loan_case.case_id,
        borrower_name=loan_case.borrower_name,
        industry=loan_case.industry,
        naics_code=loan_case.naics_code,
        loan_amount=loan_case.loan_amount,
        sba_guaranteed_amount=loan_case.sba_guaranteed_amount,
        guarantee_ratio=round(guarantee_ratio, 4),
        term_months=loan_case.term_months,
        jobs_supported=loan_case.jobs_supported,
        borrower_credit_score=loan_case.borrower_credit_score,
        years_in_business=loan_case.years_in_business,
        prior_default=loan_case.prior_default,
        missing_documents=list(loan_case.missing_documents),
        confidence=max(confidence, 0.40),
        warnings=warnings,
    )
