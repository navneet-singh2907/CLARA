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


def _print_progress(completed: int, total: int, current_case: str) -> None:
    print(f"[{completed}/{total}] current={current_case}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CLARA's Week 4 baseline eval.")
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_BASELINE_PATH,
        help="Where to write the JSON experiment artifact.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_MARKDOWN_PATH,
        help="Where to write the lightweight markdown summary.",
    )
    parser.add_argument(
        "--log-langsmith",
        action="store_true",
        help="Also log a summary run to LangSmith using configured credentials.",
    )
    parser.add_argument(
        "--langsmith-run-name",
        default="CLARA Week 4 Baseline",
        help="Run name to use when logging the summary to LangSmith.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live LLM and LangSmith settings from .env instead of reproducible offline mode.",
    )
    args = parser.parse_args()

    artifact = run_week4_baseline_experiment(
        output_path=args.output_path,
        report_path=args.report_path,
        use_live_runtime=args.live,
        progress_callback=_print_progress,
    )
    print(json.dumps(artifact["summary"], indent=2))
    print(f"JSON artifact: {args.output_path}")
    print(f"Markdown report: {args.report_path}")
    if args.log_langsmith:
        project = log_week4_experiment_to_langsmith(
            artifact,
            run_name=args.langsmith_run_name,
        )
        print(f"Logged summary run to LangSmith project: {project}")


if __name__ == "__main__":
    main()
