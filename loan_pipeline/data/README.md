# Data Sources

## Curated Working Set

`sba_loans.csv` is the project's stable 30-case working set. It is intentionally small so the evaluation harness, ablation study, judge scaffold, and Streamlit demo remain deterministic.

## Public SBA FOIA Data

The official public source for larger raw data exports is the SBA Open Data dataset:

```text
7(a) & 504 FOIA
https://data.sba.gov/dataset/7-a-504-foia
```

The SBA dataset provides segmented CSV files for 7(a) and 504 loans, plus a data dictionary. The project loader in `load_sba_public.py` normalizes SBA FOIA-style columns into the internal `LoanCase` schema.

Downloaded raw exports should be stored as local files such as:

```text
loan_pipeline/data/foia_7a_2020_present.downloaded.csv
```

Files matching `*.downloaded.csv` and `*.local.csv` are ignored by Git.

## Recommended V2 Upgrade

For a stronger CV artifact, use the loader to create a second public-data-derived evaluation set:

- Download a recent SBA 7(a) FOIA export.
- Normalize it with `load_sba_public.py`.
- Select a balanced sample across approval size, industry, jobs supported, and outcome/default signals.
- Preserve missing underwriting fields as missing instead of inventing them.
- Hand-label the final cases before adding them to the gold set.

The existing 30-case set should remain as the stable regression benchmark.
