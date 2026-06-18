"""Compliance Checker Agent."""

from loan_pipeline.config import get_settings
from loan_pipeline.graph.state import (
    ComplianceFinding,
    ComplianceResult,
    ExtractedTerms,
    ReviewPolicy,
)
from loan_pipeline.llm.client import add_llm_compliance_note
from loan_pipeline.review.policies import get_policy_profile


def run_compliance_checker(
    terms: ExtractedTerms,
    review_policy: ReviewPolicy = "sba_reviewer",
) -> ComplianceResult:
    result = run_compliance_checker_deterministic(terms, review_policy=review_policy)
    if get_settings().use_llm_agents:
        return add_llm_compliance_note(terms, result)
    return result


def run_compliance_checker_deterministic(
    terms: ExtractedTerms,
    review_policy: ReviewPolicy = "sba_reviewer",
) -> ComplianceResult:
    profile = get_policy_profile(review_policy)
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

    if terms.guarantee_ratio > profile.compliance_guarantee_review_threshold:
        severity = "HIGH" if terms.guarantee_ratio > profile.compliance_guarantee_high_threshold else "MEDIUM"
        findings.append(
            ComplianceFinding(
                rule_id="SBA-001",
                severity=severity,
                description=f"SBA guarantee ratio exceeds {profile.label} review tolerance.",
                evidence=f"guarantee_ratio={terms.guarantee_ratio:.2%}",
            )
        )

    if terms.prior_default:
        findings.append(
            ComplianceFinding(
                rule_id="HIST-001",
                severity=profile.prior_default_severity,
                description=f"Prior default disclosed under {profile.label} review policy.",
                evidence="prior_default=True",
            )
        )

    has_high = any(finding.severity == "HIGH" for finding in findings)
    status = "FAIL" if has_high else "REVIEW" if findings else "PASS"
    confidence = 0.90 if findings else 0.95

    return ComplianceResult(status=status, findings=findings, confidence=confidence)
