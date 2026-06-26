"""Week 4 LangSmith dashboard tests."""

import copy
import json
from types import SimpleNamespace

from loan_pipeline.eval.week4_dataset import WEEK4_DATASET_VERSION
from loan_pipeline.eval.week4_experiment import run_week4_baseline_experiment
from loan_pipeline.eval.week4_langsmith_dashboard import create_week4_langsmith_dashboard


class FakeLangSmithClient:
    def __init__(self) -> None:
        self.datasets = {}
        self.examples = []
        self.projects = []
        self.runs = []

    def read_dataset(self, *, dataset_name: str):
        if dataset_name not in self.datasets:
            raise KeyError(dataset_name)
        return self.datasets[dataset_name]

    def create_dataset(self, dataset_name: str, **kwargs):
        dataset = SimpleNamespace(id="dataset-123", name=dataset_name, kwargs=kwargs)
        self.datasets[dataset_name] = dataset
        return dataset

    def create_example(self, **kwargs):
        self.examples.append(kwargs)
        return SimpleNamespace(id=f"example-{len(self.examples)}")

    def create_project(self, project_name: str, **kwargs):
        self.projects.append({"project_name": project_name, **kwargs})
        return SimpleNamespace(id="project-123", name=project_name)

    def create_run(self, name: str, inputs: dict, run_type: str, **kwargs) -> None:
        self.runs.append(
            {
                "name": name,
                "inputs": inputs,
                "run_type": run_type,
                **kwargs,
            }
        )


def test_week4_langsmith_dashboard_logs_baseline_and_improved_runs(tmp_path) -> None:
    baseline_path = tmp_path / "baseline.json"
    improved_path = tmp_path / "improved.json"
    report_path = tmp_path / "baseline.md"

    baseline = run_week4_baseline_experiment(
        output_path=baseline_path,
        report_path=report_path,
    )
    improved = copy.deepcopy(baseline)
    improved["experiment"]["name"] = "CLARA Week 4 Improved"
    improved["summary"]["accuracy"]["overall"]["risk_band_accuracy"] = 1.0
    improved_path.write_text(json.dumps(improved), encoding="utf-8")

    fake_client = FakeLangSmithClient()

    result = create_week4_langsmith_dashboard(
        baseline_path=baseline_path,
        improved_path=improved_path,
        client=fake_client,
    )

    assert result["dataset_id"] == "dataset-123"
    assert result["project_name"] == "CLARA Week 4 Baseline vs Improved"
    assert len(fake_client.examples) == 50
    assert len(fake_client.projects) == 1
    assert fake_client.projects[0]["reference_dataset_id"] == "dataset-123"
    assert fake_client.projects[0]["metadata"]["dataset_version"] == WEEK4_DATASET_VERSION
    assert len(fake_client.runs) == 2
    assert fake_client.runs[0]["inputs"]["dataset_version"] == WEEK4_DATASET_VERSION
    assert fake_client.runs[0]["tags"] == ["clara", "week4", "eval-dashboard", "baseline"]
    assert fake_client.runs[1]["tags"] == ["clara", "week4", "eval-dashboard", "improved"]
