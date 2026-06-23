"""Run the Week 4 CLARA baseline experiment."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loan_pipeline.eval.week4_experiment import (
    DEFAULT_BASELINE_PATH,
    DEFAULT_MARKDOWN_PATH,
    log_week4_experiment_to_langsmith,
    run_week4_baseline_experiment,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CLARA's Week 4 baseline eval.")
    parser.add_argument(
        "--log-langsmith",
        action="store_true",
        help="Also log a summary run to LangSmith using configured credentials.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live LLM and LangSmith settings from .env instead of reproducible offline mode.",
    )
    args = parser.parse_args()

    artifact = run_week4_baseline_experiment(use_live_runtime=args.live)
    print(json.dumps(artifact["summary"], indent=2))
    print(f"JSON artifact: {DEFAULT_BASELINE_PATH}")
    print(f"Markdown report: {DEFAULT_MARKDOWN_PATH}")
    if args.log_langsmith:
        project = log_week4_experiment_to_langsmith(artifact)
        print(f"Logged summary run to LangSmith project: {project}")


if __name__ == "__main__":
    main()
