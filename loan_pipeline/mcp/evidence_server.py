"""Read-only MCP evidence server for CLARA loan review artifacts.

The server exposes CLARA's evidence layer to MCP-capable clients: source loan
cases, reviewer policy profiles, gold labels, and deterministic pipeline traces.
It intentionally does not mutate audit logs, trigger live LLM calls, or write data.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from typing import Any, BinaryIO, Literal

from loan_pipeline.config import (
    GOLD_SET_JSON,
    SBA_LOANS_CSV,
    WEEK4_GOLD_SET_JSON,
    WEEK4_SBA_LOANS_CSV,
    load_sba_demo_cases,
    offline_evaluation_context,
)
from loan_pipeline.eval.metrics import score_case
from loan_pipeline.eval.run_eval import load_gold_labels
from loan_pipeline.graph.orchestrator import run_pipeline_with_state
from loan_pipeline.graph.state import ReviewPolicy
from loan_pipeline.review.policies import POLICY_PROFILES, get_policy_profile

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "clara-evidence-server"
SERVER_VERSION = "0.1.0"

DatasetName = Literal["product_demo", "week4"]

DATASETS = {
    "product_demo": {
        "cases_path": SBA_LOANS_CSV,
        "gold_path": GOLD_SET_JSON,
        "description": "Original 30-case product-demo gold set.",
    },
    "week4": {
        "cases_path": WEEK4_SBA_LOANS_CSV,
        "gold_path": WEEK4_GOLD_SET_JSON,
        "description": "Week 4 50-case evaluation lab gold set.",
    },
}


class MCPToolError(ValueError):
    """Raised when a tool call is valid JSON-RPC but invalid for CLARA."""


def list_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "list_loan_cases",
            "description": "List CLARA loan cases with optional dataset and difficulty filters.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "dataset": {
                        "type": "string",
                        "enum": list(DATASETS),
                        "default": "product_demo",
                    },
                    "tier": {"type": "string"},
                },
            },
        },
        {
            "name": "lookup_loan_case",
            "description": "Return the structured source data for one CLARA loan case.",
            "inputSchema": {
                "type": "object",
                "required": ["case_id"],
                "properties": {
                    "case_id": {"type": "string"},
                    "dataset": {
                        "type": "string",
                        "enum": list(DATASETS),
                        "default": "product_demo",
                    },
                },
            },
        },
        {
            "name": "get_policy_profile",
            "description": "Return the threshold profile for an SBA, bank, or CDFI reviewer mode.",
            "inputSchema": {
                "type": "object",
                "required": ["policy"],
                "properties": {
                    "policy": {
                        "type": "string",
                        "enum": list(POLICY_PROFILES),
                    }
                },
            },
        },
        {
            "name": "get_gold_label",
            "description": "Return the expected gold-set outcome for one case.",
            "inputSchema": {
                "type": "object",
                "required": ["case_id"],
                "properties": {
                    "case_id": {"type": "string"},
                    "dataset": {
                        "type": "string",
                        "enum": list(DATASETS),
                        "default": "product_demo",
                    },
                },
            },
        },
        {
            "name": "compare_case_to_gold",
            "description": (
                "Run CLARA deterministically for one case and compare the packet to its gold label."
            ),
            "inputSchema": {
                "type": "object",
                "required": ["case_id"],
                "properties": {
                    "case_id": {"type": "string"},
                    "dataset": {
                        "type": "string",
                        "enum": list(DATASETS),
                        "default": "product_demo",
                    },
                    "policy": {
                        "type": "string",
                        "enum": list(POLICY_PROFILES),
                        "default": "sba_reviewer",
                    },
                },
            },
        },
        {
            "name": "inspect_pipeline_trace",
            "description": (
                "Run CLARA deterministically and return agent trace entries, errors, and final packet."
            ),
            "inputSchema": {
                "type": "object",
                "required": ["case_id"],
                "properties": {
                    "case_id": {"type": "string"},
                    "dataset": {
                        "type": "string",
                        "enum": list(DATASETS),
                        "default": "product_demo",
                    },
                    "policy": {
                        "type": "string",
                        "enum": list(POLICY_PROFILES),
                        "default": "sba_reviewer",
                    },
                },
            },
        },
    ]


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    arguments = arguments or {}
    if name == "list_loan_cases":
        result = _list_loan_cases(arguments)
    elif name == "lookup_loan_case":
        result = _lookup_loan_case(arguments)
    elif name == "get_policy_profile":
        result = _get_policy_profile(arguments)
    elif name == "get_gold_label":
        result = _get_gold_label(arguments)
    elif name == "compare_case_to_gold":
        result = _compare_case_to_gold(arguments)
    elif name == "inspect_pipeline_trace":
        result = _inspect_pipeline_trace(arguments)
    else:
        raise MCPToolError(f"Unknown CLARA MCP tool: {name}")

    return {
        "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
        "structuredContent": result,
    }


def handle_request(request: dict[str, Any]) -> dict[str, Any] | None:
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params") or {}

    try:
        if method == "initialize":
            result = {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            }
        elif method == "tools/list":
            result = {"tools": list_tools()}
        elif method == "tools/call":
            result = call_tool(params.get("name", ""), params.get("arguments") or {})
        elif method in {"notifications/initialized", "initialized"}:
            return None
        elif method == "ping":
            result = {}
        else:
            return _json_rpc_error(request_id, -32601, f"Method not found: {method}")
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except MCPToolError as exc:
        return _json_rpc_error(request_id, -32602, str(exc))
    except Exception as exc:
        return _json_rpc_error(request_id, -32000, f"CLARA MCP server error: {exc}")


def serve_stdio(
    input_stream: BinaryIO = sys.stdin.buffer,
    output_stream: BinaryIO = sys.stdout.buffer,
) -> None:
    """Serve JSON-RPC messages over MCP stdio Content-Length framing."""
    while True:
        request = _read_message(input_stream)
        if request is None:
            break

        responses: list[dict[str, Any]] = []
        for item in request if isinstance(request, list) else [request]:
            response = handle_request(item)
            if response is not None:
                responses.append(response)

        if not responses:
            continue
        _write_message(responses if isinstance(request, list) else responses[0], output_stream)


def _list_loan_cases(arguments: dict[str, Any]) -> dict[str, Any]:
    dataset = _dataset_name(arguments.get("dataset"))
    tier = arguments.get("tier")
    cases = _load_cases(dataset)
    if tier:
        cases = [loan_case for loan_case in cases if loan_case.difficulty_tier == tier]

    return {
        "dataset": dataset,
        "count": len(cases),
        "cases": [
            {
                "case_id": loan_case.case_id,
                "borrower_name": loan_case.borrower_name,
                "tier": loan_case.difficulty_tier,
                "loan_amount": loan_case.loan_amount,
                "prior_default": loan_case.prior_default,
                "missing_documents": loan_case.missing_documents,
            }
            for loan_case in cases
        ],
    }


def _lookup_loan_case(arguments: dict[str, Any]) -> dict[str, Any]:
    dataset = _dataset_name(arguments.get("dataset"))
    loan_case = _case_by_id(_required_str(arguments, "case_id"), dataset)
    return {"dataset": dataset, "loan_case": asdict(loan_case)}


def _get_policy_profile(arguments: dict[str, Any]) -> dict[str, Any]:
    policy = _review_policy(arguments.get("policy"))
    return {"policy_profile": asdict(get_policy_profile(policy))}


def _get_gold_label(arguments: dict[str, Any]) -> dict[str, Any]:
    dataset = _dataset_name(arguments.get("dataset"))
    label = _gold_label_by_id(_required_str(arguments, "case_id"), dataset)
    return {"dataset": dataset, "gold_label": asdict(label)}


def _compare_case_to_gold(arguments: dict[str, Any]) -> dict[str, Any]:
    dataset = _dataset_name(arguments.get("dataset"))
    policy = _review_policy(arguments.get("policy", "sba_reviewer"))
    loan_case = _case_by_id(_required_str(arguments, "case_id"), dataset)
    gold_label = _gold_label_by_id(loan_case.case_id, dataset)

    with offline_evaluation_context():
        state = run_pipeline_with_state(loan_case, review_policy=policy)

    packet = state["review_packet"]
    if packet is None:
        raise MCPToolError(f"Pipeline produced no review packet for {loan_case.case_id}.")

    score = score_case(loan_case, packet, gold_label)
    return {
        "dataset": dataset,
        "case_id": loan_case.case_id,
        "policy": policy,
        "expected": asdict(gold_label),
        "predicted": {
            "compliance_status": packet.compliance.status,
            "risk_band": packet.risk.band,
            "escalation_required": packet.escalation_required,
            "recommended_outcome": packet.recommended_outcome,
        },
        "score": asdict(score),
        "agent_errors": state["agent_errors"],
    }


def _inspect_pipeline_trace(arguments: dict[str, Any]) -> dict[str, Any]:
    dataset = _dataset_name(arguments.get("dataset"))
    policy = _review_policy(arguments.get("policy", "sba_reviewer"))
    loan_case = _case_by_id(_required_str(arguments, "case_id"), dataset)

    with offline_evaluation_context():
        state = run_pipeline_with_state(loan_case, review_policy=policy)

    packet = state["review_packet"]
    return {
        "dataset": dataset,
        "case_id": loan_case.case_id,
        "policy": policy,
        "agent_errors": state["agent_errors"],
        "validation_errors": state["validation_errors"],
        "execution_trace": [asdict(entry) for entry in state["execution_trace"]],
        "review_packet": asdict(packet) if packet else None,
    }


def _load_cases(dataset: DatasetName):
    return load_sba_demo_cases(DATASETS[dataset]["cases_path"])


def _load_labels(dataset: DatasetName):
    return load_gold_labels(DATASETS[dataset]["gold_path"])


def _case_by_id(case_id: str, dataset: DatasetName):
    cases = {loan_case.case_id: loan_case for loan_case in _load_cases(dataset)}
    try:
        return cases[case_id]
    except KeyError as exc:
        raise MCPToolError(f"Unknown case_id for {dataset}: {case_id}") from exc


def _gold_label_by_id(case_id: str, dataset: DatasetName):
    labels = {label.case_id: label for label in _load_labels(dataset)}
    try:
        return labels[case_id]
    except KeyError as exc:
        raise MCPToolError(f"No gold label found for {dataset} case_id: {case_id}") from exc


def _dataset_name(raw_value: Any) -> DatasetName:
    dataset = raw_value or "product_demo"
    if dataset not in DATASETS:
        raise MCPToolError(f"Unknown dataset: {dataset}. Expected one of {list(DATASETS)}.")
    return dataset


def _review_policy(raw_value: Any) -> ReviewPolicy:
    policy = raw_value or "sba_reviewer"
    if policy not in POLICY_PROFILES:
        raise MCPToolError(f"Unknown review policy: {policy}. Expected one of {list(POLICY_PROFILES)}.")
    return policy


def _required_str(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MCPToolError(f"Missing required string argument: {key}")
    return value.strip()


def _json_rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _read_message(input_stream: BinaryIO) -> dict[str, Any] | list[dict[str, Any]] | None:
    headers: dict[str, str] = {}
    while True:
        line = input_stream.readline()
        if line == b"":
            return None
        if line.lstrip().startswith(b"{"):
            return json.loads(line.decode("utf-8"))
        if line in {b"\r\n", b"\n"}:
            break
        key, _, value = line.decode("ascii").partition(":")
        if key and value:
            headers[key.lower()] = value.strip()

    content_length = headers.get("content-length")
    if not content_length:
        raise MCPToolError("Missing Content-Length header.")
    body = input_stream.read(int(content_length))
    return json.loads(body.decode("utf-8"))


def _write_message(response: dict[str, Any] | list[dict[str, Any]], output_stream: BinaryIO) -> None:
    body = json.dumps(response, separators=(",", ":")).encode("utf-8")
    output_stream.write(body + b"\n")
    output_stream.flush()


def main() -> None:
    serve_stdio()


if __name__ == "__main__":
    main()
