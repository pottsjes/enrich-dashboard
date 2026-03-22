"""RecommendationAgent — generates actionable recommendations using LLM."""

from __future__ import annotations

from models.schemas import (
    AnalysisResult,
    AnomalyReport,
    RecommendationReport,
)
from agents.llm_client import call, SONNET

SYSTEM_PROMPT = """\
You are an expert short-term rental revenue management consultant. \
Given property performance data and detected anomalies, generate specific, \
actionable recommendations for each issue.

Guidelines:
- Be SPECIFIC: "reduce weekday rate by $15-20" not "adjust pricing"
- Use pricing data (base price, market percentiles, recommended base price) \
for pricing suggestions
- Use pickup metrics to inform timing: "booking pace is lagging STLY by X% \
at the 30-day window — consider a rate reduction for the next 2 weeks"
- Use weekend vs weekday occupancy splits for day-of-week pricing strategies
- Each recommendation needs a confidence score and priority
- Do NOT give generic advice — every recommendation must reference specific \
metrics from the data

Return your response as a JSON object matching the provided schema."""


class RecommendationAgent:
    """Generates actionable recommendations from analysis + anomalies."""

    def recommend(
        self,
        analysis: AnalysisResult,
        anomaly_report: AnomalyReport,
        feedback: str | None = None,
    ) -> RecommendationReport:
        listings_data = [
            {
                "name": l.listing_name,
                "occupancy": l.occupancy_pct,
                "occupancy_stly": l.occupancy_stly,
                "weekend_occ": l.weekend_occupancy_pct,
                "weekday_occ": l.weekday_occupancy_pct,
                "revenue": l.total_revenue,
                "revenue_stly": l.total_revenue_stly,
                "rental_adr": l.rental_adr,
                "market_adr": l.market_adr,
                "adr_index": l.adr_index,
                "revpar_index": l.revpar_index,
                "base_price": l.base_price,
                "recommended_base_price": l.recommended_base_price,
                "final_price": l.final_price,
                "market_median_price": l.market_median_price,
                "market_75th_price": l.market_75th_percentile_price,
                "mpi": l.market_penetration_index,
                "booking_window": l.avg_booking_window,
                "market_booking_window": l.market_avg_booking_window,
                "occ_pickup_30d": l.occupancy_pickup_30d,
                "occ_pickup_stly_30d": l.occupancy_pickup_stly_30d,
                "rev_pickup_30d": l.revenue_pickup_30d,
                "rev_pickup_stly_30d": l.revenue_pickup_stly_30d,
                "booked_nights": l.booked_nights,
                "available_nights": l.available_nights,
                "blocked_nights": l.blocked_nights,
            }
            for l in analysis.listings
        ]
        anomalies_data = [a.model_dump() for a in anomaly_report.anomalies]

        user_msg = (
            f"Portfolio Summary:\n{analysis.portfolio_summary.model_dump()}\n\n"
            f"Listings Data:\n{listings_data}\n\n"
            f"Detected Anomalies:\n{anomalies_data}\n\n"
            f"Anomaly Summary: {anomaly_report.summary}\n\n"
            "Generate specific, actionable recommendations."
        )
        if feedback:
            user_msg += (
                f"\n\nPREVIOUS ATTEMPT FEEDBACK (improve based on this):\n{feedback}"
            )

        return call(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_msg,
            model=SONNET,
            output_schema=RecommendationReport,
            max_tokens=8192,
        )
