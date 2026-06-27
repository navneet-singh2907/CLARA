"""LangSmith dashboard helpers for Week 4 baseline-vs-improved experiments."""

import json
from pathlib import Path
from typing import Any, Protocol

from loan_pipeline.eval.week4_compare import DEFAULT_IMPROVED_PATH
from loan_pipeline.eval.week4_dataset import WEEK4_DATASET_VERSION, build_week4_dataset_records
from loan_pipeline.eval.week4_historical_baseline import (
    DEFAULT_HISTORICAL_BASELINE_PATH,
    load_or_create_week4_historical_baseline,
)

DEFAULT_LANGSMITH_DATASET_NAME = "CLARA Week 4 Loan Review Eval"
DEFAULT_LANGSMITH_PROJECT_NAME = "CLARA Week 4 Baseline vs Improved"


class LangSmithClientProtocol(Protocol):
    """Small protocol so tests can verify LangSmith behavior without network calls."""

    def read_dataset(self, *, dataset_name: str) -> Any: ...

    def create_dataset(self, dataset_name: str, **kwargs: Any) -> Any: ...

    def create_example(self, **kwargs: Any) -> Any: ...

    def read_project(self, *, project_name: str, include_stats: bool = False) -> Any: ...

    def create_project(self, project_name: str, **kwargs: Any) -> Any: ...

    def create_run(self, name: str, inputs: dict[str, Any], run_type: str, **kwargs: Any) -> None: ...


def create_week4_langsmith_dashboard(
    baseline_path: Path = DEFAULT_HISTORICAL_BASELINE_PATH,
    improved_path: Path = DEFAULT_IMPROVED_PATH,
    *,
    dataset_name: str = DEFAULT_LANGSMITH_DATASET_NAME,
    project_name: str = DEFAULT_LANGSMITH_PROJECT_NAME,
    client: LangSmithClientProtocol | None = None,
) -> dict[str, Any]:
    """Create a LangSmith project with comparable baseline and improved summary runs."""
    langsmith_client = client or _default_langsmith_client()
    dataset_id = ensure_week4_langsmith_dataset(langsmith_client, dataset_name)

    ensure_week4_langsmith_project(
        langsmith_client,
        project_name=project_name,
        dataset_id=dataset_id,
    )

    baseline = _load_artifact(baseline_path, "baseline")
    improved = _load_artifact(improved_path, "improved")

    baseline_run = log_week4_artifact_to_langsmith(
        langsmith_client,
        baseline,
        project_name=project_name,
        run_label="baseline",
        dataset_id=dataset_id,
        artifact_path=baseline_path,
    )
    improved_run = log_week4_artifact_to_langsmith(
        langsmith_client,
        improved,
        project_name=project_name,
        run_label="improved",
        dataset_id=dataset_id,
        artifact_path=improved_path,
    )

    return {
        "project_name": project_name,
        "dataset_name": dataset_name,
        "dataset_version": WEEK4_DATASET_VERSION,
        "dataset_id": str(dataset_id),
        "runs": [baseline_run, improved_run],
    }


def ensure_week4_langsmith_dataset(
    client: LangSmithClientProtocol,
    dataset_name: str = DEFAULT_LANGSMITH_DATASET_NAME,
) -> str:
    """Return an existing LangSmith dataset id or create the Week 4 dataset."""
    try:
        dataset = client.read_dataset(dataset_name=dataset_name)
        return str(dataset.id)
    except Exception:
        dataset = client.create_dataset(
            dataset_name,
            description=(
                "50-case CLARA loan review evaluation dataset with clean, ambiguous, "
                "edge, known-failure, and adversarial cases."
            ),
            metadata={
                "product": "CLARA",
                "case_count": 50,
                "dataset_version": WEEK4_DATASET_VERSION,
                "source": "repo-controlled SBA-style Week 4 gold set",
            },
        )

    dataset_id = str(dataset.id)
    for record in build_week4_dataset_records():
        client.create_example(
            dataset_id=dataset_id,
            inputs=record["inputs"],
            outputs=record["outputs"],
            metadata=record["metadata"],
        )
    return dataset_id


def ensure_week4_langsmith_project(
    client: LangSmithClientProtocol,
    *,
    project_name: str,
    dataset_id: str,
) -> str:
    """Create or reuse the LangSmith project used for the before/after dashboard."""
    metadata = {
        "product": "CLARA",
        "week": "4",
        "evaluation_type": "baseline_vs_improved",
        "dataset_version": WEEK4_DATASET_VERSION,
    }
    try:
        project = client.create_project(
            project_name,
            description=(
                "CLARA Week 4 dashboard comparing baseline and targeted improved runs "
                "on the same 50-case loan review evaluation dataset."
            ),
            metadata=metadata,
            upsert=True,
            reference_dataset_id=dataset_id,
        )
    except Exception as exc:
        if "already exists" not in str(exc).lower() and "409" not in str(exc):
            raise
        project = client.read_project(project_name=project_name, include_stats=False)
    return str(project.id)


def log_week4_artifact_to_langsmith(
    client: LangSmithClientProtocol,
    artifact: dict[str, Any],
    *,
    project_name: str,
    run_label: str,
    dataset_id: str,
    artifact_path: Path,
) -> dict[str, str]:
    """Log one experiment artifact as a comparable LangSmith summary run."""
    experiment = artifact["experiment"]
    run_name = f"CLARA Week 4 {run_label.title()} - {experiment['runtime']}"
    client.create_run(
        name=run_name,
        inputs={
            "dataset": experiment["dataset"],
            "dataset_id": dataset_id,
            "dataset_version": experiment["dataset_version"],
            "case_count": experiment["case_count"],
            "runtime": experiment["runtime"],
            "artifact_path": str(artifact_path),
        },
        outputs=artifact["summary"],
        run_type="chain",
        project_name=project_name,
        tags=["clara", "week4", "eval-dashboard", run_label],
        extra={
            "metadata": {
                "experiment_name": experiment["name"],
                "created_at": experiment["created_at"],
                "case_count": experiment["case_count"],
                "dataset_version": experiment["dataset_version"],
                "dataset_id": dataset_id,
                "artifact_path": str(artifact_path),
            }
        },
    )
    return {"label": run_label, "run_name": run_name}


def _default_langsmith_client() -> Any:
    try:
        from langsmith import Client
    except ImportError as exc:
        raise RuntimeError("Install langsmith to create the Week 4 LangSmith dashboard.") from exc

    return Client()


def _load_artifact(path: Path, label: str) -> dict[str, Any]:
    if label == "baseline" and path == DEFAULT_HISTORICAL_BASELINE_PATH and not path.exists():
        return load_or_create_week4_historical_baseline(source_path=DEFAULT_IMPROVED_PATH)
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {label} artifact at {path}. Run the Week 4 experiment first."
        )
    return json.loads(path.read_text(encoding="utf-8"))
