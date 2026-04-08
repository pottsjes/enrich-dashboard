"""Pipeline orchestrator — single and concurrent multi-CSV execution."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable

from agents.data_analyst import DataAnalystAgent
from agents.anomaly_detection import AnomalyDetectionAgent
from agents.recommendation import RecommendationAgent
from agents.eval import EvalAgent
from agents.report_composer import ReportComposerAgent
from models.schemas import AnalysisResult, AnomalyReport, RecommendationReport


class Step(IntEnum):
    ANALYZE = 0
    ANOMALIES = 1
    RECOMMENDATIONS = 2
    EVAL = 3
    COMPOSE = 4
    DONE = 5

STEP_LABELS = {
    Step.ANALYZE: "Analyzing data...",
    Step.ANOMALIES: "Detecting anomalies...",
    Step.RECOMMENDATIONS: "Generating recommendations...",
    Step.EVAL: "Evaluating quality...",
    Step.COMPOSE: "Composing report...",
    Step.DONE: "Complete",
}

STEP_PROGRESS = {
    Step.ANALYZE: 5,
    Step.ANOMALIES: 20,
    Step.RECOMMENDATIONS: 45,
    Step.EVAL: 65,
    Step.COMPOSE: 80,
    Step.DONE: 100,
}


@dataclass
class PipelineResult:
    """Result of a single pipeline run."""
    pdf_bytes: bytes
    analysis: AnalysisResult
    anomaly_report: AnomalyReport
    rec_report: RecommendationReport


@dataclass
class PipelineJob:
    """State machine for a single CSV's pipeline progression."""
    name: str
    csv_path: str
    report_title: str
    month: str
    year: str
    logo_path: str | None = None
    brand_color: str = "#d4cfcf"

    # State
    step: Step = Step.ANALYZE
    error: str | None = None
    analysis: AnalysisResult | None = None
    anomaly_report: AnomalyReport | None = None
    rec_report: RecommendationReport | None = None
    eval_passed: bool = False
    retried: bool = False
    pdf_bytes: bytes | None = None

    @property
    def is_done(self) -> bool:
        return self.step == Step.DONE or self.error is not None

    @property
    def progress_pct(self) -> int:
        return STEP_PROGRESS.get(self.step, 0)

    @property
    def status_text(self) -> str:
        if self.error:
            return f"Failed: {self.error}"
        return STEP_LABELS.get(self.step, "Unknown")

    def run_current_step(self) -> None:
        """Execute the current step and advance to the next."""
        try:
            if self.step == Step.ANALYZE:
                self.analysis = DataAnalystAgent().analyze(
                    self.csv_path, month=self.month, year=self.year
                )
                # Skip LLM steps — go straight to compose
                self.anomaly_report = AnomalyReport(anomalies=[], summary="")
                self.rec_report = RecommendationReport(recommendations=[], summary="")
                self.step = Step.COMPOSE

            elif self.step == Step.COMPOSE:
                _, self.pdf_bytes = ReportComposerAgent().compose(
                    self.analysis, self.anomaly_report, self.rec_report,
                    self.report_title, self.month, self.year,
                    self.logo_path, self.brand_color,
                )
                self.step = Step.DONE

        except Exception as e:
            self.error = str(e)

    def to_result(self) -> PipelineResult | None:
        if self.pdf_bytes is None:
            return None
        return PipelineResult(
            pdf_bytes=self.pdf_bytes,
            analysis=self.analysis,
            anomaly_report=self.anomaly_report,
            rec_report=self.rec_report,
        )


def run_single(
    csv_path: str,
    report_title: str,
    month: str,
    year: str,
    logo_path: str | None = None,
    brand_color: str = "#d4cfcf",
    on_status: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> PipelineResult:
    """Run pipeline for a single CSV synchronously."""
    _status = on_status or (lambda m: None)
    _cancelled = cancel_check or (lambda: False)

    job = PipelineJob(
        name="single",
        csv_path=csv_path,
        report_title=report_title,
        month=month,
        year=year,
        logo_path=logo_path,
        brand_color=brand_color,
    )
    while not job.is_done:
        if _cancelled():
            raise RuntimeError("Pipeline cancelled by user.")
        _status(job.status_text)
        job.run_current_step()

    if job.error:
        raise RuntimeError(job.error)
    _status("Complete")
    return job.to_result()


def run_batch(
    jobs: list[PipelineJob],
    max_workers: int | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> None:
    """Run multiple pipeline jobs concurrently.

    Jobs advance independently — fast jobs don't wait for slow ones.
    """
    _cancelled = cancel_check or (lambda: False)

    def _run_job(job: PipelineJob):
        """Run a single job through all its steps."""
        while not job.is_done:
            if _cancelled():
                job.error = "Pipeline cancelled by user."
                return
            job.run_current_step()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_run_job, j): j for j in jobs}
        for f in as_completed(futures):
            pass  # errors captured inside run_current_step
