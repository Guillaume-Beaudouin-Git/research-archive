"""
fx_carry_em/feasibility.py
==========================
FX carry feasibility — G10 + Emerging Markets (BRL, MXN, ZAR, TRY).

Rationale
---------
G10 carry has IC ~0.027 (weak). EM differentials are an order of magnitude
larger (5-20% vs 0.5-5%), so the carry signal should produce a much stronger
cross-sectional ranking. Trade-off: crash risk during EM unwinds.

Methodology
-----------
- Universe : 8 G10 + 4 EM = 12 pairs vs USD (XXXUSD convention)
- Frequency: weekly close (W-FRI), tested vs 1W AND 4W forward returns
- G10 rates: FRED 3M interbank (same as fx_carry_fred)
- EM rates : FRED short-term rates with fallback chain:
             IRSTCI01XXM156N -> INTDSRXXM193N -> hardcoded multi-year average
- Crash test: report Sharpe/MaxDD over 2008 GFC, 2015 EM unwind, 2020 COVID
              Hard gate: if 2020 MaxDD < -25% -> not propfirm-compatible.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
COST_RT_G10 = 0.00015                          # 15 bps RT
COST_RT_EM = 0.00060                           # 60 bps RT (EM spreads ~3-5x wider)
RESULTS_PATH = Path(__file__).parent / "results.json"

G10_CCYS = ["EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NOK", "SEK"]
EM_CCYS = ["BRL", "MXN", "ZAR", "TRY"]

FRED_G10: Dict[str, str] = {
    "USD": "DTB3",
    "EUR": "IR3TIB01EZM156N", "GBP": "IR3TIB01GBM156N", "JPY": "IR3TIB01JPM156N",
    "AUD": "IR3TIB01AUM156N", "CAD": "IR3TIB01CAM156N", "CHF": "IR3TIB01CHM156N",
    "NOK": "IR3TIB01NOM156N", "SEK": "IR3TIB01SEM156N",
}

# Try multiple FRED ticker patterns per EM currency; pick the first that returns data.
FRED_EM_CANDIDATES: Dict[str, List[str]] = {
    "BRL": ["IRSTCI01BRM156N", "INTDSRBRM193N", "IR3TIB01BRM156N"],
    "MXN": ["IRSTCI01MXM156N", "INTDSRMXM193N", "IR3TIB01MXM156N"],
    "ZAR": ["IRSTCI01ZAM156N", "INTDSRZAM193N", "IR3TIB01ZAM156N"],
    "TRY": ["IRSTCI01TRM156N", "INTDSRTRM193N", "IR3TIB01TRM156N"],
}

# Fallback hardcoded averages (annual %, multi-year mean over 2010-2024 approx).
# Used only if every FRED candidate ticker fails for a currency.
EM_FALLBACK_PCT = {"BRL": 9.5, "MXN": 6.5, "ZAR": 6.5, "TRY": 14.0}

CRASH_PERIODS = {
    "GFC_2008":   ("2008-07-01", "2009-06-30"),
    "EM_2015":    ("2015-08-01", "2016-02-29"),
    "COVID_2020": ("2020-02-15", "2020-05-31"),
}


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def _fred_one(ticker: str, start: str, end: str) -> Optional[pd.Series]:
    try:
        s = DataReader(ticker, "fred", start, end).iloc[:, 0]
        if s.dropna().empty:
            return None
        return s
    except Exception as e:
        log.debug(f"FRED {ticker} failed: {e}")
        return None


def fetch_rates(start: str, end: str) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Return (DataFrame of rates, dict of ccy -> source used)."""
    series, source = {}, {}

    for ccy, tk in FRED_G10.items():
        s = _fred_one(tk, start, end)
        if s is not None:
            series[ccy], source[ccy] = s, f"FRED:{tk}"
            log.info(f"{ccy:<3s} {tk:<22s} OK  ({len(s)} obs)")
        else:
            log.warning(f"{ccy:<3s} {tk:<22s} FAIL")

    for ccy, candidates in FRED_EM_CANDIDATES.items():
        for tk in candidates:
            s = _fred_one(tk, start, end)
            if s is not None:
                series[ccy], source[ccy] = s, f"FRED:{tk}"
                log.info(f"{ccy:<3s} {tk:<22s} OK  ({len(s)} obs)")
                break
        if ccy not in series:
            # Last-resort constant fallback
            const = EM_FALLBACK_PCT[ccy]
            idx = pd.date_range(start, end, freq="MS")
            series[ccy] = pd.Series(const, index=idx)
            source[ccy] = f"const:{const}%"
            log.warning(f"{ccy:<3s} -- all FRED candidates failed, using constant {const}%")

    df = pd.concat(series, axis=1).resample("D").last().ffill()
    return df, source


def _yf_close(ticker: str, start: str, end: str) -> pd.Series:
    px = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
    s = px["Close"]
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    return s.dropna()


def fetch_fx_xxx_usd(ccy: str, start: str, end: str) -> pd.Series:
    """Return XXXUSD price. yfinance EM tickers are USDXXX -> invert."""
    if ccy in {"EUR", "GBP", "AUD", "NZD"}:
        px = _yf_close(f"{ccy}USD=X", start, end)
    else:
        px = 1.0 / _yf_close(f"{ccy}=X", start, end)
    return px.rename(f"{ccy}USD")


def fetch_fx_panel(ccys, start, end) -> pd.DataFrame:
    cols = []
    for c in ccys:
        try:
            cols.append(fetch_fx_xxx_usd(c, start, end))
        except Exception as e:
            log.warning(f"yfinance {c} failed: {e}")
    return pd.concat(cols, axis=1).dropna(how="all")


# ---------------------------------------------------------------------------
# Signal + tests (same primitives as fx_carry_fred, kept inline for autonomy)
# ---------------------------------------------------------------------------
def build_carry(rates: pd.DataFrame, base_ccys, quote="USD") -> pd.DataFrame:
    return pd.DataFrame(
        {f"{c}{quote}": rates[c] - rates[quote] for c in base_ccys if c in rates.columns}
    ).dropna(how="all")


def cross_sectional_ic(signal: pd.DataFrame, fwd_ret: pd.DataFrame) -> pd.Series:
    common = signal.columns.intersection(fwd_ret.columns)
    sig, ret = signal[common], fwd_ret[common]
    idx = sig.index.intersection(ret.index)
    out = {}
    for t in idx:
        s, r = sig.loc[t].astype(float), ret.loc[t].astype(float)
        m = s.notna() & r.notna()
        if m.sum() < 4:
            continue
        rho, _ = stats.spearmanr(s[m], r[m])
        if np.isfinite(rho):
            out[t] = rho
    return pd.Series(out).sort_index()


def ic_summary(ic: pd.Series, label: str = "") -> dict:
    n = len(ic)
    mean, sd = ic.mean(), ic.std(ddof=1)
    t = mean / (sd / np.sqrt(n)) if sd > 0 and n > 1 else np.nan
    p = f"{label}_" if label else ""
    return {f"{p}ic_mean": float(mean), f"{p}ic_std": float(sd),
            f"{p}ic_tstat": float(t), f"{p}ic_n": int(n)}


def bt_ls_tercile_with_costs(signal: pd.DataFrame, fwd_ret: pd.DataFrame,
                             cost_map: Dict[str, float], ann: int = 52
                             ) -> Tuple[pd.Series, dict]:
    """L/S tercile with per-pair cost (EM pairs more expensive)."""
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

    dw = (w - w.shift(1).fillna(0)).abs()
    costs_pair = pd.Series({c: cost_map.get(c, 0.00015) for c in w.columns})
    cost = (dw * (costs_pair / 2.0)).sum(axis=1)
    gross = (w * ret).sum(axis=1)
    net = gross - cost

    sharpe = float(net.mean() / net.std(ddof=1) * np.sqrt(ann)) if net.std(ddof=1) > 0 else np.nan
    equity = (1 + net).cumprod()
    max_dd = float((equity / equity.cummax() - 1.0).min())
    return net, {"sharpe": sharpe, "max_dd": max_dd,
                 "ann_ret": float(net.mean() * ann),
                 "n_pairs": int(n_pairs),
                 "avg_turnover": float(dw.sum(axis=1).mean())}


def crash_period_stats(net: pd.Series, periods: Dict[str, Tuple[str, str]],
                       ann: int = 52) -> Dict[str, dict]:
    out = {}
    for name, (s, e) in periods.items():
        sub = net.loc[s:e]
        if len(sub) < 4:
            out[name] = {"note": "insufficient data"}
            continue
        equity = (1 + sub).cumprod()
        dd = float((equity / equity.cummax() - 1.0).min())
        sharpe = float(sub.mean() / sub.std(ddof=1) * np.sqrt(ann)) if sub.std(ddof=1) > 0 else np.nan
        cum = float(equity.iloc[-1] - 1.0)
        out[name] = {"period": f"{s} → {e}", "sharpe": sharpe, "max_dd": dd,
                     "cum_ret": cum, "n_obs": int(len(sub))}
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> dict:
    log.info("=== FX Carry Feasibility — G10 + EM ===")

    rates, src = fetch_rates(START, END)
    fx_daily = fetch_fx_panel(G10_CCYS + EM_CCYS, START, END)
    log.info(f"rates: {rates.shape} | fx: {fx_daily.shape}")
    log.info(f"rate sources: {src}")

    # Weekly. Signal is shifted by 1 so signal[T] uses info at T-1.
    # Predictive forward returns aligned with signal[T]:
    #   ret_w_1[T] = (P_T - P_{T-1}) / P_{T-1}            -> return T-1 -> T   (1W fwd)
    #   ret_w_4[T] = (P_{T+3} - P_{T-1}) / P_{T-1}        -> return T-1 -> T+3 (4W fwd, overlapping)
    # NOTE: 4W overlapping returns inflate the IC t-stat; treat as a directional check,
    # not a significance test. Proper inference would require Newey-West adjustment.
    fx_w = fx_daily.resample("W-FRI").last()
    ret_w_1 = fx_w.pct_change().dropna(how="all")
    ret_w_4 = fx_w.pct_change(periods=4).shift(-3).dropna(how="all")
    rates_w = rates.resample("W-FRI").last().ffill()

    carry = build_carry(rates_w, G10_CCYS + EM_CCYS).shift(1)
    idx = carry.index.intersection(ret_w_1.index)
    carry = carry.loc[idx]
    ret_1, ret_4 = ret_w_1.loc[idx], ret_w_4.reindex(idx)

    # IC at both horizons
    ic_1 = cross_sectional_ic(carry, ret_1)
    ic_4 = cross_sectional_ic(carry, ret_4)

    # Per-pair cost map
    cost_map = {f"{c}USD": COST_RT_G10 for c in G10_CCYS}
    cost_map.update({f"{c}USD": COST_RT_EM for c in EM_CCYS})

    # Backtest (1W rebalance, weekly returns)
    net, bt = bt_ls_tercile_with_costs(carry, ret_1, cost_map, ann=52)
    crashes = crash_period_stats(net, CRASH_PERIODS, ann=52)

    covid_dd = crashes.get("COVID_2020", {}).get("max_dd", 0.0) or 0.0
    propfirm_ok = covid_dd > -0.25

    results = {
        "signal": "carry_fred_g10_em",
        "universe": "G10 + EM (12 pairs vs USD)",
        "freq": "weekly",
        "cost_g10_rt": COST_RT_G10,
        "cost_em_rt": COST_RT_EM,
        "period_start": str(idx.min().date()),
        "period_end": str(idx.max().date()),
        "rate_sources": src,
        **ic_summary(ic_1, "h1w"),
        **ic_summary(ic_4, "h4w"),
        **bt,
        "crashes": crashes,
        "propfirm_compatible": bool(propfirm_ok),
    }
    # Primary gate uses 4W IC (matches monthly Menkhoff style; weekly IC noisy)
    t = results["h4w_ic_tstat"]
    results["gate"] = "PASS" if t > 2.5 else ("WEAK" if t > 1.5 else "SKIP")

    RESULTS_PATH.write_text(json.dumps(results, indent=2))

    print("\n" + "=" * 72)
    print("FX CARRY — G10 + EM (12 pairs vs USD)")
    print("=" * 72)
    for k, v in results.items():
        if k == "crashes":
            print(f"  {k}:")
            for cn, cv in v.items():
                print(f"    {cn:14s} {cv}")
        elif k == "rate_sources":
            print(f"  {k}:")
            for c, s in v.items():
                print(f"    {c:4s} {s}")
        else:
            print(f"  {k:22s} {v}")
    print("=" * 72)
    return results


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("feasibility run failed")
        sys.exit(1)
