# European Cross-Commodity Risk Pack
**Author:** Xiyun Fu | xiyun1.fu@gmail.com
**Date:** 2026-04-03

## Cross-commodity monitor metrics

| Metric | Today's Value | Signal | Trading Relevance |
|--------|--------------|--------|-------------------|
| Clean Dark Spread | -42.09 EUR/MWh | ▲ | Sets the floor for baseload power — negative CDS means coal plants destroy value at current prices, pushing power supply toward gas and renewables |
| Clean Spark Spread | -7.69 EUR/MWh | ▲ | Gas-to-power switching threshold — negative CSS signals even gas plants struggle to cover variable costs, compressing power curve upside |
| TTF 30d Z-Score | -0.91 | ▼ | Flags whether gas is priced tight or loose relative to recent history — sub-zero z-score confirms near-term oversupply |
| EUA/TTF Ratio | 1.34 | ▲ | Measures carbon's weight in marginal generation cost — above 1.2 threshold, carbon actively shifts the merit order toward gas over coal |
| Storage vs 5yr Avg | -35.00 pp | ▼ | Quantifies winter supply cushion — deficit against seasonal norms prices in injection demand and winter scarcity risk premium |
| Implied SRMC (marginal) | 54.96 EUR/MWh | ▼ | Anchors where Day-Ahead power should clear — the marginal plant's variable cost sets the theoretical price floor for baseload |

## Gas tightness

TTF front-month trades at a z-score of -0.91 against its 30-day rolling mean, placing current price nearly one standard deviation below recent average levels. Near-term fundamentals read loose: the negative z-score reflects comfortable prompt supply, likely driven by mild late-season temperatures and adequate LNG arrivals. The 30-day average z-score of +0.41 confirms this is a recent shift — gas moved from firm to soft within the past month.

The storage picture tells a different story. EU aggregate fill sits 35.00 percentage points below the 5-year seasonal average at 27.77%, a material deficit heading into injection season. This gap widened from the 30-day average deficit of -25.46 pp, indicating storage draws accelerated relative to historical norms. Rebuilding from 27.77% to adequate pre-winter levels (~85%) requires sustained injection rates well above seasonal norms through Q2–Q3. The paradox — loose prompt pricing against tight structural inventory — keeps winter 2026-27 risk premium bid despite near-term softness.

## Carbon supply and policy signal

EUA trades at an implied ratio of 1.34 against TTF, above the empirical fuel-switching threshold of ~1.2 where carbon cost begins to dominate the coal-gas merit order decision. At this level, carbon adds approximately €22.85/MWh to coal SRMC (EUA × 0.34 emission factor) versus €13.44/MWh to gas SRMC (EUA × 0.20). Carbon actively amplifies the cost disadvantage of coal-fired generation, widening the CDS-CSS gap.

The EUA/TTF ratio rose from a 30-day average of 1.25 to 1.34, a 7% move that increases carbon's marginal cost contribution. This trend supports structural displacement of coal from the merit order and reinforces gas as the price-setting fuel across most dispatch hours.

## European power curve implications

Gas is unambiguously at the margin. Clean Spark Spread at -7.69 EUR/MWh sits well above Clean Dark Spread at -42.09 EUR/MWh — coal is 34.40 EUR/MWh further out of the money than gas. The marginal plant operates at an implied SRMC of 54.96 EUR/MWh (gas CCGT: TTF × 1.5 + EUA × 0.20), down from the 30-day average of 58.37 EUR/MWh as gas prices softened.

Both spreads are negative, meaning neither coal nor gas generation covers variable costs at current Day-Ahead clearing prices. The -42.09 CDS represents demand destruction for coal baseload — these plants run only under grid-stability obligations or during scarcity spikes. Gas plants at -7.69 CSS operate at a slim loss, implying DA clears slightly below gas SRMC, likely depressed by high renewable output or low-demand hours pulling the daily average down.

Cal+1 baseload faces downward pressure. The declining SRMC trend (54.96 vs 58.37 30-day average) compresses the forward curve, and the negative spark spread suggests the market prices in continued renewable displacement during shoulder-season hours. Upside requires either a storage-driven TTF rally or sustained high-demand periods that push DA above marginal SRMC.

## Key risk

The dominant risk is to the upside on gas and power. EU storage at 27.77% fill (35 pp below seasonal average) requires aggressive injection through summer — any disruption to Norwegian pipeline flows or LNG cargo diversions to Asia tightens the injection path materially, repricing TTF higher and dragging power and carbon with it. The market is complacent on prompt supply while the structural deficit grows.

---

**Charts:**

![Clean dark spread vs EUA — 60-day twin-axis](charts/spread_regime.png)

![TTF with ±1σ band and storage vs 5yr average](charts/gas_fundamentals.png)

**Prompt log:** `outputs/logs/prompt_log.jsonl`
**AI call (latest):** Model: claude-sonnet-4-20250514 | Input tokens: 369 | Output tokens: 400
