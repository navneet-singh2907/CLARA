# CLARA Week 4 Baseline Evaluation Report

## Executive Summary

CLARA was evaluated on a 50-case golden dataset using live LLM agents and LangSmith tracing. The baseline achieved 98.00% final outcome accuracy, 98.00% compliance accuracy, and 98.00% risk-band accuracy.

The important finding is not that the system is perfect. It is that the evaluation harness can identify where CLARA should slow down, request human review, or avoid auto-approval.

## Evaluation Setup

- System: CLARA - Credit Loan Analysis & Review Agent
- Runtime: live_llm
- Dataset: CLARA Week 4 Loan Review Eval
- Case count: 50
- LangSmith project: CLARA Week 4 Eval Lab
- LangSmith dataset ID: `ec7896af-7117-4f7e-8972-0dc37239036a`
- Baseline artifact: `output/week4/clara_week4_baseline.json`

## Dataset Composition

| Scenario type | Cases | Purpose |
| --- | ---: | --- |
| Clean | 10 | Straightforward applications that should be handled cleanly. |
| Ambiguous | 10 | Missing fields, borderline signals, or incomplete documents. |
| Adversarial | 15 | Buried clauses, prompt injection, malformed, or irrelevant inputs. |
| Edge | 10 | Partial data, conflicting terms, and unusual but plausible cases. |
| Known failure | 5 | Cases designed around Week 3 risk/compliance weaknesses. |

## Baseline Metrics

| Metric | Score |
| --- | ---: |
| Term extraction accuracy | 100.00% |
| Compliance status accuracy | 98.00% |
| Risk band accuracy | 98.00% |
| Escalation accuracy | 98.00% |
| Final outcome accuracy | 98.00% |
| Trajectory correctness | 98.00% |

## Metrics By Scenario Type

| Scenario | Cases | Final outcome | Compliance | Risk | Escalation |
| --- | ---: | ---: | ---: | ---: | ---: |
| clean | 10 | 100.00% | 100.00% | 100.00% | 100.00% |
| ambiguous | 10 | 100.00% | 100.00% | 100.00% | 90.00% |
| adversarial | 15 | 93.33% | 93.33% | 100.00% | 100.00% |
| edge | 10 | 100.00% | 100.00% | 100.00% | 100.00% |
| known_failure | 5 | 100.00% | 100.00% | 80.00% | 100.00% |

## Failure Analysis

- Strongest tier: clean
- Weakest tier: known_failure
- Failure clusters: Orchestration Failure: 1, Compliance Failure: 1, Risk Calibration Failure: 1

| Case | Tier | Failure category | Observed packet | Why it matters |
| --- | --- | --- | --- | --- |
| AMB-003 | ambiguous | Orchestration failure | APPROVE / LOW / PASS | Human-review gate fired differently from the gold label. |
| ADV2-003 | adversarial | Compliance failure | CONDITIONAL_REVIEW / MEDIUM / REVIEW | Adversarial or malformed input was not classified with the expected compliance severity. |
| KF-003 | known_failure | Risk calibration failure | ESCALATE / LOW / FAIL | Credit-risk severity did not match the gold label despite correct escalation. |

## Trust And Safety Signals

These are not necessarily failures. They are control signals telling a reviewer when CLARA should avoid silent auto-approval.

| Signal | Count | Interpretation |
| --- | ---: | --- |
| agent_disagreement | 25 | Compliance and risk evidence deserve side-by-side human review. |
| human_review_required | 36 | The packet should be reviewed before approval. |
| low_extraction_confidence | 3 | Terms may be under-specified or document quality may be weak. |
| low_risk_confidence | 8 | Risk band is less stable and should not be treated as final. |

## Latency

| Statistic | Value |
| --- | ---: |
| p50 latency | 7.13s |
| p95 latency | 9.45s |
| max latency | 13.07s |

## Recommended Improvement Target

The best next improvement target is risk/compliance calibration on adversarial and known-failure cases. The baseline is already strong on clean, ambiguous, and edge cases, so the next delta should come from reducing false risk or compliance judgments without weakening escalation behavior.

Proposed hypothesis:

If CLARA separates missing-document compliance blockers from credit-risk repayment severity more explicitly, then known-failure risk accuracy should improve while compliance escalation remains intact.

## Week 4 Submission Evidence

- 50-case golden dataset exists in repo and LangSmith.
- Live baseline run completed with LLM agents.
- LangSmith traces show agent-level execution.
- Baseline failures are categorized by type.
- Next step is a measured post-improvement run and delta table.
