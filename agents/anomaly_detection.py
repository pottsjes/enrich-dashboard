"""AnomalyDetectionAgent — rule-based flagging + LLM explanation."""

from __future__ import annotations

from models.schemas import AnalysisResult, Anomaly, AnomalyReport
from agents.llm_client import call, SONNET

SYSTEM_PROMPT = """\
You are a short-term rental revenue management analyst. You are given a set of \
flagged anomalies from a property portfolio along with the full portfolio summary. \
Your job is to:
1. Explain WHY each anomaly matters in 1 concise sentence each.
2. Identify cross-listing patterns (e.g., "3 of 5 listings show declining weekday occupancy").
3. Assign a severity: "low", "medium", or "high" based on financial impact.
4. If historical data is provided, note trends.
5. Write a 2-3 sentence summary of the overall anomaly landscape.

Keep explanations brief and specific. Avoid repetitive phrasing across anomalies.

Return your response as a JSON object matching the provided schema."""


class AnomalyDetectionAgent:
    """Detects anomalies via rules, then uses LLM to explain them."""

    def detect(
        self,
        analysis: AnalysisResult,
        history: list[AnalysisResult] | None = None,
    ) -> AnomalyReport:
        flagged = self._rule_based_flags(analysis)
        # Keep only the most severe anomaly per listing (largest absolute deviation)
        best_per_listing: dict[str, dict] = {}
        for f in flagged:
            name = f["listing_name"]
            if name not in best_per_listing or abs(f["deviation_pct"]) > abs(best_per_listing[name]["deviation_pct"]):
                best_per_listing[name] = f
        flagged = list(best_per_listing.values())

        if not flagged and not history:
            return AnomalyReport(
                anomalies=[],
                summary="No anomalies detected in the current dataset.",
            )
        return self._llm_explain(analysis, flagged, history or [])

    @staticmethod
    def _rule_based_flags(
        analysis: AnalysisResult,
    ) -> list[dict]:
        """Apply simple threshold rules to flag potential anomalies."""
        flags: list[dict] = []
        for l in analysis.listings:
            # RevPAR Index below 0.85
            if l.revpar_index is not None and l.revpar_index < 0.85:
                flags.append({
                    "listing_name": l.listing_name,
                    "metric": "RevPAR Index",
                    "current_value": l.revpar_index,
                    "comparison_value": 1.0,
                    "deviation_pct": round((l.revpar_index - 1.0) / 1.0 * 100, 1),
                })
            # Occupancy YoY decline > 10%
            if (
                l.occupancy_pct is not None
                and l.occupancy_stly is not None
                and l.occupancy_stly > 0
            ):
                yoy = (l.occupancy_pct - l.occupancy_stly) / l.occupancy_stly
                if yoy < -0.10:
                    flags.append({
                        "listing_name": l.listing_name,
                        "metric": "Occupancy YoY",
                        "current_value": l.occupancy_pct,
                        "comparison_value": l.occupancy_stly,
                        "deviation_pct": round(yoy * 100, 1),
                    })
            # Revenue YoY decline > 15%
            if (
                l.total_revenue is not None
                and l.total_revenue_stly is not None
                and l.total_revenue_stly > 0
            ):
                rev_yoy = (l.total_revenue - l.total_revenue_stly) / l.total_revenue_stly
                if rev_yoy < -0.15:
                    flags.append({
                        "listing_name": l.listing_name,
                        "metric": "Revenue YoY",
                        "current_value": l.total_revenue,
                        "comparison_value": l.total_revenue_stly,
                        "deviation_pct": round(rev_yoy * 100, 1),
                    })
            # Market Penetration Index below 80%
            if l.market_penetration_index is not None and l.market_penetration_index < 0.80:
                flags.append({
                    "listing_name": l.listing_name,
                    "metric": "Market Penetration Index",
                    "current_value": l.market_penetration_index,
                    "comparison_value": 1.0,
                    "deviation_pct": round((l.market_penetration_index - 1.0) * 100, 1),
                })
            # Booking window >30% shorter than market
            if (
                l.avg_booking_window is not None
                and l.market_avg_booking_window is not None
                and l.market_avg_booking_window > 0
            ):
                bw_diff = (l.avg_booking_window - l.market_avg_booking_window) / l.market_avg_booking_window
                if bw_diff < -0.30:
                    flags.append({
                        "listing_name": l.listing_name,
                        "metric": "Booking Window vs Market",
                        "current_value": l.avg_booking_window,
                        "comparison_value": l.market_avg_booking_window,
                        "deviation_pct": round(bw_diff * 100, 1),
                    })
            # Zero bookings with available nights
            if (
                l.number_of_bookings is not None
                and l.number_of_bookings == 0
                and l.available_nights is not None
                and l.available_nights > 0
            ):
                flags.append({
                    "listing_name": l.listing_name,
                    "metric": "Zero Bookings",
                    "current_value": 0,
                    "comparison_value": float(l.available_nights),
                    "deviation_pct": -100.0,
                })
        return flags

    @staticmethod
    def _llm_explain(
        analysis: AnalysisResult,
        flagged: list[dict],
        history: list[AnalysisResult],
    ) -> AnomalyReport:
        summary_data = analysis.portfolio_summary.model_dump()
        listings_brief = [
            {
                "name": l.listing_name,
                "revpar_index": l.revpar_index,
                "occupancy": l.occupancy_pct,
                "revenue": l.total_revenue,
                "mpi": l.market_penetration_index,
            }
            for l in analysis.listings
        ]

        history_note = ""
        if history:
            prev_dates = [h.report_date for h in history]
            history_note = (
                f"\nHistorical reports available for: {', '.join(prev_dates)}. "
                "Note any recurring patterns."
            )

        user_msg = (
            f"Portfolio: {analysis.total_listings} listings. "
            f"Avg occupancy: {summary_data['avg_occupancy']:.1%}, "
            f"Avg market penetration: {summary_data['avg_market_penetration']:.1%}\n\n"
            f"Listings:\n{listings_brief}\n\n"
            f"Flagged Anomalies ({len(flagged)}):\n{flagged}\n"
            f"{history_note}\n\n"
            "Analyze these anomalies and return the structured AnomalyReport."
        )
        return call(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_msg,
            model=SONNET,
            output_schema=AnomalyReport,
            max_tokens=16384,
        )
