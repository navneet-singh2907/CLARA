# CLARA Deployment Guide

This guide covers local demo setup and cloud deployment for CLARA, the Credit Loan Analysis & Review Agent.

## Architecture

```text
Next.js UI
  |
  | HTTPS fetch + EventSource
  v
FastAPI backend
  |
  | LangGraph + LangChain
  v
LLM provider / LangSmith / local evaluation harness
```

Recommended cloud shape:

```text
Project 1: CLARA API
  Root: repository root
  Entrypoint: api/index.py
  Runtime: Python

Project 2: CLARA Web UI
  Root: web/
  Runtime: Next.js
  Env: NEXT_PUBLIC_API_BASE_URL=<deployed API URL>
```

The UI can be deployed to Vercel. The backend can be deployed to Vercel for basic API routes, but long-running SSE/model calls are more reliable on a backend host that supports persistent HTTP streaming and longer request timeouts, such as Render, Railway, Fly.io, or a small VM.

## Local Demo

Start the API:

```powershell
cd C:\Users\nsingh1\CLARA
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m uvicorn loan_pipeline.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Start the web UI:

```powershell
cd C:\Users\nsingh1\CLARA\web
npm.cmd install
$env:NEXT_PUBLIC_API_BASE_URL="http://127.0.0.1:8000"
npm.cmd run dev
```

Open:

```text
http://localhost:3000
```

Sanity checks:

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/readiness
curl.exe -N "http://127.0.0.1:8000/review/stream?case_id=ADV-001&policy=sba_reviewer"
```

## Dockerized Full Stack

Docker lets you run the CLARA API and web UI with one command.

Files:

```text
Dockerfile.api
web/Dockerfile
docker-compose.yml
.env.docker.example
```

First-time setup:

```powershell
Copy-Item .env.docker.example .env
```

If you already have a working `.env`, keep it and only add the Docker-specific `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` value.

Start the full stack:

```powershell
docker compose up --build
```

Open:

```text
http://localhost:3000
```

API checks:

```text
http://localhost:8000/health
http://localhost:8000/readiness
```

Stop the stack:

```powershell
docker compose down
```

For live LLM mode, edit `.env` before starting Docker:

```text
USE_LLM_AGENTS=true
NEBIUS_API_KEY=<your_key>
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1/
OPENAI_MODEL=<exact_available_model_id>
LLM_TEMPERATURE=0.7
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Keep `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` for local Docker demos because the browser runs outside the Docker network.

## Environment Variables

Backend variables:

```text
USE_LLM_AGENTS=true
LLM_PROVIDER=nebius
NEBIUS_API_KEY=<your_nebius_key>
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1/
OPENAI_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507
LLM_TEMPERATURE=0.2
PRIMARY_JUDGE_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507
SECONDARY_JUDGE_MODEL=openai/gpt-oss-120b
JUDGE_TEMPERATURE=0.2
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=loan-review-pipeline
APP_ENV=production
```

Generic provider aliases are also supported:

```text
LLM_API_KEY=<provider_key>
LLM_BASE_URL=<openai_compatible_base_url>
```

Use either the Nebius-specific variables or the generic variables. Do not put API keys in the frontend project.

Frontend variables:

```text
NEXT_PUBLIC_API_BASE_URL=https://<your-clara-api-domain>
```

## Deploy The FastAPI Backend

### Option A: Vercel Python API

1. Create a new Vercel project from the repo root.
2. Keep root directory as the repository root.
3. Ensure the entrypoint exists:

```text
api/index.py
```

4. Add backend environment variables in Vercel.
5. Deploy.
6. Verify:

```text
https://<api-project>.vercel.app/health
https://<api-project>.vercel.app/readiness
```

Use this for lightweight demo endpoints. If long evaluation, judge, upload, or SSE requests time out, move the backend to Option B.

### Option B: Render/Railway/Fly Backend

Use this command:

```bash
uvicorn loan_pipeline.api.app:app --host 0.0.0.0 --port $PORT
```

Install command:

```bash
python -m pip install --upgrade pip && pip install -r requirements.txt
```

Health check path:

```text
/health
```

## Deploy The Next.js UI To Vercel

1. Create a second Vercel project.
2. Set root directory to:

```text
web
```

3. Add:

```text
NEXT_PUBLIC_API_BASE_URL=https://<your-clara-api-domain>
```

4. Build command:

```text
npm run build
```

5. Install command:

```text
npm ci
```

6. Deploy.

The top-right System Readiness panel should show whether the UI can reach the API and whether live LLM drift is available.

## Demo Checklist

Before recording:

- API `/health` returns `{"status":"ok"}`.
- API `/readiness` shows `api: connected`.
- UI System Readiness shows `Ready`.
- Drift tab can run one selected case three times.
- Loan Review tab streams LangGraph events.
- PDF packet download works.
- Judge Agreement can score an uploaded packet.
- Report tab downloads a PDF evaluation report.

## Common Errors

### UI Says API Offline

Cause: `NEXT_PUBLIC_API_BASE_URL` is missing or points to the wrong backend.

Fix:

```text
NEXT_PUBLIC_API_BASE_URL=https://<your-clara-api-domain>
```

Then redeploy the web project.

### Live Drift Says LLM Mode Is Required

Cause: backend does not have live LLM mode enabled.

Fix:

```text
USE_LLM_AGENTS=true
NEBIUS_API_KEY=<your_key>
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1/
OPENAI_MODEL=<exact_available_model_id>
```

Then redeploy or restart the backend.

### Model Does Not Exist

Cause: `OPENAI_MODEL` does not match a model ID available to your provider account.

Fix: verify the exact model ID in the provider dashboard or `/v1/models` endpoint and update `OPENAI_MODEL`.

### Long Runs Hang Or Timeout

Cause: serverless timeout or buffering.

Fix: use a backend host with longer request timeouts and streaming support. Keep the Next UI on Vercel and point `NEXT_PUBLIC_API_BASE_URL` to that backend.

### CORS Error

Cause: frontend origin is not allowed by the FastAPI CORS settings.

Current backend allows:

```text
http://localhost:3000
http://127.0.0.1:3000
https://*.vercel.app
```

If using a custom domain, add it to `allow_origins` in `loan_pipeline/api/app.py`.

## Production Notes

- Never expose model provider keys in the Next.js frontend.
- Keep full 30-case live judging intentional because it can make many API calls.
- Use the deterministic benchmark for reproducible metrics.
- Use the live LLM drift probe for nondeterminism evidence in the demo.
- Treat CLARA as decision support; final loan decisions remain human-reviewed.
