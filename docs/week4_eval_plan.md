# CLARA Week 4 Evaluation Plan

## Evaluation One-Liner

I will measure loan-review correctness, compliance finding accuracy, risk calibration, faithfulness, trajectory quality, latency, and cost on CLARA using a 50-case golden dataset covering clean, ambiguous, edge, known-failure, and adversarial loan-review scenarios, with exact-match evaluators, code-based trajectory checks, LLM-as-judge scoring, and LangSmith tracing. Pass bar: at least 90% final outcome accuracy, at least 85% compliance and risk accuracy, 4/5 or higher average judge faithfulness, visible trace coverage for every agent step, and a measured baseline-to-improvement delta.

## Agent Under Test

CLARA - Credit Loan Analysis & Review Agent. The system uses LangGraph to coordinate a Term Extractor, Schema Validator, Compliance Checker, Credit Risk Scorer, and Review Synthesizer for small business loan review.

## User Outcome

A loan officer should be able to use CLARA's review packet to decide whether a small business loan should be approved, escalated, or rejected, while seeing why the system reached that recommendation and when human override is required.

## Golden Dataset

Week 4 uses a 50-case controlled SBA-style dataset:

| Scenario type | Count | Purpose |
| --- | ---: | --- |
| Clean | 10 | Well-formed cases that should be approved. |
| Ambiguous | 10 | Existing Week 3 cases with missing fields, incomplete documents, or borderline signals. |
| Adversarial | 15 | Original 10 adversarial cases plus 5 wrong-format, prompt-injection, irrelevant-input, and malformed cases. |
| Edge | 10 | Partial data, ambiguous terms, conflicting clauses, and missing fields. |
| Known failure | 5 | Cases designed around places CLARA may miscalibrate risk or over-escalate from Week 3 behavior. |

Files:

- `loan_pipeline/data/week4_sba_loans.csv`
- `loan_pipeline/eval/week4_gold_set.json`
- `loan_pipeline/eval/week4_dataset.py`

Local export command:

```powershell
.\.venv\Scripts\python.exe scripts\week4_export_dataset.py
```

LangSmith upload command:

```powershell
.\.venv\Scripts\python.exe scripts\week4_upload_dataset.py
```

## Metrics

| Metric | Evaluator type | Why it matters |
| --- | --- | --- |
| Final outcome accuracy | Exact match | Measures whether the final decision is usable. |
| Compliance status accuracy | Exact match | Measures whether blockers are caught. |
| Risk band accuracy | Exact match | Measures whether underwriting severity is calibrated. |
| Escalation accuracy | Exact match | Measures whether human review is triggered at the right time. |
| Term extraction accuracy | Code-based | Ensures core loan fields are grounded in the case. |
| Trajectory correctness | Code-based | Verifies the LangGraph path actually ran the expected agents. |
| Faithfulness | LLM-as-judge | Measures whether claims are supported by source case data. |
| Explainability | LLM-as-judge | Measures whether a loan officer can act on the output. |
| Latency and cost | LangSmith run metadata | Prevents quality gains from hiding cost regressions. |

## LangSmith Instrumentation

Every baseline and post-improvement run should trace:

- Top-level CLARA pipeline run
- Term Extractor
- Schema Validator
- Compliance Checker
- Credit Risk Scorer
- Review Synthesizer
- LLM judge calls
- Runtime metadata: model, latency, token usage, cost, errors

LangSmith project name:

```text
CLARA Week 4 Eval Lab
```

## MCP Usage Plan

MCP is part of the evaluation operations layer, not a side note.

| MCP/tooling layer | Used for | Evidence produced |
| --- | --- | --- |
| Browser MCP | Verify deployed CLARA UI, progress bars, SSE traces, and packet download flow. | Screenshots for report and Loom. |
| PDF/Docs MCP | Generate the final board-style evaluation report. | `docs/week4_eval_report.pdf` |
| Filesystem/code tools | Create reproducible dataset/evaluator scripts. | Repo files and CI output. |
| LangSmith SDK/UI | Store dataset, run baseline/post-improvement evals, compare runs. | LangSmith project and run links. |

## Baseline Run

The baseline run uses the current CLARA behavior before improvements. It should report:

- Overall metric table
- Metric breakdown by scenario type
- Top 3 failure clusters
- Representative LangSmith trace per failure cluster
- p50/p95 latency
- cost per run

Local baseline command:

```powershell
.\.venv\Scripts\python.exe scripts\week4_run_baseline.py
```

Live LLM + LangSmith tracing command:

```powershell
.\.venv\Scripts\python.exe scripts\week4_run_baseline.py --live --log-langsmith
```

## Failure Taxonomy

Failures will be clustered as:

- Extraction failure
- Compliance miss
- Risk miscalibration
- Orchestration or trajectory failure
- Faithfulness or unsupported rationale
- Judge disagreement
- Document quality or malformed input failure

## Targeted Improvements

Pick 3 to 4 changes only after the baseline failure clusters are visible.

Candidate improvements:

1. Refine compliance prompt/rule checklist for missing ownership, tax, contract, and license evidence.
2. Tune credit risk calibration for high-guarantee cases with strong mitigating factors.
3. Add stricter extraction validation for malformed, irrelevant, or prompt-injection documents.
4. Refine LLM-as-judge rubric and compare primary vs secondary judge disagreement.

Each improvement must include a hypothesis and measured delta.

## Winning Section: When Should CLARA Not Be Trusted?

The final report should explicitly identify cases where CLARA should not be allowed to auto-approve:

- High agent disagreement
- Low extraction confidence
- Low risk confidence
- Judge disagreement above one point
- Drift across repeated LLM runs
- Escalation required with high-severity compliance findings

This turns the project from "my agent works" into "my evaluation system knows when my agent is unsafe."

## Deliverables

- Week 4 evaluation report
- 50-case golden dataset
- LangSmith dataset and project link
- Baseline run link
- Post-improvement run link
- Failure cluster table
- Improvement delta table
- Loom walkthrough
