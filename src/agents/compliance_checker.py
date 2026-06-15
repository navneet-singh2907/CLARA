"""Compliance checker agent wrapper."""

from src.rules.compliance_rules import check_compliance
from src.schemas.loan import ComplianceResult, ExtractedTerms


def run_compliance_checker(terms: ExtractedTerms) -> ComplianceResult:
    return check_compliance(terms)

