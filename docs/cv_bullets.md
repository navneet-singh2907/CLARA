# CV And Interview Notes

## Project Title

CLARA - Credit Loan Analysis & Review Agent

## One-Line Summary

Built CLARA, a LangChain + LangGraph multi-agent loan review product with specialist agents, reviewer policy modes, rigorous evaluation, human override audit logs, LangSmith-compatible tracing, and PDF review packet export.

## Resume Bullets

- Built CLARA, a multi-agent small business loan review product using LangGraph, LangChain, and Streamlit, coordinating specialist agents for term extraction, compliance review, and credit risk scoring.
- Designed a 30-case gold-set evaluation harness split across clean, ambiguous, and adversarial loan applications, with ablation studies, failure categorization, LLM-as-judge scoring, and inter-rater agreement.
- Implemented responsible-AI controls including contradiction detection, counterfactual explanations, confidence calibration, repeated-run drift detection, human override audit logging, and PDF review packet export.
- Added configurable reviewer policy modes for SBA reviewer, bank underwriter, and CDFI lender postures, allowing the same loan application to be evaluated under different institutional risk tolerances.
- Added LangSmith-compatible tracing and a local LangGraph execution trace to improve observability across the orchestration flow and parallel specialist review stage.

## Best Three Resume Bullets

- Built CLARA as a LangGraph multi-agent loan review product with parallel compliance and credit-risk specialist agents, reviewer policy modes, human override audit logs, and PDF review packet export.
- Designed a 30-case evaluation harness with clean, ambiguous, and adversarial tiers, ablation visualization, failure analysis, LLM-as-judge scaffolding, inter-rater agreement, confidence calibration, and drift detection.
- Added responsible-AI governance features for high-stakes financial review, including contradiction detection, counterfactual explanations, LangSmith-compatible observability, and auditable human-in-the-loop decisions.

## LinkedIn / Portfolio Summary

I built CLARA, a multi-agent small business loan review product using LangGraph, LangChain, and Streamlit. The system reviews SBA-style loan applications through specialist agents for term extraction, compliance checking, and credit risk scoring, then produces an auditable human review packet.

The project emphasizes production-grade AI evaluation and governance: a 30-case gold set, ablation visualization, LLM-as-judge scaffolding, inter-rater agreement, confidence calibration, repeated-run drift detection, contradiction detection, counterfactual explanations, human override audit logs, reviewer policy modes, optional LangSmith tracing, and PDF export.

## Interview Talking Points

### Why This Problem?

Loan review is high stakes. A wrong decision can affect a business owner's ability to receive capital, hire employees, or survive a liquidity crunch. That makes evaluation, auditability, and human oversight essential.

### What Makes It Agentic?

The workflow uses a LangGraph orchestrator with stateful specialist agents. The Term Extractor and Validator create shared structured state. Then Compliance Checker and Credit Risk Scorer run as parallel specialist reviewers. The Synthesizer joins their outputs, resolves contradictions, generates counterfactuals, and prepares the human review packet.

### What Makes The Evaluation Strong?

The evaluation is not a single accuracy number. It includes a 30-case tiered gold set, ablation studies, failure analysis, judge agreement, manual spot-checking, confidence calibration, and drift detection.

### What Was The Main Tradeoff?

The default mode is deterministic to keep evaluation reproducible. For demos, live LLM agent mode can be enabled with `USE_LLM_AGENTS=true`, `OPENAI_API_KEY`, and `LLM_TEMPERATURE>0`. That lets me show actual model-backed agent behavior while still keeping the gold-set evaluation reproducible when needed.

### What Would You Build Next?

- Use a larger hand-labeled sample from public SBA FOIA loan records.
- Add a FastAPI backend for enterprise integration.
- Add a durable checkpoint store for long-running human-in-the-loop workflows.
- Connect external document parsers for scanned application packets.
- Run live LangSmith traces for LLM-backed extraction and reviewer notes.

## Short Pitch

This project shows that I can build more than an LLM demo. I can design an agentic workflow with state, evaluation, observability, human oversight, and auditability in a regulated-domain context.
