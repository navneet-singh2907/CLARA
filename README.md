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
6. Evaluation Harness scores the system against a 30-case gold set.

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

## Project Structure

```text
app.py
data/
  raw/
  processed/
  gold/
docs/
  architecture.md
  evaluation_plan.md
src/
  agents/
  data/
  eval/
  graph/
  reporting/
  rules/
  schemas/
  utils/
tests/
```

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install pinned dependencies:

```powershell
pip install -r requirements.txt
```

Copy environment variables:

```powershell
Copy-Item .env.example .env
```

Run the app once implemented:

```powershell
streamlit run app.py
```

## Cupcake MVP

The first vertical slice uses deterministic sample cases and rules-first agents:

- `CLEAN-001`: straightforward low-risk case
- `AMB-001`: ambiguous case with missing owner credit report
- `ADV-001`: adversarial case with prior default and missing documents

Run tests:

```powershell
pytest
```

## SDLC Status

- Step 1: Problem Statement complete
- Step 2: Architecture Design complete
- Step 3: Environment & Hygiene complete
- Step 4: Cupcake MVP in progress
