"""LLM-as-judge scaffolding for loan review outputs."""

import json
from dataclasses import asdict, dataclass
from typing import Any

from loan_pipeline.eval.metrics import GoldLabel
from loan_pipeline.graph.state import LoanCase, ReviewPacket

JUDGE_DIMENSIONS = [
    "faithfulness",
    "completeness",
    "risk_calibration",
    "compliance_accuracy",
    "explainability",
]

JUDGE_PROMPT_TEMPLATE = """You are evaluating a loan review agent output.

Score each dimension from 1 to 5:

1. Faithfulness:
Are all claims grounded in the source loan record and extracted fields?

2. Completeness:
Were all key loan terms, borrower details, risk indicators, and compliance-relevant facts captured?

3. Risk calibration:
Is the risk rating justified by the available evidence?

4. Compliance accuracy:
Were the correct compliance concerns identified without unsupported flags?

5. Explainability:
Could a loan officer understand and act on this output?

Source loan record:
{source_document}

Agent output:
{agent_output}

Gold answer:
{gold_answer}

Return JSON only with this schema:
{{
  "faithfulness": 1,
  "completeness": 1,
  "risk_calibration": 1,
  "compliance_accuracy": 1,
  "explainability": 1,
  "overall_score": 1,
  "major_failure_category": "",
  "rationale": ""
}}
"""


@dataclass(frozen=True)
class JudgeScore:
    faithfulness: int
    completeness: int
    risk_calibration: int
    compliance_accuracy: int
    explainability: int
    overall_score: int
    major_failure_category: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_judge_prompt(loan_case: LoanCase, packet: ReviewPacket, gold: GoldLabel) -> str:
    return JUDGE_PROMPT_TEMPLATE.format(
        source_document=json.dumps(asdict(loan_case), indent=2),
        agent_output=json.dumps(asdict(packet), indent=2),
        gold_answer=json.dumps(asdict(gold), indent=2),
    )


def parse_judge_response(raw_response: str) -> JudgeScore:
    try:
        payload = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError("Judge response must be valid JSON.") from exc

    return validate_judge_payload(payload)


def validate_judge_payload(payload: dict[str, Any]) -> JudgeScore:
    required_fields = [
        *JUDGE_DIMENSIONS,
        "overall_score",
        "major_failure_category",
        "rationale",
    ]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        raise ValueError(f"Judge response missing required fields: {', '.join(missing)}.")

    for field in [*JUDGE_DIMENSIONS, "overall_score"]:
        value = payload[field]
        if not isinstance(value, int) or not 1 <= value <= 5:
            raise ValueError(f"Judge field '{field}' must be an integer from 1 to 5.")

    if not isinstance(payload["major_failure_category"], str):
        raise ValueError("Judge field 'major_failure_category' must be a string.")

    if not isinstance(payload["rationale"], str) or not payload["rationale"].strip():
        raise ValueError("Judge field 'rationale' must be a non-empty string.")

    return JudgeScore(
        faithfulness=payload["faithfulness"],
        completeness=payload["completeness"],
        risk_calibration=payload["risk_calibration"],
        compliance_accuracy=payload["compliance_accuracy"],
        explainability=payload["explainability"],
        overall_score=payload["overall_score"],
        major_failure_category=payload["major_failure_category"],
        rationale=payload["rationale"],
    )


def run_local_judge(loan_case: LoanCase, packet: ReviewPacket, gold: GoldLabel) -> JudgeScore:
    faithfulness = 5 if packet.extracted_terms.case_id == loan_case.case_id else 2
    completeness = 4 if packet.extracted_terms.confidence >= 0.80 else 3
    risk_calibration = 5 if packet.risk.band == gold.expected_risk_band else 2
    compliance_accuracy = 5 if packet.compliance.status == gold.expected_compliance_status else 2
    explainability = 5 if packet.summary and packet.risk.rationale else 3

    dimensions = [
        faithfulness,
        completeness,
        risk_calibration,
        compliance_accuracy,
        explainability,
    ]
    overall_score = round(sum(dimensions) / len(dimensions))
    major_failure_category = _major_failure_category(
        risk_calibration=risk_calibration,
        compliance_accuracy=compliance_accuracy,
        completeness=completeness,
    )

    return JudgeScore(
        faithfulness=faithfulness,
        completeness=completeness,
        risk_calibration=risk_calibration,
        compliance_accuracy=compliance_accuracy,
        explainability=explainability,
        overall_score=overall_score,
        major_failure_category=major_failure_category,
        rationale=(
            "Local judge scaffold scored the output using deterministic checks against "
            "the loan case, review packet, and gold label."
        ),
    )


def run_strict_local_judge(loan_case: LoanCase, packet: ReviewPacket, gold: GoldLabel) -> JudgeScore:
    primary_score = run_local_judge(loan_case, packet, gold)
    completeness = primary_score.completeness
    risk_calibration = primary_score.risk_calibration
    explainability = primary_score.explainability

    if packet.extracted_terms.confidence < 0.80:
        completeness = max(1, completeness - 1)

    if loan_case.difficulty_tier == "adversarial" and packet.risk.band != gold.expected_risk_band:
        risk_calibration = 1

    if packet.escalation_required and not packet.human_review_notes:
        explainability = max(1, explainability - 1)

    dimensions = [
        primary_score.faithfulness,
        completeness,
        risk_calibration,
        primary_score.compliance_accuracy,
        explainability,
    ]

    return JudgeScore(
        faithfulness=primary_score.faithfulness,
        completeness=completeness,
        risk_calibration=risk_calibration,
        compliance_accuracy=primary_score.compliance_accuracy,
        explainability=explainability,
        overall_score=round(sum(dimensions) / len(dimensions)),
        major_failure_category=_major_failure_category(
            risk_calibration=risk_calibration,
            compliance_accuracy=primary_score.compliance_accuracy,
            completeness=completeness,
        ),
        rationale=(
            "Strict local judge scaffold applies a harsher penalty for low-confidence "
            "extraction and adversarial risk miscalibration."
        ),
    )


def _major_failure_category(
    risk_calibration: int,
    compliance_accuracy: int,
    completeness: int,
) -> str:
    if risk_calibration < 4:
        return "Risk Calibration Failure"
    if compliance_accuracy < 4:
        return "Compliance Failure"
    if completeness < 4:
        return "Extraction Failure"
    return "None"
