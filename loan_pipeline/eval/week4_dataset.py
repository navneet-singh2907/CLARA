"""Week 4 LangSmith-ready dataset export utilities."""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from loan_pipeline.config import WEEK4_GOLD_SET_JSON, WEEK4_SBA_LOANS_CSV, load_sba_demo_cases
from loan_pipeline.eval.run_eval import load_gold_labels

DEFAULT_EXPORT_PATH = Path("output") / "week4" / "clara_week4_langsmith_dataset.jsonl"
WEEK4_DATASET_VERSION = "clara-week4-v1"


def build_week4_dataset_records(
    cases_path: Path = WEEK4_SBA_LOANS_CSV,
    gold_path: Path = WEEK4_GOLD_SET_JSON,
) -> list[dict[str, Any]]:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases(cases_path)}
    records = []
    for label in load_gold_labels(gold_path):
        loan_case = cases[label.case_id]
        records.append(
            {
                "id": label.case_id,
                "inputs": {
                    "loan_case": asdict(loan_case),
                    "review_policy": "sba_reviewer",
                },
                "outputs": {
                    "expected_compliance_status": label.expected_compliance_status,
                    "expected_risk_band": label.expected_risk_band,
                    "expected_escalation": label.expected_escalation,
                    "expected_outcome": label.expected_outcome,
                },
                "metadata": {
                    "dataset_version": WEEK4_DATASET_VERSION,
                    "tier": label.tier,
                    "scenario_type": _scenario_type(label.tier),
                    "source": "CLARA Week 4 controlled SBA-style evaluation set",
                },
            }
        )
    return records


def export_week4_dataset_jsonl(output_path: Path = DEFAULT_EXPORT_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    records = build_week4_dataset_records()
    with output_path.open("w", encoding="utf-8") as jsonl_file:
        for record in records:
            jsonl_file.write(json.dumps(record) + "\n")
    return output_path


def upload_week4_dataset_to_langsmith(dataset_name: str = "CLARA Week 4 Loan Review Eval") -> str:
    """Upload the Week 4 dataset when the optional LangSmith SDK is installed.

    The JSONL export is the source of truth; this helper is intentionally optional
    so local tests and CI do not require network access or LangSmith credentials.
    """
    try:
        from langsmith import Client
    except ImportError as exc:
        raise RuntimeError("Install langsmith to upload the Week 4 dataset.") from exc

    client = Client()
    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description=(
            "50-case CLARA evaluation set: 30 Week 3 cases plus 10 edge, "
            "5 known-failure, and 5 adversarial robustness cases."
        ),
        metadata={
            "product": "CLARA",
            "dataset_version": WEEK4_DATASET_VERSION,
            "case_count": 50,
            "source": "repo-controlled SBA-style Week 4 gold set",
        },
    )
    for record in build_week4_dataset_records():
        client.create_example(
            dataset_id=dataset.id,
            inputs=record["inputs"],
            outputs=record["outputs"],
            metadata=record["metadata"],
        )
    return str(dataset.id)


def _scenario_type(tier: str) -> str:
    if tier == "clean":
        return "happy_path"
    if tier in {"ambiguous", "edge"}:
        return "edge_case"
    if tier == "known_failure":
        return "known_failure"
    return "adversarial"


if __name__ == "__main__":
    print(export_week4_dataset_jsonl())
