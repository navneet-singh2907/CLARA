# SSE Streaming API

The Streamlit dashboard remains the main demo UI. The FastAPI SSE server is an optional observability layer for showing live agent and evaluation progress outside Streamlit.

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
GET /judge-agreement/stream
```

## Event Types

```text
run_started
agent_completed
graph_update
progress
run_completed
error
```

## Example

```text
event: progress
data: {"completed": 12, "total": 30, "current_case": "AMB-002"}
```

The review stream uses the compiled LangGraph workflow and emits graph/node updates as the pipeline advances. The evaluation and judge-agreement streams emit per-case progress so full 30-case live runs do not look frozen.
