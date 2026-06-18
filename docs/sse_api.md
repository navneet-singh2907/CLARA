# SSE Streaming API

The Next/Vercel dashboard is the main demo UI. The FastAPI SSE server is the observability layer for showing live agent, evaluation, judge, and drift progress.

## Run

```powershell
uvicorn loan_pipeline.api.app:app --reload --port 8000
```

## Endpoints

```text
GET /health
GET /cases
GET /review/stream?case_id=ADV-001&policy=sba_reviewer
GET /evaluation/stream
GET /drift/live/stream?case_id=ADV-001&policy=sba_reviewer&repeats=3
GET /judge-agreement/stream
```

## Event Types

```text
run_started
agent_completed
graph_update
drift_activity
drift_run_completed
progress
run_completed
error
```

## Example

```text
event: progress
data: {"completed": 12, "total": 30, "current_case": "AMB-002"}
```

The review stream uses the compiled LangGraph workflow and emits graph/node updates as the pipeline advances. The evaluation and judge-agreement streams emit per-case progress so full 30-case runs do not look frozen. The live drift stream repeats one selected case through live LLM agents, emits a fingerprint after each run, and returns a final variant count so the UI can show whether nondeterministic model calls changed the material loan-review output.
