"""Export the Week 4 CLARA dataset as LangSmith-ready JSONL."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loan_pipeline.eval.week4_dataset import export_week4_dataset_jsonl

if __name__ == "__main__":
    print(export_week4_dataset_jsonl())
