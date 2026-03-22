"""AI Analysis tab — pipeline runner + chat interface."""

from __future__ import annotations

import os
import tempfile

import pandas as pd
import streamlit as st

from models.schemas import AnalysisResult, AnomalyReport, RecommendationReport
# from storage.local import LocalStorage


def render_agent_page():
    """Render the AI Analysis tab with pipeline runner and chat."""
    _render_pipeline_section()
    st.divider()
    _render_chat_section()


def _render_pipeline_section():
    st.subheader("AI Analysis Pipeline")

    with st.form(key="agent_pipeline_form"):
        client_id = st.text_input(
            "Client ID",
            placeholder="e.g. legacy-beach-homes",
            help="Unique identifier for this client.",
        )
        report_title = st.text_input(
            "Report Title",
            placeholder="Enter title for the report",
            value="Monthly Revenue Report",
        )
        month = st.selectbox(
            "Month",
            options=[
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November",
                "December",
            ],
            index=pd.Timestamp.now().month - 1,
        )
        year = st.selectbox(
            "Year",
            options=[str(y) for y in range(2020, pd.Timestamp.now().year + 1)],
            index=pd.Timestamp.now().year - 2020,
        )
        csv_file = st.file_uploader(
            "Upload CSV", type=["csv", "xlsx"],
            help="Upload PriceLabs CSV/Excel export.",
        )
        logo_file = st.file_uploader(
            "Upload Logo (optional)", type=["png", "jpg", "jpeg"],
        )
        brand_color = st.color_picker(
            "Brand Color", value="#d4cfcf",
        )
        run_btn = st.form_submit_button("Run Analysis")

    if run_btn:
        if not csv_file or not client_id:
            st.error("Please provide a Client ID and upload a CSV file.")
            return

        # storage = LocalStorage()

        # Save uploaded CSV to temp file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".csv"
        ) as tmp:
            tmp.write(csv_file.getvalue())
            csv_path = tmp.name

        # Save CSV to storage
        # storage.save_csv(
        #     client_id, csv_file.getvalue(),
        #     pd.Timestamp.now().strftime("%Y-%m-%d"), # Change to selected date
        # )

        # Handle logo
        logo_path = None
        if logo_file:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".png"
            ) as tmp_logo:
                tmp_logo.write(logo_file.getvalue())
                logo_path = tmp_logo.name

        # Run pipeline with status updates
        from orchestrator import run_pipeline

        status_container = st.status("Running AI Analysis Pipeline...", expanded=True)
        status_messages: list[str] = []

        def on_status(msg: str):
            status_messages.append(msg)
            status_container.write(msg)

        try:
            pdf_bytes, analysis, anomaly_report, rec_report = run_pipeline(
                csv_path=csv_path,
                client_id=client_id,
                report_title=report_title or "Report",
                month=month,
                year=year,
                logo_path=logo_path,
                brand_color=brand_color,
                on_status_update=on_status,
            )
            status_container.update(label="Pipeline Complete", state="complete")
        except Exception as e:
            status_container.update(label="Pipeline Failed", state="error")
            st.error(f"Pipeline error: {e}")
            return
        finally:
            # Cleanup temp files
            if os.path.exists(csv_path):
                os.unlink(csv_path)
            if logo_path and os.path.exists(logo_path):
                os.unlink(logo_path)

        # Store results in session state for chat
        st.session_state["agent_analysis"] = analysis
        st.session_state["agent_anomalies"] = anomaly_report
        st.session_state["agent_recommendations"] = rec_report

        # Download button
        st.download_button(
            label="Download AI Report PDF",
            data=pdf_bytes,
            file_name=f"{client_id}_ai_report.pdf",
            mime="application/pdf",
        )

        # Show results in expandable sections
        with st.expander("Executive Summary", expanded=True):
            st.write(
                f"Analyzed {analysis.total_listings} listings. "
                f"Found {len(anomaly_report.anomalies)} anomalies and "
                f"generated {len(rec_report.recommendations)} recommendations."
            )

        with st.expander(f"Anomalies ({len(anomaly_report.anomalies)})"):
            if anomaly_report.anomalies:
                rows = []
                for a in anomaly_report.anomalies:
                    rows.append({
                        "Listing": a.listing_name,
                        "Metric": a.metric,
                        "Current": f"{a.current_value:.2f}",
                        "Benchmark": f"{a.comparison_value:.2f}",
                        "Deviation": f"{a.deviation_pct:.1f}%",
                        "Severity": a.severity.upper(),
                        "Explanation": a.explanation,
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
                st.write(anomaly_report.summary)
            else:
                st.info("No anomalies detected.")

        with st.expander(f"Recommendations ({len(rec_report.recommendations)})"):
            for rec in rec_report.recommendations:
                pri_color = {
                    "high": "🔴", "medium": "🟡", "low": "🟢"
                }.get(rec.priority, "⚪")
                st.markdown(
                    f"{pri_color} **[{rec.priority.upper()}] {rec.listing_name}**"
                )
                st.write(f"**Action:** {rec.action}")
                st.write(f"*Rationale:* {rec.rationale}")
                st.write(
                    f"*Expected Impact:* {rec.expected_impact} "
                    f"| *Confidence:* {rec.confidence}"
                )
                st.divider()
            st.write(rec_report.summary)


def _render_chat_section():
    """Chat interface for follow-up questions about the analysis."""
    st.subheader("Chat with Your Analysis")

    if "agent_analysis" not in st.session_state:
        st.info(
            "Run the AI Analysis Pipeline above first, "
            "then ask follow-up questions here."
        )
        return

    # Initialize chat history
    if "agent_chat_history" not in st.session_state:
        st.session_state["agent_chat_history"] = []

    # Display chat history
    for msg in st.session_state["agent_chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    user_input = st.chat_input("Ask about your analysis...")
    if user_input:
        # Add user message
        st.session_state["agent_chat_history"].append(
            {"role": "user", "content": user_input}
        )
        with st.chat_message("user"):
            st.write(user_input)

        # Build context from analysis results
        analysis: AnalysisResult = st.session_state["agent_analysis"]
        anomalies: AnomalyReport = st.session_state["agent_anomalies"]
        recs: RecommendationReport = st.session_state["agent_recommendations"]

        system_prompt = (
            "You are an expert short-term rental revenue management consultant "
            "for Enrich Revenue Management. You have access to the following "
            "analysis data for this client's portfolio. Answer questions "
            "specifically using this data.\n\n"
            f"Analysis Result:\n{analysis.model_dump_json()}\n\n"
            f"Anomaly Report:\n{anomalies.model_dump_json()}\n\n"
            f"Recommendation Report:\n{recs.model_dump_json()}"
        )

        # Build conversation for the API
        from agents.llm_client import call_streaming, SONNET

        chat_history_text = ""
        for msg in st.session_state["agent_chat_history"]:
            role = "User" if msg["role"] == "user" else "Assistant"
            chat_history_text += f"{role}: {msg['content']}\n\n"

        with st.chat_message("assistant"):
            try:
                response_chunks = call_streaming(
                    system_prompt=system_prompt,
                    user_message=chat_history_text,
                    model=SONNET,
                )
                # Collect full response first, then render as markdown
                # to avoid garbled formatting during streaming
                placeholder = st.empty()
                full_response = ""
                for chunk in response_chunks:
                    full_response += chunk
                    placeholder.markdown(full_response + "▌")
                placeholder.markdown(full_response)
                response = full_response
            except Exception as e:
                response = f"Sorry, I encountered an error: {e}"
                st.error(response)

        st.session_state["agent_chat_history"].append(
            {"role": "assistant", "content": response}
        )
