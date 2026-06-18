"""SSE API tests."""

import json

from fastapi.testclient import TestClient

from loan_pipeline.api.app import app
from loan_pipeline.api.streaming import (
    sse_event,
    stream_judge_agreement_events,
    stream_review_events,
)


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
    assert "CLARA API" in response.text
    assert "/review/stream?case_id=ADV-001" in response.text


def test_api_review_stream_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/review/stream?case_id=ADV-001")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "event: run_completed" in response.text


def test_judge_agreement_stream_emits_activity_logs() -> None:
    events = list(stream_judge_agreement_events())

    assert any(event.startswith("event: judge_activity") for event in events)
    assert any("judge_pair_configured" in event for event in events)
    assert any("agreement_computed" in event for event in events)


def test_api_evaluation_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/evaluation")

    assert response.status_code == 200
    assert response.json()["summary"]["overall"]["cases"] == 30


def test_api_ablation_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/ablation")

    assert response.status_code == 200
    assert any(row["configuration"] == "full_pipeline" for row in response.json())


def test_api_drift_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/drift?repeats=2")

    assert response.status_code == 200
    assert response.json()["repeats"] == 2


def test_api_judge_agreement_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/judge-agreement")

    assert response.status_code == 200
    assert response.json()["cases"] == 30


def test_api_packet_judge_agreement_endpoint() -> None:
    client = TestClient(app)
    packet_text = "\n".join(
        [
            "CLARA Loan Review Packet",
            "Borrower: Upload Demo Bakery LLC",
            "Loan Amount: $250,000",
            "Term: 84 months",
            "Recommended Outcome: APPROVE",
            "Compliance: PASS",
            "Risk Band: LOW",
            "Risk rationale: stable borrower with clean documentation.",
            "Human Review Notes: no override required.",
        ]
    )

    response = client.post(
        "/judge-agreement/packet",
        files={"file": ("packet.txt", packet_text.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_name"] == "packet.txt"
    assert payload["cases"] == 1
    assert "primary" in payload
    assert "secondary" in payload
    assert "dimension_deltas" in payload


def test_api_report_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/report")

    assert response.status_code == 200
    assert "CLARA Evaluation Report" in response.text


def test_api_report_pdf_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/report/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_api_review_pdf_endpoint() -> None:
    client = TestClient(app)

    response = client.post(
        "/review/pdf",
        json={
            "case_id": "ADV-001",
            "policy": "sba_reviewer",
            "audit_entries": [
                {
                    "target": "Outcome - ESCALATE",
                    "decision": "Approve despite finding",
                    "reviewer": "Human reviewer",
                    "rationale": "Verified collateral support justifies conditional approval.",
                    "createdAt": "2026-06-18T00:00:00.000Z",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_api_review_document_endpoint() -> None:
    client = TestClient(app)
    document = "\n".join(
        [
            "Borrower: Upload Demo Bakery LLC",
            "Industry: Retail bakery",
            "NAICS: 311811",
            "Loan amount: $250,000",
            "SBA guarantee: $187,500",
            "Term: 84",
            "Jobs supported: 9",
            "Credit score: 701",
            "Years in business: 4.5",
            "Missing documents: none",
        ]
    )

    response = client.post(
        "/review/document",
        data={"policy": "sba_reviewer"},
        files={"file": ("loan.txt", document.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["case"]["borrower_name"] == "Upload Demo Bakery LLC"
    assert payload["loan_case"]["borrower_name"] == "Upload Demo Bakery LLC"
    assert payload["audit_targets"][0].startswith("Outcome - ")
    assert payload["packet"]["outcome"] in {"APPROVE", "CONDITIONAL_REVIEW", "ESCALATE", "REJECT"}

    pdf_response = client.post(
        "/review/pdf",
        json={
            "loan_case": payload["loan_case"],
            "policy": "sba_reviewer",
            "audit_entries": [
                {
                    "target": payload["audit_targets"][0],
                    "decision": "Accept agent finding",
                    "reviewer": "Human reviewer",
                    "rationale": "Uploaded application review accepted for demo packet.",
                    "createdAt": "2026-06-18T00:00:00.000Z",
                }
            ],
        },
    )

    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")


def _event_payload(raw_event: str) -> dict:
    data_line = next(line for line in raw_event.splitlines() if line.startswith("data: "))
    return json.loads(data_line.replace("data: ", "", 1))
