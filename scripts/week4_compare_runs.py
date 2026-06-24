"""Generate the Week 4 baseline-vs-improved delta report."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loan_pipeline.eval.week4_compare import generate_week4_improvement_report


def main() -> None:
    print(generate_week4_improvement_report())


if __name__ == "__main__":
    main()
