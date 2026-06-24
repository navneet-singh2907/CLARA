"""Generate the Week 4 baseline evaluation report."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loan_pipeline.eval.week4_report import generate_week4_baseline_report

if __name__ == "__main__":
    print(generate_week4_baseline_report())
