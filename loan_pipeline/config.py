"""Project configuration and local data helpers."""

import csv
from pathlib import Path

from loan_pipeline.graph.state import LoanCase

PROJECT_ROOT = Path(__file__).resolve().parent
SBA_LOANS_CSV = PROJECT_ROOT / "data" / "sba_loans.csv"
GOLD_SET_JSON = PROJECT_ROOT / "eval" / "gold_set.json"


def load_sba_demo_cases(path: Path = SBA_LOANS_CSV) -> list[LoanCase]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        rows = csv.DictReader(csv_file)
        return [_row_to_loan_case(row) for row in rows]


def _row_to_loan_case(row: dict[str, str]) -> LoanCase:
    credit_score = row["borrower_credit_score"].strip()
    years_in_business = row["years_in_business"].strip()
    missing_documents = row["missing_documents"].strip()

    return LoanCase(
        case_id=row["case_id"],
        borrower_name=row["borrower_name"],
        industry=row["industry"],
        naics_code=row["naics_code"],
        loan_amount=float(row["loan_amount"]),
        sba_guaranteed_amount=float(row["sba_guaranteed_amount"]),
        term_months=int(row["term_months"]),
        jobs_supported=int(row["jobs_supported"]),
        borrower_credit_score=int(credit_score) if credit_score else None,
        years_in_business=float(years_in_business) if years_in_business else None,
        prior_default=row["prior_default"].lower() == "true",
        missing_documents=missing_documents.split("|") if missing_documents else [],
        notes=row["notes"],
        difficulty_tier=row["difficulty_tier"],
    )

