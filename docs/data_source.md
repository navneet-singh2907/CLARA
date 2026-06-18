# Public SBA Data Source

The project targets the official SBA Open Data `7(a) & 504 FOIA` dataset:

```text
https://data.sba.gov/dataset/7-a-504-foia
```

The dataset contains segmented CSV exports for SBA 7(a) and 504 loan programs and a data dictionary. The SBA page states that 7(a) files are segmented by decade, 504 files by twenty-year periods, and the FOIA data is updated quarterly.

## Current Project Data

The current `loan_pipeline/data/sba_loans.csv` file is a curated 30-case working set with:

- 10 clean cases
- 10 ambiguous cases
- 10 adversarial cases

This file is deliberately stable so evaluation metrics and demos remain reproducible.

## Loader Strategy

`loan_pipeline/data/load_sba_public.py` supports normalizing downloaded SBA FOIA CSV exports into the internal `LoanCase` schema.

The loader accepts common SBA FOIA columns such as:

- borrower name
- NAICS code
- gross approval amount
- SBA approval amount
- loan term
- jobs created / retained
- loan status

Fields unavailable in FOIA exports, such as borrower credit score and years in business, are set to `None`. This is intentional: missing underwriting fields should become part of the review and escalation story rather than being silently invented.

## Gold Set Policy

The 30-case gold set should not be automatically overwritten by public data imports. Public data imports are used to create candidate records. Human adjudication is still required before a case enters the gold set.

## V2 Public Data Ingestion Roadmap

The current project uses a controlled SBA-style seed set so the bootcamp demo and evaluation report are reproducible. A production-grade portfolio extension should add a larger public-data workflow:

1. Download current SBA 7(a) and 504 FOIA CSV exports from the official SBA Open Data page.
2. Store raw downloads locally as `*.downloaded.csv` files so they stay out of Git.
3. Normalize FOIA columns with `loan_pipeline/data/load_sba_public.py`.
4. Filter candidate loans by program, industry, approval amount, term, charge-off/default status, and jobs supported.
5. Generate draft case narratives from public fields, explicitly marking missing underwriting fields as unknown.
6. Human-adjudicate a new gold set before adding labels.
7. Re-run evaluation, ablation, drift, calibration, and judge agreement against both the curated seed set and the public-data-derived set.

This keeps the current 30-case benchmark honest while creating a clear path toward real public SBA evaluation coverage.
