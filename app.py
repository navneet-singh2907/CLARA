"""Streamlit entrypoint for the loan review pipeline."""

from dataclasses import asdict

import streamlit as st

from src.data.sample_cases import SAMPLE_CASES, get_sample_case
from src.graph.orchestrator import run_pipeline_with_state


st.set_page_config(
    page_title="Small Business Loan Review",
    layout="wide",
)

st.title("Small Business Loan Review Pipeline")
st.caption("Multi-agent decision support for human loan reviewers.")

case_options = {f"{case.case_id} - {case.borrower_name}": case.case_id for case in SAMPLE_CASES}
selected_label = st.selectbox("Sample loan case", options=list(case_options.keys()))

if st.button("Run review pipeline", type="primary"):
    loan_case = get_sample_case(case_options[selected_label])
    state = run_pipeline_with_state(loan_case)
    packet = state["review_packet"]

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

    st.subheader("Agent Outputs")
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
else:
    st.info("Choose a sample case and run the pipeline to generate the first review packet.")
