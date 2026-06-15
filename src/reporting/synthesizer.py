"""Generate a human review packet from agent outputs."""

from src.schemas.loan import ComplianceResult, ExtractedTerms, ReviewPacket, RiskResult


def synthesize_review_packet(
    terms: ExtractedTerms,
    compliance: ComplianceResult,
    risk: RiskResult,
    validation_errors: list[str],
) -> ReviewPacket:
    human_review_notes: list[str] = []

    if validation_errors:
        human_review_notes.extend(validation_errors)

    if compliance.status == "FAIL":
        human_review_notes.append("Compliance blocker or high-severity finding requires review.")

    if risk.band == "HIGH":
        human_review_notes.append("High credit risk requires loan officer review.")

    if terms.confidence < 0.80:
        human_review_notes.append("Extraction confidence is below target threshold.")

    escalation_required = bool(human_review_notes)

    if validation_errors or compliance.status == "FAIL" or risk.band == "HIGH":
        recommended_outcome = "ESCALATE"
    elif compliance.status == "REVIEW" or risk.band == "MEDIUM":
        recommended_outcome = "CONDITIONAL_REVIEW"
    else:
        recommended_outcome = "APPROVE"

    summary = (
        f"{terms.borrower_name} is classified as {risk.band} risk with compliance status "
        f"{compliance.status}. Recommended outcome: {recommended_outcome}."
    )

    return ReviewPacket(
        case_id=terms.case_id,
        recommended_outcome=recommended_outcome,
        escalation_required=escalation_required,
        summary=summary,
        extracted_terms=terms,
        compliance=compliance,
        risk=risk,
        human_review_notes=human_review_notes,
    )
