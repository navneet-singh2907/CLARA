"""Server-sent event generators for the loan review API."""

import json
from queue import Queue
from threading import Thread
from typing import Any, Iterable

from loan_pipeline.config import (
    WEEK4_GOLD_SET_JSON,
    WEEK4_SBA_LOANS_CSV,
    get_settings,
    load_sba_demo_cases,
)
from loan_pipeline.eval.drift import fingerprint_review_packet
from loan_pipeline.eval.inter_rater import run_inter_rater_report
from loan_pipeline.eval.run_eval import load_gold_labels, run_eval
from loan_pipeline.graph.orchestrator import build_review_graph, run_pipeline
from loan_pipeline.graph.state import ReviewPolicy, initial_state
from loan_pipeline.llm.client import LLMResponseError


def sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def error_payload(exc: Exception, **context: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"message": str(exc), **context}
    if isinstance(exc, LLMResponseError):
        payload.update(exc.to_dict())
        payload["error_type"] = "LLMResponseError"
    else:
        payload["error_type"] = type(exc).__name__
    return payload


def stream_review_events(
    case_id: str,
    review_policy: ReviewPolicy = "sba_reviewer",
) -> Iterable[str]:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases(WEEK4_SBA_LOANS_CSV)}
    loan_case = cases.get(case_id)
    if loan_case is None:
        yield sse_event("error", {"message": f"Unknown case_id: {case_id}"})
        return

    yield sse_event(
        "run_started",
        {
            "case_id": loan_case.case_id,
            "borrower_name": loan_case.borrower_name,
            "tier": loan_case.difficulty_tier,
            "review_policy": review_policy,
        },
    )

    graph = build_review_graph()
    review_packet = None
    try:
        for chunk in graph.stream(initial_state(loan_case, review_policy=review_policy)):
            for node, update in chunk.items():
                for trace_entry in update.get("execution_trace", []):
                    if trace_entry.status == "ERROR":
                        yield sse_event(
                            "agent_failed",
                            {
                                "node": trace_entry.node,
                                "stage": trace_entry.stage,
                                "parallel_group": trace_entry.parallel_group,
                                "duration_ms": trace_entry.duration_ms,
                                "status": trace_entry.status,
                            },
                        )
                    yield sse_event(
                        "agent_completed",
                        {
                            "node": trace_entry.node,
                            "stage": trace_entry.stage,
                            "parallel_group": trace_entry.parallel_group,
                            "duration_ms": trace_entry.duration_ms,
                            "status": trace_entry.status,
                        },
                    )

                if update.get("review_packet") is not None:
                    review_packet = update["review_packet"]

                yield sse_event("graph_update", {"node": node, "keys": sorted(update.keys())})
    except Exception as exc:
        yield sse_event("error", error_payload(exc, case_id=loan_case.case_id))
        return

    if review_packet is None:
        yield sse_event(
            "error",
            {"case_id": loan_case.case_id, "message": "Pipeline finished without a review packet."},
        )
        return

    yield sse_event(
        "run_completed",
        {
            "case_id": review_packet.case_id,
            "outcome": review_packet.recommended_outcome,
            "risk": review_packet.risk.band,
            "compliance": review_packet.compliance.status,
            "escalation_required": review_packet.escalation_required,
            "summary": review_packet.summary,
            "contradictions": len(review_packet.contradictions),
            "counterfactuals": len(review_packet.counterfactuals),
        },
    )


def stream_evaluation_events() -> Iterable[str]:
    labels = load_gold_labels(WEEK4_GOLD_SET_JSON)
    total_cases = len(labels)
    yield sse_event("run_started", {"run_type": "evaluation", "total_cases": total_cases})

    event_queue: Queue[str | None] = Queue()

    def emit_progress(completed: int, total: int, case_id: str) -> None:
        event_queue.put(
            sse_event(
                "progress",
                {"completed": completed, "total": total, "current_case": case_id},
            )
        )

    def worker() -> None:
        try:
            result = run_eval(
                gold_path=WEEK4_GOLD_SET_JSON,
                cases_path=WEEK4_SBA_LOANS_CSV,
                progress_callback=emit_progress,
            )
            event_queue.put(
                sse_event(
                    "run_completed",
                    {
                        "run_type": "evaluation",
                        "summary": result["summary"]["overall"],
                        "failure_counts": result["failure_counts"],
                    },
                )
            )
        except Exception as exc:
            event_queue.put(sse_event("error", error_payload(exc, run_type="evaluation")))
        finally:
            event_queue.put(None)

    Thread(target=worker, daemon=True).start()
    while True:
        item = event_queue.get()
        if item is None:
            break
        yield item


def stream_judge_agreement_events() -> Iterable[str]:
    total_cases = len(load_gold_labels(WEEK4_GOLD_SET_JSON))
    settings = get_settings()
    primary_model = settings.primary_judge_model or "local primary judge"
    secondary_model = settings.secondary_judge_model or "local strict secondary judge"
    yield sse_event("run_started", {"run_type": "judge_agreement", "total_cases": total_cases})
    yield sse_event(
        "judge_activity",
        {
            "step": "judge_pair_configured",
            "message": "Configured independent primary and secondary judge models.",
            "primary_judge": primary_model,
            "secondary_judge": secondary_model,
        },
    )
    yield sse_event(
        "judge_activity",
        {
            "step": "gold_set_queued",
            "message": f"Queued {total_cases} gold-set cases for pairwise judging.",
            "total_cases": total_cases,
        },
    )

    event_queue: Queue[str | None] = Queue()

    def emit_progress(completed: int, total: int, case_id: str) -> None:
        event_queue.put(
            sse_event(
                "judge_activity",
                {
                    "step": "case_scored",
                    "message": (
                        f"Primary and secondary judges finished scoring {case_id}; "
                        "agreement deltas will be computed after all cases finish."
                    ),
                    "case_id": case_id,
                    "completed": completed,
                    "total": total,
                },
            )
        )
        event_queue.put(
            sse_event(
                "progress",
                {"completed": completed, "total": total, "current_case": case_id},
            )
        )

    def worker() -> None:
        try:
            result = run_inter_rater_report(
                gold_path=WEEK4_GOLD_SET_JSON,
                cases_path=WEEK4_SBA_LOANS_CSV,
                progress_callback=emit_progress,
            )
            event_queue.put(
                sse_event(
                    "judge_activity",
                    {
                        "step": "agreement_computed",
                        "message": (
                            "Computed exact agreement, within-one-point agreement, "
                            "score deltas, and manual spot-check cases."
                        ),
                        "exact_agreement": result["exact_agreement"],
                        "within_one_point_agreement": result["within_one_point_agreement"],
                        "disagreement_case_count": result["disagreement_case_count"],
                    },
                )
            )
            event_queue.put(
                sse_event(
                    "run_completed",
                    {
                        "run_type": "judge_agreement",
                        "cases": result["cases"],
                        "exact_agreement": result["exact_agreement"],
                        "within_one_point_agreement": result["within_one_point_agreement"],
                        "disagreement_case_count": result["disagreement_case_count"],
                        "manual_spot_check_cases": result["manual_spot_check_cases"],
                    },
                )
            )
        except Exception as exc:
            event_queue.put(sse_event("error", error_payload(exc, run_type="judge_agreement")))
        finally:
            event_queue.put(None)

    Thread(target=worker, daemon=True).start()
    while True:
        item = event_queue.get()
        if item is None:
            break
        yield item


def stream_live_drift_events(
    case_id: str,
    review_policy: ReviewPolicy = "sba_reviewer",
    repeats: int = 3,
) -> Iterable[str]:
    settings = get_settings()
    if not settings.use_llm_agents:
        yield sse_event(
            "error",
            {
                "run_type": "live_drift",
                "message": "Live drift requires USE_LLM_AGENTS=true so repeated runs call the configured LLM.",
            },
        )
        return
    if not settings.llm_api_key:
        yield sse_event(
            "error",
            {
                "run_type": "live_drift",
                "message": "Live drift requires LLM_API_KEY, NEBIUS_API_KEY, or OPENAI_API_KEY.",
            },
        )
        return

    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases(WEEK4_SBA_LOANS_CSV)}
    loan_case = cases.get(case_id)
    if loan_case is None:
        yield sse_event("error", {"run_type": "live_drift", "message": f"Unknown case_id: {case_id}"})
        return

    bounded_repeats = max(2, min(repeats, 5))
    yield sse_event(
        "run_started",
        {
            "run_type": "live_drift",
            "case_id": loan_case.case_id,
            "borrower_name": loan_case.borrower_name,
            "review_policy": review_policy,
            "repeats": bounded_repeats,
            "model": settings.openai_model,
            "provider": settings.llm_provider,
            "temperature": settings.llm_temperature,
        },
    )

    fingerprints: list[str] = []
    rows: list[dict[str, Any]] = []
    for run_number in range(1, bounded_repeats + 1):
        yield sse_event(
            "drift_activity",
            {
                "step": "live_run_started",
                "message": f"Starting live LLM drift run {run_number} of {bounded_repeats}.",
                "case_id": loan_case.case_id,
                "run_number": run_number,
                "model": settings.openai_model,
            },
        )
        try:
            packet = run_pipeline(loan_case, review_policy=review_policy)
        except Exception as exc:
            yield sse_event(
                "error",
                error_payload(
                    exc,
                    run_type="live_drift",
                    case_id=loan_case.case_id,
                    run_number=run_number,
                ),
            )
            return

        fingerprint = fingerprint_review_packet(packet)
        fingerprints.append(fingerprint)
        row = {
            "run": run_number,
            "case_id": packet.case_id,
            "fingerprint": fingerprint,
            "outcome": packet.recommended_outcome,
            "risk": packet.risk.band,
            "risk_score": packet.risk.score,
            "compliance": packet.compliance.status,
            "term_confidence": packet.extracted_terms.confidence,
            "risk_confidence": packet.risk.confidence,
            "compliance_confidence": packet.compliance.confidence,
            "counterfactuals": len(packet.counterfactuals),
            "contradictions": len(packet.contradictions),
        }
        rows.append(row)
        yield sse_event("drift_run_completed", row)
        yield sse_event(
            "progress",
            {"completed": run_number, "total": bounded_repeats, "current_case": loan_case.case_id},
        )

    variant_count = len(set(fingerprints))
    yield sse_event(
        "run_completed",
        {
            "run_type": "live_drift",
            "cases": 1,
            "case_id": loan_case.case_id,
            "repeats": bounded_repeats,
            "stable_cases": 1 if variant_count == 1 else 0,
            "drifting_cases": 0 if variant_count == 1 else 1,
            "stability_rate": 1.0 if variant_count == 1 else 0.0,
            "variant_count": variant_count,
            "fingerprints": fingerprints,
            "rows": rows,
        },
    )


def json_ready_events(events: Iterable[str]) -> list[dict[str, Any]]:
    parsed_events = []
    for event in events:
        lines = [line for line in event.strip().splitlines() if line]
        event_name = lines[0].replace("event: ", "", 1)
        data = json.loads(lines[1].replace("data: ", "", 1))
        parsed_events.append({"event": event_name, "data": data})
    return parsed_events
