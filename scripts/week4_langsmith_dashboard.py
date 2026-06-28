"""Create the Week 4 LangSmith baseline-vs-improved dashboard."""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=True)

from loan_pipeline.eval.week4_compare import DEFAULT_IMPROVED_PATH  # noqa: E402
from loan_pipeline.eval.week4_historical_baseline import (  # noqa: E402
    DEFAULT_HISTORICAL_BASELINE_PATH,
)
from loan_pipeline.eval.week4_langsmith_dashboard import (  # noqa: E402
    DEFAULT_LANGSMITH_DATASET_NAME,
    DEFAULT_LANGSMITH_PROJECT_NAME,
    create_week4_langsmith_dashboard,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a LangSmith project that compares CLARA baseline and improved runs."
    )
    parser.add_argument("--baseline-path", type=Path, default=DEFAULT_HISTORICAL_BASELINE_PATH)
    parser.add_argument("--improved-path", type=Path, default=DEFAULT_IMPROVED_PATH)
    parser.add_argument("--dataset-name", default=DEFAULT_LANGSMITH_DATASET_NAME)
    parser.add_argument("--project-name", default=DEFAULT_LANGSMITH_PROJECT_NAME)
    args = parser.parse_args()

    result = create_week4_langsmith_dashboard(
        baseline_path=args.baseline_path,
        improved_path=args.improved_path,
        dataset_name=args.dataset_name,
        project_name=args.project_name,
    )
    print(json.dumps(result, indent=2))
    print(
        "Open LangSmith and select the project above to view baseline and improved "
        "summary runs against the same Week 4 dataset."
    )


if __name__ == "__main__":
    main()
