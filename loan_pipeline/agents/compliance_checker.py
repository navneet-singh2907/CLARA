"""Compliance Checker Agent."""

from loan_pipeline.config import get_settings
from loan_pipeline.graph.state import ComplianceFinding, ComplianceResult, ExtractedTerms
from loan_pipeline.llm.client import add_llm_compliance_note


def run_compliance_checker(terms: ExtractedTerms) -> ComplianceResult:
    result = run_compliance_checker_deterministic(terms)
    if get_settings().use_llm_agents:
        return add_llm_compliance_note(terms, result)
    return result


def run_compliance_checker_deterministic(terms: ExtractedTerms) -> ComplianceResult:
    findings: list[ComplianceFinding] = []

    if terms.missing_documents:
        findings.append(
            ComplianceFinding(
                rule_id="DOC-001",
                severity="HIGH",
                description="Required loan documentation is missing.",
                evidence=", ".join(terms.missing_documents),
            )
        )

    if terms.borrower_credit_score is None:
        findings.append(
            ComplianceFinding(
                rule_id="KYC-001",
                severity="MEDIUM",
                description="Borrower credit report is unavailable for review.",
                evidence="borrower_credit_score is missing",
            )
        )

    if terms.guarantee_ratio > 0.90:
        findings.append(
            ComplianceFinding(
                rule_id="SBA-001",
                severity="MEDIUM",
                description="SBA guarantee ratio is unusually high and requires review.",
                evidence=f"guarantee_ratio={terms.guarantee_ratio:.2%}",
            )
        )

    if terms.prior_default:
        findings.append(
            ComplianceFinding(
                rule_id="HIST-001",
                severity="HIGH",
                description="Prior default disclosed; human review required.",
                evidence="prior_default=True",
            )
        )

    has_high = any(finding.severity == "HIGH" for finding in findings)
    status = "FAIL" if has_high else "REVIEW" if findings else "PASS"
    confidence = 0.90 if findings else 0.95

    return ComplianceResult(status=status, findings=findings, confidence=confidence)
