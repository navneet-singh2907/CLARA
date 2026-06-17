# Multi-Agent Small Business Loan Review Pipeline

Week 3 project for the Gen Academy Agentic AI Bootcamp.

This project builds a multi-agent loan application review pipeline using LangChain, LangGraph, and Streamlit. The system assists a human loan reviewer by extracting loan terms, checking compliance concerns, scoring credit risk, and producing an auditable review packet.

## Architecture

The pipeline uses a hybrid LangGraph DAG:

1. Term Extractor Agent extracts structured loan-review fields.
2. Schema Validator checks completeness and state quality.
3. Compliance Checker Agent evaluates documentation and policy concerns.
4. Credit Risk Scorer Agent assigns risk band, rationale, and confidence.
5. Orchestrator resolves contradictions and prepares a human review packet.
6. Counterfactual explainer generates actionable "what would change the outcome" guidance.
7. Human reviewer can override individual findings with an audit rationale.
8. PDF packet exporter creates a portable review artifact for the human decision record.
9. Evaluation Harness scores the system against a 30-case gold set.

The current orchestrator is backed by a compiled LangGraph `StateGraph`.

## Evaluation Standard

The evaluation harness is a first-class subsystem.

Gold set:

- 10 clean loan cases
- 10 ambiguous loan cases
- 10 adversarial loan cases

Evaluation includes:

- Agent-level metrics
- End-to-end pipeline metrics
- Ablation study
- LLM-as-judge scoring
- Second judge model agreement
- Manual spot-checking
- Failure analysis by category
- Agent contradiction detection for human adjudication
- Counterfactual explanations for escalated or failed reviews
- Human override audit log per finding
- PDF export of the human review packet
- Ablation visualization that shows each agent's measured contribution
- Confidence calibration comparing risk confidence to observed accuracy
- Drift detection for repeated agent runs

## Project Structure

```text
loan_pipeline/
  agents/
    term_extractor.py
    compliance_checker.py
    credit_risk_scorer.py
  graph/
    state.py
    orchestrator.py
    edges.py
  eval/
    gold_set.json
    judge.py
    ablation.py
  review/
    contradictions.py
    counterfactuals.py
  ui/
    app.py
  data/
    sba_loans.csv
    load_sba_public.py
  config.py
docs/
  architecture.md
  data_source.md
  evaluation_plan.md
requirements.txt
README.md
tests/
```

## Setup

Create and activate a virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install pinned dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy environment variables:

```powershell
Copy-Item .env.example .env
```

Optional LLM agent mode:

```text
USE_LLM_AGENTS=false
OPENAI_MODEL=gpt-4o-mini
```

The default deterministic mode keeps evaluation reproducible. Set `USE_LLM_AGENTS=true` with `OPENAI_API_KEY` to enable LangChain-backed agent calls.

Run the app:

```powershell
streamlit run loan_pipeline/ui/app.py
```

The dashboard includes loan review, evaluation metrics, ablation results, judge agreement, and report preview tabs.

## Demo Script

1. Open the dashboard:

```powershell
streamlit run loan_pipeline/ui/app.py
```

2. In `Loan Review`, select `ADV-003` to show an adversarial case where the current risk scorer misses the gold risk band.
3. Run the pipeline and show the human review packet, agent outputs, and graph state.
4. Show the `Agent Contradictions` panel when compliance and credit-risk signals conflict.
5. Show the `Counterfactual Explanations` panel to explain what would make the review outcome improve.
6. Add a human override with a rationale in the `Human Override Audit Log`.
7. Download or save the PDF review packet as the final business artifact.
8. Open `Evaluation` to show the 30-case gold set metrics by clean, ambiguous, and adversarial tiers.
9. Open `Ablation` to show the contribution chart and prove each agent earns its place.
10. In `Evaluation`, show confidence calibration for the risk scorer.
11. Open `Drift` to show repeated-run stability across the gold set.
12. Open `Judge Agreement` to show primary vs secondary judge agreement and the manual spot-check queue.
13. Open `Report` and generate the Markdown evaluation report.

## Cupcake MVP

The first vertical slice uses SBA-style sample cases, rules-first agents, and a compiled LangGraph workflow:

- `CLEAN-001`: straightforward low-risk case
- `AMB-001`: ambiguous case with missing owner credit report
- `ADV-001`: adversarial case with prior default and missing documents

Run tests:

```powershell
pytest
```

Run the 30-case evaluation:

```powershell
python -m loan_pipeline.eval.run_eval
```

The evaluation output includes metric accuracy, failure categories, and local judge-dimension averages.

Run the ablation study:

```powershell
python -m loan_pipeline.eval.ablation
```

Run the inter-rater agreement scaffold:

```powershell
python -m loan_pipeline.eval.inter_rater
```

Generate the Markdown evaluation report:

```powershell
python -m loan_pipeline.eval.report
```

Normalize a downloaded SBA FOIA CSV in code:

```python
from pathlib import Path
from loan_pipeline.data.load_sba_public import load_sba_public_cases

cases = load_sba_public_cases(Path("loan_pipeline/data/foia_7a_2020_present.downloaded.csv"))
```

## SDLC Status

- Step 1: Problem Statement complete
- Step 2: Architecture Design complete
- Step 3: Environment & Hygiene complete
- Step 4: Cupcake MVP complete
- Step 5: Peer Review Iteration complete
- Step 6: Edge-Case Stress Testing complete
- Step 7: Ship Early Demo complete
- Step 8: Iteration Flywheel in progress
