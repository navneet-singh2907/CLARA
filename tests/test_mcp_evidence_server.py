"""Tests for the CLARA MCP evidence server."""

import json
from io import BytesIO

from loan_pipeline.mcp.evidence_server import (
    call_tool,
    handle_request,
    list_tools,
    serve_stdio,
)


def test_list_tools_exposes_clara_evidence_tools() -> None:
    tool_names = {tool["name"] for tool in list_tools()}

    assert "lookup_loan_case" in tool_names
    assert "get_gold_label" in tool_names
    assert "compare_case_to_gold" in tool_names
    assert "inspect_pipeline_trace" in tool_names


def test_lookup_loan_case_returns_structured_case() -> None:
    response = call_tool("lookup_loan_case", {"case_id": "ADV-001"})

    payload = response["structuredContent"]
    assert payload["loan_case"]["case_id"] == "ADV-001"
    assert payload["loan_case"]["borrower_name"] == "Summit Event Holdings"


def test_compare_case_to_gold_reports_prediction_and_score() -> None:
    response = call_tool("compare_case_to_gold", {"case_id": "ADV-001"})

    payload = response["structuredContent"]
    assert payload["expected"]["case_id"] == "ADV-001"
    assert payload["predicted"]["recommended_outcome"] == "ESCALATE"
    assert payload["score"]["case_id"] == "ADV-001"


def test_handle_request_returns_mcp_tools_list() -> None:
    response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    assert response is not None
    assert response["id"] == 1
    assert response["result"]["tools"]


def test_handle_request_returns_tool_error_for_unknown_case() -> None:
    response = handle_request(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "lookup_loan_case",
                "arguments": {"case_id": "MISSING-999"},
            },
        }
    )

    assert response is not None
    assert response["error"]["code"] == -32602
    assert "Unknown case_id" in response["error"]["message"]


def test_serve_stdio_supports_content_length_framing() -> None:
    request = json.dumps({"jsonrpc": "2.0", "id": 3, "method": "initialize"}).encode("utf-8")
    input_stream = BytesIO(b"Content-Length: " + str(len(request)).encode("ascii") + b"\r\n\r\n" + request)
    output_stream = BytesIO()

    serve_stdio(input_stream, output_stream)

    raw_output = output_stream.getvalue()
    _, _, body = raw_output.partition(b"\r\n\r\n")
    response = json.loads(body.decode("utf-8"))
    assert response["result"]["serverInfo"]["name"] == "clara-evidence-server"
