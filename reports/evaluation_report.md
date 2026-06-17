# Small Business Loan Review Pipeline Evaluation Report

## Executive Summary

This report evaluates a LangGraph-based multi-agent small business loan review pipeline across a 30-case gold set.

- Gold set size: 30 cases
- Difficulty tiers: 10 clean, 10 ambiguous, 10 adversarial
- Final outcome accuracy: 100.00%
- Risk band accuracy: 90.00%
- Inter-rater exact agreement: 95.33%
- Manual spot-check cases: 7

## Baseline Metrics

| Tier | Cases | Term Extraction | Compliance | Risk Band | Escalation | Final Outcome |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Overall | 30 | 100.00% | 100.00% | 90.00% | 100.00% | 100.00% |
| Clean | 10 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| Ambiguous | 10 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| Adversarial | 10 | 100.00% | 100.00% | 70.00% | 100.00% | 100.00% |

## Observability

LangSmith tracing is supported as an optional runtime mode. Set `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, and `LANGSMITH_PROJECT=loan-review-pipeline` to emit traces for the top-level loan review run, Term Extractor, Compliance Checker, Credit Risk Scorer, and Review Synthesizer.

The dashboard also includes a local LangGraph execution trace, so the demo remains inspectable even when LangSmith credentials are not configured.

## Parallel Specialist Review Trace

The graph fans out after schema validation so independent specialists can review the same extracted terms before synthesis.

- Sample case: CLEAN-001
- Parallel group: specialist_review
- Parallel nodes: compliance_checker, credit_risk_scorer

| Node | Stage | Parallel Group | Duration ms | Status |
| --- | --- | --- | ---: | --- |
| term_extractor | term_extraction |  | 0.023 | SUCCESS |
| schema_validator | validation |  | 0.002 | SUCCESS |
| compliance_checker | parallel_specialist_review | specialist_review | 0.016 | SUCCESS |
| credit_risk_scorer | parallel_specialist_review | specialist_review | 0.014 | SUCCESS |
| review_synthesizer | synthesis |  | 0.020 | SUCCESS |

## Ablation Study

| Configuration | Cases | Extraction | Compliance | Risk | Escalation | Final Outcome |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| full_pipeline | 30 | 100.00% | 100.00% | 90.00% | 100.00% | 100.00% |
| no_compliance_checker | 30 | 100.00% | 43.33% | 90.00% | 90.00% | 76.67% |
| no_risk_scorer | 30 | 100.00% | 100.00% | 63.33% | 100.00% | 100.00% |
| term_extractor_only | 30 | 100.00% | 43.33% | 63.33% | 56.67% | 43.33% |
| single_agent_baseline_stub | 30 | 100.00% | 63.33% | 80.00% | 100.00% | 86.67% |

## Failure Analysis

| Failure Category | Count |
| --- | ---: |
| Risk Calibration Failure | 3 |

| Case ID | Tier | Failure Category |
| --- | --- | --- |
| ADV-003 | adversarial | Risk Calibration Failure |
| ADV-007 | adversarial | Risk Calibration Failure |
| ADV-009 | adversarial | Risk Calibration Failure |

## Confidence Calibration

This section compares the Credit Risk Scorer's stated confidence against observed risk-band accuracy on the gold set.

- Expected calibration error: 7.00%

| Confidence Bucket | Cases | Average Confidence | Observed Accuracy | Gap | Case IDs |
| --- | ---: | ---: | ---: | ---: | --- |
| 0.7-0.8 | 4 | 70.00% | 100.00% | 30.00% | AMB-001, AMB-002, AMB-006, AMB-010 |
| 0.8-0.9 | 26 | 85.00% | 88.46% | 3.46% | CLEAN-001, CLEAN-002, CLEAN-003, CLEAN-004, CLEAN-005, CLEAN-006, CLEAN-007, CLEAN-008, CLEAN-009, CLEAN-010, AMB-003, AMB-004, AMB-005, AMB-007, AMB-008, AMB-009, ADV-001, ADV-002, ADV-003, ADV-004, ADV-005, ADV-006, ADV-007, ADV-008, ADV-009, ADV-010 |

## Drift Detection

Each gold-set case is run multiple times and material review outputs are fingerprinted to detect nondeterministic drift.

| Metric | Value |
| --- | ---: |
| Cases | 30 |
| Runs per case | 5 |
| Stable cases | 30 |
| Drifting cases | 0 |
| Stability rate | 100.00% |

| Tier | Cases | Stable Cases | Stability Rate | Max Variants |
| --- | ---: | ---: | ---: | ---: |
| Clean | 10 | 10 | 100.00% | 1 |
| Ambiguous | 10 | 10 | 100.00% | 1 |
| Adversarial | 10 | 10 | 100.00% | 1 |

## Agent Contradiction Analysis

The orchestrator surfaces conflicts where compliance and credit-risk agents point in different decision directions.

| Signal | Value |
| --- | ---: |
| Risk calibration cases requiring adjudication | 3 |

Demo candidates: ADV-003, ADV-007, ADV-009

## Counterfactual Explanation Coverage

Escalated and failed cases can produce actionable borrower or reviewer-facing counterfactuals such as supplying missing documents, improving credit evidence, or resolving prior default concerns.

| Signal | Value |
| --- | ---: |
| Evaluation failures with likely counterfactual review value | 3 |

Counterfactual demo candidates: ADV-003, ADV-007, ADV-009

## Human Override Governance

The reviewer UI supports per-finding override audit entries. Each entry records the case, target type, target ID, original agent value, override decision, rationale, reviewer, and timestamp.

| Control | Status |
| --- | --- |
| Per-finding target selection | Implemented |
| Required human rationale | Implemented |
| Reviewer identity field | Implemented |
| Timestamped audit entry | Implemented |

## Reviewer Policy Mode

The same loan application can be reviewed under different institutional policy profiles. These profiles are configurable review postures, not official legal rules.

Sample case: AMB-003

| Policy | Outcome | Compliance | Risk | Escalation |
| --- | --- | --- | --- | --- |
| SBA Reviewer | APPROVE | PASS | LOW | No |
| Bank Underwriter | CONDITIONAL_REVIEW | PASS | MEDIUM | No |
| CDFI Lender | APPROVE | PASS | LOW | No |

## Local Judge Summary

| Dimension | Average Score |
| --- | ---: |
| faithfulness | 5.0000 |
| completeness | 3.8667 |
| risk_calibration | 4.7000 |
| compliance_accuracy | 5.0000 |
| explainability | 5.0000 |
| overall_score | 4.9000 |

## Inter-Rater Agreement

| Metric | Value |
| --- | ---: |
| Cases | 30 |
| Dimensions per case | 5 |
| Exact agreement | 95.33% |
| Within-one-point agreement | 100.00% |
| Average score delta | 0.0467 |
| Highest disagreement dimension | completeness |
| Disagreement cases | 7 |

## Manual Spot-Check Queue

These cases should be manually reviewed because the primary and secondary judges disagreed.

AMB-001, AMB-002, AMB-006, AMB-010, ADV-003, ADV-007, ADV-009

## V2 Recommendations

- Prioritize v2 risk calibration for adversarial loan cases.
- Add real model-backed judge providers after the local judge contract is stable.
- Calibrate the credit risk scorer against adversarial cases with known risk misses.
- Replace SBA-style seed rows with downloaded public SBA records and hand-adjudicated labels.
- Manually adjudicate judge disagreement cases before final submission.
