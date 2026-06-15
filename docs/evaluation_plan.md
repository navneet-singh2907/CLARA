# Evaluation Plan

## Gold Set

The project will use a 30-case gold set:

- 10 clean cases
- 10 ambiguous cases
- 10 adversarial cases

## Metrics

- Term extraction accuracy
- Compliance detection accuracy
- Risk band accuracy
- Escalation accuracy
- Faithfulness
- Completeness
- Risk calibration
- Compliance accuracy
- Explainability

## Ablation Matrix

| Configuration | Extraction | Compliance | Risk | Escalation | Faithfulness | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Agent 1 Only |  | N/A | N/A | N/A |  |  |
| Agent 2 Only | N/A |  | N/A |  |  |  |
| Agent 3 Only | N/A | N/A |  |  |  |  |
| Agent 1 + Agent 2 |  |  | N/A |  |  |  |
| Agent 1 + Agent 3 |  | N/A |  |  |  |  |
| Full Pipeline |  |  |  |  |  |  |
| Full Pipeline + HITL |  |  |  |  |  |  |
| Single-Agent Baseline |  |  |  |  |  |  |

## Failure Categories

- Extraction Failure
- Compliance Failure
- Risk Calibration Failure
- Orchestration Failure
- Document Quality Failure

## Judge Model Agreement

Two judge models will score the same outputs. The report will include exact agreement, within-one-point agreement, average score delta, disagreement cases, and manual adjudication notes.

