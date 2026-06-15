"""Small in-repo cases for the Cupcake MVP."""

from src.schemas.loan import LoanCase


SAMPLE_CASES: list[LoanCase] = [
    LoanCase(
        case_id="CLEAN-001",
        borrower_name="River City Bakery LLC",
        industry="Retail bakery",
        naics_code="311811",
        loan_amount=185000.00,
        sba_guaranteed_amount=138750.00,
        term_months=84,
        jobs_supported=11,
        borrower_credit_score=724,
        years_in_business=6.5,
        prior_default=False,
        missing_documents=[],
        notes="Stable local bakery requesting working capital and oven upgrades.",
        difficulty_tier="clean",
    ),
    LoanCase(
        case_id="AMB-001",
        borrower_name="Northline Fabrication Co.",
        industry="Light manufacturing",
        naics_code="332312",
        loan_amount=640000.00,
        sba_guaranteed_amount=544000.00,
        term_months=120,
        jobs_supported=22,
        borrower_credit_score=None,
        years_in_business=1.2,
        prior_default=False,
        missing_documents=["owner_credit_report"],
        notes="Application references pending contracts but omits owner credit report.",
        difficulty_tier="ambiguous",
    ),
    LoanCase(
        case_id="ADV-001",
        borrower_name="Summit Event Holdings",
        industry="Event venue management",
        naics_code="711310",
        loan_amount=950000.00,
        sba_guaranteed_amount=902500.00,
        term_months=36,
        jobs_supported=4,
        borrower_credit_score=608,
        years_in_business=0.8,
        prior_default=True,
        missing_documents=["tax_returns", "beneficial_ownership_certification"],
        notes=(
            "Narrative emphasizes projected revenue but discloses prior default and missing "
            "beneficial ownership certification in the final paragraph."
        ),
        difficulty_tier="adversarial",
    ),
]


def get_sample_case(case_id: str) -> LoanCase:
    for loan_case in SAMPLE_CASES:
        if loan_case.case_id == case_id:
            return loan_case
    raise ValueError(f"Unknown sample case: {case_id}")

