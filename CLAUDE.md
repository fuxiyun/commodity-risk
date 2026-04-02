# CLAUDE.md — European Cross-Commodity Risk Pack

## Project overview
Build an automated daily monitor that ingests public gas and carbon data,
computes 6 desk-relevant metrics, generates two charts, and uses the
Claude API to produce a structured trading narrative. Output: one PDF/
Markdown desk note + all supporting code.

## Repo layout to create
```
risk_pack/
├── CLAUDE.md               ← this file
├── requirements.txt
├── config.py               ← API keys, date range, output paths
├── data/
│   └── raw/                ← downloaded CSVs land here
├── src/
│   ├── ingest.py           ← Step 1: pull public data
│   ├── metrics.py          ← Step 2: compute the 6 metrics
│   ├── charts.py           ← Step 3: generate two matplotlib charts
│   ├── ai_narrative.py     ← Step 4: Claude API call + prompt log
│   └── report.py           ← Step 5: assemble PDF/Markdown output
├── outputs/
│   ├── charts/
│   ├── logs/               ← prompt_log.jsonl goes here
│   └── desk_note.md (or .pdf)
└── run.py                  ← single entry point: python run.py
```

---

## Step 1 — Implement `src/ingest.py`

Pull the following public datasets. All sources are free and require no
paid subscription. Save each as a dated CSV under `data/raw/`.

| Dataset | Source | Notes |
|---|---|---|
| TTF front-month settle | Yahoo Finance `TTF=F` via `yfinance` | Daily OHLCV |
| EU ETS EUA Dec front | Yahoo Finance `CO2.L` or Quandl `CHRIS/ICE_M1` | Daily settle |
| German power DA price | SMARD API (bundesnetzagentur.de) | Hourly, aggregate to daily avg |
| European gas storage fill % | GIE AGSI+ REST API (api.gie.eu) | Aggregate EU total |
| NBP day-ahead gas | Yahoo Finance `NBP=F` or Quandl | Daily settle |

Use `yfinance`, `requests`, and `pandas`. Implement a `fetch_all(start, end)`
function that returns a single merged daily DataFrame indexed by date.
Cache results to avoid re-downloading on reruns. Handle missing values with
forward-fill (max 2 days) and flag any gap > 2 days with a warning.

---

## Step 2 — Implement `src/metrics.py`

Compute exactly these 6 metrics from the merged DataFrame. Each function
should return a float for "today" and a pandas Series for the trailing
60-day history (needed for charts).
```python
def clean_dark_spread(df):
    """
    CDS = Power_DA - (Gas_TTF * heat_rate) - (EUA * emission_factor)
    heat_rate = 2.0 MWh_gas / MWh_power (typical hard-coal CCGT proxy)
    emission_factor = 0.34 tCO2 / MWh_power (CCGT)
    Unit: EUR/MWh. Positive = coal/gas generation profitable.
    Trading relevance: primary signal for baseload power curve level.
    """

def clean_spark_spread(df):
    """
    CSS = Power_DA - (Gas_TTF * gas_heat_rate) - (EUA * 0.2)
    gas_heat_rate = 1.5 (CCGT gas efficiency proxy)
    emission_factor = 0.20 tCO2/MWh for gas
    Unit: EUR/MWh. Positive = gas generation profitable.
    Trading relevance: gas-to-power switching threshold.
    """

def ttf_30d_rolling_zscore(df):
    """
    Z-score of TTF front-month vs its 30-day rolling mean/std.
    Trading relevance: flags whether gas is unusually tight or loose.
    """

def eua_ttf_ratio(df):
    """
    EUA (EUR/tCO2) / TTF (EUR/MWh). 
    Normalises carbon cost relative to gas cost.
    Trading relevance: high ratio = carbon dominates marginal cost,
    shifts merit order toward gas over coal.
    """

def storage_fill_vs_5yr_avg(df):
    """
    Current EU gas storage fill % minus the 5-year seasonal average
    for the same calendar week.
    Trading relevance: deficit = upside risk for winter gas/power.
    """

def implied_srmc(df):
    """
    Short-run marginal cost of the price-setting unit.
    SRMC_gas  = Gas_TTF * 1.5 + EUA * 0.20   (gas CCGT)
    SRMC_coal = Coal_proxy * 2.0 + EUA * 0.34 (hard coal — use a
                fixed coal price or NBP as a proxy if coal unavailable)
    Return both; the lower one is the current marginal unit.
    Trading relevance: power DA should track SRMC of marginal plant.
    """
```

Export a `compute_all(df)` function that returns a dict of
`{metric_name: (today_value, history_series)}`.

---

## Step 3 — Implement `src/charts.py`

Generate exactly two charts saved as PNG to `outputs/charts/`.

**Chart 1 — Spread regime chart**
- Twin-axis time series over the trailing 60 days
- Left axis: Clean Dark Spread (EUR/MWh) — solid line, color #D85A30
- Right axis: EUA front-month settle (EUR/tCO2) — dashed line, color #178ADD
- Horizontal zero line on left axis
- Title: "Clean dark spread vs EUA — 60d"
- Mark today's value for each series with a dot + annotation
- Save as `outputs/charts/spread_regime.png`

**Chart 2 — Gas tightness dashboard**
- Two subplots stacked vertically, shared x-axis, trailing 60 days
- Top subplot: TTF front-month + 30-day rolling mean, with ±1σ band shaded
- Bottom subplot: EU storage fill % with the 5-year seasonal average
  as a dashed reference line
- Title: "Gas fundamentals — TTF & storage"
- Save as `outputs/charts/gas_fundamentals.png`

Use `matplotlib` with `rcParams` set for a clean, publication-style look
(no gridlines on top/right spines, muted background, 150 dpi).

---

## Step 4 — Implement `src/ai_narrative.py`

Call the Anthropic Claude API to generate a structured desk narrative.
Log every prompt and response to `outputs/logs/prompt_log.jsonl`.
```python
import anthropic, json, datetime

def generate_narrative(metrics_dict: dict, chart_paths: list) -> str:
    """
    Build a structured prompt from today's metric values.
    Call claude-sonnet-4-20250514.
    Return the narrative string.
    Log prompt + response to JSONL.
    """
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    # --- Build the metrics block ---
    metrics_text = "\n".join([
        f"- {name}: {vals[0]:.2f}" 
        for name, vals in metrics_dict.items()
    ])

    system_prompt = """You are a senior European power and gas trader writing
a morning desk note. You are precise, direct, and quantitative. You do not
pad with caveats. You write in present tense. You never say 'it is important
to note'. You always anchor observations to specific numbers."""

    user_prompt = f"""Today's cross-commodity metrics ({datetime.date.today()}):

{metrics_text}

Write a desk note with the following sections:
1. **Gas tightness** (3–5 sentences): interpret the TTF z-score and storage
   deficit/surplus. Is gas tight or loose? What does this imply for winter
   risk premium?
2. **Carbon signal** (2–4 sentences): interpret the EUA level and EUA/TTF
   ratio. Is carbon adding to or subtracting from marginal cost pressure?
3. **Power curve implications** (4–6 sentences): given the CDS, CSS, and
   SRMC, which fuel is at the margin? Is the dark spread positive or
   negative — what does this say about Cal+1 baseload direction?
4. **Key risk** (1–2 sentences): state the single biggest risk to the
   current view (upside or downside).

Keep total length under 350 words. Use numbers throughout."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        messages=[{"role": "user", "content": user_prompt}],
        system=system_prompt,
    )

    narrative = response.content[0].text

    # --- Log prompt and output ---
    log_entry = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "model": "claude-sonnet-4-20250514",
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "response": narrative,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
    with open("outputs/logs/prompt_log.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    return narrative
```

---

## Step 5 — Implement `src/report.py`

Assemble the final Markdown desk note at `outputs/desk_note.md`.

Structure:
```
# European Cross-Commodity Risk Pack — {date}
**Author:** [Your Name] | [Your Email]

## Monitor metrics
| Metric | Value | 30d Avg | Signal |
|--------|-------|---------|--------|
... one row per metric, signal = ▲/▼/→ based on z-score or threshold ...

## Charts
![Spread regime](outputs/charts/spread_regime.png)
![Gas fundamentals](outputs/charts/gas_fundamentals.png)

## Desk note
{ai_narrative}

---
*Generated: {timestamp} | Model: claude-sonnet-4-20250514*
*Prompt log: outputs/logs/prompt_log.jsonl*
```

Optionally convert to PDF using `weasyprint` or `markdown-pdf` if available.
If neither is installed, emit a warning and save Markdown only.

---

## Step 6 — Implement `run.py`

Single entry point. Should:
1. Parse `--start` / `--end` CLI args (default: last 90 days)
2. Call `ingest.fetch_all()`
3. Call `metrics.compute_all()`
4. Call `charts.generate_charts()`
5. Call `ai_narrative.generate_narrative()`
6. Call `report.assemble()`
7. Print a summary: metrics table + path to output files
8. Exit 0 on success, 1 on any data error

---

## `requirements.txt` to create
```
anthropic>=0.25.0
yfinance>=0.2.40
pandas>=2.0.0
numpy>=1.26.0
matplotlib>=3.8.0
requests>=2.31.0
python-dotenv>=1.0.0
weasyprint>=60.0    # optional, for PDF
```

---

## Fundamental logic to embed in comments and narrative

The causal chain the AI narrative must reflect:
```
Gas tightness (TTF z-score, storage deficit)
        ↓
Higher gas SRMC → raises clean spark spread threshold
        ↓
If CDS > CSS: coal at margin → power tracks coal+carbon
If CSS > CDS: gas at margin → power tracks TTF+EUA
        ↓
EUA level amplifies marginal cost in both cases
(high EUA widens gap between SRMC_coal and SRMC_gas)
        ↓
Cal+1 baseload = weighted avg of expected SRMC over delivery period
+ risk premium from storage/supply uncertainty
```

Encode the merit-order switching logic in `metrics.implied_srmc()` with
a comment explaining this chain. The AI prompt must reference these
computed values, not reason from scratch.

---

## Definition of done

- [ ] `python run.py` completes without error on a fresh venv
- [ ] `outputs/desk_note.md` exists and is ≤ 3 pages when rendered
- [ ] `outputs/charts/spread_regime.png` and `gas_fundamentals.png` exist
- [ ] `outputs/logs/prompt_log.jsonl` has at least one entry with
      `system_prompt`, `user_prompt`, `response`, and token counts
- [ ] All 6 metrics appear in the metrics table in the desk note
- [ ] The narrative is grounded in today's numbers (not generic text)
- [ ] Code runs in under 2 minutes (excluding initial data download)
