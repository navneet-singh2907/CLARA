"""SSE API tests."""

import json

from fastapi.testclient import TestClient

import loan_pipeline.api.app as api_app
import loan_pipeline.graph.orchestrator as orchestrator
from loan_pipeline.api.app import app
from loan_pipeline.api.rate_limit import reset_rate_limits
from loan_pipeline.api.streaming import (
    error_payload,
    sse_event,
    stream_judge_agreement_events,
    stream_live_drift_events,
    stream_review_events,
)
from loan_pipeline.config import reset_settings_cache
from loan_pipeline.llm.client import LLMResponseError


def test_sse_event_formats_named_json_event() -> None:
    raw = sse_event("progress", {"completed": 1, "total": 30})

    assert raw.startswith("event: progress\n")
    assert 'data: {"completed": 1, "total": 30}' in raw
    assert raw.endswith("\n\n")


def test_error_payload_preserves_llm_context() -> None:
    payload = error_payload(
        LLMResponseError(
            "Response is not valid JSON.",
            agent_name="credit_risk_scorer",
            case_id="ADV2-003",
            operation="add_risk_rationale",
            provider="nebius",
            model="Qwen/Qwen3-235B-A22B-Instruct-2507",
            temperature=0.2,
            response_preview="not json",
        ),
        run_type="live_drift",
    )

    assert payload["error_type"] == "LLMResponseError"
    assert payload["run_type"] == "live_drift"
    assert payload["agent_name"] == "credit_risk_scorer"
    assert payload["case_id"] == "ADV2-003"
    assert payload["operation"] == "add_risk_rationale"
    assert payload["provider"] == "nebius"
    assert payload["model"] == "Qwen/Qwen3-235B-A22B-Instruct-2507"
    assert payload["response_preview"] == "not json"


def test_review_stream_emits_run_completed() -> None:
    events = list(stream_review_events("ADV-001"))

    assert any(event.startswith("event: run_started") for event in events)
    assert any(event.startswith("event: agent_completed") for event in events)
    assert any(event.startswith("event: run_completed") for event in events)


def test_review_stream_emits_agent_failed_for_specialist_failure(monkeypatch) -> None:
    def failing_compliance_agent(*args, **kwargs):
        raise RuntimeError("simulated compliance outage")

    monkeypatch.setattr(orchestrator, "run_compliance_checker", failing_compliance_agent)

    events = list(stream_review_events("CLEAN-001"))

    assert any(event.startswith("event: agent_failed") for event in events)
    assert any(event.startswith("event: run_completed") for event in events)
    packet_event = next(event for event in events if event.startswith("event: run_completed"))
    payload = _event_payload(packet_event)
    assert payload["outcome"] == "ESCALATE"
    assert payload["escalation_required"] is True


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


def test_rate_limit_protects_expensive_endpoints(monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_EXPENSIVE_REQUESTS", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "3600")
    reset_settings_cache()
    reset_rate_limits()
    client = TestClient(app)

    first_response = client.get("/evaluation")
    second_response = client.get("/evaluation")

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert second_response.json()["detail"]["bucket"] == "expensive"
    assert "Retry-After" in second_response.headers


def test_rate_limit_allows_demo_key_bypass(monkeypatch) -> None:
    monkeypatch.setenv("CLARA_DEMO_KEY", "demo-secret")
    monkeypatch.setenv("RATE_LIMIT_EXPENSIVE_REQUESTS", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "3600")
    reset_settings_cache()
    reset_rate_limits()
    client = TestClient(app)

    first_response = client.get("/evaluation")
    second_response = client.get("/evaluation", headers={"x-clara-demo-key": "demo-secret"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200


def test_api_readiness_endpoint() -> None:
    client = TestClient(app)

    response = client.get("/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["api"] == "connected"
    assert payload["app"] == "CLARA"
    assert payload["gold_set_cases"] == 30
    assert payload["difficulty_tiers"] == {"clean": 10, "ambiguous": 10, "adversarial": 10}
    assert payload["live_drift_available"] is False


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


def test_live_drift_stream_requires_llm_mode() -> None:
    events = list(stream_live_drift_events("ADV-001", repeats=2))

    assert len(events) == 1
    assert events[0].startswith("event: error")
    payload = _event_payload(events[0])
    assert "USE_LLM_AGENTS=true" in payload["message"]


def test_api_live_drift_stream_endpoint_reports_configuration_error() -> None:
    client = TestClient(app)

    response = client.get("/drift/live/stream?case_id=ADV-001&repeats=2")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "USE_LLM_AGENTS=true" in response.text


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


def test_api_review_document_rejects_oversized_upload(monkeypatch) -> None:
    monkeypatch.setattr(api_app, "MAX_UPLOAD_BYTES", 20)
    client = TestClient(app)

    response = client.post(
        "/review/document",
        data={"policy": "sba_reviewer"},
        files={"file": ("large.txt", b"x" * 21, "text/plain")},
    )

    assert response.status_code == 400
    assert "too large" in response.json()["detail"]


def test_api_review_document_rejects_missing_required_fields() -> None:
    client = TestClient(app)
    document = "\n".join(
        [
            "Borrower: Missing Fields LLC",
            "Industry: Retail bakery",
            "This upload intentionally omits loan amount and term.",
        ]
    )

    response = client.post(
        "/review/document",
        data={"policy": "sba_reviewer"},
        files={"file": ("missing_fields.txt", document.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["message"] == "Uploaded loan document is missing required structured fields."
    assert "loan amount" in detail["missing_fields"]
    assert "loan term" in detail["missing_fields"]


def _event_payload(raw_event: str) -> dict:
    data_line = next(line for line in raw_event.splitlines() if line.startswith("data: "))
    return json.loads(data_line.replace("data: ", "", 1))
