"""DataAnalystAgent — pure Python/pandas data transformation, no LLM needed."""

from __future__ import annotations

from datetime import date

import pandas as pd

from models.schemas import AnalysisResult, ListingMetrics, PortfolioSummary


def _clean_value(val, as_type: str = "float"):
    """Clean a single CSV cell value.

    Handles: '$ 2,689.00' -> 2689.0, '43.90%' -> 0.439, 'N/A' -> None
    """
    if pd.isna(val) or val is None:
        return None
    s = str(val).strip()
    if s.upper() in ("N/A", "NA", "", "-"):
        return None

    s = s.replace("$", "").replace(",", "").strip()
    is_pct = s.endswith("%")
    if is_pct:
        s = s.rstrip("%").strip()

    try:
        num = float(s)
        if is_pct:
            num = num / 100.0
        if as_type == "int":
            return int(round(num * 100)) if is_pct else int(round(num))
        return num
    except (ValueError, TypeError):
        return None


def _clean_int(val):
    return _clean_value(val, as_type="int")


def _clean_float(val):
    return _clean_value(val, as_type="float")


def _safe_str(val) -> str:
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip()


# Column name mapping: Pydantic field -> CSV column name
# Commented entries are preserved for future AI/LLM integration.
_COL_MAP = {
    "listing_name": "Listing Name",
    # Occupancy
    "occupancy_pct": "Occupancy %",
    "occupancy_stly": "Occupancy % STLY",
    "market_occupancy_pct": "Market Occupancy %",
    "market_occupancy_stly": "Market Occupancy % STLY",
    "market_penetration_index": "Market Penetration Index %",
    "paid_occupancy_pct": "Paid Occupancy %",
    "paid_occupancy_stly": "Paid Occupancy % STLY",
    # "weekend_occupancy_pct": "Weekend Occupancy %",
    # "weekday_occupancy_pct": "Weekday Occupancy %",
    # Revenue
    "rental_revenue": "Rental Revenue",
    "rental_revenue_stly": "Rental Revenue STLY",
    "total_revenue": "Total Revenue",
    "total_revenue_stly": "Total Revenue STLY",
    # ADR
    "rental_adr": "Rental ADR",
    "rental_adr_stly": "Rental ADR STLY",
    "adr_index": "ADR Index",
    # "market_adr": "Market ADR",
    # RevPAR
    "rental_revpar": "Rental RevPAR",
    "rental_revpar_stly": "Rental RevPAR STLY",
    "market_revpar": "Market RevPAR",
    "market_revpar_stly": "Market RevPAR STLY",
    "revpar_index": "RevPAR Index",
    # Pricing context
    # "base_price": "Base Price",
    # "recommended_base_price": "Recommended Base Price",
    # "final_price": "Final Price",
    # "market_median_price": "Market Median Price",
    # "market_75th_percentile_price": "Market 75th Percentile Price",
    # Booking dynamics
    "available_nights": "Available Nights",
    "number_of_bookings": "Number of Bookings",
    "avg_booking_window": "Average Booking Window",
    "market_avg_booking_window": "Average Market Booking Window",
    # "booked_nights": "Booked Nights",
    # "blocked_nights": "Blocked Nights",
    # "avg_los": "Average LOS",
    # "booked_nights_pickup_30d": "Booked Nights Pickup (30 Days)",
    # New metrics used in per-listing KPI grid
    "paid_occupancy_pickup_30d": "Paid Occupancy Pickup (30 Days)",
    "market_occupancy_pickup_30d": "Market Occupancy Pickup (30 Days)",
    "rental_revpar_pickup_30d": "Rental RevPAR Pickup (30 Days)",
    "market_revpar_pickup_30d": "Market RevPAR Pickup (30 Days)",
    "bookable_nights": "Bookable Nights",
    "bookable_nights_ly": "Bookable Nights LY",
    "unbookable_revenue_potential": "Unbookable Dates Potential Revenue (Final Price)",
    "median_booking_window": "Median Booking Window",
    # Pickup (for AI timing recs)
    # "occupancy_pickup_30d": "Occupancy Pickup (30 Days)",
    # "occupancy_pickup_stly_30d": "Occupancy Pickup STLY (30 Days)",
    # "revenue_pickup_30d": "Rental Revenue Pickup (30 Days)",
    # "revenue_pickup_stly_30d": "Rental Revenue Pickup STLY (30 Days)",
}

# Fields that are integers
_INT_FIELDS = {
    "available_nights", "number_of_bookings",
    "bookable_nights", "bookable_nights_ly",
}

# Fields that are strings (not cleaned as numbers)
_STR_FIELDS = {"listing_name"}


class DataAnalystAgent:
    """Transforms raw PriceLabs CSV into structured AnalysisResult. No LLM needed."""

    def analyze(self, csv_path: str, month: str = "", year: str = "") -> AnalysisResult:
        if csv_path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(csv_path)
        else:
            try:
                df = pd.read_csv(csv_path, encoding="utf-8-sig")
            except UnicodeDecodeError:
                df = pd.read_csv(csv_path, encoding="latin-1")

        listings = []
        for _, row in df.iterrows():
            kwargs = {}
            for field, col in _COL_MAP.items():
                if col not in df.columns:
                    if field in _STR_FIELDS:
                        kwargs[field] = ""
                    else:
                        kwargs[field] = None
                    continue
                raw = row[col]
                if field in _STR_FIELDS:
                    kwargs[field] = _safe_str(raw)
                elif field in _INT_FIELDS:
                    kwargs[field] = _clean_int(raw)
                else:
                    kwargs[field] = _clean_float(raw)
            listings.append(ListingMetrics(**kwargs))

        # Build report_date from month/year if provided
        if month and year:
            month_num = {
                "january": "01", "february": "02", "march": "03",
                "april": "04", "may": "05", "june": "06",
                "july": "07", "august": "08", "september": "09",
                "october": "10", "november": "11", "december": "12",
            }.get(month.lower(), "01")
            report_date = f"{year}-{month_num}-01"
        else:
            report_date = date.today().isoformat()

        summary = self._compute_summary(listings)
        return AnalysisResult(
            report_date=report_date,
            total_listings=len(listings),
            portfolio_summary=summary,
            listings=listings,
        )

    @staticmethod
    def _compute_summary(listings: list[ListingMetrics]) -> PortfolioSummary:
        def _avg(vals: list[float | None]) -> float:
            clean = [v for v in vals if v is not None]
            return sum(clean) / len(clean) if clean else 0.0

        def _total(vals: list[float | None]) -> float:
            return sum(v for v in vals if v is not None)

        total_rev = _total([l.total_revenue for l in listings])
        total_rev_stly = _total([l.total_revenue_stly for l in listings])
        avg_occ = _avg([l.occupancy_pct for l in listings])
        avg_occ_stly = _avg([l.occupancy_stly for l in listings])
        avg_revpar = _avg([l.rental_revpar for l in listings])
        avg_revpar_stly = _avg([l.rental_revpar_stly for l in listings])
        avg_mpi = _avg([l.market_penetration_index for l in listings])
        avg_adr_idx = _avg([l.adr_index for l in listings])

        scored = [
            (l.listing_name, l.revpar_index if l.revpar_index is not None else 0.0)
            for l in listings
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[0][0] if scored else "N/A"
        bottom = scored[-1][0] if scored else "N/A"

        above = sum(
            1 for l in listings
            if l.revpar_index is not None and l.revpar_index >= 1.0
        )
        below = sum(
            1 for l in listings
            if l.revpar_index is not None and l.revpar_index < 1.0
        )

        return PortfolioSummary(
            total_revenue=total_rev,
            total_revenue_stly=total_rev_stly,
            avg_occupancy=avg_occ,
            avg_occupancy_stly=avg_occ_stly,
            avg_revpar=avg_revpar,
            avg_revpar_stly=avg_revpar_stly,
            avg_market_penetration=avg_mpi,
            avg_adr_index=avg_adr_idx,
            top_performer=top,
            bottom_performer=bottom,
            listings_above_market=above,
            listings_below_market=below,
        )
