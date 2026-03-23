"""AI Analysis tab — pipeline runner + chat interface."""

from __future__ import annotations

import os
import tempfile
import threading
import time
import zipfile
from io import BytesIO

import pandas as pd
import streamlit as st

from models.schemas import AnalysisResult, AnomalyReport, RecommendationReport
from orchestrator import run_pipeline


def render_agent_page():
    """Render the AI Analysis tab with pipeline runner and chat."""
    _render_pipeline_section()
    if not st.session_state.get("batch_mode", False):
        st.divider()
        _render_chat_section()


def _render_pipeline_section():
    st.subheader("AI Analysis Pipeline")

    if "batch_mode" not in st.session_state:
        st.session_state["batch_mode"] = False

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
        csv_files = st.file_uploader(
            "Upload CSV(s)",
            type=["csv", "xlsx"],
            accept_multiple_files=True,
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
        if not csv_files or not client_id:
            st.error("Please provide a Client ID and upload a CSV file.")
            return

        st.session_state["batch_mode"] = len(csv_files) > 1
        st.session_state["pipeline_cancelled"] = False

        # Prepare temp files before threading
        csv_temps = []
        for csv in csv_files:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                tmp.write(csv.getvalue())
                csv_temps.append((csv.name, tmp.name))

        logo_path = None
        if logo_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_logo:
                tmp_logo.write(logo_file.getvalue())
                logo_path = tmp_logo.name

        # Shared state for thread communication
        progress = {"status": "Starting...", "done": False, "error": None, "results": []}
        is_batch = st.session_state["batch_mode"]
        current_file = {"name": ""}

        def on_status(msg: str):
            if is_batch and current_file["name"]:
                progress["status"] = f"[{current_file['name']}] {msg}"
            else:
                progress["status"] = msg

        def run_in_thread():
            try:
                for csv_name, csv_path in csv_temps:
                    if st.session_state.get("pipeline_cancelled"):
                        progress["error"] = "Pipeline cancelled by user."
                        return
                    current_file["name"] = csv_name
                    on_status(f"Starting...")
                    pdf_bytes, analysis, anomaly_report, rec_report = run_pipeline(
                        csv_path=csv_path,
                        client_id=client_id,
                        report_title=report_title or "Report",
                        month=month,
                        year=year,
                        logo_path=logo_path,
                        brand_color=brand_color,
                        on_status_update=on_status,
                        cancel_check=lambda: st.session_state.get("pipeline_cancelled", False),
                    )
                    progress["results"].append({
                        "name": csv_name.split(".")[0],
                        "pdf_bytes": pdf_bytes,
                        "analysis": analysis,
                        "anomaly_report": anomaly_report,
                        "rec_report": rec_report,
                    })
            except Exception as e:
                progress["error"] = str(e)
            finally:
                progress["done"] = True
                # Cleanup
                for _, path in csv_temps:
                    if os.path.exists(path):
                        os.unlink(path)
                if logo_path and os.path.exists(logo_path):
                    os.unlink(logo_path)

        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()

        # Poll for updates with live UI
        progress_bar = st.progress(0, text="Starting pipeline...")
        cancel_placeholder = st.empty()

        # Map known status messages to progress percentages
        step_progress = {
            "Analyzing data...": 5,
            "Detecting anomalies...": 15,
            "Detecting anomalies done": 35,
            "Generating recommendations...": 40,
            "Generating recommendations done": 60,
            "Evaluating quality...": 65,
            "Evaluating quality done": 70,
            "Improving recommendations...": 72,
            "Re-evaluating...": 78,
            "Composing report...": 80,
            "Composing report done": 95,
        }
        last_status = ""

        while not progress["done"]:
            current = progress["status"]
            if current != last_status:
                last_status = current
                # Find best matching progress value
                pct = 10
                for key, val in step_progress.items():
                    if key in current:
                        pct = val
                        break
                progress_bar.progress(min(pct, 99), text=current)
            if cancel_placeholder.button("Cancel Pipeline", key=f"cancel_{time.time()}"):
                st.session_state["pipeline_cancelled"] = True
                progress["status"] = "Cancelling..."
            time.sleep(0.3)

        cancel_placeholder.empty()

        if progress["error"]:
            progress_bar.progress(100, text=f"Failed: {progress['error']}")
            st.error(f"Pipeline error: {progress['error']}")
            return

        progress_bar.progress(100, text="Pipeline complete")
        results = progress["results"]

        # Single file mode: show details + chat
        if not st.session_state["batch_mode"] and results:
            r = results[0]
            st.session_state["agent_analysis"] = r["analysis"]
            st.session_state["agent_anomalies"] = r["anomaly_report"]
            st.session_state["agent_recommendations"] = r["rec_report"]

            with st.expander("Executive Summary", expanded=True):
                st.write(
                    f"Analyzed {r['analysis'].total_listings} listings. "
                    f"Found {len(r['anomaly_report'].anomalies)} anomalies and "
                    f"generated {len(r['rec_report'].recommendations)} recommendations."
                )

            with st.expander(f"Anomalies ({len(r['anomaly_report'].anomalies)})"):
                if r["anomaly_report"].anomalies:
                    rows = []
                    for a in r["anomaly_report"].anomalies:
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
                    st.write(r["anomaly_report"].summary)
                else:
                    st.info("No anomalies detected.")

            with st.expander(f"Recommendations ({len(r['rec_report'].recommendations)})"):
                for rec in r["rec_report"].recommendations:
                    pri_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec.priority, "⚪")
                    st.markdown(f"{pri_color} **[{rec.priority.upper()}] {rec.listing_name}**")
                    st.write(f"**Action:** {rec.action}")
                    st.write(f"*Rationale:* {rec.rationale}")
                    st.write(f"*Expected Impact:* {rec.expected_impact} | *Confidence:* {rec.confidence}")
                    st.divider()
                st.write(r["rec_report"].summary)

            st.download_button(
                label="Download AI Report PDF",
                data=r["pdf_bytes"],
                file_name=f"{client_id}_ai_report.pdf",
                mime="application/pdf",
            )
        elif results:
            # Batch mode: zip download
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for r in results:
                    zf.writestr(f"{r['name']}_ai_report.pdf", r["pdf_bytes"])
            st.download_button(
                label="Download All Reports",
                data=zip_buffer.getvalue(),
                file_name="reports.zip",
                mime="application/zip",
            )
    


def _render_chat_section():
    """Chat interface for follow-up questions about the analysis."""
    st.subheader("Chat with Your Analysis")

    if "agent_analysis" not in st.session_state:
        st.info(
            "Run the AI Analysis Pipeline above for a single CSV first, "
            "then ask follow-up questions here."
        )
        return

    if "agent_chat_history" not in st.session_state:
        st.session_state["agent_chat_history"] = []

    for msg in st.session_state["agent_chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask about your analysis...")
    if user_input:
        st.session_state["agent_chat_history"].append(
            {"role": "user", "content": user_input}
        )
        with st.chat_message("user"):
            st.write(user_input)

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
