# European Cross-Commodity Risk Pack

Automated daily monitor that ingests public European gas, carbon, and power market data, computes 6 cross-commodity trading metrics, and generates a structured desk note with charts and an LLM-written narrative — output is a single Markdown file ready for morning distribution.

## Quickstart

```bash
git clone <repo-url> && cd commodity-risk
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add at least one API key (see below)
python run.py
```

Runtime: ~60–90 seconds (mostly data download on first run; cached on reruns).

On completion, `outputs/` contains:
- `desk_note.md` — full desk note with metrics table, charts, and narrative
- `charts/spread_regime.png` and `charts/gas_fundamentals.png`
- `logs/prompt_log.jsonl` — full prompt/response audit log

## Data ingestion

| Dataset | Source | Library / API | Registration | Caching | Unavailability handling |
|---------|--------|---------------|-------------|---------|------------------------|
| TTF front-month settle | Yahoo Finance (`TTF=F`) | `yfinance` | No | MD5-hashed CSV per ticker + date range in `data/raw/` | Returns empty Series; forward-fill up to 2 days, warns on gaps > 2 days |
| EU ETS EUA Dec front | Yahoo Finance (`CO2.L`) | `yfinance` | No | Same as above | Same as above |
| NBP day-ahead gas | Yahoo Finance (`NBP=F`) | `yfinance` | No | Same as above | Same; also used as coal price proxy in SRMC calculation |
| German power DA price | SMARD API (bundesnetzagentur.de) | `requests` — fetches weekly JSON via `index_hour.json` endpoint, aggregates hourly to daily avg | No | CSV cache in `data/raw/` | If SMARD returns no data, Power_DA is proxied as `TTF × 1.5 + EUA × 0.2 + 5` (gas CCGT SRMC + margin); a warning is emitted |
| EU gas storage fill % | GIE AGSI+ REST API (`agsi.gie.eu`) | `requests` with pagination | API key optional (public endpoint) | CSV cache in `data/raw/` | Falls back to synthetic seasonal curve (`55 + 35 × sin(...)`) approximating 5-year average shape; warns |

All series are merged onto a daily DatetimeIndex. Forward-fill is capped at 2 days; gaps exceeding this threshold trigger a warning but are left as NaN beyond the fill limit.

## Metrics

| Metric | Formula | Unit | Trading Relevance |
|--------|---------|------|-------------------|
| Clean Dark Spread | `Power_DA − TTF × 2.0 − EUA × 0.34` | EUR/MWh | Coal generation profitability — negative CDS means coal plants destroy value, pushing supply toward gas and renewables |
| Clean Spark Spread | `Power_DA − TTF × 1.5 − EUA × 0.20` | EUR/MWh | Gas-to-power switching threshold — positive CSS means gas plants cover variable costs |
| TTF 30d Z-Score | `(TTF − rolling_mean_30d) / rolling_std_30d` | dimensionless | Flags whether gas is unusually tight or loose relative to recent history |
| EUA/TTF Ratio | `EUA / TTF` | tCO₂/MWh | Carbon's relative weight in marginal cost — above ~1.2, carbon actively shifts the merit order toward gas over coal |
| Storage vs 5yr Avg | `Storage_Fill − (55 + 35 × sin(2π(doy−80)/365))` | percentage points | Winter supply cushion — deficit supports risk premium; surplus dampens it |
| Implied SRMC (marginal) | `min(TTF × 1.5 + EUA × 0.20, NBP × 2.0 + EUA × 0.34)` | EUR/MWh | Theoretical DA clearing price — the lower SRMC identifies the current marginal fuel |

Each function in `src/metrics.py` returns `(today_value, trailing_60d_series)`. The `compute_all()` wrapper returns a dict of all six.

## Chart outputs

### `outputs/charts/spread_regime.png`
**Layout:** Twin-axis time series, 60 trailing days.
- Left axis: Clean Dark Spread (solid orange `#D85A30`), with zero line
- Right axis: EUA front-month (dashed blue `#178ADD`)
- Today's value annotated with a dot on each series

**Why:** Visualises the coal profitability regime against carbon cost. A trader uses this to judge whether coal is in or out of the money and how carbon is moving relative to the spread — the two lines diverging signals a merit-order shift.

### `outputs/charts/gas_fundamentals.png`
**Layout:** Two vertically stacked subplots, shared x-axis, 60 trailing days.
- Top: TTF front-month with 30-day rolling mean and ±1σ shaded band
- Bottom: EU storage fill % with 5-year seasonal average as dashed reference

**Why:** Combines price-based (z-score visual) and fundamental (storage) gas signals in one view. A trader scans this to assess whether prompt TTF is stretched relative to history and whether storage supports or undermines the current price level.

## AI workflow

**Model:** Claude Sonnet (`claude-sonnet-4-20250514`) as primary, Google Gemini 2.0 Flash as fallback, rule-based template as final fallback. Claude Sonnet chosen for strong quantitative reasoning at low token cost.

**System prompt design:** The LLM is cast as a senior European power/gas trader writing a morning desk note. Explicit constraints suppress filler language ("it is important to note"), enforce present tense, and require every observation to anchor to a specific number. This prevents generic commodity commentary.

**Metric injection:** Today's 6 metric values are formatted as a bullet list and inserted into the user prompt. The LLM never computes metrics — it interprets pre-computed values. This keeps the narrative grounded and auditable.

**Prompt structure:** The user prompt requests 4 sections (gas tightness, carbon signal, power curve implications, key risk) with sentence-count targets and a 350-word cap. Max tokens set to 600.

**Logging:** Every prompt/response pair is appended to `outputs/logs/prompt_log.jsonl`. Each entry contains: `timestamp`, `model`, `system_prompt`, `user_prompt`, `response`, `input_tokens`, `output_tokens`.

**Token usage:** ~370 input tokens, ~400 output tokens per run (~770 total). At Claude Sonnet pricing this is < $0.01/run.

**What this replaces:** A senior analyst would manually scan TTF, EUA, storage, and power screens each morning, mentally compute spread levels, assess the merit order, then write a 300-word desk note. This takes 20–30 minutes. The pipeline does it in ~90 seconds with full audit trail.

## Output artifacts

| Path | Format | Contents |
|------|--------|----------|
| `outputs/desk_note.md` | Markdown | Full desk note: metrics table, embedded chart references, AI narrative, generation metadata |
| `outputs/desk_note.pdf` | PDF (optional) | Same content rendered via weasyprint, if installed |
| `outputs/charts/spread_regime.png` | PNG (150 DPI) | Clean dark spread vs EUA twin-axis chart, 60 days |
| `outputs/charts/gas_fundamentals.png` | PNG (150 DPI) | TTF + σ-band and storage vs 5yr avg, 60 days |
| `outputs/logs/prompt_log.jsonl` | JSON Lines | Append-only log of every LLM call: prompts, responses, token counts |
| `data/raw/merged.csv` | CSV | Merged daily DataFrame of all 5 input series |
| `data/raw/<ticker>_<hash>.csv` | CSV | Per-source cached downloads |

## Dependencies

| Package | Version | Purpose | API key required |
|---------|---------|---------|-----------------|
| `anthropic` | ≥ 0.25.0 | Claude API client for AI narrative | Yes — `ANTHROPIC_API_KEY` |
| `google-genai` | ≥ 1.70.0 | Gemini API client (fallback narrative) | Yes — `GEMINI_API_KEY` |
| `yfinance` | ≥ 0.2.40 | TTF, EUA, NBP price data from Yahoo Finance | No |
| `pandas` | ≥ 2.0.0 | Data manipulation and time series alignment | No |
| `numpy` | ≥ 1.26.0 | Numerical operations for metrics and seasonal curves | No |
| `matplotlib` | ≥ 3.8.0 | Chart generation | No |
| `requests` | ≥ 2.31.0 | HTTP client for SMARD and GIE APIs | No |
| `python-dotenv` | ≥ 1.0.0 | Load `.env` file for API keys | No |
| `weasyprint` | ≥ 60.0 | Optional PDF rendering from Markdown | No |

At least one of `ANTHROPIC_API_KEY` or `GEMINI_API_KEY` is needed for AI narrative. If neither is set, the pipeline falls back to a rule-based template narrative.

## Known limitations

- **SMARD power data can fail silently.** The SMARD API occasionally returns empty responses for recent weeks. When this happens, Power_DA is proxied from TTF-derived SRMC + fixed margin, which makes Clean Spark Spread mechanically constant. The desk note warns but the metric loses diagnostic value.
- **Storage 5-year average is approximated.** GIE AGSI+ does not serve historical multi-year data in the free tier. The 5-year seasonal baseline is a sine-curve approximation, not actual historical fill rates. Production use would require a paid data vendor or pre-loaded historical CSVs.
- **NBP is used as a coal price proxy.** No free coal price feed was available. `implied_srmc` uses NBP × 2.0 as a stand-in for coal SRMC, which overstates coal cost when UK gas diverges from ARA coal. A real coal series (API2) would improve accuracy.
- **Weekend/holiday gaps exceed the 2-day ffill limit.** Market data has natural 2–3 day gaps over weekends. The pipeline warns on 3-day gaps that are normal. A business-day-aware fill would be cleaner.
- **No live scheduling.** The pipeline runs on-demand via `python run.py`. Production deployment would need a cron job or orchestrator, error alerting, and data-quality gates before the desk note is distributed.
