"""
fx_carry_fred/feasibility.py
============================
FX carry feasibility — G10 cross-section, 3M interbank rates from FRED.

Fix vs prior run (Forex/research/passed/g10_feasibility): replaces hardcoded
annual rate averages with monthly FRED 3M series. Expected t-stat: 1.70 -> 2.5+.

Methodology
-----------
- Universe : 8 G10 currencies vs USD (EUR, GBP, JPY, AUD, CAD, CHF, NOK, SEK)
- Frequency: weekly close (W-FRI) — same as previous run for direct A/B
- Signal   : carry[XXXUSD, t-1] = r_3M[XXX, t-1] - r_3M[USD, t-1]
             monthly FRED rates forward-filled to weekly, shifted by 1 week.
- Returns  : weekly pct_change on XXXUSD prices (USD-quote convention,
             USDXXX pairs inverted upstream).
- Tests    : (1) cross-sectional Spearman IC, t-stat on mean
             (2) equal-weight tercile L/S backtest, 15 bps RT cost

Gate: t > 2.5 -> advance to walk-forward + DSR.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
import yfinance as yf
from pandas_datareader.data import DataReader
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
START = "2005-01-01"
END = pd.Timestamp.today().strftime("%Y-%m-%d")
COST_RT = 0.00015                              # 15 bps round-trip (institutional FX)
RESULTS_PATH = Path(__file__).parent / "results.json"

FRED_RATES_3M: Dict[str, str] = {
    "USD": "DTB3",                             # 3M T-Bill (daily)
    "EUR": "IR3TIB01EZM156N",                  # 3M EURIBOR
    "GBP": "IR3TIB01GBM156N",                  # 3M GBP LIBOR
    "JPY": "IR3TIB01JPM156N",                  # 3M JPY TIBOR
    "AUD": "IR3TIB01AUM156N",                  # 3M AUD IBOR
    "CAD": "IR3TIB01CAM156N",                  # 3M CAD IBOR
    "CHF": "IR3TIB01CHM156N",                  # 3M CHF LIBOR
    "NOK": "IR3TIB01NOM156N",                  # 3M NOK NIBOR
    "SEK": "IR3TIB01SEM156N",                  # 3M SEK STIBOR
}

# G10 currencies vs USD; we hold the funding leg (USD) as the quote currency.
G10_CCYS = ["EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NOK", "SEK"]


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------
def fetch_fred_rates(tickers: Dict[str, str], start: str, end: str) -> pd.DataFrame:
    """Pull every FRED rate series. Daily index with forward-fill (monthly source)."""
    series = {}
    for ccy, tk in tickers.items():
        try:
            s = DataReader(tk, "fred", start, end).iloc[:, 0]
            series[ccy] = s
            log.info(
                f"FRED {ccy:<3s} {tk:<22s} {len(s):>5d} obs "
                f"{s.index.min().date()} -> {s.index.max().date()}"
            )
        except Exception as e:
            log.warning(f"FRED fetch failed for {ccy} ({tk}): {e}")
    if "USD" not in series:
        raise RuntimeError("USD rate is required (DTB3) — aborting.")
    df = pd.concat(series, axis=1).resample("D").last().ffill()
    return df


def _yf_close(ticker: str, start: str, end: str) -> pd.Series:
    px = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
    if "Close" not in px.columns:
        raise RuntimeError(f"No Close column for {ticker}")
    s = px["Close"]
    if isinstance(s, pd.DataFrame):  # yfinance occasionally returns multi-col frames
        s = s.iloc[:, 0]
    return s.dropna()


def fetch_fx_xxx_usd(ccy: str, start: str, end: str) -> pd.Series:
    """Return XXXUSD price (USD per 1 XXX). Inverts USD-base pairs."""
    if ccy in {"EUR", "GBP", "AUD", "NZD"}:
        px = _yf_close(f"{ccy}USD=X", start, end)
    else:
        px = 1.0 / _yf_close(f"{ccy}=X", start, end)  # USDXXX -> XXXUSD
    return px.rename(f"{ccy}USD")


def fetch_fx_panel(ccys, start: str, end: str) -> pd.DataFrame:
    cols = []
    for c in ccys:
        try:
            cols.append(fetch_fx_xxx_usd(c, start, end))
        except Exception as e:
            log.warning(f"yfinance fetch failed for {c}: {e}")
    return pd.concat(cols, axis=1).dropna(how="all")


# ---------------------------------------------------------------------------
# Signal + tests
# ---------------------------------------------------------------------------
def build_carry(rates: pd.DataFrame, base_ccys, quote: str = "USD") -> pd.DataFrame:
    """carry[XXX{quote}] = r[XXX] - r[quote]."""
    cols = {}
    for c in base_ccys:
        if c in rates.columns:
            cols[f"{c}{quote}"] = rates[c] - rates[quote]
    return pd.DataFrame(cols).dropna(how="all")


def cross_sectional_ic(signal: pd.DataFrame, fwd_ret: pd.DataFrame) -> pd.Series:
    """Per-row Spearman correlation between signal and forward return."""
    common = signal.columns.intersection(fwd_ret.columns)
    sig, ret = signal[common], fwd_ret[common]
    idx = sig.index.intersection(ret.index)
    out = {}
    for t in idx:
        s = sig.loc[t].astype(float)
        r = ret.loc[t].astype(float)
        m = s.notna() & r.notna()
        if m.sum() < 4:
            continue
        rho, _ = stats.spearmanr(s[m], r[m])
        if np.isfinite(rho):
            out[t] = rho
    return pd.Series(out).sort_index()


def ic_summary(ic: pd.Series) -> dict:
    n = len(ic)
    mean, sd = ic.mean(), ic.std(ddof=1)
    t = mean / (sd / np.sqrt(n)) if sd > 0 and n > 1 else np.nan
    return {"ic_mean": float(mean), "ic_std": float(sd),
            "ic_tstat": float(t), "ic_n": int(n)}


def backtest_ls_tercile(signal: pd.DataFrame, fwd_ret: pd.DataFrame,
                        cost_rt: float, ann_factor: int = 52) -> dict:
    """Equal-weight long top tercile / short bottom tercile, gross of leverage."""
    common = signal.columns.intersection(fwd_ret.columns)
    sig = signal[common].dropna(how="all")
    ret = fwd_ret[common]
    idx = sig.index.intersection(ret.index)
    sig, ret = sig.loc[idx], ret.loc[idx]
    n_pairs = sig.shape[1]
    k = max(1, n_pairs // 3)

    w = pd.DataFrame(0.0, index=sig.index, columns=sig.columns)
    for t in sig.index:
        s = sig.loc[t].dropna()
        if len(s) < 2 * k:
            continue
        ranked = s.sort_values()
        w.loc[t, ranked.index[-k:]] = 1.0 / k
        w.loc[t, ranked.index[:k]] = -1.0 / k

    gross = (w * ret).sum(axis=1)
    turnover = (w - w.shift(1).fillna(0)).abs().sum(axis=1)
    cost = turnover * (cost_rt / 2.0)               # turnover counts each side
    net = gross - cost

    sharpe = float(net.mean() / net.std(ddof=1) * np.sqrt(ann_factor)) if net.std(ddof=1) > 0 else np.nan
    equity = (1 + net).cumprod()
    max_dd = float((equity / equity.cummax() - 1.0).min())
    return {"sharpe": sharpe, "max_dd": max_dd,
            "ann_ret": float(net.mean() * ann_factor),
            "n_pairs": int(n_pairs),
            "avg_turnover": float(turnover.mean())}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> dict:
    log.info("=== FX Carry Feasibility — G10 vs USD, FRED 3M ===")

    rates = fetch_fred_rates(FRED_RATES_3M, START, END)
    fx_daily = fetch_fx_panel(G10_CCYS, START, END)
    log.info(f"rates: {rates.shape} | fx: {fx_daily.shape}")

    # Weekly close, weekly returns
    fx_w = fx_daily.resample("W-FRI").last()
    ret_w = fx_w.pct_change().dropna(how="all")
    rates_w = rates.resample("W-FRI").last().ffill()

    # Signal at T-1, return at T
    carry = build_carry(rates_w, G10_CCYS).shift(1)

    # Align
    idx = carry.index.intersection(ret_w.index)
    carry, ret_w = carry.loc[idx], ret_w.loc[idx]

    ic = cross_sectional_ic(carry, ret_w)
    bt = backtest_ls_tercile(carry, ret_w, COST_RT, ann_factor=52)

    results = {
        "signal": "carry_fred_g10",
        "universe": "G10 vs USD (8 pairs)",
        "freq": "weekly",
        "cost_rt": COST_RT,
        "period_start": str(idx.min().date()),
        "period_end": str(idx.max().date()),
        **ic_summary(ic),
        **bt,
    }
    gate = "PASS" if results["ic_tstat"] > 2.5 else ("WEAK" if results["ic_tstat"] > 1.5 else "SKIP")
    results["gate"] = gate

    RESULTS_PATH.write_text(json.dumps(results, indent=2))

    print("\n" + "=" * 72)
    print("FX CARRY — FRED 3M (G10, 8 pairs vs USD)")
    print("=" * 72)
    for k, v in results.items():
        print(f"  {k:18s} {v}")
    print("=" * 72)
    return results


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("feasibility run failed")
        sys.exit(1)
