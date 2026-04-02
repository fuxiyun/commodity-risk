"""Step 2 — Compute the 6 desk-relevant cross-commodity metrics."""

import numpy as np
import pandas as pd


def clean_dark_spread(df: pd.DataFrame) -> tuple[float, pd.Series]:
    """
    CDS = Power_DA - (Gas_TTF * heat_rate) - (EUA * emission_factor)
    heat_rate = 2.0 MWh_gas / MWh_power (typical hard-coal proxy)
    emission_factor = 0.34 tCO2 / MWh_power
    Unit: EUR/MWh. Positive = coal/gas generation profitable.
    Trading relevance: primary signal for baseload power curve level.
    """
    heat_rate = 2.0
    emission_factor = 0.34
    cds = df["Power_DA"] - (df["TTF"] * heat_rate) - (df["EUA"] * emission_factor)
    history = cds.iloc[-60:]
    today = float(cds.iloc[-1])
    return today, history


def clean_spark_spread(df: pd.DataFrame) -> tuple[float, pd.Series]:
    """
    CSS = Power_DA - (Gas_TTF * gas_heat_rate) - (EUA * 0.2)
    gas_heat_rate = 1.5 (CCGT gas efficiency proxy)
    emission_factor = 0.20 tCO2/MWh for gas
    Unit: EUR/MWh. Positive = gas generation profitable.
    Trading relevance: gas-to-power switching threshold.
    """
    gas_heat_rate = 1.5
    emission_factor = 0.20
    css = df["Power_DA"] - (df["TTF"] * gas_heat_rate) - (df["EUA"] * emission_factor)
    history = css.iloc[-60:]
    today = float(css.iloc[-1])
    return today, history


def ttf_30d_rolling_zscore(df: pd.DataFrame) -> tuple[float, pd.Series]:
    """
    Z-score of TTF front-month vs its 30-day rolling mean/std.
    Trading relevance: flags whether gas is unusually tight or loose.
    """
    ttf = df["TTF"]
    rolling_mean = ttf.rolling(30).mean()
    rolling_std = ttf.rolling(30).std()
    zscore = (ttf - rolling_mean) / rolling_std
    history = zscore.iloc[-60:]
    today = float(zscore.iloc[-1])
    return today, history


def eua_ttf_ratio(df: pd.DataFrame) -> tuple[float, pd.Series]:
    """
    EUA (EUR/tCO2) / TTF (EUR/MWh).
    Normalises carbon cost relative to gas cost.
    Trading relevance: high ratio = carbon dominates marginal cost,
    shifts merit order toward gas over coal.
    """
    ratio = df["EUA"] / df["TTF"]
    history = ratio.iloc[-60:]
    today = float(ratio.iloc[-1])
    return today, history


def storage_fill_vs_5yr_avg(df: pd.DataFrame) -> tuple[float, pd.Series]:
    """
    Current EU gas storage fill % minus the 5-year seasonal average
    for the same calendar week.
    Trading relevance: deficit = upside risk for winter gas/power.

    Since we only have current-year data from GIE, we approximate
    the 5-year average with a smooth seasonal curve (trough ~30% in
    March/April, peak ~95% in October).
    """
    storage = df["Storage_Fill"]
    # Approximate 5-year seasonal average
    day_of_year = storage.index.dayofyear
    five_yr_avg = 55 + 35 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
    delta = storage - five_yr_avg
    history = delta.iloc[-60:]
    today = float(delta.iloc[-1])
    return today, history


def implied_srmc(df: pd.DataFrame) -> tuple[float, pd.Series]:
    """
    Short-run marginal cost of the price-setting unit.

    SRMC_gas  = Gas_TTF * 1.5 + EUA * 0.20   (gas CCGT)
    SRMC_coal = Coal_proxy * 2.0 + EUA * 0.34 (hard coal — use NBP as proxy)

    The lower SRMC sets the marginal unit:
      - If SRMC_gas < SRMC_coal → gas at margin → power tracks TTF+EUA
      - If SRMC_coal < SRMC_gas → coal at margin → power tracks coal+carbon

    Merit-order switching logic (causal chain):
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

    Returns the marginal (lower) SRMC.
    """
    srmc_gas = df["TTF"] * 1.5 + df["EUA"] * 0.20
    # Use NBP as coal proxy if coal price unavailable
    coal_proxy = df["NBP"] if "NBP" in df.columns else df["TTF"]
    srmc_coal = coal_proxy * 2.0 + df["EUA"] * 0.34
    marginal = pd.DataFrame({"gas": srmc_gas, "coal": srmc_coal}).min(axis=1)
    history = marginal.iloc[-60:]
    today = float(marginal.iloc[-1])
    return today, history


def compute_all(df: pd.DataFrame) -> dict:
    """
    Compute all 6 metrics. Returns dict of
    {metric_name: (today_value, history_series)}.
    """
    return {
        "Clean Dark Spread": clean_dark_spread(df),
        "Clean Spark Spread": clean_spark_spread(df),
        "TTF 30d Z-Score": ttf_30d_rolling_zscore(df),
        "EUA/TTF Ratio": eua_ttf_ratio(df),
        "Storage vs 5yr Avg": storage_fill_vs_5yr_avg(df),
        "Implied SRMC (marginal)": implied_srmc(df),
    }
