"""ReportComposerAgent — LLM narratives + FPDF2 PDF assembly."""

from __future__ import annotations

import math

from fpdf import FPDF

from models.schemas import (
    AnalysisResult,
    AnomalyReport,
    RecommendationReport,
    ReportContent,
)
from agents.llm_client import call, SONNET

SYSTEM_PROMPT = """\
You are a professional report writer for a short-term rental revenue \
management company called Enrich Revenue Management. Write clear, concise, \
data-driven narratives for a monthly performance report.

Guidelines:
- Executive summary: 4-6 sentences covering overall portfolio health, \
aggregate trends, and key takeaways
- Per-listing narratives: 2-3 sentences each, referencing specific metrics
- Anomaly summary: 1 paragraph summarizing key issues
- Recommendations summary: 1 paragraph summarizing top priorities
- Use professional but accessible language
- Reference specific numbers from the data

Return your response as a JSON object matching the provided schema."""


def _sanitize(text: str) -> str:
    """Replace Unicode characters unsupported by FPDF's built-in fonts."""
    replacements = {
        "\u2014": "--",   # em dash
        "\u2013": "-",    # en dash
        "\u2018": "'",    # left single quote
        "\u2019": "'",    # right single quote
        "\u201c": '"',    # left double quote
        "\u201d": '"',    # right double quote
        "\u2026": "...",  # ellipsis
        "\u2022": "*",    # bullet
        "\u00a0": " ",    # non-breaking space
        "\u2010": "-",    # hyphen
        "\u2011": "-",    # non-breaking hyphen
        "\u2012": "-",    # figure dash
        "\u00b7": "*",    # middle dot
        "\u2032": "'",    # prime
        "\u2033": '"',    # double prime
        "\u00ab": '"',    # left guillemet
        "\u00bb": '"',    # right guillemet
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    # Fallback: replace any remaining non-latin1 characters
    return text.encode("latin-1", errors="replace").decode("latin-1")


class ReportComposerAgent:
    """Generates narrative content via LLM and assembles the final PDF."""

    def compose(
        self,
        analysis: AnalysisResult,
        anomaly_report: AnomalyReport,
        rec_report: RecommendationReport,
        report_title: str,
        month: str,
        year: str,
        logo_path: str | None = None,
        brand_color: str = "#d4cfcf",
    ) -> tuple[ReportContent, bytes]:
        # Skip LLM narratives — use empty placeholders
        content = ReportContent(
            executive_summary="",
            listing_narratives=[],
            anomaly_summary="",
            recommendations_summary="",
        )
        pdf_bytes = self._build_pdf(
            content, analysis, anomaly_report, rec_report,
            report_title, month, year, logo_path, brand_color,
        )
        return content, pdf_bytes

    @staticmethod
    def _generate_narratives(
        analysis: AnalysisResult,
        anomaly_report: AnomalyReport,
        rec_report: RecommendationReport,
    ) -> ReportContent:
        listings_brief = [
            {
                "name": l.listing_name,
                "occupancy": l.occupancy_pct,
                "occupancy_stly": l.occupancy_stly,
                "revenue": l.total_revenue,
                "revenue_stly": l.total_revenue_stly,
                "revpar_index": l.revpar_index,
                "adr_index": l.adr_index,
                "mpi": l.market_penetration_index,
            }
            for l in analysis.listings
        ]
        user_msg = (
            f"Portfolio Summary:\n{analysis.portfolio_summary.model_dump()}\n\n"
            f"Listings:\n{listings_brief}\n\n"
            f"Anomalies ({len(anomaly_report.anomalies)} found):\n"
            f"{anomaly_report.summary}\n\n"
            f"Recommendations ({len(rec_report.recommendations)}):\n"
            f"{rec_report.summary}\n\n"
            f"Listing names for per-listing narratives: "
            f"{[l.listing_name for l in analysis.listings]}\n\n"
            "Generate all narrative sections for the report."
        )
        return call(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_msg,
            model=SONNET,
            output_schema=ReportContent,
            max_tokens=8192,
        )

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        h = hex_color.lstrip("#")
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))

    def _build_pdf(
        self,
        content: ReportContent,
        analysis: AnalysisResult,
        anomaly_report: AnomalyReport,
        rec_report: RecommendationReport,
        report_title: str,
        month: str,
        year: str,
        logo_path: str | None,
        brand_color: str,
    ) -> bytes:
        pdf = FPDF(orientation="L")
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_left_margin(15)
        r, g, b = self._hex_to_rgb(brand_color)
        CONTENT_TOP = 55  # Y position where content starts (below 35mm header + margin)

        def _header(title_text: str = ""):
            pdf.set_fill_color(r, g, b)
            pdf.rect(0, 0, 297, 30, style="F")
            pdf.set_font("Arial", "B", 24)
            pdf.set_text_color(0, 0, 0)
            pdf.set_xy(15, 8)
            pdf.cell(267, 20, txt=_sanitize(f"{month} {year} - {report_title}"), align="C")
            if logo_path:
                pdf.image(logo_path, x=15, y=8, w=50)
            if title_text:
                pdf.set_xy(5, 33)
                pdf.set_font("Arial", "B", 14)
                pdf.cell(267, 10, txt=_sanitize(title_text))

        # # Page 1: Executive Summary + Portfolio KPIs
        # pdf.add_page()
        # _header("Executive Summary")
        # pdf.set_xy(15, CONTENT_TOP)
        # pdf.set_font("Arial", "", 10)
        # pdf.set_text_color(0, 0, 0)
        # pdf.multi_cell(267, 5, _sanitize(content.executive_summary))

        # # KPIs below the summary text
        # ps = analysis.portfolio_summary
        # kpis = [
        #     ("Total Revenue", f"${ps.total_revenue:,.0f}"),
        #     ("Revenue STLY", f"${ps.total_revenue_stly:,.0f}"),
        #     ("Avg Occupancy", f"{ps.avg_occupancy:.1%}"),
        #     ("Avg Occupancy STLY", f"{ps.avg_occupancy_stly:.1%}"),
        #     ("Avg RevPAR", f"${ps.avg_revpar:,.2f}"),
        #     ("Avg ADR Index", f"{ps.avg_adr_index:.2f}"),
        #     ("Avg Market Penetration", f"{ps.avg_market_penetration:.1%}"),
        #     ("Above Market", str(ps.listings_above_market)),
        #     ("Below Market", str(ps.listings_below_market)),
        # ]
        # col_x = 15
        # cell_w = 42  # each cell width (label + value = 84 per column)
        # pair_w = cell_w * 2  # 84mm per label+value pair
        # total_pairs_w = pair_w * 3  # 204mm for all pairs
        # gap = (267 - total_pairs_w) / 2  # distribute remaining space as gaps
        # col_spacing = pair_w + gap
        # row_y = min(pdf.get_y() + 4, 130)
        # for i, (label, value) in enumerate(kpis):
        #     x = col_x + (i % 3) * col_spacing
        #     y = row_y + (i // 3) * 18
        #     pdf.set_xy(x, y)
        #     pdf.set_font("Arial", "B", 10)
        #     pdf.cell(cell_w, 8, label, border=1, align="C")
        #     pdf.set_font("Arial", "", 10)
        #     pdf.cell(cell_w, 8, _sanitize(value), border=1, align="C")

        # # Top/Bottom performer in full-width rows below the grid
        # num_kpi_rows = (len(kpis) + 2) // 3
        # perf_y = row_y + num_kpi_rows * 18
        # kpi_total_width = 267  # match text width
        # for j, (label, value) in enumerate([
        #     ("Top Performer", ps.top_performer),
        #     ("Bottom Performer", ps.bottom_performer),
        # ]):
        #     y = perf_y + j * 18
        #     pdf.set_xy(col_x, y)
        #     pdf.set_font("Arial", "B", 10)
        #     pdf.cell(60, 8, label, border=1, align="C")
        #     pdf.set_font("Arial", "", 10)
        #     val_width = kpi_total_width - 60
        #     pdf.cell(val_width, 8, _sanitize(f"   {value}"), border=1, align="L")

        # Market Performance pages (Revenue + Occupancy) — native FPDF drawing
        market_data = []
        for l in analysis.listings:
            revpar_idx = l.revpar_index if l.revpar_index is not None else 0.0
            revpar_idx_stly = (
                l.rental_revpar_stly / l.market_revpar
                if l.rental_revpar_stly and l.market_revpar and l.market_revpar > 0
                else 0.0
            )
            mpi = l.market_penetration_index if l.market_penetration_index is not None else 0.0
            mpi_stly = (
                l.occupancy_stly / l.market_occupancy_pct
                if l.occupancy_stly and l.market_occupancy_pct and l.market_occupancy_pct > 0
                else 0.0
            )
            market_data.append({
                "name": l.listing_name,
                "revpar_idx": revpar_idx,
                "revpar_idx_stly": revpar_idx_stly,
                "mpi": mpi,
                "mpi_stly": mpi_stly,
            })

        def _draw_metric_table(entries, curr_key, stly_key, title, description):
            """Draw a listing_metric_table-style chart using native FPDF primitives."""
            rows = [e for e in entries if e[curr_key] != 0.0 or e[stly_key] != 0.0]
            rows.sort(key=lambda e: e[curr_key], reverse=True)
            if not rows:
                return

            max_per_page = 12

            # Compute min/max across all non-zero values for this metric
            non_zero_vals = [
                e[k] for e in rows for k in (curr_key, stly_key) if e[k] != 0.0
            ]
            val_max = max(non_zero_vals) if non_zero_vals else 1.5
            val_min = min(non_zero_vals) if non_zero_vals else 0.5
            # Ensure baseline (1.0) is always in range
            val_max = max(val_max, 1.0)
            val_min = min(val_min, 1.0)

            def _draw_page(page_rows, is_continued=False):
                pdf.add_page()
                suffix = " (continued)" if is_continued else ""
                _header(_sanitize(title + suffix))

                pdf.set_xy(15, CONTENT_TOP - 5)
                pdf.set_font("Arial", "", 8)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(267, 4, _sanitize(description), ln=True)
                pdf.set_text_color(0, 0, 0)

                name_col_w = 80
                bar_area_x = 145
                bar_area_w = 135
                base_val = 1.0
                start_y = pdf.get_y() + 1
                available_h = 195 - start_y
                row_h = max(10, min(22, available_h / len(page_rows)))
                bar_h = min(4, (row_h - 6) / 2)

                label_margin = 7  # space reserved for value labels
                usable_w = bar_area_w - 2 * label_margin  # reserve on both sides
                val_range = val_max - val_min
                if val_range == 0:
                    val_range = 1.0
                scale = usable_w / val_range
                # Position baseline within the bar area proportionally
                base_x = bar_area_x + label_margin + (base_val - val_min) * scale

                for i, entry in enumerate(page_rows):
                    y = start_y + i * row_h

                    if i % 2 == 0:
                        pdf.set_fill_color(230, 240, 250)
                        pdf.rect(15, y - 2, 270, row_h, style="F")

                    pdf.set_xy(15, y + (row_h - 5) / 2)
                    pdf.set_font("Arial", "", 9)
                    pdf.set_text_color(0, 0, 0)
                    name = _sanitize(entry["name"])
                    if len(name) > 70:
                        name = name[:68] + "..."
                    pdf.cell(name_col_w, 5, name)

                    for j, (key, label) in enumerate([(curr_key, "Current"), (stly_key, "STLY")]):
                        val = entry[key]
                        total_bars_h = 2 * bar_h  # no gap between bars
                        bar_y = y + (row_h - total_bars_h) / 2 + j * bar_h

                        # Period label (Current / STLY)
                        pdf.set_font("Arial", "", 7)
                        pdf.set_xy(bar_area_x - 18, bar_y)
                        pdf.cell(16, bar_h, label, align="R")

                        # Skip bar + value for no-data entries
                        if val == 0.0:
                            pdf.set_fill_color(200, 200, 200)
                            pdf.rect(base_x - 2, bar_y, 2, bar_h, style="F")
                            pdf.set_font("Arial", "", 7)
                            pdf.set_xy(base_x - 16, bar_y)
                            pdf.cell(12, bar_h, "N/A", align="R")
                            continue

                        if val >= base_val:
                            pdf.set_fill_color(180, 230, 180)
                        else:
                            pdf.set_fill_color(255, 200, 200)

                        bar_len = (val - base_val) * scale
                        if bar_len >= 0:
                            pdf.rect(base_x, bar_y, bar_len, bar_h, style="F")
                        else:
                            pdf.rect(base_x + bar_len, bar_y, abs(bar_len), bar_h, style="F")

                        pdf.set_font("Arial", "", 7)
                        val_str = f"{val:.2f}"
                        bar_end = base_x + bar_len
                        if bar_len >= 0:
                            pdf.set_xy(bar_end + 1, bar_y)
                            pdf.cell(12, bar_h, val_str, align="L")
                        else:
                            pdf.set_xy(bar_end - 13, bar_y)
                            pdf.cell(12, bar_h, val_str, align="R")

                total_h = len(page_rows) * row_h
                pdf.set_draw_color(0, 0, 0)
                pdf.dashed_line(base_x, start_y - 2, base_x, start_y + total_h, dash_length=1, space_length=1)
                pdf.set_font("Arial", "", 7)
                pdf.set_xy(base_x - 5, start_y - 6)
                pdf.cell(10, 4, "1.00", align="C")

            for chunk_start in range(0, len(rows), max_per_page):
                chunk = rows[chunk_start : chunk_start + max_per_page]
                _draw_page(chunk, is_continued=(chunk_start > 0))

        _draw_metric_table(market_data, "revpar_idx", "revpar_idx_stly",
            "Revenue vs. Market Performance",
            "Revenue of Listing compared to Market. 1.00 is market average. Comparing same time last year (STLY) performance.")
        _draw_metric_table(market_data, "mpi", "mpi_stly",
            "Occupancy vs. Market Performance",
            "Occupancy of Listing compared to Market. 1.00 is market average. Comparing same time last year (STLY) performance.")

        # Per-listing pages
        def _draw_comparison_bar(title, left_label, left_val, right_label, right_val,
                                  x, y, w, h, is_pct=False):
            """Draw a side-by-side comparison bar chart using native FPDF."""
            # Background frame
            pdf.set_fill_color(220, 220, 220)
            pdf.rect(x - 1, y - 1, w + 2, h + 2, style="F")

            # Title
            pdf.set_font("Arial", "B", 7)
            pdf.set_text_color(0, 0, 0)
            pdf.set_xy(x, y)
            pdf.cell(w, 4, _sanitize(title), align="C")

            chart_y = y + 5
            chart_h = h - 9  # remaining height for bars + labels
            bar_w = w * 0.3
            gap = w * 0.1

            max_val = max(abs(left_val), abs(right_val), 0.01)
            l_bar_h = (left_val / max_val) * chart_h if max_val else 0
            r_bar_h = (right_val / max_val) * chart_h if max_val else 0

            baseline_y = chart_y + chart_h
            l_x = x + (w / 2) - bar_w - (gap / 2)
            r_x = x + (w / 2) + (gap / 2)

            # Left bar
            pdf.set_fill_color(r, g, b)
            pdf.rect(l_x, baseline_y - l_bar_h, bar_w, l_bar_h, style="F")
            # Right bar
            pdf.set_fill_color(50, 50, 50)
            pdf.rect(r_x, baseline_y - r_bar_h, bar_w, r_bar_h, style="F")

            # Value labels inside bars
            pdf.set_font("Arial", "", 7)
            if is_pct:
                l_str = f"{left_val:.0f}%" if left_val else "0%"
                r_str = f"{right_val:.0f}%" if right_val else "0%"
            else:
                l_str = f"${left_val:,.0f}" if left_val else "$0"
                r_str = f"${right_val:,.0f}" if right_val else "$0"
            pdf.set_text_color(0, 0, 0)
            pdf.set_xy(l_x, baseline_y - l_bar_h + 1)
            pdf.cell(bar_w, 4, l_str, align="C")
            pdf.set_text_color(255, 255, 255)
            pdf.set_xy(r_x, baseline_y - r_bar_h + 1)
            pdf.cell(bar_w, 4, r_str, align="C")
            pdf.set_text_color(0, 0, 0)

            # Data labels underneath bars
            pdf.set_font("Arial", "", 6)
            pdf.set_xy(l_x, baseline_y + 1)
            pdf.cell(bar_w, 3, left_label, align="C")
            pdf.set_xy(r_x, baseline_y + 1)
            pdf.cell(bar_w, 3, right_label, align="C")

        for i, listing in enumerate(analysis.listings):
            pdf.add_page()
            _header(_sanitize(listing.listing_name))

            # 4 comparison charts in a row — matches KPI width (15 to 282)
            chart_w = 63
            chart_h = 45
            chart_y = CONTENT_TOP
            chart_x_start = 15
            chart_spacing = (267 - 4 * chart_w) / 3

            charts = [
                ("Paid Occupancy", "Current",
                 (listing.paid_occupancy_pct or 0) * 100,
                 "STLY",
                 (listing.paid_occupancy_stly or 0) * 100,
                 True),
                ("Market Occupancy vs Last Year", "Current",
                 (listing.market_occupancy_pct or 0) * 100,
                 "STLY",
                 (listing.market_occupancy_stly or 0) * 100,
                 True),
                ("Rental Revenue", "Current",
                 listing.rental_revenue or 0,
                 "STLY",
                 listing.rental_revenue_stly or 0,
                 False),
                ("RevPAR", "Current",
                 listing.rental_revpar or 0,
                 "Market",
                 listing.market_revpar or 0,
                 False),
            ]
            for ci, (title, l_label, l_val, r_label, r_val, is_pct) in enumerate(charts):
                cx = chart_x_start + ci * (chart_w + chart_spacing)
                _draw_comparison_bar(title, l_label, l_val, r_label, r_val,
                                     cx, chart_y, chart_w, chart_h, is_pct)

            # KPI boxes below charts
            kpi_y = chart_y + chart_h + 10

            def _fmt_pct(v):
                return f"{v:.1%}" if v is not None and v != 0 else "N/A"

            def _fmt_dollars(v):
                return f"${v:,.0f}" if v is not None and v != 0 else "N/A"

            def _fmt_num(v, digits=0):
                if v is None:
                    return "N/A"
                return f"{v:,.{digits}f}"

            def _fmt_idx(v):
                return f"{v:.2f}" if v is not None and v != 0 else "N/A"

            # Compute derived STLY indexes
            mpi = listing.market_penetration_index
            mpi_stly = None
            if listing.paid_occupancy_stly and listing.market_occupancy_stly and listing.market_occupancy_stly > 0:
                mpi_stly = listing.paid_occupancy_stly / listing.market_occupancy_stly

            revpar_idx = listing.revpar_index
            revpar_idx_stly = None
            if listing.rental_revpar_stly and listing.market_revpar_stly and listing.market_revpar_stly > 0:
                revpar_idx_stly = listing.rental_revpar_stly / listing.market_revpar_stly

            # 12 KPIs: (label, current_label, current_val, stly_label, stly_val)
            # stly_label/stly_val None means single-value KPI
            kpis = [
                ("Paid Occupancy", "Current", _fmt_pct(listing.paid_occupancy_pct),
                 "STLY", _fmt_pct(listing.paid_occupancy_stly)),
                ("Rental Revenue", "Current", _fmt_dollars(listing.rental_revenue),
                 "STLY", _fmt_dollars(listing.rental_revenue_stly)),
                ("Number of Bookings", None, _fmt_num(listing.number_of_bookings),
                 None, None),
                ("Occupancy vs Market (MPI)", "Current", _fmt_idx(mpi),
                 "STLY", _fmt_idx(mpi_stly)),
                ("Revenue vs Market (RevPAR Idx)", "Current", _fmt_idx(revpar_idx),
                 "STLY", _fmt_idx(revpar_idx_stly)),
                ("Occupancy Pickup vs Market", "Listing", _fmt_pct(listing.paid_occupancy_pickup_30d),
                 "Market", _fmt_pct(listing.market_occupancy_pickup_30d)),
                ("Market Occupancy", "Current", _fmt_pct(listing.market_occupancy_pct),
                 "STLY", _fmt_pct(listing.market_occupancy_stly)),
                ("Average Daily Rate", "Current", _fmt_dollars(listing.rental_adr),
                 "STLY", _fmt_dollars(listing.rental_adr_stly)),
                ("Rental Revenue Pickup vs Market", "Listing", _fmt_dollars(listing.rental_revpar_pickup_30d),
                 "Market", _fmt_dollars(listing.market_revpar_pickup_30d)),
                ("Bookable Nights", "Current", _fmt_num(listing.bookable_nights),
                 "STLY", _fmt_num(listing.bookable_nights_ly)),
                ("Blocked Nights Potential", None, _fmt_dollars(listing.unbookable_revenue_potential),
                 None, None),
                ("Booking Window vs Market", "Listing", _fmt_num(listing.median_booking_window, 1),
                 "Market", _fmt_num(listing.market_avg_booking_window, 1)),
            ]

            # Layout: 3 columns × 4 rows, each cell has label bar + value bar(s)
            cols = 3
            cell_w = 89
            col_gap = (267 - cols * cell_w) / (cols - 1)
            label_h = 6
            value_h = 12
            cell_h = label_h + value_h
            row_gap = 0

            for j, (label, left_lbl, left_val, right_lbl, right_val) in enumerate(kpis):
                col = j % cols
                row = j // cols
                cx = 15 + col * (cell_w + col_gap)
                cy = kpi_y + row * (cell_h + row_gap)

                # Label bar (top)
                pdf.set_xy(cx, cy)
                pdf.set_font("Arial", "B", 9)
                pdf.cell(cell_w, label_h, _sanitize(label), border=1, align="C")

                # Value bar (bottom) — single or dual
                pdf.set_xy(cx, cy + label_h)
                if right_val is None:
                    # Single value
                    pdf.set_font("Arial", "", 12)
                    if left_val == "N/A":
                        pdf.set_text_color(180, 180, 180)
                    else:
                        pdf.set_text_color(0, 0, 0)
                    pdf.cell(cell_w, value_h, _sanitize(left_val), border=1, align="C")
                    pdf.set_text_color(0, 0, 0)
                else:
                    # Dual value: split in half
                    half_w = cell_w / 2
                    pdf.set_font("Arial", "", 7)
                    pdf.set_text_color(0, 0, 0)
                    # Left sub-label (small) + value
                    pdf.cell(half_w, value_h / 2, _sanitize(left_lbl), border="LT", align="C")
                    pdf.set_xy(cx + half_w, cy + label_h)
                    pdf.cell(half_w, value_h / 2, _sanitize(right_lbl), border="TR", align="C")
                    # Values row
                    pdf.set_xy(cx, cy + label_h + value_h / 2)
                    pdf.set_font("Arial", "", 10)
                    if left_val == "N/A":
                        pdf.set_text_color(180, 180, 180)
                    else:
                        pdf.set_text_color(0, 0, 0)
                    pdf.cell(half_w, value_h / 2, _sanitize(left_val), border="LB", align="C")
                    pdf.set_xy(cx + half_w, cy + label_h + value_h / 2)
                    if right_val == "N/A":
                        pdf.set_text_color(180, 180, 180)
                    else:
                        pdf.set_text_color(0, 0, 0)
                    pdf.cell(half_w, value_h / 2, _sanitize(right_val), border="RB", align="C")
                    pdf.set_text_color(0, 0, 0)

            num_kpi_rows = (len(kpis) + cols - 1) // cols

            # Listing narrative
            if i < len(content.listing_narratives):
                narr = content.listing_narratives[i]
                ny = kpi_y + num_kpi_rows * (cell_h + row_gap) + 2
                pdf.set_xy(15, ny)
                pdf.set_font("Arial", "", 11)
                pdf.multi_cell(267, 6, _sanitize(narr.content))

        # Anomalies page
        if anomaly_report.anomalies:
            pdf.add_page()
            _header("Anomalies Detected")
            pdf.set_xy(15, CONTENT_TOP)
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(267, 6, _sanitize(content.anomaly_summary))
            pdf.ln(5)

            # Table header
            pdf.set_font("Arial", "B", 9)
            col_widths = [60, 45, 30, 30, 25, 77]
            headers = ["Listing", "Metric", "Current", "Benchmark", "Severity", "Explanation"]
            for w, h in zip(col_widths, headers):
                pdf.cell(w, 8, h, border=1, align="C")
            pdf.ln()

            pdf.set_font("Arial", "", 8)
            for a in anomaly_report.anomalies:
                sev_colors = {"high": (255, 200, 200), "medium": (255, 235, 200), "low": (255, 255, 200)}
                sr, sg, sb = sev_colors.get(a.severity, (255, 255, 255))
                x_start = pdf.get_x()
                y_start = pdf.get_y()
                if y_start > 180:
                    pdf.add_page()
                    _header("Anomalies (continued)")
                    pdf.set_xy(15, CONTENT_TOP)
                    pdf.set_font("Arial", "", 8)
                vals = [
                    _sanitize(a.listing_name[:25]),
                    _sanitize(a.metric),
                    f"{a.current_value:.2f}",
                    f"{a.comparison_value:.2f}",
                    a.severity.upper(),
                    _sanitize(a.explanation[:45] + "..." if len(a.explanation) > 45 else a.explanation),
                ]
                for w, v in zip(col_widths, vals):
                    if v == a.severity.upper():
                        pdf.set_fill_color(sr, sg, sb)
                        pdf.cell(w, 7, v, border=1, align="C", fill=True)
                    else:
                        pdf.cell(w, 7, v, border=1, align="C")
                pdf.ln()

        # Recommendations page
        if rec_report.recommendations:
            pdf.add_page()
            _header("Recommendations")
            pdf.set_xy(15, CONTENT_TOP)
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(267, 6, _sanitize(content.recommendations_summary))
            pdf.ln(5)

            # Sort by priority
            priority_order = {"high": 0, "medium": 1, "low": 2}
            sorted_recs = sorted(
                rec_report.recommendations,
                key=lambda x: priority_order.get(x.priority, 3),
            )
            for rec in sorted_recs:
                # Estimate height needed for this recommendation
                pdf.set_font("Arial", "", 9)
                rationale_text = _sanitize(f"Rationale: {rec.rationale}")
                impact_text = _sanitize(f"Expected Impact: {rec.expected_impact} | Confidence: {rec.confidence}")
                action_text = _sanitize(f"Action: {rec.action}")
                chars_per_line = 85
                action_lines = max(1, math.ceil(len(action_text) / chars_per_line))
                rationale_lines = max(1, math.ceil(len(rationale_text) / chars_per_line))
                impact_lines = max(1, math.ceil(len(impact_text) / chars_per_line))
                est_height = 7 + (action_lines * 6) + (rationale_lines * 5) + (impact_lines * 5) + 3

                y = pdf.get_y()
                if y + est_height > 195:
                    pdf.add_page()
                    _header("Recommendations (continued)")
                    pdf.set_xy(15, CONTENT_TOP)
                pri_colors = {"high": (220, 50, 50), "medium": (220, 150, 50), "low": (100, 150, 100)}
                pr, pg_, pb = pri_colors.get(rec.priority, (0, 0, 0))
                pdf.set_text_color(pr, pg_, pb)
                pdf.set_font("Arial", "B", 10)
                pdf.cell(267, 7, _sanitize(f"[{rec.priority.upper()}] {rec.listing_name}"), ln=True)
                pdf.set_text_color(0, 0, 0)
                pdf.set_font("Arial", "B", 9)
                pdf.multi_cell(267, 6, _sanitize(f"Action: {rec.action}"))
                pdf.set_x(15)
                pdf.set_font("Arial", "", 9)
                pdf.multi_cell(267, 5, _sanitize(f"Rationale: {rec.rationale}"))
                pdf.set_x(15)
                pdf.set_font("Arial", "I", 9)
                pdf.multi_cell(267, 5, _sanitize(f"Expected Impact: {rec.expected_impact} | Confidence: {rec.confidence}"))
                pdf.ln(3)

        return bytes(pdf.output())
