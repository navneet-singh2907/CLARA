# CLARA Week 4 Submission Packet

This packet is the recommended review order for CLARA's Week 4 AI evaluation submission. It is designed so a judge can quickly understand the problem, inspect the evaluation evidence, and reproduce the measured improvement loop.

## 1. Start Here

Read: [Week 4 Submission Narrative](week4_submission.md)

This is the main story:

- what CLARA is,
- why loan review is high stakes,
- how the multi-agent graph works,
- how the 50-case golden dataset is structured,
- what failed in the baseline,
- which agents were responsible,
- what targeted change improved the system,
- what evidence shows no regressions.

## 2. Baseline Evidence

Read: [Week 4 Baseline Report](week4_baseline_report.md)

Baseline live LLM run:

| Metric | Result |
| --- | ---: |
| Final outcome accuracy | 98.00% |
| Compliance accuracy | 98.00% |
| Risk band accuracy | 98.00% |
| Failures | 3 |

Baseline failures:

| Case | Responsible agent | Failure type |
| --- | --- | --- |
| `AMB-003` | Review Synthesizer / Orchestrator | Escalation misclassification |
| `ADV2-003` | Compliance Checker Agent | Compliance misclassification |
| `KF-003` | Credit Risk Scorer Agent | Risk calibration failure |

## 3. Improvement Evidence

Read: [Week 4 Improvement Report](week4_improvement_report.md)

Improved live LLM run:

| Metric | Result |
| --- | ---: |
| Final outcome accuracy | 100.00% |
| Compliance accuracy | 100.00% |
| Risk band accuracy | 100.00% |
| Failures | 0 |
| New regressions | 0 |

The improvement loop is intentionally narrow: identify failure, attribute it to an agent, make one targeted calibration change, and rerun the same 50-case dataset.

## 4. LangSmith Evidence

LangSmith project:

```text
CLARA Week 4 Eval Lab
```

LangSmith dataset ID:

```text
ec7896af-7117-4f7e-8972-0dc37239036a
```

Use LangSmith to verify:

- traces are attached to live runs,
- evaluation examples map to the 50-case dataset,
- failures are visible at the case level,
- agent execution paths are observable instead of only final answers.

## 5. Reproduce Locally

Run from the repository root.

Export the 50-case dataset:

```powershell
.\.venv\Scripts\python.exe scripts\week4_export_dataset.py
```

Upload to LangSmith:

```powershell
.\.venv\Scripts\python.exe scripts\week4_upload_dataset.py
```

Run the live baseline:

```powershell
.\.venv\Scripts\python.exe scripts\week4_run_baseline.py --live --log-langsmith
```

Run the improved live evaluation:

```powershell
.\.venv\Scripts\python.exe scripts\week4_run_baseline.py --live --log-langsmith --output-path output\week4\clara_week4_improved.json --report-path output\week4\clara_week4_improved_report.md --langsmith-run-name "CLARA Week 4 Improved - Risk Calibration"
```

Generate the before/after delta:

```powershell
.\.venv\Scripts\python.exe scripts\week4_compare_runs.py
```

Run quality checks:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check loan_pipeline tests scripts
```

## 6. Reliability Hardening

CLARA includes reliability controls that make the live agent system easier to debug and safer to demo:

| Control | Why it matters |
| --- | --- |
| LLM timeout | Prevents slow provider calls from hanging a live run indefinitely. |
| Contextual LLM errors | Identifies the failing agent, case, operation, provider, model, and response preview. |
| Structured SSE errors | Keeps backend failures visible in the live timeline instead of hiding them in generic strings. |
| Upload size limit | Protects the API from oversized PDF/text uploads. |
| Uploaded document validation | Rejects incomplete loan packets before they reach the review graph. |
| Specialist failure recovery | Produces a conservative human-review packet if Compliance or Risk scoring fails. |

## 7. What This Proves

CLARA is not just a loan-review demo. It is an evaluation-driven multi-agent system with:

- a 50-case golden dataset,
- live LLM execution,
- LangSmith traceability,
- case-level failure attribution,
- agent-level failure categories,
- reliability controls for live agent failures,
- targeted improvement,
- before/after delta reporting,
- no-regression evidence.

That is the core Week 4 submission claim.
