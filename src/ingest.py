"""Step 1 — Pull public gas, carbon, power, and storage data."""

import warnings
import datetime
import hashlib
import json
import time

import pandas as pd
import numpy as np
import yfinance as yf
import requests

import config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cache_path(name: str, start: str, end: str) -> str:
    """Return a deterministic CSV cache path for a dataset + date window."""
    tag = hashlib.md5(f"{name}_{start}_{end}".encode()).hexdigest()[:8]
    return str(config.DATA_RAW / f"{name}_{tag}.csv")


def _read_cache(path: str) -> pd.DataFrame | None:
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        if not df.empty:
            return df
    except FileNotFoundError:
        pass
    return None


# ---------------------------------------------------------------------------
# Individual fetchers
# ---------------------------------------------------------------------------

def fetch_yf(ticker: str, name: str, start: str, end: str) -> pd.Series:
    """Fetch a single Yahoo Finance ticker; return the Close series."""
    cache = _cache_path(name, start, end)
    cached = _read_cache(cache)
    if cached is not None:
        return cached.iloc[:, 0]

    print(f"  Downloading {name} ({ticker}) from Yahoo Finance …")
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if df.empty:
        warnings.warn(f"No data returned for {ticker}")
        return pd.Series(dtype=float)

    close = df["Close"].squeeze()
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close.name = name
    close.to_frame().to_csv(cache)
    return close


def fetch_smard_power(start: str, end: str) -> pd.Series:
    """
    Fetch German day-ahead power prices from SMARD.
    SMARD serves weekly JSON blocks keyed by Monday timestamps (ms).
    """
    cache = _cache_path("power_da", start, end)
    cached = _read_cache(cache)
    if cached is not None:
        return cached.iloc[:, 0]

    print("  Downloading German DA power from SMARD …")
    start_dt = pd.Timestamp(start)
    end_dt = pd.Timestamp(end)

    # Fetch the index of available weekly timestamps from SMARD
    index_url = (
        f"{config.SMARD_BASE_URL}/{config.SMARD_FILTER_ID}/"
        f"{config.SMARD_REGION}/index_hour.json"
    )
    try:
        idx_resp = requests.get(index_url, timeout=15)
        idx_resp.raise_for_status()
        all_timestamps = idx_resp.json().get("timestamps", [])
    except Exception:
        all_timestamps = []

    # Filter to timestamps covering our date range
    week_timestamps = [
        ts for ts in all_timestamps
        if pd.Timestamp(ts, unit="ms") >= start_dt - pd.Timedelta(days=7)
        and pd.Timestamp(ts, unit="ms") <= end_dt + pd.Timedelta(days=7)
    ]

    rows = []
    for ts_ms in week_timestamps:
        url = (
            f"{config.SMARD_BASE_URL}/{config.SMARD_FILTER_ID}/"
            f"{config.SMARD_REGION}/{config.SMARD_FILTER_ID}_{config.SMARD_REGION}_hour_{ts_ms}.json"
        )
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            series_data = resp.json().get("series", [])
            for ts_val, price in series_data:
                if price is not None:
                    rows.append((pd.Timestamp(ts_val, unit="ms"), price))
        except Exception:
            pass  # some weeks may not have data
        time.sleep(0.2)

    if not rows:
        warnings.warn("No SMARD power data retrieved; using fallback")
        return pd.Series(dtype=float)

    hourly = pd.DataFrame(rows, columns=["timestamp", "price"])
    hourly["date"] = hourly["timestamp"].dt.date
    daily = hourly.groupby("date")["price"].mean()
    daily.index = pd.DatetimeIndex(daily.index)
    daily.name = "Power_DA"
    daily.to_frame().to_csv(cache)
    return daily


def fetch_gie_storage(start: str, end: str) -> pd.Series:
    """Fetch EU aggregate gas storage fill % from GIE AGSI+."""
    cache = _cache_path("storage", start, end)
    cached = _read_cache(cache)
    if cached is not None:
        return cached.iloc[:, 0]

    print("  Downloading EU gas storage from GIE AGSI+ …")
    headers = {"x-key": ""}  # public endpoint, key optional
    params = {
        "type": "eu",
        "from": start,
        "till": end,
        "size": "300",
    }

    rows = []
    page = 1
    while True:
        params["page"] = page
        try:
            resp = requests.get(
                config.GIE_API_URL, params=params, headers=headers, timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            warnings.warn(f"GIE API error: {e}")
            break

        entries = data.get("data", [])
        if not entries:
            break

        for entry in entries:
            try:
                dt = pd.Timestamp(entry["gasDayStart"])
                fill = float(entry["full"])
                rows.append((dt, fill))
            except (KeyError, ValueError, TypeError):
                continue

        # Check if more pages
        last_page = data.get("last_page", page)
        if page >= last_page:
            break
        page += 1
        time.sleep(0.3)

    if not rows:
        warnings.warn("No GIE storage data; generating synthetic seasonal curve")
        idx = pd.date_range(start, end, freq="D")
        # Typical EU storage seasonal shape: low ~30% in March, high ~95% in Oct
        day_of_year = idx.dayofyear
        fill = 55 + 35 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
        s = pd.Series(fill, index=idx, name="Storage_Fill")
        s.to_frame().to_csv(cache)
        return s

    storage = pd.DataFrame(rows, columns=["date", "fill"]).set_index("date")
    storage = storage.sort_index()
    storage = storage[~storage.index.duplicated(keep="last")]
    s = storage["fill"]
    s.name = "Storage_Fill"
    s.to_frame().to_csv(cache)
    return s


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def fetch_all(start: str, end: str) -> pd.DataFrame:
    """
    Fetch all datasets and merge into a single daily DataFrame.

    Columns: TTF, EUA, Power_DA, Storage_Fill, NBP
    Index: DatetimeIndex (daily)
    """
    print("Fetching data …")

    ttf = fetch_yf(config.TICKER_TTF, "TTF", start, end)
    eua = fetch_yf(config.TICKER_EUA, "EUA", start, end)
    nbp = fetch_yf(config.TICKER_NBP, "NBP", start, end)
    power = fetch_smard_power(start, end)
    storage = fetch_gie_storage(start, end)

    # Merge on date
    df = pd.DataFrame(index=pd.date_range(start, end, freq="D"))
    df.index.name = "date"

    for series in [ttf, eua, nbp, power, storage]:
        if series.empty:
            continue
        # Align to daily index
        s = series.copy()
        s.index = pd.DatetimeIndex(s.index).normalize()
        s = s[~s.index.duplicated(keep="last")]
        df[s.name] = s

    # If Power_DA is missing, derive from gas SRMC as a proxy
    if "Power_DA" not in df.columns or df["Power_DA"].isna().all():
        if "TTF" in df.columns and "EUA" in df.columns:
            warnings.warn(
                "Power_DA unavailable from SMARD; deriving proxy from "
                "TTF*1.5 + EUA*0.2 + 5 (gas CCGT SRMC + margin)"
            )
            df["Power_DA"] = df["TTF"] * 1.5 + df["EUA"] * 0.2 + 5

    # Forward-fill gaps up to 2 days, warn on larger gaps
    for col in df.columns:
        gap_lengths = df[col].isna().astype(int).groupby(
            df[col].notna().cumsum()
        ).cumsum()
        max_gap = gap_lengths.max()
        if max_gap > 2:
            warnings.warn(
                f"{col}: gap of {max_gap} days detected (> 2-day ffill limit)"
            )
        df[col] = df[col].ffill(limit=2)

    # Drop leading NaN rows (before first data point)
    df = df.dropna(how="all")

    # Save merged dataset
    merged_path = config.DATA_RAW / "merged.csv"
    df.to_csv(merged_path)
    print(f"  Merged dataset: {len(df)} rows, columns: {list(df.columns)}")
    print(f"  Saved to {merged_path}")

    return df
