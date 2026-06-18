"""Server-sent event generators for the loan review API."""

import json
from queue import Queue
from threading import Thread
from typing import Any, Iterable

from loan_pipeline.config import load_sba_demo_cases
from loan_pipeline.eval.inter_rater import run_inter_rater_report
from loan_pipeline.eval.run_eval import load_gold_labels, run_eval
from loan_pipeline.graph.orchestrator import build_review_graph
from loan_pipeline.graph.state import ReviewPolicy, initial_state


def sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


def stream_review_events(
    case_id: str,
    review_policy: ReviewPolicy = "sba_reviewer",
) -> Iterable[str]:
    cases = {loan_case.case_id: loan_case for loan_case in load_sba_demo_cases()}
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
        yield sse_event("error", {"case_id": loan_case.case_id, "message": str(exc)})
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
    labels = load_gold_labels()
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
            result = run_eval(progress_callback=emit_progress)
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
            event_queue.put(sse_event("error", {"run_type": "evaluation", "message": str(exc)}))
        finally:
            event_queue.put(None)

    Thread(target=worker, daemon=True).start()
    while True:
        item = event_queue.get()
        if item is None:
            break
        yield item


def stream_judge_agreement_events() -> Iterable[str]:
    total_cases = len(load_gold_labels())
    yield sse_event("run_started", {"run_type": "judge_agreement", "total_cases": total_cases})

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
            result = run_inter_rater_report(progress_callback=emit_progress)
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
            event_queue.put(
                sse_event("error", {"run_type": "judge_agreement", "message": str(exc)})
            )
        finally:
            event_queue.put(None)

    Thread(target=worker, daemon=True).start()
    while True:
        item = event_queue.get()
        if item is None:
            break
        yield item


def json_ready_events(events: Iterable[str]) -> list[dict[str, Any]]:
    parsed_events = []
    for event in events:
        lines = [line for line in event.strip().splitlines() if line]
        event_name = lines[0].replace("event: ", "", 1)
        data = json.loads(lines[1].replace("data: ", "", 1))
        parsed_events.append({"event": event_name, "data": data})
    return parsed_events
