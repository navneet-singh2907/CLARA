# Architecture Design

## Decision

Use a hybrid LangGraph DAG implemented with a compiled `StateGraph`:

```text
Loan Case
  -> Term Extractor
  -> Schema Validator
  -> Compliance Checker + Credit Risk Scorer
  -> Conflict and Escalation Resolver
  -> Human Review Packet
```

## Rationale

This design keeps the system modular while preserving an agentic orchestration story. The Term Extractor creates validated shared state, while the Compliance Checker and Credit Risk Scorer operate independently. The orchestrator owns routing, state transitions, contradiction handling, and escalation logic.

## Core Modules

- `loan_pipeline/agents/`: agent implementations
- `loan_pipeline/graph/`: graph state, orchestration, and edge topology
- `loan_pipeline/eval/`: gold-set evaluation, ablation, judge scoring, and failure analysis
- `loan_pipeline/ui/`: Streamlit reviewer interface
- `loan_pipeline/data/`: curated 30-case working set and SBA FOIA normalization helpers
- `loan_pipeline/config.py`: local configuration and data loading helpers

## Cupcake MVP Implementation

The first implementation uses deterministic agent functions rather than live LLM calls. The orchestrator is already a compiled LangGraph `StateGraph`, which keeps the vertical slice testable while preserving the planned graph boundaries:

- `loan_pipeline/agents/term_extractor.py`
- `loan_pipeline/agents/compliance_checker.py`
- `loan_pipeline/agents/credit_risk_scorer.py`
- `loan_pipeline/graph/orchestrator.py`
- `loan_pipeline/graph/edges.py`

The public agent functions support optional LangChain-backed behavior behind `USE_LLM_AGENTS=true`. Deterministic mode remains the default so tests and evaluation stay reproducible without API keys.

LLM mode:

- Term Extractor can call a LangChain prompt for structured extraction.
- Compliance Checker keeps rule findings and can request an LLM reviewer note.
- Credit Risk Scorer keeps deterministic score/band and can request an LLM rationale.

## Validation Gate Behavior

Validation errors force escalation. A loan case cannot receive an approve recommendation when required identifiers, numeric fields, borrower classifications, or financial consistency checks fail.

## Agent Contract

Each agent receives graph state and returns a partial state update. Agents must not mutate unrelated fields. Outputs should be structured, confidence-scored, and auditable.

## Demo Surface

The Streamlit dashboard is the reviewer-facing surface. It exposes the loan review workflow, evaluation dashboard, ablation study, judge agreement report, and generated Markdown evaluation artifact from one place.
