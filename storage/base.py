"""Abstract storage interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from models.schemas import AnalysisResult


class Storage(ABC):
    @abstractmethod
    def save_analysis(self, client_id: str, analysis: AnalysisResult) -> None:
        ...

    @abstractmethod
    def get_history(self, client_id: str, max_months: int = 6) -> list[AnalysisResult]:
        ...

    @abstractmethod
    def save_csv(self, client_id: str, csv_bytes: bytes, report_date: str) -> str:
        ...
