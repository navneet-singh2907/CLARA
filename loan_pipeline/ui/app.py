"""Streamlit dashboard for the loan review pipeline."""

import os
import sys
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import cast

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

from loan_pipeline.config import get_settings, load_sba_demo_cases, reset_settings_cache
from loan_pipeline.eval.ablation import run_ablation_study, summarize_ablation_table
from loan_pipeline.eval.drift import run_drift_study
from loan_pipeline.eval.inter_rater import run_inter_rater_report
from loan_pipeline.eval.report import (
    REPORT_PATH,
    generate_evaluation_report,
    write_evaluation_report,
)
from loan_pipeline.eval.run_eval import run_eval
from loan_pipeline.graph.orchestrator import build_review_graph, run_pipeline_with_state
from loan_pipeline.graph.state import GraphState, LoanCase, ReviewPolicy, initial_state
from loan_pipeline.review.audit import OverrideTarget, create_human_override
from loan_pipeline.review.pdf_export import build_review_packet_pdf, write_review_packet_pdf
from loan_pipeline.review.policies import POLICY_PROFILES

st.set_page_config(
    page_title="Small Business Loan Review",
    layout="wide",
)

PIPELINE_NODE_LABELS = {
    "term_extractor": "Term Extractor",
    "schema_validator": "Schema Validator",
    "compliance_checker": "Compliance Checker",
    "credit_risk_scorer": "Credit Risk Scorer",
    "review_synthesizer": "Review Synthesizer",
}

EXPECTED_PIPELINE_NODES = set(PIPELINE_NODE_LABELS)


@st.cache_data(show_spinner=False)
def cached_cases() -> list[LoanCase]:
    return load_sba_demo_cases()


@st.cache_data(show_spinner=False)
def cached_eval() -> dict:
    return run_eval()


def run_eval_with_progress() -> dict:
    progress_bar = st.progress(0)
    status = st.empty()

    def update(completed: int, total: int, case_id: str) -> None:
        ratio = completed / total if total else 1
        progress_bar.progress(min(1.0, ratio))
        if completed >= total:
            status.write("Completed live evaluation for all 30 cases.")
        else:
            status.write(f"Running live evaluation: {completed}/{total} complete. Current: {case_id}")

    return run_eval(progress_callback=update)


@st.cache_data(show_spinner=False)
def cached_offline_eval() -> dict:
    with deterministic_batch_context():
        return run_eval()


@st.cache_data(show_spinner=False)
def cached_ablation_table() -> list[dict]:
    return summarize_ablation_table(run_ablation_study())


@st.cache_data(show_spinner=False)
def cached_offline_ablation_table() -> list[dict]:
    with deterministic_batch_context():
        return summarize_ablation_table(run_ablation_study())


@st.cache_data(show_spinner=False)
def cached_inter_rater() -> dict:
    return run_inter_rater_report()


def run_inter_rater_with_progress() -> dict:
    progress_bar = st.progress(0)
    status = st.empty()

    def update(completed: int, total: int, case_id: str) -> None:
        ratio = completed / total if total else 1
        progress_bar.progress(min(1.0, ratio))
        status.write(f"Live judge agreement: {completed}/{total} cases complete. Latest: {case_id}")

    return run_inter_rater_report(progress_callback=update)


def run_pipeline_with_ui_events(
    loan_case: LoanCase,
    review_policy: ReviewPolicy,
) -> GraphState:
    graph = build_review_graph()
    state = initial_state(loan_case, review_policy=review_policy)
    completed_nodes: set[str] = set()
    event_rows: list[dict[str, str | float | None]] = []

    st.subheader("Live LangGraph Agent Timeline")
    st.caption(
        "This panel streams the same run triggered by the button below, so the demo shows "
        "which agent completed, which stage it belongs to, and where parallel review happens."
    )
    status_box = st.status("Starting LangGraph loan review", expanded=True)
    progress_bar = st.progress(0)
    event_table = st.empty()

    status_box.write(f"Run started for {loan_case.case_id} - {loan_case.borrower_name}")
    status_box.write(f"Reviewer policy: {review_policy}")
    status_box.write("Orchestrator queued: term extraction -> validation -> parallel specialist review -> synthesis.")

    try:
        for chunk in graph.stream(initial_state(loan_case, review_policy=review_policy)):
            for node, update in chunk.items():
                _merge_graph_update(state, update)
                trace_entries = update.get("execution_trace", [])

                if not trace_entries:
                    status_box.write(f"Graph update received from {PIPELINE_NODE_LABELS.get(node, node)}")

                for trace_entry in trace_entries:
                    completed_nodes.add(trace_entry.node)
                    label = PIPELINE_NODE_LABELS.get(trace_entry.node, trace_entry.node)
                    if trace_entry.parallel_group == "specialist_review":
                        label = f"{label} (parallel specialist stage)"

                    status_box.write(
                        f"{label} completed in {trace_entry.duration_ms:.1f} ms "
                        f"with status {trace_entry.status}."
                    )
                    event_rows.append(
                        {
                            "agent": PIPELINE_NODE_LABELS.get(trace_entry.node, trace_entry.node),
                            "node": trace_entry.node,
                            "stage": trace_entry.stage,
                            "parallel_group": trace_entry.parallel_group,
                            "duration_ms": trace_entry.duration_ms,
                            "status": trace_entry.status,
                        }
                    )

                progress = len(completed_nodes & EXPECTED_PIPELINE_NODES) / len(EXPECTED_PIPELINE_NODES)
                progress_bar.progress(min(1.0, progress))
                if event_rows:
                    event_table.dataframe(pd.DataFrame(event_rows), use_container_width=True, hide_index=True)

        if state["review_packet"] is None:
            status_box.update(label="LangGraph run finished without a review packet", state="error")
            return state

        packet = state["review_packet"]
        progress_bar.progress(1.0)
        status_box.write(
            f"Final packet created: outcome={packet.recommended_outcome}, "
            f"risk={packet.risk.band}, compliance={packet.compliance.status}."
        )
        if packet.escalation_required:
            status_box.write("Human gate: escalation required because one or more findings need review.")
        else:
            status_box.write("Human gate: no escalation required for this packet.")
        status_box.update(label="LangGraph run completed", state="complete")
        return state
    except Exception:
        status_box.update(label="LangGraph run failed", state="error")
        raise


def _merge_graph_update(state: GraphState, update: dict) -> None:
    for key, value in update.items():
        if key in {
            "validation_errors",
            "agent_errors",
            "execution_trace",
            "contradictions",
            "counterfactuals",
        }:
            state[key].extend(value)
        else:
            state[key] = value


def write_live_report_with_progress() -> Path:
    stage_progress = st.progress(0)
    stage_status = st.empty()
    case_progress = st.progress(0)
    case_status = st.empty()
    stage_weights = {
        "evaluation": 0.05,
        "ablation": 0.45,
        "drift": 0.60,
        "judge_agreement": 0.75,
        "render_report": 0.95,
    }
    stage_labels = {
        "evaluation": "Running 30-case live evaluation",
        "ablation": "Running ablation study",
        "drift": "Running drift analysis",
        "judge_agreement": "Running 30-case primary/secondary judge agreement",
        "render_report": "Rendering Markdown report",
    }

    def update_stage(stage: str) -> None:
        stage_progress.progress(stage_weights.get(stage, 0.0))
        stage_status.write(stage_labels.get(stage, stage))

    def update_eval(completed: int, total: int, case_id: str) -> None:
        ratio = completed / total if total else 1
        case_progress.progress(min(1.0, ratio))
        case_status.write(f"Evaluation: {completed}/{total} cases complete. Current: {case_id}")

    def update_judge(completed: int, total: int, case_id: str) -> None:
        ratio = completed / total if total else 1
        case_progress.progress(min(1.0, ratio))
        case_status.write(f"Judge agreement: {completed}/{total} cases complete. Latest: {case_id}")

    path = write_evaluation_report(
        eval_progress_callback=update_eval,
        inter_rater_progress_callback=update_judge,
        stage_callback=update_stage,
    )
    stage_progress.progress(1.0)
    stage_status.write("Full live report generated.")
    return path


@st.cache_data(show_spinner=False)
def cached_offline_inter_rater() -> dict:
    with deterministic_batch_context():
        return run_inter_rater_report()


@st.cache_data(show_spinner=False)
def cached_drift_study() -> dict:
    return run_drift_study()


@st.cache_data(show_spinner=False)
def cached_offline_drift_study() -> dict:
    with deterministic_batch_context():
        return run_drift_study()


@st.cache_data(show_spinner=False)
def cached_offline_report() -> str:
    with deterministic_batch_context():
        return generate_evaluation_report()


def live_model_mode_enabled() -> bool:
    settings = get_settings()
    return bool(
        settings.use_llm_agents
        or settings.primary_judge_model
        or settings.secondary_judge_model
    )


@contextmanager
def deterministic_batch_context():
    env_names = [
        "USE_LLM_AGENTS",
        "PRIMARY_JUDGE_MODEL",
        "SECONDARY_JUDGE_MODEL",
        "LANGSMITH_TRACING",
        "LANGCHAIN_TRACING_V2",
    ]
    previous_values = {name: os.environ.get(name) for name in env_names}
    os.environ["USE_LLM_AGENTS"] = "false"
    os.environ["PRIMARY_JUDGE_MODEL"] = ""
    os.environ["SECONDARY_JUDGE_MODEL"] = ""
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    reset_settings_cache()
    try:
        yield
    finally:
        for name, value in previous_values.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        reset_settings_cache()


def render_live_batch_option(action_label: str, key: str, detail: str) -> bool:
    if not live_model_mode_enabled():
        return False

    st.info(
        "Live model mode is active. Showing the reproducible offline benchmark by default. "
        f"{detail}"
    )
    return st.button(action_label, key=key, type="primary")


def main() -> None:
    settings = get_settings()

    st.title("Small Business Loan Application Review Pipeline")
    st.caption("LangChain + LangGraph + Streamlit | SBA-style data | 30-case gold set")

    mode_label = "LLM mode" if settings.use_llm_agents else "Deterministic mode"
    st.sidebar.metric("Agent mode", mode_label)
    st.sidebar.metric("LLM provider", settings.llm_provider if settings.use_llm_agents else "Off")
    st.sidebar.metric("LLM model", settings.openai_model if settings.use_llm_agents else "Off")
    st.sidebar.metric("LLM temperature", f"{settings.llm_temperature:.2f}" if settings.use_llm_agents else "Off")
    st.sidebar.metric("Primary judge", settings.primary_judge_model or "Local")
    st.sidebar.metric("Secondary judge", settings.secondary_judge_model or "Local strict")
    st.sidebar.metric("LangSmith tracing", "On" if settings.langsmith_tracing else "Off")
    st.sidebar.caption(f"Trace project: {settings.langsmith_project}")
    st.sidebar.metric("Gold set", "30 cases")
    st.sidebar.metric("Difficulty tiers", "3")

    tab_review, tab_eval, tab_ablation, tab_drift, tab_judges, tab_report = st.tabs(
        [
            "Loan Review",
            "Evaluation",
            "Ablation",
            "Drift",
            "Judge Agreement",
            "Report",
        ]
    )

    with tab_review:
        render_loan_review()

    with tab_eval:
        render_evaluation_dashboard()

    with tab_ablation:
        render_ablation_dashboard()

    with tab_drift:
        render_drift_dashboard()

    with tab_judges:
        render_judge_dashboard()

    with tab_report:
        render_report_dashboard()


def _render_document_input_mode() -> None:
    settings = get_settings()
    if not settings.use_llm_agents:
        st.warning(
            "Document parsing requires LLM mode. "
            "Set USE_LLM_AGENTS=true and provide an API key in your .env file."
        )
        return

    uploaded = st.file_uploader("Upload PDF (optional)", type=["pdf"])
    if uploaded is not None:
        import io

        try:
            import pdfplumber
        except ImportError:
            st.error("PDF upload requires pdfplumber. Run `pip install -r requirements.txt`.")
            return

        with pdfplumber.open(io.BytesIO(uploaded.read())) as pdf:
            extracted = "\n".join(page.extract_text() or "" for page in pdf.pages)
        st.session_state["_doc_text"] = extracted

    doc_text = st.text_area(
        "Loan application narrative",
        value=st.session_state.get("_doc_text", ""),
        height=280,
        placeholder=(
            "Paste a raw loan application here - borrower name, industry, loan amount, "
            "term, credit score, years in business, prior defaults, missing documents. "
            "The LLM will extract all structured fields."
        ),
        key="_doc_text_area",
    )

    policy_options = {profile.label: policy for policy, profile in POLICY_PROFILES.items()}
    selected_policy_label = st.selectbox(
        "Reviewer policy", options=list(policy_options.keys()), key="_doc_policy"
    )
    review_policy = policy_options[selected_policy_label]

    if st.button("Parse and review", type="primary", disabled=not doc_text.strip()):
        from loan_pipeline.llm.client import parse_document_to_loan_case
        with st.spinner("Parsing document with LLM..."):
            try:
                loan_case = parse_document_to_loan_case(doc_text)
                st.session_state["_doc_loan_case"] = loan_case
                st.session_state["_doc_review_state"] = run_pipeline_with_state(
                    loan_case, review_policy=review_policy
                )
            except Exception as exc:
                render_pipeline_error(exc)
                return

    doc_loan_case = st.session_state.get("_doc_loan_case")
    if doc_loan_case:
        st.subheader("Parsed Loan Case")
        render_case_summary(doc_loan_case)

    state = st.session_state.get("_doc_review_state")
    if state is None:
        return

    packet = state["review_packet"]
    if packet is None:
        st.error("Pipeline completed without producing a review packet.")
        return

    _render_packet_output(state, packet)


def render_loan_review() -> None:
    input_mode = st.radio(
        "Input mode",
        ["Gold set case", "Paste / Upload document"],
        horizontal=True,
    )

    if input_mode == "Paste / Upload document":
        _render_document_input_mode()
        return

    # --- Gold set case mode ---
    cases = cached_cases()
    case_options = {f"{case.case_id} - {case.borrower_name}": case.case_id for case in cases}
    selected_label = st.selectbox("SBA loan case", options=list(case_options.keys()))
    loan_case = next(case for case in cases if case.case_id == case_options[selected_label])
    policy_options = {profile.label: policy for policy, profile in POLICY_PROFILES.items()}
    selected_policy_label = st.selectbox("Reviewer policy", options=list(policy_options.keys()))
    review_policy = policy_options[selected_policy_label]

    render_case_summary(loan_case)
    render_policy_note(review_policy)
    render_policy_comparison(loan_case)

    review_state_key = f"review_state_{loan_case.case_id}_{review_policy}"
    if st.button("Run review pipeline", type="primary"):
        try:
            st.session_state[review_state_key] = run_pipeline_with_ui_events(
                loan_case,
                review_policy=review_policy,
            )
        except Exception as exc:
            render_pipeline_error(exc)
            return

    state = st.session_state.get(review_state_key)
    if state is None:
        return
    packet = state["review_packet"]
    if packet is None:
        st.error("Pipeline completed without producing a review packet.")
        return
    _render_packet_output(state, packet)


def _render_packet_output(state: dict, packet) -> None:
    st.subheader("Human Review Packet")
    metric_cols = st.columns(4)
    metric_cols[0].metric("Outcome", packet.recommended_outcome)
    metric_cols[1].metric("Risk", packet.risk.band)
    metric_cols[2].metric("Compliance", packet.compliance.status)
    metric_cols[3].metric("Escalation", "Yes" if packet.escalation_required else "No")
    st.caption(f"Reviewer policy: {POLICY_PROFILES[packet.review_policy].label}")

    st.write(packet.summary)
    if get_settings().use_llm_agents:
        st.success(
            "Live LLM agent mode is active. Term extraction, compliance reviewer notes, "
            "and risk rationale use model calls."
        )

    if packet.human_review_notes:
        st.warning("Human review notes")
        for note in packet.human_review_notes:
            st.write(f"- {note}")

    if packet.compliance.reviewer_note:
        st.subheader("LLM Compliance Reviewer Note")
        st.write(packet.compliance.reviewer_note)

    if packet.contradictions:
        st.subheader("Agent Contradictions")
        for contradiction in packet.contradictions:
            st.error(contradiction.title)
            cols = st.columns(2)
            cols[0].write("Compliance position")
            cols[0].write(contradiction.compliance_position)
            cols[1].write("Credit risk position")
            cols[1].write(contradiction.risk_position)
            st.write(contradiction.reviewer_prompt)

    if packet.counterfactuals:
        st.subheader("Counterfactual Explanations")
        for counterfactual in packet.counterfactuals:
            with st.expander(counterfactual.title, expanded=True):
                st.write("Current state")
                st.write(counterfactual.current_state)
                st.write("Suggested change")
                st.write(counterfactual.suggested_change)
                st.write("Expected effect")
                st.write(counterfactual.expected_effect)

    render_execution_trace(state["execution_trace"])
    render_human_override_panel(packet)
    render_pdf_export(packet)

    tab_terms, tab_compliance, tab_risk, tab_state = st.tabs(
        ["Term Extractor", "Compliance Checker", "Credit Risk Scorer", "Graph State"]
    )
    with tab_terms:
        st.json(asdict(packet.extracted_terms))
    with tab_compliance:
        st.json(asdict(packet.compliance))
    with tab_risk:
        st.json(asdict(packet.risk))
    with tab_state:
        st.json(
            {
                "validation_errors": state["validation_errors"],
                "review_policy": state["review_policy"],
                "agent_errors": state["agent_errors"],
                "contradictions": [asdict(item) for item in state["contradictions"]],
                "counterfactuals": [asdict(item) for item in state["counterfactuals"]],
                "audit_log": st.session_state.get(f"audit_log_{packet.case_id}", []),
                "execution_trace": [asdict(item) for item in state["execution_trace"]],
            }
        )


def render_execution_trace(trace_entries) -> None:
    st.subheader("LangGraph Execution Trace")
    trace_table = pd.DataFrame([asdict(entry) for entry in trace_entries])
    if trace_table.empty:
        st.caption("No execution trace available.")
        return

    st.dataframe(trace_table, use_container_width=True, hide_index=True)
    parallel_nodes = trace_table[trace_table["parallel_group"] == "specialist_review"]
    if len(parallel_nodes) >= 2:
        st.success("Compliance Checker and Credit Risk Scorer ran in the parallel specialist review stage.")


def render_policy_note(review_policy: ReviewPolicy) -> None:
    profile = POLICY_PROFILES[review_policy]
    st.info(f"{profile.label}: {profile.note}")


def render_policy_comparison(loan_case: LoanCase) -> None:
    with st.expander("Compare reviewer policies"):
        settings = get_settings()
        if settings.use_llm_agents:
            st.warning(
                "Live LLM mode is active. Running policy comparison will execute the pipeline "
                "for all reviewer policies and may use multiple model calls."
            )

        if not st.button("Run policy comparison"):
            st.caption("Click to compare this loan under SBA, bank, and CDFI review postures.")
            return

        rows = []
        for policy, profile in POLICY_PROFILES.items():
            try:
                packet = run_pipeline_with_state(loan_case, review_policy=policy)["review_packet"]
            except Exception as exc:
                render_pipeline_error(exc)
                return
            if packet is None:
                continue
            rows.append(
                {
                    "Policy": profile.label,
                    "Outcome": packet.recommended_outcome,
                    "Compliance": packet.compliance.status,
                    "Risk": packet.risk.band,
                    "Escalation": "Yes" if packet.escalation_required else "No",
                    "Summary": packet.summary,
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_pipeline_error(exc: Exception) -> None:
    message = str(exc)
    if "does not exist" in message and "model" in message.lower():
        st.error(
            "Live model error: the configured model ID is not available from this provider. "
            "Check OPENAI_MODEL, PRIMARY_JUDGE_MODEL, and SECONDARY_JUDGE_MODEL against "
            "your provider's /v1/models list."
        )
        st.caption(message)
        return

    if "insufficient_quota" in message or "exceeded your current quota" in message:
        st.error(
            "Live model quota error: your API key is valid enough to reach the provider, but "
            "the account does not currently have quota/billing available. Add billing/quota, "
            "switch provider keys, or switch back to deterministic mode for offline demo."
        )
        return

    if "API_KEY" in message:
        st.error("Live LLM mode requires LLM_API_KEY, NEBIUS_API_KEY, or OPENAI_API_KEY in your .env file.")
        return

    st.error(f"Pipeline run failed: {exc}")


def render_human_override_panel(packet) -> None:
    st.subheader("Human Override Audit Log")
    targets = override_targets(packet)
    audit_key = f"audit_log_{packet.case_id}"
    st.session_state.setdefault(audit_key, [asdict(entry) for entry in packet.audit_log])

    with st.form(f"override_form_{packet.case_id}"):
        selected_label = st.selectbox("Finding", options=list(targets.keys()))
        override_decision = st.selectbox(
            "Decision",
            options=[
                "Accept agent finding",
                "Override finding",
                "Request additional evidence",
                "Approve despite finding",
                "Reject despite finding",
            ],
        )
        reviewer = st.text_input("Reviewer", value="Human reviewer")
        rationale = st.text_area("Rationale")
        submitted = st.form_submit_button("Add audit entry")

    if submitted:
        if not rationale.strip():
            st.error("Rationale is required for the audit log.")
        else:
            target = targets[selected_label]
            entry = create_human_override(
                case_id=packet.case_id,
                target_type=cast(OverrideTarget, target["target_type"]),
                target_id=target["target_id"],
                original_value=target["original_value"],
                override_decision=override_decision,
                rationale=rationale,
                reviewer=reviewer,
            )
            st.session_state[audit_key].append(asdict(entry))
            st.success("Audit entry added.")

    audit_log = st.session_state[audit_key]
    if audit_log:
        st.dataframe(pd.DataFrame(audit_log), use_container_width=True, hide_index=True)
    else:
        st.caption("No human override decisions logged yet.")


def render_pdf_export(packet) -> None:
    st.subheader("Review Packet Export")
    audit_log = st.session_state.get(f"audit_log_{packet.case_id}", [])
    pdf_bytes = build_review_packet_pdf(packet, audit_log=audit_log)
    file_name = f"loan_review_packet_{packet.case_id}.pdf"

    cols = st.columns([1, 1])
    cols[0].download_button(
        "Download PDF packet",
        data=pdf_bytes,
        file_name=file_name,
        mime="application/pdf",
    )

    if cols[1].button("Save PDF artifact"):
        output_path = Path("output") / "pdf" / file_name
        write_review_packet_pdf(packet, output_path, audit_log=audit_log)
        st.success(f"Saved {output_path}")


def override_targets(packet) -> dict[str, dict[str, str]]:
    targets = {
        f"Outcome - {packet.recommended_outcome}": {
            "target_type": "OUTCOME",
            "target_id": "recommended_outcome",
            "original_value": packet.recommended_outcome,
        },
        f"Risk band - {packet.risk.band}": {
            "target_type": "RISK",
            "target_id": "risk_band",
            "original_value": f"{packet.risk.band}: {packet.risk.rationale}",
        },
    }

    for finding in packet.compliance.findings:
        targets[f"Compliance {finding.rule_id} - {finding.severity}"] = {
            "target_type": "COMPLIANCE",
            "target_id": finding.rule_id,
            "original_value": f"{finding.severity}: {finding.description} Evidence: {finding.evidence}",
        }

    for index, contradiction in enumerate(packet.contradictions, start=1):
        targets[f"Contradiction {index} - {contradiction.severity}"] = {
            "target_type": "CONTRADICTION",
            "target_id": f"contradiction_{index}",
            "original_value": (
                f"{contradiction.title} Compliance: {contradiction.compliance_position} "
                f"Risk: {contradiction.risk_position}"
            ),
        }

    for index, counterfactual in enumerate(packet.counterfactuals, start=1):
        targets[f"Counterfactual {index} - {counterfactual.title}"] = {
            "target_type": "COUNTERFACTUAL",
            "target_id": f"counterfactual_{index}",
            "original_value": (
                f"{counterfactual.current_state} Suggested change: "
                f"{counterfactual.suggested_change}"
            ),
        }

    return targets


def render_case_summary(loan_case: LoanCase) -> None:
    st.subheader("Loan Case")
    metric_cols = st.columns(5)
    metric_cols[0].metric("Tier", loan_case.difficulty_tier)
    metric_cols[1].metric("Loan", money(loan_case.loan_amount))
    metric_cols[2].metric("SBA Guarantee", money(loan_case.sba_guaranteed_amount))
    metric_cols[3].metric("Term", f"{loan_case.term_months} mo")
    metric_cols[4].metric("Jobs", loan_case.jobs_supported)

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Borrower": loan_case.borrower_name,
                    "Industry": loan_case.industry,
                    "NAICS": loan_case.naics_code,
                    "Credit Score": loan_case.borrower_credit_score or "Missing",
                    "Years in Business": loan_case.years_in_business,
                    "Prior Default": loan_case.prior_default,
                    "Missing Documents": ", ".join(loan_case.missing_documents) or "None",
                }
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.write(loan_case.notes)


def render_evaluation_dashboard() -> None:
    run_live = render_live_batch_option(
        "Run live evaluation",
        "run_live_evaluation",
        "Click the button only when you want a full live judged evaluation trace.",
    )

    try:
        if run_live:
            result = run_eval_with_progress()
        elif not live_model_mode_enabled():
            result = cached_eval()
        else:
            result = cached_offline_eval()
    except Exception as exc:
        render_pipeline_error(exc)
        return
    if live_model_mode_enabled() and not run_live:
        st.caption("Displaying offline benchmark results. Live evaluation is available with the button above.")
    overall = result["summary"]["overall"]

    metric_cols = st.columns(5)
    metric_cols[0].metric("Cases", overall["cases"])
    metric_cols[1].metric("Extraction", pct(overall["term_extraction_accuracy"]))
    metric_cols[2].metric("Compliance", pct(overall["compliance_status_accuracy"]))
    metric_cols[3].metric("Risk", pct(overall["risk_band_accuracy"]))
    metric_cols[4].metric("Outcome", pct(overall["final_outcome_accuracy"]))

    st.subheader("Difficulty Tiers")
    st.dataframe(
        pd.DataFrame(
            [
                {"tier": "overall", **result["summary"]["overall"]},
                *[
                    {"tier": tier, **result["summary"]["by_tier"][tier]}
                    for tier in ["clean", "ambiguous", "adversarial"]
                ],
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Failure Analysis")
    failure_counts = result["failure_counts"] or {"None": 0}
    st.dataframe(
        pd.DataFrame(
            [{"failure_category": category, "count": count} for category, count in failure_counts.items()]
        ),
        use_container_width=True,
        hide_index=True,
    )

    if result["failures"]:
        st.dataframe(pd.DataFrame(result["failures"]), use_container_width=True, hide_index=True)

    render_confidence_calibration(result["risk_confidence_calibration"])


def render_confidence_calibration(calibration: dict) -> None:
    st.subheader("Risk Confidence Calibration")
    st.metric("Expected calibration error", pct(calibration["expected_calibration_error"]))

    buckets = calibration["buckets"]
    if not buckets:
        st.caption("No calibration buckets available.")
        return

    bucket_table = pd.DataFrame(buckets)
    st.dataframe(bucket_table, use_container_width=True, hide_index=True)
    st.line_chart(
        bucket_table,
        x="confidence_bucket",
        y=["average_confidence", "observed_accuracy"],
        use_container_width=True,
    )


def render_ablation_dashboard() -> None:
    run_live = render_live_batch_option(
        "Run live ablation study",
        "run_live_ablation",
        "Live ablation runs several model-backed pipeline configurations across the gold set.",
    )

    try:
        rows = (
            cached_ablation_table()
            if run_live or not live_model_mode_enabled()
            else cached_offline_ablation_table()
        )
    except Exception as exc:
        render_pipeline_error(exc)
        return
    if live_model_mode_enabled() and not run_live:
        st.caption("Displaying offline ablation results. Live ablation is available with the button above.")
    table = pd.DataFrame(rows)
    st.dataframe(table, use_container_width=True, hide_index=True)

    full = next(row for row in rows if row["configuration"] == "full_pipeline")
    baseline = next(row for row in rows if row["configuration"] == "single_agent_baseline_stub")
    no_compliance = next(row for row in rows if row["configuration"] == "no_compliance_checker")
    no_risk = next(row for row in rows if row["configuration"] == "no_risk_scorer")
    term_only = next(row for row in rows if row["configuration"] == "term_extractor_only")

    delta = full["final_outcome_accuracy"] - baseline["final_outcome_accuracy"]
    metric_cols = st.columns(4)
    metric_cols[0].metric("Full vs single-agent outcome lift", pct(delta))
    metric_cols[1].metric(
        "Compliance agent lift",
        pct(full["compliance_status_accuracy"] - no_compliance["compliance_status_accuracy"]),
    )
    metric_cols[2].metric(
        "Risk scorer lift",
        pct(full["risk_band_accuracy"] - no_risk["risk_band_accuracy"]),
    )
    metric_cols[3].metric(
        "Pipeline vs extractor-only lift",
        pct(full["final_outcome_accuracy"] - term_only["final_outcome_accuracy"]),
    )

    st.subheader("Ablation Accuracy Comparison")
    chart_data = ablation_chart_data(rows)
    st.bar_chart(
        chart_data,
        x="Configuration",
        y=["Extraction", "Compliance", "Risk", "Escalation", "Final Outcome"],
        use_container_width=True,
    )

    st.subheader("Agent Contribution Readout")
    contribution_rows = [
        {
            "Question": "What breaks when compliance is removed?",
            "Answer": f"Compliance accuracy drops by {pct(full['compliance_status_accuracy'] - no_compliance['compliance_status_accuracy'])}.",
        },
        {
            "Question": "What breaks when risk scoring is removed?",
            "Answer": f"Risk band accuracy drops by {pct(full['risk_band_accuracy'] - no_risk['risk_band_accuracy'])}.",
        },
        {
            "Question": "Does orchestration beat extraction alone?",
            "Answer": f"Final outcome accuracy improves by {pct(full['final_outcome_accuracy'] - term_only['final_outcome_accuracy'])}.",
        },
    ]
    st.dataframe(pd.DataFrame(contribution_rows), use_container_width=True, hide_index=True)


def ablation_chart_data(rows: list[dict]) -> pd.DataFrame:
    labels = {
        "full_pipeline": "Full Pipeline",
        "no_compliance_checker": "No Compliance",
        "no_risk_scorer": "No Risk",
        "term_extractor_only": "Extractor Only",
        "single_agent_baseline_stub": "Single Agent",
    }
    chart_rows = []
    for row in rows:
        chart_rows.append(
            {
                "Configuration": labels.get(row["configuration"], row["configuration"]),
                "Extraction": row["term_extraction_accuracy"],
                "Compliance": row["compliance_status_accuracy"],
                "Risk": row["risk_band_accuracy"],
                "Escalation": row["escalation_accuracy"],
                "Final Outcome": row["final_outcome_accuracy"],
            }
        )
    return pd.DataFrame(chart_rows)


def render_drift_dashboard() -> None:
    run_live = render_live_batch_option(
        "Run live drift study",
        "run_live_drift",
        "Live drift repeats each case multiple times to measure model-output variance.",
    )

    try:
        result = (
            cached_drift_study()
            if run_live or not live_model_mode_enabled()
            else cached_offline_drift_study()
        )
    except Exception as exc:
        render_pipeline_error(exc)
        return
    if live_model_mode_enabled() and not run_live:
        st.caption("Displaying offline drift results. Live drift is available with the button above.")

    metric_cols = st.columns(4)
    metric_cols[0].metric("Cases", result["cases"])
    metric_cols[1].metric("Runs per case", result["repeats"])
    metric_cols[2].metric("Stable cases", result["stable_cases"])
    metric_cols[3].metric("Stability rate", pct(result["stability_rate"]))

    rows = pd.DataFrame(result["rows"])
    st.subheader("Repeated-Run Drift Results")
    st.dataframe(rows, use_container_width=True, hide_index=True)

    tier_summary = (
        rows.groupby("tier", as_index=False)
        .agg(cases=("case_id", "count"), stable_cases=("stable", "sum"), max_variants=("variant_count", "max"))
    )
    tier_summary["stability_rate"] = tier_summary["stable_cases"] / tier_summary["cases"]

    st.subheader("Drift by Difficulty Tier")
    st.dataframe(tier_summary, use_container_width=True, hide_index=True)
    st.bar_chart(tier_summary, x="tier", y="stability_rate", use_container_width=True)


def render_judge_dashboard() -> None:
    run_live = render_live_batch_option(
        "Run live judge agreement",
        "run_live_judge_agreement",
        "The live button runs primary and secondary judges across all 30 gold-set cases.",
    )

    try:
        if run_live:
            inter_rater = run_inter_rater_with_progress()
            judge_summary = inter_rater["primary_judge_summary"]
            judge_summary_label = "Live Primary Judge Summary"
            settings = get_settings()
            st.success(
                f"Live judge agreement completed for {inter_rater['cases']} cases using "
                f"{settings.primary_judge_model} and {settings.secondary_judge_model}."
            )
        elif not live_model_mode_enabled():
            eval_result = cached_eval()
            inter_rater = cached_inter_rater()
            judge_summary = eval_result["local_judge_summary"]
            judge_summary_label = "Local Judge Summary"
        else:
            eval_result = cached_offline_eval()
            inter_rater = cached_offline_inter_rater()
            judge_summary = eval_result["local_judge_summary"]
            judge_summary_label = "Offline Judge Summary"
    except Exception as exc:
        render_pipeline_error(exc)
        return
    if live_model_mode_enabled() and not run_live:
        st.caption("Displaying offline judge-agreement results. Live judge agreement is available with the button above.")

    st.subheader(judge_summary_label)
    st.dataframe(
        pd.DataFrame(
            [
                {"dimension": dimension, "average_score": score}
                for dimension, score in judge_summary.items()
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("Exact Agreement", pct(inter_rater["exact_agreement"]))
    metric_cols[1].metric("Within 1 Point", pct(inter_rater["within_one_point_agreement"]))
    metric_cols[2].metric("Avg Delta", f"{inter_rater['average_score_delta']:.4f}")
    metric_cols[3].metric("Disagreements", inter_rater["disagreement_case_count"])

    if run_live and inter_rater.get("case_rows"):
        st.subheader("Live Judge Audit Trail")
        st.dataframe(
            pd.DataFrame(inter_rater["case_rows"]),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Manual Spot-Check Queue")
    st.write(", ".join(inter_rater["manual_spot_check_cases"]) or "None")

    if inter_rater["disagreement_cases"]:
        st.dataframe(
            pd.DataFrame(inter_rater["disagreement_cases"]),
            use_container_width=True,
            hide_index=True,
        )


def render_report_dashboard() -> None:
    live_mode = live_model_mode_enabled()
    run_live = False
    if live_mode:
        st.info(
            "Live model mode is active. Showing the reproducible offline report by default. "
            "Click below to generate the full 30-case live evaluation report."
        )
        run_live = st.button("Generate full live evaluation report", type="primary")
    else:
        run_live = st.button("Generate evaluation report", type="primary")

    try:
        if run_live or not live_mode:
            path = write_live_report_with_progress() if run_live else write_evaluation_report()
            st.success(f"Generated {path}")
            report_text = path.read_text(encoding="utf-8")
        else:
            report_text = cached_offline_report()
    except Exception as exc:
        render_pipeline_error(exc)
        return

    st.download_button(
        "Download evaluation report",
        data=report_text,
        file_name="evaluation_report.md",
        mime="text/markdown",
    )

    if REPORT_PATH.exists():
        st.caption(str(REPORT_PATH))

    st.markdown(report_text)


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def money(value: float) -> str:
    return f"${value:,.0f}"


if __name__ == "__main__":
    main()
