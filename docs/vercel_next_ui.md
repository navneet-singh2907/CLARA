# Vercel Next.js UI Experiment

This branch adds a browser-native Next.js UI in `web/`.

## Local Demo

Start the FastAPI/LangGraph backend:

```powershell
cd C:\Users\nsingh1\CLARA
.\.venv\Scripts\Activate.ps1
uvicorn loan_pipeline.api.app:app --reload --port 8000
```

Start the Next.js frontend:

```powershell
cd C:\Users\nsingh1\CLARA\web
npm.cmd install
npm.cmd run dev
```

Open:

```text
http://localhost:3000
```

## Vercel Shape

Recommended if we continue this route:

1. Deploy the Python API as one Vercel project from repo root.
   - Entrypoint: `api/index.py`
   - Backend app: `loan_pipeline.api.app:app`

2. Deploy the Next.js UI as a second Vercel project using `web/` as the root directory.
   - Set `NEXT_PUBLIC_API_BASE_URL` to the deployed API URL.

This keeps the Streamlit app untouched and lets the Vercel UI call the same FastAPI SSE endpoints.

## Current UI Coverage

- Case selector
- Reviewer policy selector
- Live `EventSource` stream from `/review/stream`
- LangGraph agent timeline
- Final review packet summary
- Human override audit log UI
- Evaluation tab backed by `/evaluation`
- Ablation tab backed by `/ablation`
- Drift tab backed by `/drift`
- Judge agreement tab backed by `/judge-agreement`
- Markdown report preview/download backed by `/report`
- Visible progress panel for evaluation, ablation, drift, judge agreement, report, and PDF generation
- Activity log panels across the long-running tabs so the demo does not look frozen
- Document/PDF upload review backed by `/review/document`
- PDF review packet download backed by `/review/pdf`

## Still Missing Compared With Streamlit

- Streamlit's detailed graph-state JSON inspectors
