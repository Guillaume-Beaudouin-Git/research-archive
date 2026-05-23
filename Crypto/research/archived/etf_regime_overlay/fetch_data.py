"""
Phase 2 data pipeline — ETF flows (BitBO) + stablecoin supply (DeFiLlama).

Farside was the original source but returned 403 (Cloudflare IP block, confirmed 2026-05-23).
BitBO (bitbo.io/treasuries/etf-flows/) returns HTTP 200 with ETF flow data embedded as
JavaScript arrays in the HTML. Data is BTC-denominated; z-score normalization in engine.py
makes the unit (BTC vs USD) irrelevant for the regime score.

Run: python fetch_data.py
Outputs: data/etf_flows_raw.parquet, data/stablecoin_supply_raw.parquet
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import requests

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

ETF_FLOWS_PATH = DATA_DIR / "etf_flows_raw.parquet"
STABLE_PATH = DATA_DIR / "stablecoin_supply_raw.parquet"

BITBO_URL = "https://bitbo.io/treasuries/etf-flows/"
DEFI_URL = "https://stablecoins.llama.fi/stablecoincharts/all"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _shift_to_prev_business_day(dt: pd.Timestamp) -> pd.Timestamp:
    """Replicate JS getPreviousBusinessDay: shift Sat→Fri, Sun→Fri."""
    while dt.weekday() >= 5:
        dt -= pd.Timedelta(days=1)
    return dt.normalize()


def fetch_bitbo_etf_flows() -> pd.DataFrame:
    """
    Scrape BitBO Bitcoin ETF flow page.

    Extracts the embedded `historyBtc` JavaScript array (total net BTC flows
    across all US spot ETFs, daily). Returns DataFrame indexed by Date with
    columns net_flow_btc and net_flow_all (alias for compatibility with engine.py).

    Units: BTC (not USD). z-score normalization in engine.py is unit-invariant.

    Raises RuntimeError on HTTP error or if expected JS variable is absent.
    """
    print(f"Fetching BitBO ETF flows from {BITBO_URL} ...")
    try:
        resp = requests.get(BITBO_URL, headers=HEADERS, timeout=30)
    except requests.RequestException as e:
        raise RuntimeError(f"BitBO request failed: {e}") from e

    if resp.status_code != 200:
        raise RuntimeError(
            f"STOP CONDITION: BitBO returned HTTP {resp.status_code}. "
            "If persistent, archive with note 'data source fragile'."
        )

    html = resp.text

    # The page embeds historyBtc (plain BTC values) and historyUsd (BTC × spot price).
    # Extract only historyBtc — bounded by [const historyBtc, const historyUsd).
    btc_start = html.find("const historyBtc = [")
    usd_start = html.find("const historyUsd = [")
    if btc_start == -1:
        raise RuntimeError(
            "STOP CONDITION: 'historyBtc' not found in BitBO HTML — page schema changed."
        )
    if usd_start == -1 or usd_start <= btc_start:
        raise RuntimeError(
            "STOP CONDITION: 'historyUsd' boundary not found — cannot isolate historyBtc."
        )

    block = html[btc_start:usd_start]

    # Each data row: [getPreviousBusinessDay(unix_ms), truncate(float, 2)]
    # Match only plain floats (no multiplication = BTC values, not USD).
    pattern = re.compile(r"getPreviousBusinessDay\((\d+)\),\s*truncate\((-?[\d.]+),\s*2\)")
    matches = pattern.findall(block)

    if len(matches) < 100:
        raise RuntimeError(
            f"STOP CONDITION: Only {len(matches)} entries parsed — expected 400+. "
            "BitBO schema may have changed."
        )

    records = []
    for ts_ms, val in matches:
        dt = _shift_to_prev_business_day(pd.Timestamp(int(ts_ms), unit="ms"))
        records.append({"Date": dt, "net_flow_btc": float(val)})

    df = pd.DataFrame(records)
    # Deduplicate: for same business day, take the last entry (latest JS row wins)
    df = df.drop_duplicates(subset="Date", keep="last").set_index("Date").sort_index()

    # Alias for engine.py compatibility (regime score uses net_flow_all)
    df["net_flow_all"] = df["net_flow_btc"]

    print(f"  BitBO: {len(df)} rows, {df.index[0].date()} → {df.index[-1].date()}")
    print(f"  net_flow_btc: mean={df['net_flow_btc'].mean():.0f}, "
          f"min={df['net_flow_btc'].min():.0f}, max={df['net_flow_btc'].max():.0f} BTC")
    return df


def fetch_stablecoin_supply() -> pd.DataFrame:
    """
    Fetch total stablecoin supply from DeFiLlama stablecoincharts/all.

    Returns DataFrame with column total_supply_usd, indexed by Date.
    """
    print(f"Fetching DeFiLlama stablecoin supply from {DEFI_URL} ...")
    try:
        resp = requests.get(DEFI_URL, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"DeFiLlama request failed: {e}") from e

    data = resp.json()
    print(f"  DeFiLlama: {len(data)} daily observations")

    records = []
    for entry in data:
        ts = entry.get("date")
        circ = entry.get("totalCirculating", {})
        supply_usd = circ.get("peggedUSD", np.nan)
        if ts is not None and not np.isnan(float(supply_usd)):
            records.append({"Date": pd.Timestamp(int(ts), unit="s"), "total_supply_usd": float(supply_usd)})

    df = pd.DataFrame(records).set_index("Date").sort_index()
    df = df[df.index >= "2023-01-01"]

    print(f"  Stablecoin supply: {len(df)} rows, {df.index[0].date()} → {df.index[-1].date()}")
    print(f"  Supply range: ${df['total_supply_usd'].min()/1e9:.1f}B → "
          f"${df['total_supply_usd'].max()/1e9:.1f}B")
    return df


def main() -> None:
    try:
        etf_df = fetch_bitbo_etf_flows()
        etf_df.to_parquet(ETF_FLOWS_PATH)
        print(f"  Saved → {ETF_FLOWS_PATH}\n")
    except RuntimeError as e:
        print(f"\n[ERROR] {e}")
        raise SystemExit(1)

    try:
        stable_df = fetch_stablecoin_supply()
        stable_df.to_parquet(STABLE_PATH)
        print(f"  Saved → {STABLE_PATH}\n")
    except RuntimeError as e:
        print(f"\n[ERROR] DeFiLlama: {e}")
        raise SystemExit(1)

    print("Phase 2 data fetch complete.")


if __name__ == "__main__":
    main()
