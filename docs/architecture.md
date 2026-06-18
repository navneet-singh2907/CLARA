# Architecture Design

## Decision

Use a hybrid LangGraph DAG implemented with a compiled `StateGraph`:

```text
Loan Case
  -> Term Extractor
  -> Schema Validator
  -> Compliance Checker + Credit Risk Scorer in parallel
  -> Conflict and Escalation Resolver
  -> Human Review Packet
```

## Rationale

This design keeps the system modular while preserving an agentic orchestration story. The Term Extractor creates validated shared state, while the Compliance Checker and Credit Risk Scorer operate independently. The orchestrator owns routing, state transitions, contradiction handling, and escalation logic.

## Parallel Specialist Review

After schema validation, LangGraph fans out to the Compliance Checker and Credit Risk Scorer. These agents consume the same validated extracted terms and write independent state updates before the synthesizer joins their outputs. The graph records an execution trace with `parallel_group="specialist_review"` so the dashboard and report can show the parallel stage explicitly.

## Observability

The pipeline supports optional LangSmith tracing. When `LANGSMITH_TRACING=true`, the top-level loan review run and core agent stages emit LangSmith traces with case ID, stage, and agent tags. This complements the local execution trace shown in Streamlit: LangSmith is for remote LLM/agent observability, while the local trace keeps the demo self-contained when no API key is configured.

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

## Contradiction Detection

The review synthesizer detects conflicts between specialist agents. Examples include compliance blockers paired with low or medium credit risk, high credit risk without compliance findings, and compliance-review requirements paired with low credit risk. These contradictions are surfaced to the human reviewer with both agent positions side by side.

## Counterfactual Explanations

The review layer generates borrower- and reviewer-facing counterfactuals for cases with remediable issues. Instead of stopping at "high risk" or "missing documents," the packet states the current blocker, the specific change needed, and the expected effect on compliance or risk review. Examples include supplying missing documents, providing owner credit evidence, improving a sub-640 credit score, documenting operating history, or resolving a prior default concern.

## Human Override Audit Log

The reviewer interface supports per-finding human override entries. A reviewer can select the final outcome, risk band, compliance finding, contradiction, or counterfactual, choose an override decision, and record a rationale. The audit entry captures the case ID, target type, original agent value, reviewer identity, rationale, and timestamp so the demo can show accountable human-in-the-loop governance.

## PDF Review Packet Export

The Streamlit interface can export the current review packet as a PDF artifact. The packet includes the recommended outcome, extracted terms, compliance findings, credit risk rationale, contradictions, counterfactual explanations, and human override audit log. This turns the agent run into a portable business record that a reviewer could attach to a loan file.

## Reviewer Policy Mode

The pipeline supports configurable institutional review postures: SBA Reviewer, Bank Underwriter, and CDFI Lender. These are policy profiles for demonstration and decision-support configuration, not official legal rules. Each profile adjusts risk tolerance, guarantee-ratio review thresholds, prior-default severity, and mission-impact treatment so the same loan can produce different review outputs under different institutional contexts.

## Ablation Evidence View

The dashboard visualizes ablation results from the evaluation harness. It compares full-pipeline accuracy against disabled-agent and single-agent baselines, then summarizes the measured lift from compliance checking, credit risk scoring, and orchestration. This gives the demo a direct answer to why the system is multi-agent rather than a single prompt.

## Confidence Calibration

The evaluation harness measures whether the Credit Risk Scorer's confidence is calibrated against observed gold-set accuracy. The dashboard and report show confidence buckets, observed risk-band accuracy, calibration gaps, and expected calibration error so reviewers can distinguish accurate predictions from merely confident ones.

## Drift Detection

The evaluation harness has two drift paths. The deterministic 30-case benchmark runs each case multiple times and fingerprints material review outputs to confirm baseline reproducibility. The live LLM drift probe repeats one selected case through live model-backed agents and compares fingerprints across runs. That second path is the nondeterminism check: it reveals whether temperature, provider behavior, prompts, or orchestration produce different outcomes, risk bands, compliance statuses, contradictions, counterfactuals, or human-review notes.

## Agent Contract

Each agent receives graph state and returns a partial state update. Agents must not mutate unrelated fields. Outputs should be structured, confidence-scored, and auditable.

## Demo Surface

The Streamlit dashboard is the reviewer-facing surface. It exposes the loan review workflow, evaluation dashboard, ablation study, judge agreement report, and generated Markdown evaluation artifact from one place.
