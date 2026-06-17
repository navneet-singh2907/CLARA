"""Detect contradictions between specialist agent outputs."""

from dataclasses import dataclass
from typing import Literal

from loan_pipeline.graph.state import ComplianceResult, RiskResult

ContradictionSeverity = Literal["LOW", "MEDIUM", "HIGH"]


@dataclass(frozen=True)
class AgentContradiction:
    severity: ContradictionSeverity
    title: str
    compliance_position: str
    risk_position: str
    reviewer_prompt: str


def detect_contradictions(
    compliance: ComplianceResult,
    risk: RiskResult,
) -> list[AgentContradiction]:
    contradictions: list[AgentContradiction] = []

    if compliance.status == "FAIL" and risk.band in {"LOW", "MEDIUM"}:
        contradictions.append(
            AgentContradiction(
                severity="HIGH",
                title="Compliance blocker conflicts with non-high credit risk.",
                compliance_position=_summarize_compliance(compliance),
                risk_position=_summarize_risk(risk),
                reviewer_prompt=(
                    "Review whether documentation or eligibility issues should override "
                    "the credit-risk band before any recommendation is accepted."
                ),
            )
        )

    if compliance.status == "PASS" and risk.band == "HIGH":
        contradictions.append(
            AgentContradiction(
                severity="MEDIUM",
                title="High credit risk with no compliance blocker.",
                compliance_position=_summarize_compliance(compliance),
                risk_position=_summarize_risk(risk),
                reviewer_prompt=(
                    "Review whether the high risk score is driven by credit factors rather "
                    "than missing or noncompliant documentation."
                ),
            )
        )

    if compliance.status == "REVIEW" and risk.band == "LOW":
        contradictions.append(
            AgentContradiction(
                severity="MEDIUM",
                title="Compliance review required despite low credit risk.",
                compliance_position=_summarize_compliance(compliance),
                risk_position=_summarize_risk(risk),
                reviewer_prompt=(
                    "Review whether low credit risk is sufficient to proceed while "
                    "compliance findings remain unresolved."
                ),
            )
        )

    return contradictions


def _summarize_compliance(compliance: ComplianceResult) -> str:
    if not compliance.findings:
        return f"Compliance status {compliance.status} with no findings."
    findings = "; ".join(
        f"{finding.rule_id}({finding.severity}): {finding.description}"
        for finding in compliance.findings
    )
    return f"Compliance status {compliance.status}: {findings}"


def _summarize_risk(risk: RiskResult) -> str:
    factors = "; ".join(risk.primary_risk_factors) or "No primary risk factors."
    mitigants = "; ".join(risk.mitigating_factors) or "No mitigating factors."
    return f"Risk band {risk.band}, score {risk.score}/5. Factors: {factors}. Mitigants: {mitigants}"

