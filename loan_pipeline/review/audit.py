"""Human override audit helpers."""

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from loan_pipeline.graph.state import HumanOverride

OverrideTarget = Literal["COMPLIANCE", "RISK", "CONTRADICTION", "COUNTERFACTUAL", "OUTCOME"]


def create_human_override(
    *,
    case_id: str,
    target_type: OverrideTarget,
    target_id: str,
    original_value: str,
    override_decision: str,
    rationale: str,
    reviewer: str,
) -> HumanOverride:
    return HumanOverride(
        entry_id=str(uuid4()),
        case_id=case_id,
        target_type=target_type,
        target_id=target_id,
        original_value=original_value,
        override_decision=override_decision,
        rationale=rationale.strip(),
        reviewer=reviewer.strip() or "Human reviewer",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
