"""Rules-first compliance checks for the Cupcake MVP."""

from src.schemas.loan import ComplianceFinding, ComplianceResult, ExtractedTerms


def check_compliance(terms: ExtractedTerms) -> ComplianceResult:
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

