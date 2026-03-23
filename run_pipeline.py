#!/usr/bin/env python3
"""CLI entry point for running the AI analysis pipeline."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Enrich Revenue Management — AI Analysis Pipeline"
    )
    parser.add_argument("--client", required=True, help="Client identifier")
    parser.add_argument("--csv", required=True, help="Path to CSV file")
    parser.add_argument("--title", default="Monthly Revenue Report", help="Report title")
    parser.add_argument("--month", required=True, help="Report month")
    parser.add_argument("--year", required=True, help="Report year")
    parser.add_argument("--logo", default=None, help="Path to logo image")
    parser.add_argument(
        "--color", default="#d4cfcf", help="Brand color hex (default: #d4cfcf)"
    )
    args = parser.parse_args()

    if not os.path.exists(args.csv):
        print(f"Error: CSV file not found: {args.csv}")
        sys.exit(1)

    from orchestrator import run_single

    def status_update(msg: str):
        print(f"  → {msg}")

    print(f"\nEnrich AI Analysis Pipeline")
    print(f"Client: {args.client}")
    print(f"CSV: {args.csv}")
    print(f"Report: {args.title} — {args.month} {args.year}\n")

    result = run_single(
        csv_path=args.csv,
        report_title=args.title,
        month=args.month,
        year=args.year,
        logo_path=args.logo,
        brand_color=args.color,
        on_status=status_update,
    )

    # Save PDF
    report_dir = Path(f"data/reports/{args.client}")
    report_dir.mkdir(parents=True, exist_ok=True)
    date_key = result.analysis.report_date[:7]
    pdf_path = report_dir / f"{date_key}.pdf"
    pdf_path.write_bytes(result.pdf_bytes)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Pipeline Complete")
    print(f"{'='*60}")
    print(f"PDF saved to: {pdf_path}")
    print(f"Listings analyzed: {result.analysis.total_listings}")
    print(f"Anomalies found: {len(result.anomaly_report.anomalies)}")
    print(f"Recommendations: {len(result.rec_report.recommendations)}")


if __name__ == "__main__":
    main()
