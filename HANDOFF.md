# CLARA Project Handoff

## Current Objective

Temporarily deploy the complete CLARA Next.js frontend and FastAPI backend to
the existing AWS Elastic Beanstalk environment for a full video demo. Vercel
must remain unchanged so it can become the primary public demo again afterward.

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
Version: clara-aws-proof-204
Health: Green / Ok
Domain: http://Clara-aws-demo-env-1.eba-kuxghc9b.us-east-2.elasticbeanstalk.com
```

The latest Elastic Beanstalk events confirm that the instance deployment,
application-version deployment, and environment update completed successfully.
Direct endpoint verification originally passed in deterministic mode:

```text
GET /health -> {"status":"ok"}
GET /readiness -> API connected, llm_mode=false, langsmith_tracing=false
```

The environment was upgraded to full live functionality on July 31, 2026. The
AWS CLI credential on the workstation was expired, so the already authenticated
AWS Console session was used to apply the configuration to the same healthy
environment. Twelve environment properties were loaded directly from the local
ignored `.env` without printing or committing their values. Elastic Beanstalk
reported `Environment update completed successfully` and `Successfully deployed
new configuration to environment` at 12:21:09 (UTC-4), and the environment
overview returned to Health `Ok`.

Current AWS verification:

```text
GET /health -> 200 {"status":"ok"}
GET /readiness -> llm_mode=true, live_llm_available=true,
                  live_judges_available=true, langsmith_tracing=true,
                  langsmith_project=CLARA-AWS
Live ADV-001 review -> all five graph nodes SUCCESS, zero errors, final packet
Live packet judges -> both judge results returned, no API error
Sample PDF intake -> DOC-11E772B7, final packet returned, no API error
Review PDF export -> valid PDF, 6,525 bytes
```

The live review exercised `term_extractor`, `schema_validator`,
`credit_risk_scorer`, `compliance_checker`, and `review_synthesizer` against the
Nebius provider on the AWS domain. The sample document was
`Northstar_Custom_Cabinets_Loan_Profile.pdf` and completed extraction plus the
same live review graph.

The user subsequently requested a fully live model-backed configuration for the
video proof. The Vercel API is now repaired and fully live. The legacy catch-all
rewrite to `/api/index.py` was removed, and `pyproject.toml` now declares the
explicit Vercel entrypoint `loan_pipeline.api.app:app`. A `.vercelignore` file
prevents local secrets, virtual environments, tests, the frontend project, and
build artifacts from entering the API deployment bundle.

The local ignored `.env` was used only as a secure secret source. A minimal live
request proved the Nebius credential and configured Qwen model were valid before
deployment. Required Nebius, model, judge, and LangSmith values were then synced
to Vercel Preview and Production; provider and LangSmith keys are stored as
sensitive variables. `LLM_API_KEY` and `NEBIUS_API_KEY` contain the same verified
credential so the generic-key precedence in `loan_pipeline/config.py` cannot
shadow the provider-specific key.

Verified Vercel deployment on July 31, 2026:

```text
Project: clara-api
Production deployment: dpl_DxFTFMcF6iRzbqQJQ9xL9nZ1QwMA
Stable API: https://clara-api-eight.vercel.app
Preview used for verification: dpl_14CDG2bAovWVDiuHsuHBgmHTbjhd
Frontend: https://clara-web-beta.vercel.app
```

Production `/health`, `/readiness`, and `/cases` passed. Readiness reports live
Nebius mode, both judge models, LangSmith tracing, and the 50-case dataset. A
public production review of `ADV-001` completed `term_extractor`,
`schema_validator`, `compliance_checker`, `credit_risk_scorer`, and
`review_synthesizer` with `SUCCESS`, zero errors, and a final packet. The actual
frontend was also run in Chrome: it reached 100%, showed `ESCALATE / HIGH / FAIL`,
and had no browser console errors. The successful result is left open for video
proof.

The deployment/configuration fix is committed locally on
`feature/aws-deployment` as `e3782a2` (`fix: harden Vercel FastAPI deployment`).
An automated push was not permitted because repository guidance reserves Git
operations for the user. The commit contains no `.env` or `.env.local` files;
both are ignored. Push this existing commit when authorized so the remote branch
matches the live Vercel deployment.

LangSmith tracing is enabled and configured, but the account reported HTTP 429
because its monthly unique-trace quota is exhausted. This does not interrupt the
review pipeline or frontend result, but new traces may not appear until the quota
resets or the LangSmith plan/limits are changed.

AWS Console is open on the healthy environment's Events page showing the
successful configuration update. No commit or push was performed during the AWS
configuration work, per the user's instruction to ask first.

The prior `Clara-aws-demo-env` remains an orphaned historical environment whose
CloudFormation stack `awseb-e-32zfmfpy32-stack` no longer exists. Do not attempt
another deployment to it.

The AWS environment is intentionally in live mode for the full-functionality
video proof. Do not switch `USE_LLM_AGENTS` or `LANGSMITH_TRACING` back to false
until the evidence is captured.

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

1. Record the video proof from the open AWS CLARA tab. It is already showing the
   completed `ADV-001` result at 100% with `ESCALATE / HIGH / FAIL`.
2. LangSmith trace uploads may not appear until the exhausted monthly unique-trace
   quota resets; this does not interrupt the pipeline.
3. Do not commit or push without the user's explicit permission. After the demo,
   use the unchanged Vercel frontend again and terminate the AWS environments to
   stop EC2 charges.

## AWS Full-Stack Bundle History (Superseded)

This section describes the original source-build artifact. Its AWS deployment
timed out because the small EC2 instance spent more than 15 minutes building
the frontend. It has been superseded by the prebuilt bundle documented below.
The implementation remains deliberately uncommitted. It adds
`Dockerfile.aws-fullstack`, a two-process
supervisor in `scripts/start_aws_fullstack.py`, conditional same-origin API
rewrites in `web/next.config.ts`, and
`scripts/build_aws_fullstack_bundle.ps1`. The production Vercel fallback is
unchanged; an intentionally empty `NEXT_PUBLIC_API_BASE_URL` is used only by the
AWS image.

The final container uses the Python 3.12 slim base so Uvicorn retains its native
OpenSSL dependencies, copies in Node 22 for the standalone Next.js server, binds
Next.js to port 8000, and binds FastAPI internally to 127.0.0.1:8001. The first
local smoke run caught and corrected the missing OpenSSL runtime issue before
deployment.

Verified locally on July 31, 2026:

```text
Next.js production build -> passed
Frontend ESLint -> passed
Ruff -> passed
Pytest -> 138 passed, one third-party ReportLab warning
Docker production image -> built successfully
GET / on combined container -> 200
GET /health and /readiness through same origin -> passed
GET /cases through same origin -> 50 cases
ADV-001 SSE through same origin -> five SUCCESS nodes, final packet returned
```

Final archive:

```text
dist/clara-aws-fullstack-elastic-beanstalk.zip
190,432 bytes
SHA256 50957DDD6542E5A73CE4B03365DB66F797625B393AEB1C6F3EBC2BFABBDBE717
```

The archive and Docker context explicitly exclude `.env*`, `node_modules`,
`.next`, `out`, `__pycache__`, and `*.pyc`.

## AWS Full-Stack Deployment Final State

The first source-build deployment (`clara-aws-fullstack-20260731-v1`) timed out
after 15 minutes and left the instance temporarily unresponsive. The exact EC2
instance was rebooted, then the known-good `clara-aws-proof-20260731-v3` version
was redeployed successfully to restore Health `Ok`.

To avoid building Next.js on the small instance, the frontend is now built
locally and packaged with `Dockerfile.aws-fullstack-prebuilt` and
`scripts/build_aws_prebuilt_bundle.ps1`. The final AWS bundle is:

```text
dist/clara-aws-fullstack-prebuilt-elastic-beanstalk.zip
3,932,439 bytes
SHA256 04F33C4A767F36AA92DD19A944E081E2DFFC7FB3147A8553509EB036E01E9F45
```

The first prebuilt upload deployed as `clara-aws-proof-203`, but its Windows
build used an empty `NEXT_PUBLIC_API_BASE_URL`; PowerShell removed that variable
and Next.js compiled the Vercel/local fallback. This was corrected by using the
explicit `__SAME_ORIGIN__` build marker in `web/app/page.tsx`,
`Dockerfile.aws-fullstack`, and `scripts/build_aws_prebuilt_bundle.ps1`.

The corrected bundle deployed successfully as `clara-aws-proof-204`. Elastic
Beanstalk reports Health `Ok`. Chrome verification on the AWS domain confirmed:

```text
System readiness -> Ready
Loan cases -> loaded from the same-origin FastAPI backend
ADV-001 live review -> 100%
term_extractor -> completed
schema_validator -> completed
compliance_checker -> completed
credit_risk_scorer -> completed
review_synthesizer -> completed
Final packet -> ESCALATE / HIGH risk / Compliance FAIL / human gate required
```

The successful run had multi-second model-agent durations and no 401 or stream
error. The completed result is left open in Chrome for video proof. Focused AWS
configuration tests passed (5/5), frontend lint passed, and the corrected
Next.js production build passed. No commit or push was made for this work.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check loan_pipeline tests
```

## Review Findings (August 10-11, 2026)

A review stress audit found two reproducible defects. Both were fixed and
covered by regression tests on August 11. No commit, push, or deployment was
made.

Original defects:

1. Failed graph nodes were hidden by the Next.js timeline. The SSE backend
   emitted both `agent_failed` and `agent_completed` (with `status=ERROR`) for a
   failed trace. The frontend did not subscribe to `agent_failed` and counted
   every `agent_completed` event toward its five-node progress total. A simulated
   compliance-agent outage therefore produced five `agent_completed` events,
   100% progress, and no visible failed-agent event.
2. `GET /drift` did not call `enforce_rate_limit`, although one request could run
   all 50 cases up to 10 times. With `RATE_LIMIT_EXPENSIVE_REQUESTS=1`, two
   consecutive `/drift?repeats=2` calls both returned HTTP 200. As a control,
   the protected `/report` endpoint returned HTTP 429 on the second request.

Resolution:

1. `stream_review_events` now emits exactly one terminal SSE event per trace:
   `agent_failed` for an error or `agent_completed` for success. The Next.js
   client subscribes to `agent_failed`, renders it as an error, and includes
   both success and failure terminal events in progress without mislabeling a
   failure as completed.
2. `GET /drift` now accepts `Request` and enforces the existing `expensive`
   rate-limit bucket before starting the drift study.
3. Regression coverage verifies the failed specialist is not also emitted as
   completed, the browser SSE contract includes failure events, and the second
   drift request returns HTTP 429 when the expensive limit is one.

Audit verification:

```text
Focused regression tests: 31 passed, 1 third-party ReportLab warning
Full pytest: 141 passed, 1 third-party ReportLab warning
Ruff: passed
Frontend ESLint: passed
Next.js production build: passed
```

## Collaboration Notes

- Explain each meaningful change and why it is needed.
- Ask before making major architectural changes.
- The user handles Git unless they explicitly ask Codex to do it.
- Never expose or commit API keys.
- Preserve the working Vercel deployment and existing evaluation artifacts.

## Planned Amazon Bedrock Migration (August 11, 2026)

A planning-only, local-only runbook was added at
`docs/aws-bedrock-deployment-plan.md`. The user explicitly requested that this
file not be committed, so its exact path is listed in `.gitignore`. No AWS
setting, source code, dependency, commit, push, or deployment was changed for
this plan.

The plan keeps the Next.js/FastAPI/LangGraph container on the existing Elastic
Beanstalk environment and swaps only the model client to
`ChatBedrockConverse`. It recommends a least-privilege policy on the EB EC2
instance profile, no long-lived AWS access keys, staged regression testing, a
new `clara-aws-bedrock-v1` application version, and `clara-aws-proof-204` as the
rollback target. Because the repository pins LangChain 0.3, dependency
compatibility must be preserved rather than installing `langchain-aws` 1.x
blindly.

## Amazon Bedrock Migration Progress (August 13, 2026)

The migration is now implemented and verified locally, but it has not yet been
deployed or committed. Amazon Bedrock access was enabled in `us-east-2`, and a
playground request to the US Claude Haiku 4.5 inference profile returned the
requested JSON successfully.

The Elastic Beanstalk instance profile is
`aws-elasticbeanstalk-service-role`. After explicit user confirmation, the
inline policy `ClaraBedrockInvokeHaiku45` was attached to that role. It grants
only `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` for the
Claude Haiku 4.5 US inference profile and its foundation model. No AWS access
keys or Anthropic API keys were created or added to the application.

Uncommitted source changes add a provider-neutral model factory shared by the
five review agents and both live judge paths. `LLM_PROVIDER=bedrock` selects
`ChatBedrockConverse`, uses the EC2 role credential chain, and normalizes both
string and Bedrock content-block responses. Readiness and live drift now treat
Bedrock IAM configuration as valid without an LLM API key. The existing Nebius
and OpenAI-compatible path remains supported. The compatible dependency is
`langchain-aws==0.2.10`; do not upgrade this repository to `langchain-aws` 1.x
without migrating the existing LangChain 0.3 stack.

Verification completed:

```text
Focused Bedrock/provider/API tests -> 53 passed
Full pytest -> 146 passed, one third-party ReportLab warning
Ruff -> passed
pip check -> no broken requirements
Frontend ESLint -> passed
Next.js production build -> passed
Exact staged Docker image -> built successfully on Python 3.12
Container GET / -> 200
Container GET /health -> ok
Container GET /readiness -> API connected
Container GET /cases -> 50 cases
```

Verified deployment archive:

```text
dist/clara-aws-bedrock-v1-elastic-beanstalk.zip
3,933,902 bytes
SHA256 D609DE711CDCFAF9B50E276A75C1DEFD499ECF63E579AD726DFE6C3009E7E158
Archive entries: 1,180
Unsafe .env/cache/bytecode entries: 0
```

The verified archive was deployed as `clara-aws-bedrock-v1`. The application
version was first deployed with the existing Nebius properties; Health returned
to `Ok`, readiness stayed live, and `ADV-001` completed all five agents with no
failure or error events. This proved that the new provider factory preserved
the rollback provider before the configuration switch.

The environment was then updated separately with:

```text
LLM_PROVIDER=bedrock
BEDROCK_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0
AWS_REGION=us-east-2
PRIMARY_JUDGE_MODEL=us.anthropic.claude-haiku-4-5-20251001-v1:0
SECONDARY_JUDGE_MODEL=us.anthropic.claude-haiku-4-5-20251001-v1:0
```

Elastic Beanstalk reported `Environment update completed successfully` and
Health `Ok`. Current AWS state:

```text
Environment: Clara-aws-demo-env-1
Version: clara-aws-bedrock-v1
Platform: Docker running on 64bit Amazon Linux 2023/4.13.6
Provider: bedrock
Model: us.anthropic.claude-haiku-4-5-20251001-v1:0
Live LLM: available
Live judges: available
Live drift: available
```

AWS Bedrock smoke verification:

```text
GET /health -> 200 ok
GET /readiness -> bedrock, Haiku 4.5, all live features available
ADV-001 SSE -> five agent_completed, zero agent_failed/error, final packet
Chrome ADV-001 -> 100%, ESCALATE / HIGH / FAIL, human gate required
Northstar PDF intake -> DOC-11E772B7, ESCALATE / LOW / FAIL
Live packet judges -> primary 4/5, secondary 4/5, no API error
Review PDF export -> 200 application/pdf, valid %PDF signature, 6,702 bytes
```

The completed Bedrock `ADV-001` result is left open in Chrome for video proof.
The prior external-provider keys remain in Elastic Beanstalk only for the short
rollback window; they were not displayed, copied, or added to source. Remove
them from the environment and revoke the provider credential after the user
confirms the rollback window is closed. `clara-aws-proof-204` remains the
application-version rollback target. Do not commit or push these uncommitted
changes without fresh user permission.
