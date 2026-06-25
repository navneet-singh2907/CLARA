# CLARA Week 4 Submission: Evaluation-Driven Multi-Agent Loan Review

## Project Summary

CLARA, short for Credit Loan Analysis & Review Agent, is a multi-agent small business loan review system. It uses LangGraph to coordinate specialist agents that extract loan terms, check compliance, score credit risk, synthesize a review packet, surface contradictions, generate counterfactual explanations, and support human override.

The Week 4 goal was not to add another feature. The goal was to prove that CLARA can be evaluated like a real decision-support system: with a golden dataset, traceable agent runs, failure attribution, and a measured baseline-to-improvement loop.

## Why This Problem Matters

A wrong loan review decision can affect whether a small business receives working capital, hires staff, survives a cash crunch, or gets escalated for human review. In this setting, a plausible-looking answer is not enough. The system must show:

- what each agent did,
- whether the final decision matched the expected label,
- which agent failed when the system was wrong,
- whether the fix improved the system without creating regressions.

That is the evaluation bar CLARA was built around.

## System Under Test

CLARA's Week 4 system under test is the same multi-agent loan review graph used in the application:

```text
Loan Case
  -> Term Extractor Agent
  -> Schema Validator
  -> Compliance Checker Agent
  -> Credit Risk Scorer Agent
  -> Review Synthesizer / Orchestrator
  -> Review Packet + Human Review Controls
```

The specialist review step runs compliance and risk scoring as parallel LangGraph branches. The final packet includes the recommended outcome, risk band, compliance status, escalation flag, contradiction checks, counterfactuals, and human-review notes.

## Evaluation Dataset

The Week 4 evaluation uses a 50-case controlled SBA-style golden dataset.

| Scenario type | Cases | Purpose |
| --- | ---: | --- |
| Clean | 10 | Straightforward cases the system should handle cleanly. |
| Ambiguous | 10 | Missing fields, borderline signals, or incomplete documents. |
| Adversarial | 15 | Buried clauses, prompt injection, malformed, or irrelevant inputs. |
| Edge | 10 | Partial data, conflicting terms, and unusual but plausible cases. |
| Known failure | 5 | Cases designed around Week 3 risk/compliance weaknesses. |

Dataset files:

- `loan_pipeline/data/week4_sba_loans.csv`
- `loan_pipeline/eval/week4_gold_set.json`
- `output/week4/clara_week4_langsmith_dataset.jsonl`

LangSmith dataset ID:

```text
ec7896af-7117-4f7e-8972-0dc37239036a
```

LangSmith project:

```text
CLARA Week 4 Eval Lab
```

## Metrics

CLARA is evaluated with exact-match, trajectory, trust-signal, and latency metrics.

| Metric | What it checks |
| --- | --- |
| Term extraction accuracy | Whether the extracted case terms match source fields. |
| Compliance status accuracy | Whether compliance status matches the gold label. |
| Risk band accuracy | Whether the underwriting severity matches the gold label. |
| Escalation accuracy | Whether human review is triggered when expected. |
| Final outcome accuracy | Whether the final recommendation is correct. |
| Trajectory correctness | Whether expected LangGraph agents ran successfully. |
| Trust-risk flags | Whether CLARA knows when not to silently auto-approve. |
| Latency | Whether quality gains hide performance regressions. |

## Baseline Run

The live LLM baseline was run across all 50 cases with LangSmith tracing.

| Metric | Baseline |
| --- | ---: |
| Term extraction accuracy | 100.00% |
| Compliance status accuracy | 98.00% |
| Risk band accuracy | 98.00% |
| Escalation accuracy | 98.00% |
| Final outcome accuracy | 98.00% |
| Trajectory correctness | 98.00% |

The baseline found three failures.

| Case | Responsible agent | Failure mode | Expected | Actual |
| --- | --- | --- | --- | --- |
| AMB-003 | Review Synthesizer / Orchestrator | Behavioral misclassification | Outcome APPROVE; escalation False | Outcome APPROVE; escalation True |
| ADV2-003 | Compliance Checker Agent | Behavioral misclassification | Compliance status PASS | Compliance status REVIEW |
| KF-003 | Credit Risk Scorer Agent | Behavioral misclassification | Risk band MEDIUM | Risk band LOW |

This is the key Week 4 point: CLARA did not only report that cases failed. It attributed each failure to the responsible graph agent.

## Failure Attribution Method

The evaluator separates two failure types:

| Failure type | Meaning |
| --- | --- |
| Runtime failure | An agent crashed or returned an execution error. |
| Behavioral failure | An agent ran successfully but produced the wrong judgment. |

The attribution rule is:

| Failed check | Responsible agent |
| --- | --- |
| Term extraction mismatch | Term Extractor Agent |
| Compliance mismatch | Compliance Checker Agent |
| Risk mismatch | Credit Risk Scorer Agent |
| Correct specialists but wrong outcome/escalation | Review Synthesizer / Orchestrator |
| Trace node status ERROR | Runtime failure at that graph node |

This makes the evaluation useful for engineering, not just scoring.

## Targeted Improvement

The baseline failures pointed to one improvement theme:

```text
Risk/compliance/orchestration calibration around borderline and malformed cases.
```

The targeted changes were:

1. Treat obvious non-loan or irrelevant inputs as intake-quality escalation instead of KYC compliance failure.
2. Add a narrower customer-contract risk rule only for large, young, weaker-credit borrowers.
3. Stop borderline extraction confidence alone from forcing escalation when the specialist agents agree the case is otherwise clean.

The goal was to fix the observed calibration weakness without broadly rewriting the system.

## Improved Run

The improved system was rerun on the same 50-case dataset with live LLM agents and LangSmith logging.

| Metric | Baseline | Improved | Delta |
| --- | ---: | ---: | ---: |
| Final outcome accuracy | 98.00% | 100.00% | +2.00 pp |
| Compliance accuracy | 98.00% | 100.00% | +2.00 pp |
| Risk band accuracy | 98.00% | 100.00% | +2.00 pp |
| Escalation accuracy | 98.00% | 100.00% | +2.00 pp |
| Known-failure risk accuracy | 80.00% | 100.00% | +20.00 pp |
| Adversarial compliance accuracy | 93.33% | 100.00% | +6.67 pp |
| Total failures | 3 | 0 | -3 |

Failure movement:

| Bucket | Count | Cases |
| --- | ---: | --- |
| Resolved baseline failures | 3 | ADV2-003, AMB-003, KF-003 |
| New failures introduced | 0 | none |
| Persisting failures | 0 | none |

## What Improved

The targeted calibration pass resolved failures across three different agent responsibilities:

| Original failure | Responsible agent | Fix effect |
| --- | --- | --- |
| AMB-003 | Review Synthesizer / Orchestrator | No longer escalates clean cases from borderline confidence alone. |
| ADV2-003 | Compliance Checker Agent | Irrelevant input is no longer mislabeled as KYC compliance failure. |
| KF-003 | Credit Risk Scorer Agent | Contract-dependent young large borrowers are risk-calibrated to MEDIUM. |

The important result is not simply that the final score reached 100%. The important result is that the evaluation identified failures, mapped them to agents, drove a targeted change, and confirmed there were no new regressions.

## Reproducibility

Export the Week 4 dataset:

```powershell
.\.venv\Scripts\python.exe scripts\week4_export_dataset.py
```

Upload the dataset to LangSmith:

```powershell
.\.venv\Scripts\python.exe scripts\week4_upload_dataset.py
```

Run the live baseline:

```powershell
.\.venv\Scripts\python.exe scripts\week4_run_baseline.py --live --log-langsmith
```

Run the improved evaluation:

```powershell
.\.venv\Scripts\python.exe scripts\week4_run_baseline.py --live --log-langsmith --output-path output\week4\clara_week4_improved.json --report-path output\week4\clara_week4_improved_report.md --langsmith-run-name "CLARA Week 4 Improved - Risk Calibration"
```

Generate the before/after delta report:

```powershell
.\.venv\Scripts\python.exe scripts\week4_compare_runs.py
```

Run local verification:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check loan_pipeline tests scripts
```

Latest verification:

```text
100 passed
Ruff clean
```

## Submission Evidence

| Evidence | Location |
| --- | --- |
| Week 4 evaluation plan | `docs/week4_eval_plan.md` |
| Baseline report | `docs/week4_baseline_report.md` |
| Improvement delta report | `docs/week4_improvement_report.md` |
| Golden dataset CSV | `loan_pipeline/data/week4_sba_loans.csv` |
| Gold labels | `loan_pipeline/eval/week4_gold_set.json` |
| Eval runner | `scripts/week4_run_baseline.py` |
| Dataset export | `scripts/week4_export_dataset.py` |
| Dataset upload | `scripts/week4_upload_dataset.py` |
| Delta report generator | `scripts/week4_compare_runs.py` |
| Failure attribution logic | `loan_pipeline/eval/failure_attribution.py` |

## Limitations

The dataset is controlled and SBA-style, not a full production SBA corpus. That is intentional for Week 4 because the goal is repeatable evaluation, not ingestion volume.

The 100% improved score should be interpreted carefully. It means CLARA resolved the tracked failures in this controlled 50-case evaluation set. It does not mean the system is production-ready for autonomous lending decisions.

The correct production posture remains human-in-the-loop. CLARA should support a loan officer by identifying risk, compliance blockers, contradictions, and counterfactuals, not replace final underwriting judgment.

## Final Takeaway

CLARA demonstrates an evaluation-driven agentic workflow:

```text
Build multi-agent system
  -> Create golden dataset
  -> Run live traced baseline
  -> Identify failures
  -> Attribute failures to agents
  -> Improve one target area
  -> Rerun same dataset
  -> Report measured delta
```

That is the core Week 4 story: CLARA does not just answer. It can be evaluated, debugged, improved, and audited.
