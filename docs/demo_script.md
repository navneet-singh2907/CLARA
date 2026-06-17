# Demo Script

## Goal

Show that this is not just a Streamlit app. It is a multi-agent financial review workflow with evaluation, observability, policy configurability, human review, and auditable output.

## Setup

Run the dashboard:

```powershell
streamlit run loan_pipeline/ui/app.py
```

Optional LangSmith tracing:

```powershell
$env:LANGSMITH_TRACING="true"
$env:LANGSMITH_API_KEY="your_langsmith_key"
$env:LANGSMITH_PROJECT="loan-review-pipeline"
```

## 2-Minute Walkthrough

### 1. Open With The Stakes

Say:

> This project reviews small business loan applications with multiple specialist agents. The point is not only to make a recommendation, but to make the recommendation auditable, testable, and configurable for different lending contexts.

### 2. Show Reviewer Policy Mode

Go to `Loan Review`.

Select:

```text
AMB-003
```

Open `Compare reviewer policies`.

Point out:

```text
SBA Reviewer      -> APPROVE / LOW
Bank Underwriter  -> CONDITIONAL_REVIEW / MEDIUM
CDFI Lender       -> APPROVE / LOW
```

Say:

> Same loan, different institutional posture. The system is not hard-coded to one lending tolerance.

### 3. Show An Adversarial Review

Select:

```text
ADV-001
```

Run the pipeline.

Show:

- Final outcome
- Compliance status
- Risk band
- Human review notes
- LangGraph execution trace

Say:

> The Term Extractor and Validator run first. After validation, LangGraph fans out into parallel specialist review: Compliance Checker and Credit Risk Scorer. Their outputs join at the Review Synthesizer.

### 4. Show A Contradiction Case

Select:

```text
AMB-002
```

Run the pipeline.

Show:

- Agent Contradictions
- Compliance position
- Credit risk position
- Human adjudication prompt

Say:

> The system does not hide disagreement between agents. It surfaces the conflict for human adjudication with both rationales side by side.

### 5. Show Counterfactuals

Return to:

```text
ADV-001
```

Scroll to `Counterfactual Explanations`.

Highlight examples:

- supply missing documents
- improve credit evidence
- resolve prior default concern

Say:

> This turns a rejection or escalation into actionable feedback.

### 6. Show Human Override Audit Log

Add an audit entry:

```text
Finding: Risk band - HIGH
Decision: Request additional evidence
Reviewer: Loan Officer A
Rationale: Need guarantor support before final decision.
```

Say:

> The human can override or adjudicate an agent finding, but the rationale is logged against a specific target.

### 7. Export The PDF Packet

Click:

```text
Download PDF packet
```

Say:

> The agent run becomes a portable review artifact that can be attached to a loan file.

### 8. Show Evaluation

Open `Evaluation`.

Highlight:

- 30 cases
- clean / ambiguous / adversarial tiers
- risk confidence calibration
- failure categories

Say:

> The project is evaluated by difficulty tier, not just overall accuracy.

### 9. Show Ablation

Open `Ablation`.

Highlight:

- full pipeline vs single-agent baseline
- compliance agent lift
- risk scorer lift
- extractor-only baseline

Say:

> This proves each agent earns its place.

### 10. Show Drift

Open `Drift`.

Highlight:

```text
30 cases
5 runs per case
100% stability rate in deterministic mode
```

Say:

> This harness is ready to detect nondeterministic drift when LLM mode is enabled.

### 11. Show Judge Agreement

Open `Judge Agreement`.

Highlight:

- primary vs secondary judge agreement
- manual spot-check queue

Say:

> This treats LLM-as-judge as something to validate, not blindly trust.

## Closing Line

Say:

> The main engineering idea is that agentic AI in finance needs more than a clever prompt. It needs orchestration, observability, evaluation, human override, calibration, drift checks, and auditable outputs.
