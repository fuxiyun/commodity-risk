#!/usr/bin/env python3
"""
European Cross-Commodity Risk Pack — single entry point.

Usage:
    python run.py                        # last 90 days
    python run.py --start 2026-01-01 --end 2026-04-01
"""

import argparse
import datetime
import sys

from src.ingest import fetch_all
from src.metrics import compute_all
from src.charts import generate_charts
from src.ai_narrative import generate_narrative
from src.report import assemble


def main():
    parser = argparse.ArgumentParser(description="European Cross-Commodity Risk Pack")
    today = datetime.date.today()
    default_start = (today - datetime.timedelta(days=90)).isoformat()
    default_end = today.isoformat()

    parser.add_argument("--start", default=default_start, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default=default_end, help="End date (YYYY-MM-DD)")
    args = parser.parse_args()

    print(f"═══ European Cross-Commodity Risk Pack ═══")
    print(f"Period: {args.start} → {args.end}\n")

    try:
        # Step 1: Ingest data
        df = fetch_all(args.start, args.end)
        if df.empty:
            print("ERROR: No data fetched. Exiting.", file=sys.stderr)
            sys.exit(1)

        # Step 2: Compute metrics
        print("\nComputing metrics …")
        metrics = compute_all(df)

        # Print metrics summary
        print(f"\n{'Metric':<30s} {'Value':>10s} {'30d Avg':>10s}")
        print("─" * 52)
        for name, (val, hist) in metrics.items():
            avg = hist.iloc[-30:].mean() if len(hist) >= 30 else hist.mean()
            print(f"{name:<30s} {val:>+10.2f} {avg:>+10.2f}")
        print()

        # Step 3: Generate charts
        chart_paths = generate_charts(metrics, df)

        # Step 4: Generate AI narrative
        print("\nGenerating AI narrative …")
        narrative = generate_narrative(metrics, chart_paths)

        # Step 5: Assemble report
        print("\nAssembling report …")
        report_path = assemble(metrics, narrative, chart_paths)

        print(f"\n═══ Done ═══")
        print(f"Desk note: {report_path}")
        print(f"Charts:    {', '.join(chart_paths)}")
        print(f"Logs:      outputs/logs/prompt_log.jsonl")

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
