"""Fetch per-constituent fundamentals from yfinance, with on-disk caching.

Vintage: whatever yfinance served on the run date (stamped into the cache).
Nothing here is imputed: a field yfinance does not return stays NaN and is
counted in the coverage report produced by 03_aggregate.py.

Fields taken from Ticker.info (Yahoo Finance "key statistics" surface):
    marketCap, trailingPE, forwardPE, priceToSalesTrailing12Months,
    enterpriseToEbitda, priceToBook, profitMargins, revenueGrowth,
    earningsGrowth, totalDebt, totalCash, ebitda, ...

Fallback growth (computed here, not taken from Yahoo) uses the annual
income statement: revenue CAGR and diluted-EPS CAGR over the available
fiscal years.

Usage:  python3 02_fundamentals.py [--refresh]
"""
from __future__ import annotations

import argparse
import json
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
RAW = CACHE / "raw"
RAW.mkdir(parents=True, exist_ok=True)

INFO_FIELDS = [
    "shortName", "currency", "financialCurrency", "sector", "industry",
    "marketCap", "enterpriseValue", "sharesOutstanding", "floatShares",
    "currentPrice", "regularMarketPrice", "previousClose",
    "trailingPE", "forwardPE", "priceToSalesTrailing12Months",
    "enterpriseToEbitda", "enterpriseToRevenue", "priceToBook",
    "profitMargins", "grossMargins", "operatingMargins", "returnOnEquity",
    "revenueGrowth", "earningsGrowth", "earningsQuarterlyGrowth",
    "totalDebt", "totalCash", "ebitda", "totalRevenue", "netIncomeToCommon",
    "trailingEps", "forwardEps", "bookValue", "beta",
    "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "dividendYield", "payoutRatio",
    "numberOfAnalystOpinions",
]


def _jsonable(v):
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (str, int, float, bool, type(None))):
        return v
    return str(v)


def _fin_series(df: pd.DataFrame | None, names: list[str]) -> pd.Series | None:
    """Pull the first matching row from a yfinance financials frame,
    returned oldest->newest."""
    if df is None or df.empty:
        return None
    for n in names:
        if n in df.index:
            s = df.loc[n].dropna()
            if isinstance(s, pd.DataFrame):
                s = s.iloc[0].dropna()
            if len(s) >= 2:
                return s.sort_index()
    return None


def _cagr(s: pd.Series) -> tuple[float, int]:
    """CAGR from oldest to newest. Undefined if the oldest value is <= 0."""
    if s is None or len(s) < 2:
        return np.nan, 0
    first, last = float(s.iloc[0]), float(s.iloc[-1])
    n_years = len(s) - 1
    if first <= 0 or n_years < 1:
        return np.nan, len(s)
    if last <= 0:
        return np.nan, len(s)
    return (last / first) ** (1.0 / n_years) - 1.0, len(s)


def fetch_one(ticker: str, refresh: bool = False) -> dict:
    path = RAW / f"{ticker.replace('.', '_')}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text())

    rec: dict = {"ticker": ticker,
                 "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    tk = yf.Ticker(ticker)

    try:
        info = tk.info or {}
        rec["info_n_fields"] = len(info)
        for f in INFO_FIELDS:
            rec[f] = _jsonable(info.get(f))
    except Exception as e:  # noqa: BLE001
        rec["info_error"] = f"{type(e).__name__}: {e}"
        rec["info_n_fields"] = 0

    # --- annual statements: growth fallback + net debt fallback ---
    try:
        inc = tk.income_stmt
        rev = _fin_series(inc, ["Total Revenue", "Operating Revenue"])
        eps = _fin_series(inc, ["Diluted EPS", "Basic EPS"])
        ebi = _fin_series(inc, ["EBITDA", "Normalized EBITDA"])
        g, n = _cagr(rev)
        rec["rev_cagr_stmt"], rec["rev_cagr_nyears"] = g, n
        g, n = _cagr(eps)
        rec["eps_cagr_stmt"], rec["eps_cagr_nyears"] = g, n
        rec["ebitda_stmt"] = float(ebi.iloc[-1]) if ebi is not None else np.nan
        if rev is not None:
            rec["rev_yoy_stmt"] = float(rev.iloc[-1] / rev.iloc[-2] - 1) if rev.iloc[-2] > 0 else np.nan
            rec["rev_fy_last"] = str(rev.index[-1].date())
        if eps is not None:
            rec["eps_yoy_stmt"] = (float(eps.iloc[-1] / eps.iloc[-2] - 1)
                                   if eps.iloc[-2] > 0 else np.nan)
    except Exception as e:  # noqa: BLE001
        rec["stmt_error"] = f"{type(e).__name__}: {e}"

    try:
        bs = tk.balance_sheet
        td = _fin_series(bs, ["Total Debt"])
        cc = _fin_series(bs, ["Cash And Cash Equivalents",
                              "Cash Cash Equivalents And Short Term Investments"])
        rec["total_debt_bs"] = float(td.iloc[-1]) if td is not None else np.nan
        rec["cash_bs"] = float(cc.iloc[-1]) if cc is not None else np.nan
    except Exception as e:  # noqa: BLE001
        rec["bs_error"] = f"{type(e).__name__}: {e}"

    path.write_text(json.dumps(rec, indent=1))
    return rec


def main(refresh: bool = False) -> None:
    ndx = pd.read_csv(CACHE / "constituents_ndx.csv")
    dax = pd.read_csv(CACHE / "constituents_dax.csv")
    jobs = ([(t, "NDX") for t in ndx.ticker] + [(t, "DAX") for t in dax.ticker])

    out = []
    for i, (t, idx) in enumerate(jobs, 1):
        cached = (RAW / f"{t.replace('.', '_')}.json").exists()
        try:
            rec = fetch_one(t, refresh=refresh)
        except Exception as e:  # noqa: BLE001
            rec = {"ticker": t, "fatal_error": f"{type(e).__name__}: {e}",
                   "info_n_fields": 0}
        rec["index"] = idx
        out.append(rec)
        if not cached or refresh:
            time.sleep(0.6)
        if i % 20 == 0:
            print(f"  {i}/{len(jobs)} ...", flush=True)

    df = pd.DataFrame(out)
    df.to_csv(CACHE / "fundamentals_raw.csv", index=False)
    print(f"wrote {len(df)} rows; info_n_fields==0 for "
          f"{(df.info_n_fields == 0).sum()} tickers")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    main(**vars(ap.parse_args()))
