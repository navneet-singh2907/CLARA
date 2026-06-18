"""LLM-as-judge scaffolding for loan review outputs."""

import json
from dataclasses import asdict, dataclass
from typing import Any

from loan_pipeline.config import get_settings
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

All score values MUST be integers between 1 and 5. Do not use words like "high" or "low".
1 = very poor, 2 = below average, 3 = average, 4 = good, 5 = excellent.

Return JSON only. Example of correct format (replace values with your actual scores):
{{
  "faithfulness": 4,
  "completeness": 3,
  "risk_calibration": 5,
  "compliance_accuracy": 4,
  "explainability": 5,
  "overall_score": 4,
  "major_failure_category": "None",
  "rationale": "One sentence explaining the scores."
}}
"""

PACKET_JUDGE_PROMPT_TEMPLATE = """You are independently evaluating a generated small-business loan review packet.

Score each dimension from 1 to 5:

1. Faithfulness:
Are the packet claims internally grounded in cited loan terms, findings, and evidence?

2. Completeness:
Does the packet include the key borrower terms, compliance findings, risk rationale, outcome, and human-review context?

3. Risk calibration:
Is the risk rating justified by the evidence in the packet?

4. Compliance accuracy:
Are compliance concerns clear, evidence-backed, and free of unsupported flags?

5. Explainability:
Could a loan officer understand and act on this packet?

Review packet text:
{packet_text}

All score values MUST be integers between 1 and 5. Do not use words like "high" or "low".
1 = very poor, 2 = below average, 3 = average, 4 = good, 5 = excellent.

Return JSON only. Example of correct format:
{{
  "faithfulness": 4,
  "completeness": 4,
  "risk_calibration": 5,
  "compliance_accuracy": 4,
  "explainability": 5,
  "overall_score": 4,
  "major_failure_category": "None",
  "rationale": "One sentence explaining the scores."
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


def build_packet_judge_prompt(packet_text: str) -> str:
    return PACKET_JUDGE_PROMPT_TEMPLATE.format(packet_text=packet_text.strip()[:12000])


def parse_judge_response(raw_response: str) -> JudgeScore:
    try:
        payload = json.loads(_extract_json_object(raw_response))
    except json.JSONDecodeError as exc:
        raise ValueError("Judge response must be valid JSON.") from exc

    return validate_judge_payload(payload)


def run_configured_primary_judge(
    loan_case: LoanCase,
    packet: ReviewPacket,
    gold: GoldLabel,
) -> JudgeScore:
    settings = get_settings()
    if settings.primary_judge_model:
        return run_model_judge(loan_case, packet, gold, settings.primary_judge_model)
    return run_local_judge(loan_case, packet, gold)


def run_configured_secondary_judge(
    loan_case: LoanCase,
    packet: ReviewPacket,
    gold: GoldLabel,
) -> JudgeScore:
    settings = get_settings()
    if settings.secondary_judge_model:
        return run_model_judge(loan_case, packet, gold, settings.secondary_judge_model)
    return run_strict_local_judge(loan_case, packet, gold)


def run_model_judge(
    loan_case: LoanCase,
    packet: ReviewPacket,
    gold: GoldLabel,
    model: str,
) -> JudgeScore:
    settings = get_settings()
    if not settings.llm_api_key:
        raise RuntimeError("Live judge models require LLM_API_KEY, NEBIUS_API_KEY, or OPENAI_API_KEY.")

    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=model,
        temperature=settings.judge_temperature,
    )
    response = llm.invoke(build_judge_prompt(loan_case, packet, gold))
    content = response.content if hasattr(response, "content") else str(response)
    if not isinstance(content, str):
        content = str(content)
    return parse_judge_response(content)


def run_configured_primary_packet_judge(packet_text: str) -> JudgeScore:
    settings = get_settings()
    if settings.primary_judge_model:
        return run_model_packet_judge(packet_text, settings.primary_judge_model)
    return run_local_packet_judge(packet_text)


def run_configured_secondary_packet_judge(packet_text: str) -> JudgeScore:
    settings = get_settings()
    if settings.secondary_judge_model:
        return run_model_packet_judge(packet_text, settings.secondary_judge_model)
    return run_strict_local_packet_judge(packet_text)


def run_model_packet_judge(packet_text: str, model: str) -> JudgeScore:
    settings = get_settings()
    if not settings.llm_api_key:
        raise RuntimeError("Live packet judges require LLM_API_KEY, NEBIUS_API_KEY, or OPENAI_API_KEY.")

    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        model=model,
        temperature=settings.judge_temperature,
    )
    response = llm.invoke(build_packet_judge_prompt(packet_text))
    content = response.content if hasattr(response, "content") else str(response)
    if not isinstance(content, str):
        content = str(content)
    return parse_judge_response(content)


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
        value = _coerce_score(payload[field])
        if not 1 <= value <= 5:
            raise ValueError(f"Judge field '{field}' must be an integer from 1 to 5.")
        payload[field] = value

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


def _extract_json_object(content: str) -> str:
    stripped = _strip_json_fence(content)
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return stripped
    return stripped[start : end + 1]


def _strip_json_fence(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    return stripped


_QUALITATIVE_SCORE_MAP = {
    "very poor": 1, "very low": 1, "poor": 1,
    "below average": 2, "low": 2,
    "average": 3, "moderate": 3, "medium": 3, "fair": 3,
    "good": 4, "high": 4, "above average": 4,
    "excellent": 5, "very high": 5, "very good": 5, "perfect": 5,
}


def _coerce_score(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("Judge score must not be a boolean.")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
        mapped = _QUALITATIVE_SCORE_MAP.get(stripped.lower())
        if mapped is not None:
            return mapped
    raise ValueError(f"Judge score {value!r} could not be converted to an integer from 1 to 5.")


def run_local_packet_judge(packet_text: str) -> JudgeScore:
    text = packet_text.lower()
    has_terms = all(keyword in text for keyword in ["borrower", "loan amount", "term"])
    has_risk = "risk" in text and ("rationale" in text or "risk factor" in text)
    has_compliance = "compliance" in text
    has_outcome = "recommended outcome" in text or "outcome" in text
    has_audit = "audit" in text or "human review" in text

    faithfulness = 4 if has_terms and has_outcome else 3
    completeness = 5 if has_terms and has_risk and has_compliance and has_audit else 4
    risk_calibration = 4 if has_risk else 3
    compliance_accuracy = 4 if has_compliance else 3
    explainability = 5 if has_outcome and has_risk else 4
    dimensions = [
        faithfulness,
        completeness,
        risk_calibration,
        compliance_accuracy,
        explainability,
    ]
    overall_score = round(sum(dimensions) / len(dimensions))
    return JudgeScore(
        faithfulness=faithfulness,
        completeness=completeness,
        risk_calibration=risk_calibration,
        compliance_accuracy=compliance_accuracy,
        explainability=explainability,
        overall_score=overall_score,
        major_failure_category="None" if overall_score >= 4 else "Packet completeness",
        rationale=(
            "Local packet judge scored the uploaded review packet for internal grounding, "
            "risk/compliance clarity, and loan-officer usability."
        ),
    )


def run_strict_local_packet_judge(packet_text: str) -> JudgeScore:
    primary_score = run_local_packet_judge(packet_text)
    faithfulness = max(1, primary_score.faithfulness - 1)
    risk_calibration = max(1, primary_score.risk_calibration - 1)
    dimensions = [
        faithfulness,
        primary_score.completeness,
        risk_calibration,
        primary_score.compliance_accuracy,
        primary_score.explainability,
    ]
    return JudgeScore(
        faithfulness=faithfulness,
        completeness=primary_score.completeness,
        risk_calibration=risk_calibration,
        compliance_accuracy=primary_score.compliance_accuracy,
        explainability=primary_score.explainability,
        overall_score=round(sum(dimensions) / len(dimensions)),
        major_failure_category=primary_score.major_failure_category,
        rationale=(
            "Strict local packet judge applies an extra penalty where packet evidence "
            "does not fully prove faithfulness or risk calibration."
        ),
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
