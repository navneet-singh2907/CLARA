# Architecture Design

## Decision

Use a hybrid LangGraph DAG:

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

- `src/agents/`: agent implementations
- `src/graph/`: LangGraph state and orchestration
- `src/schemas/`: Pydantic contracts
- `src/rules/`: deterministic compliance and risk helpers
- `src/reporting/`: final human review packet generation
- `src/eval/`: gold-set evaluation, ablation, judge scoring, and failure analysis
- `src/data/`: SBA data loading, preprocessing, and sampling
- `src/utils/`: configuration, logging, and LLM client helpers

## Cupcake MVP Implementation

The first implementation uses deterministic agent functions rather than live LLM calls. This keeps the vertical slice testable while preserving the planned graph boundaries:

- `src/agents/term_extractor.py`
- `src/agents/compliance_checker.py`
- `src/agents/credit_risk_scorer.py`
- `src/graph/orchestrator.py`
- `src/reporting/synthesizer.py`

Future iterations can replace deterministic internals with LangChain prompts and tools without changing the agent contracts.

## Agent Contract

Each agent receives graph state and returns a partial state update. Agents must not mutate unrelated fields. Outputs should be structured, confidence-scored, and auditable.
