"""Step 5 — Assemble the final Markdown desk note."""

import datetime
import warnings

import numpy as np
import pandas as pd

import config


def _signal(today: float, history: pd.Series) -> str:
    """Return ▲/▼/→ based on recent trend (last 5 days vs prior 5 days)."""
    if len(history) < 10:
        return "→"
    recent = history.iloc[-5:].mean()
    prior = history.iloc[-10:-5].mean()
    if prior == 0:
        return "→"
    pct_change = (recent - prior) / abs(prior)
    if pct_change > 0.02:
        return "▲"
    elif pct_change < -0.02:
        return "▼"
    return "→"


def assemble(metrics_dict: dict, narrative: str, chart_paths: list) -> str:
    """
    Assemble the Markdown desk note and save to outputs/desk_note.md.
    Optionally convert to PDF if weasyprint is available.
    Returns path to the output file.
    """
    today = datetime.date.today()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build metrics table
    table_rows = []
    for name, (val, hist) in metrics_dict.items():
        avg_30d = hist.iloc[-30:].mean() if len(hist) >= 30 else hist.mean()
        sig = _signal(val, hist)
        table_rows.append(f"| {name} | {val:+.2f} | {avg_30d:+.2f} | {sig} |")

    metrics_table = "\n".join(table_rows)

    md = f"""# European Cross-Commodity Risk Pack — {today}
**Generated:** {timestamp}

## Monitor metrics
| Metric | Value | 30d Avg | Signal |
|--------|-------|---------|--------|
{metrics_table}

## Charts
![Spread regime](charts/spread_regime.png)
![Gas fundamentals](charts/gas_fundamentals.png)

## Desk note
{narrative}

---
*Generated: {timestamp} | Model: claude-sonnet-4-20250514*
*Prompt log: outputs/logs/prompt_log.jsonl*
"""

    out_path = config.OUTPUT_DIR / "desk_note.md"
    with open(out_path, "w") as f:
        f.write(md)
    print(f"  Desk note saved to {out_path}")

    # Try PDF conversion
    try:
        import weasyprint  # noqa: F401
        pdf_path = config.OUTPUT_DIR / "desk_note.pdf"
        weasyprint.HTML(string=md).write_pdf(str(pdf_path))
        print(f"  PDF saved to {pdf_path}")
    except ImportError:
        warnings.warn("weasyprint not installed — Markdown only, no PDF")
    except Exception as e:
        warnings.warn(f"PDF conversion failed: {e}")

    return str(out_path)
