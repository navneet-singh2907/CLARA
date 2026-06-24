# CLARA Week 4 Improvement Delta Report

## What Changed

This report compares a Week 4 baseline run against a targeted improved run on the same 50-case golden dataset. The purpose is to show one measured engineering change at a time, not to claim a vague overall improvement.

## Hypothesis

If CLARA separates missing-document compliance blockers from credit-risk repayment severity more explicitly, then risk/compliance calibration should improve on adversarial and known-failure cases without weakening escalation.

## Delta Table

| Metric | Baseline | Improved | Delta | Direction |
| --- | ---: | ---: | ---: | --- |
| Final outcome accuracy | 98.00% | 100.00% | +2.00 pp | improved |
| Compliance accuracy | 98.00% | 100.00% | +2.00 pp | improved |
| Risk band accuracy | 98.00% | 100.00% | +2.00 pp | improved |
| Escalation accuracy | 98.00% | 100.00% | +2.00 pp | improved |
| Trajectory correctness | 98.00% | 98.00% | +0.00 pp | unchanged |
| Known-failure risk accuracy | 80.00% | 100.00% | +20.00 pp | improved |
| Adversarial compliance accuracy | 93.33% | 100.00% | +6.67 pp | improved |
| Total failures | 3 | 0 | -3 | improved |
| p50 latency | 7.13s | 5.34s | -1.79s | improved |

## Failure Movement

| Bucket | Count | Cases |
| --- | ---: | --- |
| Resolved baseline failures | 3 | ADV2-003, AMB-003, KF-003 |
| New failures introduced | 0 | none |
| Persisting failures | 0 | none |

## Resolved Failure Attribution

| Case | Original responsible agent | Failure mode | Expected | Actual |
| --- | --- | --- | --- | --- |
| AMB-003 | Review Synthesizer / Orchestrator | behavioral_misclassification | Outcome APPROVE; escalation False | Outcome APPROVE; escalation True |
| ADV2-003 | Compliance Checker Agent | behavioral_misclassification | Compliance status PASS | Compliance status REVIEW |
| KF-003 | Credit Risk Scorer Agent | behavioral_misclassification | Risk band MEDIUM | Risk band LOW |

## Failure Clusters

| Cluster | Baseline | Improved | Delta |
| --- | ---: | ---: | ---: |
| Compliance Failure | 1 | 0 | -1 |
| Orchestration Failure | 1 | 0 | -1 |
| Risk Calibration Failure | 1 | 0 | -1 |

## Interpretation

The targeted change improved Final outcome accuracy, Compliance accuracy, Risk band accuracy, Escalation accuracy, Known-failure risk accuracy, Adversarial compliance accuracy, Total failures, p50 latency with no tracked regressions.

## Reproducibility

Run the same workflow after each targeted change:

```powershell
.\.venv\Scripts\python.exe scripts\week4_run_baseline.py --live --log-langsmith --output-path output\week4\clara_week4_improved.json --report-path output\week4\clara_week4_improved_report.md --langsmith-run-name "CLARA Week 4 Improved - Risk Calibration"
.\.venv\Scripts\python.exe scripts\week4_compare_runs.py
```
