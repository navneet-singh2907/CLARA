"""Streamlit dashboard for the loan review pipeline."""

from dataclasses import asdict

import pandas as pd
import streamlit as st

from loan_pipeline.config import get_settings, load_sba_demo_cases
from loan_pipeline.eval.ablation import run_ablation_study, summarize_ablation_table
from loan_pipeline.eval.inter_rater import run_inter_rater_report
from loan_pipeline.eval.report import REPORT_PATH, generate_evaluation_report, write_evaluation_report
from loan_pipeline.eval.run_eval import run_eval
from loan_pipeline.graph.orchestrator import run_pipeline_with_state
from loan_pipeline.graph.state import LoanCase


st.set_page_config(
    page_title="Small Business Loan Review",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def cached_cases() -> list[LoanCase]:
    return load_sba_demo_cases()


@st.cache_data(show_spinner=False)
def cached_eval() -> dict:
    return run_eval()


@st.cache_data(show_spinner=False)
def cached_ablation_table() -> list[dict]:
    return summarize_ablation_table(run_ablation_study())


@st.cache_data(show_spinner=False)
def cached_inter_rater() -> dict:
    return run_inter_rater_report()


def main() -> None:
    settings = get_settings()

    st.title("Small Business Loan Application Review Pipeline")
    st.caption("LangChain + LangGraph + Streamlit | SBA-style data | 30-case gold set")

    mode_label = "LLM mode" if settings.use_llm_agents else "Deterministic mode"
    st.sidebar.metric("Agent mode", mode_label)
    st.sidebar.metric("Gold set", "30 cases")
    st.sidebar.metric("Difficulty tiers", "3")

    tab_review, tab_eval, tab_ablation, tab_judges, tab_report = st.tabs(
        [
            "Loan Review",
            "Evaluation",
            "Ablation",
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

    with tab_judges:
        render_judge_dashboard()

    with tab_report:
        render_report_dashboard()


def render_loan_review() -> None:
    cases = cached_cases()
    case_options = {f"{case.case_id} - {case.borrower_name}": case.case_id for case in cases}
    selected_label = st.selectbox("SBA loan case", options=list(case_options.keys()))
    loan_case = next(case for case in cases if case.case_id == case_options[selected_label])

    render_case_summary(loan_case)

    if st.button("Run review pipeline", type="primary"):
        state = run_pipeline_with_state(loan_case)
        packet = state["review_packet"]

        if packet is None:
            st.error("Pipeline completed without producing a review packet.")
            return

        st.subheader("Human Review Packet")
        metric_cols = st.columns(4)
        metric_cols[0].metric("Outcome", packet.recommended_outcome)
        metric_cols[1].metric("Risk", packet.risk.band)
        metric_cols[2].metric("Compliance", packet.compliance.status)
        metric_cols[3].metric("Escalation", "Yes" if packet.escalation_required else "No")

        st.write(packet.summary)

        if packet.human_review_notes:
            st.warning("Human review notes")
            for note in packet.human_review_notes:
                st.write(f"- {note}")

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
                    "agent_errors": state["agent_errors"],
                }
            )


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
    result = cached_eval()
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


def render_ablation_dashboard() -> None:
    rows = cached_ablation_table()
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    full = next(row for row in rows if row["configuration"] == "full_pipeline")
    baseline = next(row for row in rows if row["configuration"] == "single_agent_baseline_stub")
    delta = full["final_outcome_accuracy"] - baseline["final_outcome_accuracy"]
    st.metric("Full pipeline vs single-agent outcome lift", pct(delta))


def render_judge_dashboard() -> None:
    eval_result = cached_eval()
    inter_rater = cached_inter_rater()

    st.subheader("Local Judge Summary")
    st.dataframe(
        pd.DataFrame(
            [
                {"dimension": dimension, "average_score": score}
                for dimension, score in eval_result["local_judge_summary"].items()
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

    st.subheader("Manual Spot-Check Queue")
    st.write(", ".join(inter_rater["manual_spot_check_cases"]) or "None")

    if inter_rater["disagreement_cases"]:
        st.dataframe(
            pd.DataFrame(inter_rater["disagreement_cases"]),
            use_container_width=True,
            hide_index=True,
        )


def render_report_dashboard() -> None:
    if st.button("Generate evaluation report", type="primary"):
        path = write_evaluation_report()
        st.success(f"Generated {path}")

    report_text = generate_evaluation_report()
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
