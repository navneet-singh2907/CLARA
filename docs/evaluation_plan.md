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
| Full Pipeline | 1.0000 | 1.0000 | 0.9000 | 1.0000 | TBD | Current best configuration |
| No Compliance Checker | 1.0000 | 0.4333 | 0.9000 | 0.9000 | TBD | Shows compliance agent contribution |
| No Risk Scorer | 1.0000 | 1.0000 | 0.6333 | 1.0000 | TBD | Shows risk agent contribution |
| Term Extractor Only | 1.0000 | 0.4333 | 0.6333 | 0.5667 | TBD | Agent 1-only baseline |
| Single-Agent Baseline Stub | 1.0000 | 0.6333 | 0.8000 | 0.8333 | TBD | Coarse single-agent approximation |

Run:

```powershell
python -m loan_pipeline.eval.ablation
```

## Failure Categories

- Extraction Failure
- Compliance Failure
- Risk Calibration Failure
- Orchestration Failure
- Document Quality Failure

The local evaluation runner currently reports failure counts by category. The first baseline run is expected to expose calibration misses rather than hide them.

Run:

```powershell
python -m loan_pipeline.eval.run_eval
```

## Judge Model Agreement

Two judge models will score the same outputs. The report will include exact agreement, within-one-point agreement, average score delta, disagreement cases, and manual adjudication notes.

Current scaffold:

- Builds a strict JSON-only judge prompt
- Validates judge responses against required fields
- Scores a local deterministic judge baseline
- Reports average local judge dimensions in `python -m loan_pipeline.eval.run_eval`

External judge providers will be added after the local evaluation contract is stable.
