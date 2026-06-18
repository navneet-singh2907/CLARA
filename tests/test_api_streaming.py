"""SSE API tests."""

import json

from fastapi.testclient import TestClient

from loan_pipeline.api.app import app
from loan_pipeline.api.streaming import sse_event, stream_review_events


def test_sse_event_formats_named_json_event() -> None:
    raw = sse_event("progress", {"completed": 1, "total": 30})

    assert raw.startswith("event: progress\n")
    assert 'data: {"completed": 1, "total": 30}' in raw
    assert raw.endswith("\n\n")


def test_review_stream_emits_run_completed() -> None:
    events = list(stream_review_events("ADV-001"))

    assert any(event.startswith("event: run_started") for event in events)
    assert any(event.startswith("event: agent_completed") for event in events)
    assert any(event.startswith("event: run_completed") for event in events)


def test_review_stream_reports_unknown_case() -> None:
    events = list(stream_review_events("NOPE-001"))

    assert len(events) == 1
    assert events[0].startswith("event: error")
    payload = _event_payload(events[0])
    assert "Unknown case_id" in payload["message"]


def test_api_health_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_root_endpoint_lists_streaming_command() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Loan Review Pipeline API" in response.text
    assert "/review/stream?case_id=ADV-001" in response.text


def test_api_review_stream_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/review/stream?case_id=ADV-001")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "event: run_completed" in response.text


def _event_payload(raw_event: str) -> dict:
    data_line = next(line for line in raw_event.splitlines() if line.startswith("data: "))
    return json.loads(data_line.replace("data: ", "", 1))
