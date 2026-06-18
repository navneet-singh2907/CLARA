"""FastAPI entrypoint for SSE streaming endpoints."""

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, Response, StreamingResponse

from loan_pipeline.api.streaming import (
    stream_evaluation_events,
    stream_judge_agreement_events,
    stream_review_events,
)
from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.graph.state import ReviewPolicy

app = FastAPI(
    title="Loan Review Pipeline API",
    version="0.1.0",
    description="SSE endpoints for observing LangGraph loan review agents and evaluation runs.",
)

CASE_ID_QUERY = Query(..., description="Gold-set case ID, for example ADV-001.")
POLICY_QUERY = Query("sba_reviewer", description="Reviewer policy profile.")


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <title>Loan Review Pipeline API</title>
        <style>
          body { font-family: Arial, sans-serif; max-width: 880px; margin: 48px auto; line-height: 1.5; }
          code, pre { background: #f4f4f4; border-radius: 6px; padding: 2px 6px; }
          pre { padding: 12px; overflow-x: auto; }
          a { color: #b91c1c; }
        </style>
      </head>
      <body>
        <h1>Loan Review Pipeline API</h1>
        <p>This FastAPI backend streams LangGraph loan-review events with Server-Sent Events.</p>
        <h2>Quick Checks</h2>
        <ul>
          <li><a href="/health">/health</a></li>
          <li><a href="/cases">/cases</a></li>
          <li><a href="/docs">/docs</a></li>
        </ul>
        <h2>SSE Test</h2>
        <p>Use this in PowerShell so you can see events arrive live:</p>
        <pre>curl.exe -N "http://127.0.0.1:8000/review/stream?case_id=ADV-001&amp;policy=sba_reviewer"</pre>
      </body>
    </html>
    """


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/cases")
def cases() -> list[dict[str, str]]:
    return [
        {
            "case_id": loan_case.case_id,
            "borrower_name": loan_case.borrower_name,
            "tier": loan_case.difficulty_tier,
        }
        for loan_case in load_sba_demo_cases()
    ]


@app.get("/review/stream")
def review_stream(
    case_id: str = CASE_ID_QUERY,
    policy: ReviewPolicy = POLICY_QUERY,
) -> StreamingResponse:
    return StreamingResponse(
        stream_review_events(case_id=case_id, review_policy=policy),
        media_type="text/event-stream",
    )


@app.get("/evaluation/stream")
def evaluation_stream() -> StreamingResponse:
    return StreamingResponse(stream_evaluation_events(), media_type="text/event-stream")


@app.get("/judge-agreement/stream")
def judge_agreement_stream() -> StreamingResponse:
    return StreamingResponse(stream_judge_agreement_events(), media_type="text/event-stream")
