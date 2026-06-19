# CLARA Demo Script

## Goal

Show CLARA as a deployable agentic AI product, not a notebook or prompt demo. The recording should prove that the system has live orchestration, specialist agents, evaluation discipline, human oversight, and portable decision artifacts.

Target length: 4 to 6 minutes.

## Pre-Flight

Recommended demo path:

```powershell
cd C:\Users\nsingh1\CLARA
docker compose up
```

Open:

```text
http://localhost:3000
```

Optional API checks:

```powershell
curl.exe http://localhost:8000/health
curl.exe http://localhost:8000/readiness
```

Before recording:

- Docker Desktop shows `clara-api` and `clara-web` running.
- CLARA web UI opens at `http://localhost:3000`.
- System readiness shows `Ready`.
- If showing live LLM behavior, `.env` has `USE_LLM_AGENTS=true`, a valid provider key, and temperature above `0`.

## Storyboard

### 1. Opening: Product And Stakes

Screen: CLARA home page.

Say:

> This is CLARA, Credit Loan Analysis and Review Agent. It is a multi-agent small business loan review product built with LangChain, LangGraph, FastAPI SSE, and Next.js. The goal is not to auto-approve loans. The goal is to give a human reviewer an auditable decision-support workflow for a high-stakes financial process.

Point to:

- Product name
- System readiness card
- Tabs: Loan Review, Evaluation, Ablation, Drift, Judge Agreement, Report

### 2. Show The System Is Containerized

Screen: Docker Desktop.

Say:

> The app is running as a Dockerized full stack. The web service is the Next.js reviewer UI, and the API service is the FastAPI backend that streams LangGraph events.

Point to:

- `clara-api`
- `clara-web`
- Port `8000:8000`
- Port `3000:3000`

### 3. Run An Adversarial Loan Review

Screen: Loan Review tab.

Select:

```text
ADV-001 - Summit Event Holdings
```

Policy:

```text
SBA Reviewer
```

Click:

```text
Run review pipeline
```

Say:

> This is an adversarial case: weak operating history, prior default, and missing documentation. As the run executes, the UI is not waiting on a final answer; it is receiving live orchestration events from FastAPI SSE.

Point to:

- Live Agent Timeline
- Term Extractor
- Schema Validator
- Compliance Checker
- Credit Risk Scorer
- Review Synthesizer
- Decision Packet

### 4. Explain Parallel Specialist Review

Screen: Live Agent Timeline.

Say:

> After extraction and validation, the graph fans out into specialist review. Compliance and credit risk evaluate the same validated loan state independently, then the synthesizer joins the outputs into a decision packet. This is why the project is multi-agent rather than a single prompt.

Point to:

- Compliance checker event
- Credit risk scorer event
- Review synthesizer event

### 5. Show Decision Packet And Governance

Screen: Decision Packet and Human Override Audit Log.

Say:

> The system recommends an outcome, risk band, and compliance status, but the final decision remains human-reviewed. The reviewer can override or adjudicate a specific finding with a rationale.

Add audit entry:

```text
Finding: Outcome - ESCALATE
Decision: Request additional evidence
Reviewer: Loan Officer A
Rationale: Require updated tax returns and guarantor documentation before final approval.
```

Point to:

- Audit entry appears below the form
- Active packet is tied to the current review

### 6. Export PDF Review Packet

Screen: Human Override Audit Log.

Click:

```text
Download PDF packet
```

Say:

> The review becomes a portable artifact that could be attached to a loan file. It includes extracted terms, findings, risk rationale, counterfactuals, and the human override log.

### 7. Independent Judge Review Of The Packet

Screen: Judge Agreement tab.

Upload the PDF packet that was just downloaded.

Say:

> Now I can send the generated packet to independent judge models. They score faithfulness, completeness, risk calibration, compliance accuracy, explainability, and overall quality. The point is not to blindly trust one judge; the UI compares primary and secondary judge agreement.

Point to:

- Exact agreement
- Within-one-point agreement
- Highest delta
- Dimension deltas
- Primary judge card
- Secondary judge card

### 8. Evaluation: 30-Case Gold Set

Screen: Evaluation tab.

Click:

```text
Run evaluation
```

Say:

> The project uses a 30-case controlled gold set: 10 clean, 10 ambiguous, and 10 adversarial loan cases. The evaluation reports performance by case type so the system is not hiding behind one overall accuracy number.

Point to:

- Progress bar
- Activity log
- Clean / ambiguous / adversarial tiers
- Accuracy and failure tables when complete

### 9. Ablation: Prove Each Agent Earns Its Place

Screen: Ablation tab.

Click:

```text
Run ablation
```

Say:

> The ablation study compares the full pipeline against configurations with agents removed or reduced. This answers the engineering question: does each specialist agent improve the result, or is the graph just theater?

Point to:

- Full pipeline
- No compliance checker
- No risk scorer
- Term extractor only
- Single-agent baseline

### 10. Drift: Measure Nondeterminism

Screen: Drift tab.

Select a case, for example:

```text
ADV-007 - Metro MedSpa Ventures
```

Click:

```text
Run live probe
```

Say:

> With live LLM mode, repeated runs can produce small differences. The drift probe runs the same case multiple times and fingerprints material outputs: outcome, risk band, compliance status, confidences, contradictions, and counterfactuals.

Point to:

- Selected case
- Run 1 / 2 / 3 logs
- Fingerprints
- Variance summary

### 11. Closing

Screen: README or CLARA home page.

Say:

> CLARA is designed around the parts of agentic AI that matter in financial review: orchestration, observability, evaluation, human override, drift checks, judge agreement, and auditable artifacts. The core lesson is that high-stakes agent systems need more than model output; they need a review pipeline.

## Short Version

If limited to 2 minutes:

1. Show Docker Desktop with `clara-api` and `clara-web`.
2. Run `ADV-001` in Loan Review.
3. Show live timeline and decision packet.
4. Add a human override.
5. Download PDF packet.
6. Upload packet to Judge Agreement.
7. End on Evaluation/Ablation tabs as proof of engineering discipline.

## Avoid During Demo

- Do not start with implementation details.
- Do not claim CLARA makes final credit decisions.
- Do not call the seeded gold set a full production SBA corpus.
- Do not run every long live batch unless you have already tested provider quota and latency.
