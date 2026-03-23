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
from orchestrator import run_single, run_batch, PipelineJob, PipelineResult


def render_agent_page():
    """Render the AI Analysis tab with pipeline runner and chat."""
    _render_pipeline_section()
    if (
        not st.session_state.get("batch_mode", False)
        and not st.session_state.get("pipeline_running", False)
        and "agent_analysis" in st.session_state
    ):
        st.divider()
        _render_chat_section()


def _render_pipeline_section():
    st.subheader("AI Analysis Pipeline")

    if "batch_mode" not in st.session_state:
        st.session_state["batch_mode"] = False

    with st.form(key="agent_pipeline_form"):
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
        if not csv_files:
            st.error("Please upload a CSV file.")
            return

        is_batch = len(csv_files) > 1
        st.session_state["batch_mode"] = is_batch
        st.session_state["pipeline_cancelled"] = False
        st.session_state["pipeline_running"] = True
        # Clear previous results
        for key in ["single_result", "batch_zip",
                     "agent_analysis", "agent_anomalies", "agent_recommendations",
                     "agent_chat_history"]:
            st.session_state.pop(key, None)

        # Store form data for the pipeline to pick up after rerun
        st.session_state["pending_run"] = {
            "csv_files": [(f.name, f.getvalue()) for f in csv_files],
            "report_title": report_title,
            "month": month,
            "year": year,
            "logo_bytes": logo_file.getvalue() if logo_file else None,
            "brand_color": brand_color,
        }
        st.rerun()  # rerun to clear chat from DOM

    # Phase 2: pick up pending run after rerun
    pending = st.session_state.pop("pending_run", None)
    if pending:
        csv_files_data = pending["csv_files"]
        report_title = pending["report_title"]
        month = pending["month"]
        year = pending["year"]
        brand_color = pending["brand_color"]
        is_batch = st.session_state["batch_mode"]

        # Save uploads to temp files
        csv_temps = []
        for name, data in csv_files_data:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                tmp.write(data)
                csv_temps.append((name, tmp.name))

        logo_path = None
        if pending["logo_bytes"]:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_logo:
                tmp_logo.write(pending["logo_bytes"])
                logo_path = tmp_logo.name

        # Build PipelineJob objects
        jobs = [
            PipelineJob(
                name=csv_name.split(".")[0],
                csv_path=csv_path,
                report_title=report_title or "Report",
                month=month,
                year=year,
                logo_path=logo_path,
                brand_color=brand_color,
            )
            for csv_name, csv_path in csv_temps
        ]

        # Single file: run synchronously with status callback
        if not is_batch:
            job = jobs[0]
            progress_bar = st.progress(0, text="Starting pipeline...")
            cancel_placeholder = st.empty()

            def _run_single_threaded():
                while not job.is_done:
                    if st.session_state.get("pipeline_cancelled"):
                        job.error = "Pipeline cancelled by user."
                        return
                    job.run_current_step()

            thread = threading.Thread(target=_run_single_threaded, daemon=True)
            thread.start()

            while not job.is_done:
                progress_bar.progress(
                    min(job.progress_pct, 99), text=job.status_text
                )
                if cancel_placeholder.button("Cancel", key=f"c_{time.time()}"):
                    st.session_state["pipeline_cancelled"] = True
                time.sleep(0.3)

            cancel_placeholder.empty()
            _cleanup(csv_temps, logo_path)

            if job.error:
                progress_bar.progress(100, text=f"Failed: {job.error}")
                st.error(f"Pipeline error: {job.error}")
                st.session_state["pipeline_running"] = False
                return

            progress_bar.progress(100, text="Complete")
            result = job.to_result()
            st.session_state["single_result"] = result
            st.session_state["single_csv_name"] = jobs[0].name
            st.session_state["pipeline_running"] = False

        else:
            # Batch mode: run concurrently with per-job progress bars
            st.write(f"Running {len(jobs)} pipelines concurrently...")
            progress_bars = {}
            for job in jobs:
                progress_bars[job.name] = st.progress(0, text=f"{job.name}: Starting...")
            cancel_placeholder = st.empty()

            def _run_batch_threaded():
                run_batch(
                    jobs,
                    cancel_check=lambda: st.session_state.get("pipeline_cancelled", False),
                )

            thread = threading.Thread(target=_run_batch_threaded, daemon=True)
            thread.start()

            while not all(j.is_done for j in jobs):
                for job in jobs:
                    bar = progress_bars[job.name]
                    pct = min(job.progress_pct, 99) if not job.is_done else 100
                    label = f"{job.name}: {job.status_text}"
                    bar.progress(pct, text=label)
                if cancel_placeholder.button("Cancel All", key=f"cb_{time.time()}"):
                    st.session_state["pipeline_cancelled"] = True
                time.sleep(0.3)

            cancel_placeholder.empty()
            _cleanup(csv_temps, logo_path)

            for job in jobs:
                bar = progress_bars[job.name]
                if job.error:
                    bar.progress(100, text=f"{job.name}: Failed")
                else:
                    bar.progress(100, text=f"{job.name}: Complete")

            results = []
            errors = []
            for job in jobs:
                if job.error:
                    errors.append(f"{job.name}: {job.error}")
                else:
                    results.append(job)

            if errors:
                for err in errors:
                    st.error(err)

            if results:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for job in results:
                        zf.writestr(f"{job.name}_ai_report.pdf", job.pdf_bytes)
                st.session_state["batch_zip"] = zip_buffer.getvalue()
            st.session_state["pipeline_running"] = False

    # Persistent download button (survives reruns)
    if "batch_zip" in st.session_state and st.session_state.get("batch_mode"):
        st.download_button(
            label="Download Reports (ZIP)",
            data=st.session_state["batch_zip"],
            file_name="reports.zip",
            mime="application/zip",
        )

    # Persistent single-file results (survives reruns)
    if not st.session_state.get("batch_mode") and "single_result" in st.session_state:
        _show_single_results(
            st.session_state["single_result"],
            st.session_state.get("single_csv_name", "report"),
        )


def _cleanup(csv_temps: list[tuple[str, str]], logo_path: str | None):
    """Remove temp files."""
    for _, path in csv_temps:
        if os.path.exists(path):
            os.unlink(path)
    if logo_path and os.path.exists(logo_path):
        os.unlink(logo_path)


def _show_single_results(result: PipelineResult, name: str):
    """Display results for a single-file pipeline run."""
    st.session_state["agent_analysis"] = result.analysis
    st.session_state["agent_anomalies"] = result.anomaly_report
    st.session_state["agent_recommendations"] = result.rec_report

    with st.expander("Executive Summary", expanded=True):
        st.write(
            f"Analyzed {result.analysis.total_listings} listings. "
            f"Found {len(result.anomaly_report.anomalies)} anomalies and "
            f"generated {len(result.rec_report.recommendations)} recommendations."
        )

    with st.expander(f"Anomalies ({len(result.anomaly_report.anomalies)})"):
        if result.anomaly_report.anomalies:
            rows = []
            for a in result.anomaly_report.anomalies:
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
            st.write(result.anomaly_report.summary)
        else:
            st.info("No anomalies detected.")

    with st.expander(f"Recommendations ({len(result.rec_report.recommendations)})"):
        for rec in result.rec_report.recommendations:
            pri_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec.priority, "⚪")
            st.markdown(f"{pri_color} **[{rec.priority.upper()}] {rec.listing_name}**")
            st.write(f"**Action:** {rec.action}")
            st.write(f"*Rationale:* {rec.rationale}")
            st.write(f"*Expected Impact:* {rec.expected_impact} | *Confidence:* {rec.confidence}")
            st.divider()
        st.write(result.rec_report.summary)

    st.download_button(
        label="Download AI Report PDF",
        data=result.pdf_bytes,
        file_name=f"{name}_ai_report.pdf",
        mime="application/pdf",
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

    # Scrollable message container
    chat_container = st.container(height=400)
    with chat_container:
        for msg in st.session_state["agent_chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    user_input = st.chat_input("Ask about your analysis...")
    if user_input:
        st.session_state["agent_chat_history"].append(
            {"role": "user", "content": user_input}
        )
        with chat_container:
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

        with chat_container:
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
