"""LocalStorage — file-based storage for analysis history."""

from __future__ import annotations

import json
import os
from pathlib import Path

from models.schemas import AnalysisResult
from storage.base import Storage


class LocalStorage(Storage):
    """Stores analysis results and CSVs under data/history/{client_id}/."""

    def __init__(self, base_dir: str = "data/history"):
        self.base_dir = Path(base_dir)

    def _client_dir(self, client_id: str) -> Path:
        d = self.base_dir / client_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_analysis(self, client_id: str, analysis: AnalysisResult) -> None:
        d = self._client_dir(client_id)
        # Use report_date as filename (e.g. 2026-03.json)
        date_key = analysis.report_date[:7]  # YYYY-MM
        path = d / f"{date_key}.json"
        path.write_text(analysis.model_dump_json(indent=2), encoding="utf-8")

    def get_history(
        self, client_id: str, max_months: int = 6
    ) -> list[AnalysisResult]:
        d = self._client_dir(client_id)
        results: list[AnalysisResult] = []
        json_files = sorted(d.glob("*.json"), reverse=True)
        for f in json_files[:max_months]:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                results.append(AnalysisResult.model_validate(data))
            except Exception:
                continue
        return list(reversed(results))  # chronological order

    def save_csv(
        self, client_id: str, csv_bytes: bytes, report_date: str
    ) -> str:
        d = self._client_dir(client_id)
        date_key = report_date[:7]
        path = d / f"{date_key}.csv"
        path.write_bytes(csv_bytes)
        return str(path)
