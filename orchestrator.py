"""Pipeline orchestrator — coordinates the multi-agent analysis flow."""

from __future__ import annotations

import time
from typing import Callable

from agents.data_analyst import DataAnalystAgent
from agents.anomaly_detection import AnomalyDetectionAgent
from agents.recommendation import RecommendationAgent
from agents.eval import EvalAgent
from agents.report_composer import ReportComposerAgent
from models.schemas import AnalysisResult, AnomalyReport, RecommendationReport
# from storage.local import LocalStorage


def _noop(msg: str) -> None:
    pass


def run_pipeline(
    csv_path: str,
    client_id: str,
    report_title: str,
    month: str,
    year: str,
    logo_path: str | None = None,
    brand_color: str = "#d4cfcf",
    on_status_update: Callable[[str], None] | None = None,
) -> tuple[bytes, AnalysisResult, AnomalyReport, RecommendationReport]:
    """Run the full analysis pipeline synchronously.

    Returns (pdf_bytes, analysis, anomaly_report, recommendation_report).
    """
    status = on_status_update or _noop
    # storage = LocalStorage()

    def _timed(label, fn):
        status(f"{label}...")
        t0 = time.time()
        result = fn()
        elapsed = time.time() - t0
        status(f"{label} done ({elapsed:.1f}s)")
        return result

    # Step 1: Data analysis (pure Python)
    data_analyst = DataAnalystAgent()
    analysis = _timed("Analyzing data", lambda: data_analyst.analyze(csv_path, month=month, year=year))

    # Step 2: Load history
    # history = storage.get_history(client_id)
    history = None

    # Step 3: Anomaly detection (LLM)
    anomaly_agent = AnomalyDetectionAgent()
    anomaly_report = _timed("Detecting anomalies", lambda: anomaly_agent.detect(analysis, history))

    # Step 4: Recommendations (LLM)
    rec_agent = RecommendationAgent()
    rec_report = _timed("Generating recommendations", lambda: rec_agent.recommend(analysis, anomaly_report))

    # Step 5: Eval (LLM - Haiku)
    eval_agent = EvalAgent()
    eval_result = _timed("Evaluating quality", lambda: eval_agent.evaluate(rec_report))

    # Step 6: Retry if eval fails
    if not eval_result.passed:
        rec_report = _timed("Improving recommendations", lambda: rec_agent.recommend(
            analysis, anomaly_report, feedback=eval_result.feedback
        ))
        eval_result = _timed("Re-evaluating", lambda: eval_agent.evaluate(rec_report))
        if not eval_result.passed:
            status(f"Proceeding with current recommendations (eval score: {eval_result.score:.2f})")

    # Step 7: Compose report (LLM + PDF)
    composer = ReportComposerAgent()
    report_content, pdf_bytes = _timed("Composing report", lambda: composer.compose(
        analysis, anomaly_report, rec_report,
        report_title, month, year, logo_path, brand_color,
    ))

    # Step 8: Save results
    # storage.save_analysis(client_id, analysis)

    return pdf_bytes, analysis, anomaly_report, rec_report
