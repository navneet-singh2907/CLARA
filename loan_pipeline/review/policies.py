"""Reviewer policy profiles for institutional review modes."""

from dataclasses import dataclass

from loan_pipeline.graph.state import ReviewPolicy


@dataclass(frozen=True)
class PolicyProfile:
    policy: ReviewPolicy
    label: str
    compliance_guarantee_review_threshold: float
    compliance_guarantee_high_threshold: float
    prior_default_severity: str
    high_risk_min_score: int
    medium_risk_min_score: int
    mission_jobs_threshold: int
    mission_impact_credit: int
    note: str


POLICY_PROFILES: dict[ReviewPolicy, PolicyProfile] = {
    "sba_reviewer": PolicyProfile(
        policy="sba_reviewer",
        label="SBA Reviewer",
        compliance_guarantee_review_threshold=0.90,
        compliance_guarantee_high_threshold=1.01,
        prior_default_severity="HIGH",
        high_risk_min_score=4,
        medium_risk_min_score=3,
        mission_jobs_threshold=10,
        mission_impact_credit=0,
        note="Balanced eligibility and documentation review using the baseline SBA-style policy.",
    ),
    "bank_underwriter": PolicyProfile(
        policy="bank_underwriter",
        label="Bank Underwriter",
        compliance_guarantee_review_threshold=0.85,
        compliance_guarantee_high_threshold=0.95,
        prior_default_severity="HIGH",
        high_risk_min_score=3,
        medium_risk_min_score=2,
        mission_jobs_threshold=10,
        mission_impact_credit=0,
        note="Stricter repayment-risk posture with lower tolerance for credit and exposure risk.",
    ),
    "cdfi_lender": PolicyProfile(
        policy="cdfi_lender",
        label="CDFI Lender",
        compliance_guarantee_review_threshold=0.95,
        compliance_guarantee_high_threshold=1.01,
        prior_default_severity="MEDIUM",
        high_risk_min_score=5,
        medium_risk_min_score=3,
        mission_jobs_threshold=8,
        mission_impact_credit=1,
        note="Mission-oriented review with more flexibility for remediable risk and job impact.",
    ),
}


def get_policy_profile(review_policy: ReviewPolicy) -> PolicyProfile:
    return POLICY_PROFILES[review_policy]
