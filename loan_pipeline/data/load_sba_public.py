"""Normalize downloaded SBA FOIA CSV exports into internal loan cases."""

import csv
from pathlib import Path
from typing import Iterable

from loan_pipeline.graph.state import LoanCase

ColumnAliases = dict[str, tuple[str, ...]]

SBA_COLUMN_ALIASES: ColumnAliases = {
    "case_id": ("LoanNr_ChkDgt", "loan_number", "case_id"),
    "borrower_name": ("BorrName", "borrower_name", "BorrowerName"),
    "industry": ("NAICSDescription", "industry", "Industry"),
    "naics_code": ("NAICSCode", "NAICS", "naics_code"),
    "loan_amount": ("GrAppv", "gross_approval", "loan_amount"),
    "sba_guaranteed_amount": ("SBA_Appv", "sba_approval", "sba_guaranteed_amount"),
    "term_months": ("TermInMonths", "Term", "term_months"),
    "jobs_created": ("CreateJob", "jobs_created"),
    "jobs_retained": ("RetainedJob", "jobs_retained"),
    "status": ("MIS_Status", "status"),
}


def load_sba_public_cases(path: Path, limit: int | None = None) -> list[LoanCase]:
    with path.open(newline="", encoding="utf-8-sig") as csv_file:
        rows = csv.DictReader(csv_file)
        cases = [_row_to_case(row, index) for index, row in enumerate(rows, start=1)]

    if limit is not None:
        return cases[:limit]
    return cases


def normalize_sba_rows(rows: Iterable[dict[str, str]]) -> list[LoanCase]:
    return [_row_to_case(row, index) for index, row in enumerate(rows, start=1)]


def _row_to_case(row: dict[str, str], index: int) -> LoanCase:
    case_id = _get(row, "case_id") or f"SBA-{index:06d}"
    borrower_name = _get(row, "borrower_name") or "Unknown Borrower"
    naics_code = _digits(_get(row, "naics_code")) or "000000"
    industry = _get(row, "industry") or f"NAICS {naics_code}"
    loan_amount = _money(_get(row, "loan_amount"))
    sba_guaranteed_amount = _money(_get(row, "sba_guaranteed_amount"))
    term_months = _int(_get(row, "term_months"), default=0)
    jobs_supported = _int(_get(row, "jobs_created"), default=0) + _int(
        _get(row, "jobs_retained"),
        default=0,
    )
    status = (_get(row, "status") or "").upper()

    missing_documents = []
    if loan_amount <= 0:
        missing_documents.append("loan_amount")
    if sba_guaranteed_amount <= 0:
        missing_documents.append("sba_guaranteed_amount")
    if term_months <= 0:
        missing_documents.append("term_months")

    return LoanCase(
        case_id=case_id,
        borrower_name=borrower_name,
        industry=industry,
        naics_code=naics_code,
        loan_amount=loan_amount,
        sba_guaranteed_amount=sba_guaranteed_amount,
        term_months=term_months,
        jobs_supported=jobs_supported,
        borrower_credit_score=None,
        years_in_business=None,
        prior_default=status in {"CHGOFF", "CHARGE OFF", "CHARGED OFF"},
        missing_documents=missing_documents,
        notes="Normalized from downloaded SBA FOIA public data.",
        difficulty_tier="public_import",
    )


def _get(row: dict[str, str], canonical_name: str) -> str:
    for alias in SBA_COLUMN_ALIASES[canonical_name]:
        if alias in row and row[alias] is not None:
            return str(row[alias]).strip()
    return ""


def _money(value: str) -> float:
    clean = value.replace("$", "").replace(",", "").strip()
    if not clean:
        return 0.0
    return float(clean)


def _int(value: str, default: int) -> int:
    clean = value.replace(",", "").strip()
    if not clean:
        return default
    return int(float(clean))


def _digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())

