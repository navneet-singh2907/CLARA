"""Drift detection for repeated loan review runs."""

import hashlib
import json
from dataclasses import asdict
from typing import Iterable

from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.graph.orchestrator import run_pipeline
from loan_pipeline.graph.state import LoanCase, ReviewPacket


def run_drift_study(repeats: int = 5, case_ids: Iterable[str] | None = None) -> dict[str, object]:
    if repeats < 2:
        raise ValueError("Drift study requires at least two repeats.")

    selected_case_ids = set(case_ids or [])
    cases = [
        loan_case
        for loan_case in load_sba_demo_cases()
        if not selected_case_ids or loan_case.case_id in selected_case_ids
    ]

    rows = [_case_drift_row(loan_case, repeats) for loan_case in cases]
    drifting_cases = [row for row in rows if row["variant_count"] > 1]

    return {
        "cases": len(rows),
        "repeats": repeats,
        "stable_cases": len(rows) - len(drifting_cases),
        "drifting_cases": len(drifting_cases),
        "stability_rate": round((len(rows) - len(drifting_cases)) / len(rows), 4) if rows else 0.0,
        "rows": rows,
    }


def fingerprint_review_packet(packet: ReviewPacket) -> str:
    payload = {
        "review_policy": packet.review_policy,
        "extracted_terms": asdict(packet.extracted_terms),
        "recommended_outcome": packet.recommended_outcome,
        "escalation_required": packet.escalation_required,
        "compliance_status": packet.compliance.status,
        "compliance_findings": [asdict(finding) for finding in packet.compliance.findings],
        "risk_score": packet.risk.score,
        "risk_band": packet.risk.band,
        "risk_factors": packet.risk.primary_risk_factors,
        "mitigating_factors": packet.risk.mitigating_factors,
        "human_review_notes": packet.human_review_notes,
        "contradictions": [asdict(item) for item in packet.contradictions],
        "counterfactuals": [asdict(item) for item in packet.counterfactuals],
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12]


def _case_drift_row(loan_case: LoanCase, repeats: int) -> dict[str, object]:
    fingerprints = [fingerprint_review_packet(run_pipeline(loan_case)) for _ in range(repeats)]
    variant_count = len(set(fingerprints))
    return {
        "case_id": loan_case.case_id,
        "tier": loan_case.difficulty_tier,
        "runs": repeats,
        "variant_count": variant_count,
        "stable": variant_count == 1,
        "fingerprints": fingerprints,
    }


if __name__ == "__main__":
    print(json.dumps(run_drift_study(), indent=2))
