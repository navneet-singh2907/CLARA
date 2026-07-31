# CLARA Project Handoff

## Current Objective

Deploy the CLARA FastAPI backend to AWS Elastic Beanstalk as portfolio evidence. Vercel remains the primary public demo. The AWS deployment only needs a healthy environment, successful `/health` and `/readiness` responses, and screenshots before the environment can be terminated to avoid ongoing cost.

## Product Snapshot

CLARA stands for **Credit Loan Analysis & Review Agent**. It is a multi-agent small-business loan review system built with LangChain, LangGraph, FastAPI, Server-Sent Events (SSE), Next.js, Nebius-hosted models, LangSmith, and Docker.

The LangGraph workflow is:

`Term Extractor -> Schema Validator -> Compliance Checker + Credit Risk Scorer (parallel) -> Review Synthesizer`

The synthesized result supports contradiction detection, counterfactual explanations, PDF review packets, human override auditing, independent judge review, and SBA, bank-underwriter, and CDFI policy modes.

## Repository Map

- `loan_pipeline/agents/`: specialist agent implementations
- `loan_pipeline/graph/`: shared state, nodes, routing, and orchestration
- `loan_pipeline/api/`: FastAPI routes, SSE streaming, and rate limiting
- `loan_pipeline/llm/`: model client, prompts, validation, and contextual errors
- `loan_pipeline/eval/`: gold-set, drift, ablation, calibration, and judge evaluation
- `loan_pipeline/review/`: contradictions, counterfactuals, audit records, and PDF export
- `loan_pipeline/security/`: Week 6 guardrails and stress testing
- `loan_pipeline/mcp/`: MCP evidence server
- `web/`: Next.js dashboard
- `tests/`: Python test suite
- `scripts/`: evaluation, packaging, smoke-test, and LangSmith utilities
- `sample_documents/`: demo loan documents
- `docs/`: architecture, deployment, and submission material

## Completed Milestones

- Parallel multi-agent LangGraph workflow with live SSE observability
- PDF/text document intake and structured extraction
- Contradiction detection and actionable counterfactual explanations
- Human-in-the-loop override log and downloadable PDF packets
- Regulatory personas, confidence scoring, and calibration analysis
- Drift probes, ablation studies, and two-model judge agreement
- Context-rich LLM errors, call timeouts, upload limits, rate limits, and CI
- Dockerized FastAPI and Next.js services
- LangSmith traces plus a versioned 50-case Week 4 dataset
- MCP evidence server and smoke tests
- Week 6 guardrail stress lab across nine attack families

## Evaluation Status

The Week 4 gold set contains 50 labeled cases: 10 clean, 10 ambiguous, 15 adversarial, 10 edge, and 5 known-failure cases. The LangSmith dataset is `CLARA Week 4 Loan Review Eval`, version `clara-week4-v1`.

The Week 6 lab contains 45 attacks across nine families. Recorded results are 11.11% baseline pass, 33.33% baseline fail, 100% guarded pass, and zero guarded failures. Week 3 received 9.3/10, including 20/20 for evaluation rigor.

## Running Locally

```powershell
.\.venv\Scripts\python.exe -m uvicorn loan_pipeline.api.app:app --reload --port 8000
Set-Location web
npm.cmd run dev
```

For the containerized stack:

```powershell
docker compose up --build
```

Public web: `https://clara-web-beta.vercel.app/`  
Vercel API: `https://clara-api-eight.vercel.app/`

## AWS Deployment Status

AWS deployment proof succeeded on July 31, 2026. The clean replacement
environment is:

```text
Application: Clara-aws-demo
Environment: Clara-aws-demo-env-1
Environment ID: e-8m5wpwpz8s
Region: us-east-2
Platform: Docker running on 64bit Amazon Linux 2023/4.13.5
Version: clara-aws-proof-20260731-v3
Health: Green / Ok
Domain: http://Clara-aws-demo-env-1.eba-kuxghc9b.us-east-2.elasticbeanstalk.com
```

The latest Elastic Beanstalk events confirm that the instance deployment,
application-version deployment, and environment update completed successfully.
Direct endpoint verification also passed:

```text
GET /health -> {"status":"ok"}
GET /readiness -> API connected, llm_mode=false, langsmith_tracing=false
```

The user subsequently requested a fully live model-backed configuration for the
video proof. The healthy environment currently has no Elastic Beanstalk
environment properties. The local ignored `.env` contains all required Nebius,
model, judge, and LangSmith settings; presence was verified without printing or
exposing their values. However, the public Vercel demo now fails its first live
term-extractor call with Nebius HTTP 401 `Couldn't authenticate`. The live Vercel
`/readiness` endpoint still reports live mode, judges, and tracing as enabled,
which only proves a credential is present. Do not copy the current Nebius key to
AWS until a newly generated credential succeeds in a real Vercel review.

AWS Console is open on the healthy environment's Configuration page. The user
prefers to enter environment properties manually.

The prior `Clara-aws-demo-env` remains an orphaned historical environment whose
CloudFormation stack `awseb-e-32zfmfpy32-stack` no longer exists. Do not attempt
another deployment to it.

For the AWS proof deployment, use:

```text
USE_LLM_AGENTS=false
LANGSMITH_TRACING=false
```

No model or LangSmith secrets are required for this proof.

## Packaging Status

The package script and Dockerfile have been corrected. The Elastic Beanstalk ZIP
root now contains:

```text
Dockerfile
requirements.txt
pyproject.toml
README.md
.dockerignore
api/
loan_pipeline/
sample_documents/
```

The deployed root `Dockerfile` is copied from `Dockerfile.api`. The packaging
script now:

- creates a fresh staging directory under `tmp/`;
- requires `README.md` and `.dockerignore`;
- removes generated `__pycache__` directories;
- writes ZIP entries with forward slashes through the .NET ZIP API;
- validates every required root file and source directory.

Verified artifact:

```text
dist/clara-aws-elastic-beanstalk.zip
SHA256 A1185E0A083F392E0B17B6522DA3333A44A2FF214BBD272083ABA69733426B9D
```

Local verification completed on July 31, 2026:

- `tar -tf` confirmed all required root entries and forward-slash paths.
- Generated-entry count for `__pycache__` and `*.pyc` was zero.
- `docker build -f Dockerfile.api -t clara-aws-proof:local .` succeeded.
- The local container returned HTTP 200-compatible JSON from `/health` and
  `/readiness` with `USE_LLM_AGENTS=false` and `LANGSMITH_TRACING=false`.
- Ruff passed.
- Pytest passed: 132 tests, one third-party ReportLab deprecation warning.

## Do Not Repeat

- Do not restart IAM, VPC, subnet, security-group, or EC2 debugging without new evidence.
- Do not recreate Elastic Beanstalk environments repeatedly.
- Do not return to the `us-east-1` free-tier instance-selection issue.
- Do not attribute the historical Docker build error to Nebius or LangSmith. The
  current Vercel HTTP 401 is a separate credential issue.
- Do not change loan-review logic to solve a missing archive file.

## Immediate Next Steps

1. Generate a new Nebius API key. Update the Vercel API project and local ignored
   `.env` without exposing the value.
2. Redeploy the Vercel API and run one actual review. Do not rely on `/readiness`
   alone because it does not authenticate with Nebius.
3. After the Vercel review succeeds, manually configure the healthy AWS
   environment with that new Nebius key, live agent/judge settings, and LangSmith
   tracing.
4. Wait for the AWS environment update to complete and return to Green / Ok.
5. Verify `/health` and `/readiness`; readiness must show `llm_mode=true`,
   `live_llm_available=true`, `live_judges_available=true`, and
   `langsmith_tracing=true`.
6. Run one real AWS review for the video proof and confirm the trace appears in
   LangSmith.
7. Save the healthy environment, successful-events, readiness, and live review
   screenshots as portfolio evidence.
8. After the user confirms the screenshots are saved, terminate
   `Clara-aws-demo-env-1` to stop EC2 charges.
9. Also terminate the orphaned `Clara-aws-demo-env` environment record if it is
   still present.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check loan_pipeline tests
```

## Collaboration Notes

- Explain each meaningful change and why it is needed.
- Ask before making major architectural changes.
- The user handles Git unless they explicitly ask Codex to do it.
- Never expose or commit API keys.
- Preserve the working Vercel deployment and existing evaluation artifacts.
