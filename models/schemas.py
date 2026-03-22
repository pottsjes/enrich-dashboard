"""Pydantic models for inter-agent data contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ListingMetrics(BaseModel):
    """Condensed metrics for a single listing — computed by DataAnalystAgent from raw CSV."""
    listing_name: str
    listing_id: str
    city: str
    bedroom_count: str | None = None
    # Occupancy
    occupancy_pct: float | None = None
    occupancy_stly: float | None = None
    occupancy_yoy_diff: float | None = None
    market_occupancy_pct: float | None = None
    market_penetration_index: float | None = None
    paid_occupancy_pct: float | None = None
    weekend_occupancy_pct: float | None = None
    weekday_occupancy_pct: float | None = None
    market_occupancy_stly: float | None = None
    paid_occupancy_stly: float | None = None
    # Revenue
    rental_revenue: float | None = None
    rental_revenue_stly: float | None = None
    rental_revenue_yoy_pct: float | None = None
    total_revenue: float | None = None
    total_revenue_stly: float | None = None
    total_revenue_yoy_pct: float | None = None
    # ADR
    rental_adr: float | None = None
    rental_adr_stly: float | None = None
    market_adr: float | None = None
    adr_index: float | None = None
    # RevPAR
    rental_revpar: float | None = None
    rental_revpar_stly: float | None = None
    market_revpar: float | None = None
    revpar_index: float | None = None
    # Pricing context
    base_price: float | None = None
    recommended_base_price: float | None = None
    final_price: float | None = None
    market_median_price: float | None = None
    market_75th_percentile_price: float | None = None
    # Booking dynamics
    booked_nights: int | None = None
    available_nights: int | None = None
    blocked_nights: int | None = None
    number_of_bookings: int | None = None
    avg_booking_window: float | None = None
    market_avg_booking_window: float | None = None
    avg_los: float | None = None
    booked_nights_pickup_30d: float | None = None
    # Pickup (30-day window)
    occupancy_pickup_30d: float | None = None
    occupancy_pickup_stly_30d: float | None = None
    revenue_pickup_30d: float | None = None
    revenue_pickup_stly_30d: float | None = None
    # Events
    events_count: int | None = None
    events_names: str | None = None


class PortfolioSummary(BaseModel):
    """Aggregate metrics across all listings."""
    total_revenue: float
    total_revenue_stly: float
    avg_occupancy: float
    avg_occupancy_stly: float
    avg_revpar: float
    avg_revpar_stly: float
    avg_market_penetration: float
    avg_adr_index: float
    top_performer: str
    bottom_performer: str
    listings_above_market: int
    listings_below_market: int


class AnalysisResult(BaseModel):
    """Output of DataAnalystAgent — full portfolio analysis."""
    report_date: str
    total_listings: int
    portfolio_summary: PortfolioSummary
    listings: list[ListingMetrics]


class Anomaly(BaseModel):
    """A single detected anomaly."""
    listing_name: str
    metric: str
    current_value: float
    comparison_value: float
    deviation_pct: float
    severity: Literal["low", "medium", "high"]
    explanation: str


class AnomalyReport(BaseModel):
    """Output of AnomalyDetectionAgent."""
    anomalies: list[Anomaly]
    summary: str


class Recommendation(BaseModel):
    """A single actionable recommendation."""
    listing_name: str
    action: str
    rationale: str
    expected_impact: str
    confidence: Literal["low", "medium", "high"]
    priority: Literal["low", "medium", "high"]


class RecommendationReport(BaseModel):
    """Output of RecommendationAgent."""
    recommendations: list[Recommendation]
    summary: str


class EvalResult(BaseModel):
    """Output of EvalAgent."""
    passed: bool
    score: float
    feedback: str


class NarrativeInsight(BaseModel):
    """A narrative section for the PDF report."""
    section_title: str
    content: str


class ReportContent(BaseModel):
    """Everything needed to compose the final PDF."""
    executive_summary: str
    listing_narratives: list[NarrativeInsight]
    anomaly_summary: str
    recommendations_summary: str
