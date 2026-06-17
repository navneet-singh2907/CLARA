"""SBA public data loader tests."""

from loan_pipeline.data.load_sba_public import normalize_sba_rows


def test_normalize_sba_rows_maps_common_foia_columns() -> None:
    cases = normalize_sba_rows(
        [
            {
                "LoanNr_ChkDgt": "123456",
                "BorrName": "Sample Bakery LLC",
                "NAICSCode": "311811",
                "GrAppv": "$185,000",
                "SBA_Appv": "$138,750",
                "TermInMonths": "84",
                "CreateJob": "4",
                "RetainedJob": "7",
                "MIS_Status": "PIF",
            }
        ]
    )

    loan_case = cases[0]

    assert loan_case.case_id == "123456"
    assert loan_case.borrower_name == "Sample Bakery LLC"
    assert loan_case.naics_code == "311811"
    assert loan_case.loan_amount == 185000
    assert loan_case.sba_guaranteed_amount == 138750
    assert loan_case.term_months == 84
    assert loan_case.jobs_supported == 11
    assert not loan_case.prior_default
    assert loan_case.difficulty_tier == "public_import"


def test_normalize_sba_rows_flags_charge_off_status() -> None:
    cases = normalize_sba_rows(
        [
            {
                "BorrName": "Defaulted Import Co.",
                "NAICSCode": "423990",
                "GrAppv": "780000",
                "SBA_Appv": "741000",
                "TermInMonths": "48",
                "CreateJob": "1",
                "RetainedJob": "2",
                "MIS_Status": "CHGOFF",
            }
        ]
    )

    assert cases[0].prior_default


def test_normalize_sba_rows_marks_missing_core_numeric_fields() -> None:
    cases = normalize_sba_rows(
        [
            {
                "BorrName": "Sparse SBA Row",
                "NAICSCode": "",
                "GrAppv": "",
                "SBA_Appv": "",
                "TermInMonths": "",
            }
        ]
    )

    assert "loan_amount" in cases[0].missing_documents
    assert "sba_guaranteed_amount" in cases[0].missing_documents
    assert "term_months" in cases[0].missing_documents

