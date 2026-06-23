"""Upload the Week 4 CLARA golden dataset to LangSmith."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from loan_pipeline.eval.week4_dataset import upload_week4_dataset_to_langsmith

if __name__ == "__main__":
    dataset_id = upload_week4_dataset_to_langsmith()
    print(f"Uploaded CLARA Week 4 dataset: {dataset_id}")
