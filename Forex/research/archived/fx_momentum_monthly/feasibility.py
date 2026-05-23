"""
fx_momentum_monthly/feasibility.py
==================================
FX momentum feasibility at MONTHLY horizon — fix vs prior weekly test.

Previous run: IC = -0.001, t = -0.06 (12M-1M signal vs 1-week forward).
Diagnosis: wrong forward horizon. Menkhoff et al. (2012) document FX
momentum at 1-month holding periods; 1-week corresponds to short-term
reversal regime in FX (Burnside et al., 2011).

Methodology
-----------
- Universe : 8 G10 currencies vs USD (XXXUSD convention)
- Frequency: monthly (M-end close, rebalance 1st bday of month)
- Cost     : 1.5 bps RT (FX spread) -> ~18 bps/yr at 12 trades/yr

Signal A — Cross-sectional momentum (Menkhoff 2012)
    mom_cs[t] = cumret[t-12M : t-1M] / (vol_12M[t] * sqrt(11))
    - Skip last month (well-documented 1M reversal)
    - Vol scaling via 12M monthly stdev
    - L/S tercile portfolio

Signal B — Time-series momentum, tanh-scaled
    tsmom[t] = tanh( cumret_12M[t] / (vol_12M[t] * sqrt(12)) )
    - Same family as crypto Strategy A, monthly horizon
    - Allows shorts (FX short leg is documented to work, cf. Moskowitz 2012)

Both signals shifted by 1 month (signal at T-1, trade T).
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
START = "2005-01-01"
END = pd.Timestamp.today().strftime("%Y-%m-%d")
COST_RT = 0.00015                              # 15 bps RT
RESULTS_PATH = Path(__file__).parent / "results.json"

G10_CCYS = ["EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NOK", "SEK"]
LB = 12                                        # 12-month lookback
SKIP = 1                                       # skip last month (CS momentum)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def _yf_close(ticker: str, start: str, end: str) -> pd.Series:
    px = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)
    s = px["Close"]
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    return s.dropna()


def fetch_fx_xxx_usd(ccy: str, start: str, end: str) -> pd.Series:
    if ccy in {"EUR", "GBP", "AUD", "NZD"}:
        px = _yf_close(f"{ccy}USD=X", start, end)
    else:
        px = 1.0 / _yf_close(f"{ccy}=X", start, end)
    return px.rename(f"{ccy}USD")


def fetch_fx_panel(ccys, start: str, end: str) -> pd.DataFrame:
    cols = []
    for c in ccys:
        try:
            cols.append(fetch_fx_xxx_usd(c, start, end))
        except Exception as e:
            log.warning(f"yfinance failed for {c}: {e}")
    return pd.concat(cols, axis=1).dropna(how="all")


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------
def cs_momentum_signal(px_m: pd.DataFrame, lb: int = LB, skip: int = SKIP) -> pd.DataFrame:
    """cumret[t-lb : t-skip] / (vol_lb * sqrt(lb-skip)) — vol-scaled CS momentum."""
    logret = np.log(px_m / px_m.shift(1))
    # cumulative return over [t-lb, t-skip]: sum of (lb-skip) monthly log-returns,
    # ending at t-skip (i.e. shifted forward by `skip` months)
    cumret = logret.rolling(lb - skip).sum().shift(skip)
    vol = logret.rolling(lb).std()
    return cumret / (vol * np.sqrt(lb - skip))


def tsmom_tanh_signal(px_m: pd.DataFrame, lb: int = LB) -> pd.DataFrame:
    """tanh( cumret_lb / (vol_lb * sqrt(lb)) ) — TSMOM, monthly, no clipping."""
    logret = np.log(px_m / px_m.shift(1))
    cumret = logret.rolling(lb).sum()
    vol = logret.rolling(lb).std()
    return np.tanh(cumret / (vol * np.sqrt(lb)))


# ---------------------------------------------------------------------------
# Tests (IC + backtests)
# ---------------------------------------------------------------------------
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


def ic_summary(ic: pd.Series) -> dict:
    n = len(ic)
    mean, sd = ic.mean(), ic.std(ddof=1)
    t = mean / (sd / np.sqrt(n)) if sd > 0 and n > 1 else np.nan
    return {"ic_mean": float(mean), "ic_std": float(sd),
            "ic_tstat": float(t), "ic_n": int(n)}


def bt_ls_tercile(signal: pd.DataFrame, fwd_ret: pd.DataFrame,
                  cost_rt: float, ann: int = 12) -> dict:
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
    net = gross - turnover * (cost_rt / 2.0)
    return _stats(net, ann, n_pairs, turnover)


def bt_tsmom(signal: pd.DataFrame, fwd_ret: pd.DataFrame,
             cost_rt: float, ann: int = 12) -> dict:
    """TSMOM time-series: each pair sized by tanh signal, averaged across pairs."""
    common = signal.columns.intersection(fwd_ret.columns)
    sig = signal[common].dropna(how="all")
    ret = fwd_ret[common]
    idx = sig.index.intersection(ret.index)
    sig, ret = sig.loc[idx], ret.loc[idx]
    n_pairs = sig.shape[1]

    # Average over pairs, leverage 1 by construction (tanh in [-1, 1], / n_pairs)
    w = sig.fillna(0.0) / n_pairs
    gross = (w * ret).sum(axis=1)
    turnover = (w - w.shift(1).fillna(0)).abs().sum(axis=1)
    net = gross - turnover * (cost_rt / 2.0)
    return _stats(net, ann, n_pairs, turnover)


def _stats(net: pd.Series, ann: int, n_pairs: int, turnover: pd.Series) -> dict:
    sharpe = float(net.mean() / net.std(ddof=1) * np.sqrt(ann)) if net.std(ddof=1) > 0 else np.nan
    equity = (1 + net).cumprod()
    max_dd = float((equity / equity.cummax() - 1.0).min())
    return {"sharpe": sharpe, "max_dd": max_dd,
            "ann_ret": float(net.mean() * ann),
            "n_pairs": int(n_pairs),
            "avg_turnover": float(turnover.mean())}


def _gate(t: float) -> str:
    return "PASS" if t > 2.5 else ("WEAK" if t > 1.5 else "SKIP")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> dict:
    log.info("=== FX Momentum Feasibility — G10, MONTHLY horizon ===")

    fx_daily = fetch_fx_panel(G10_CCYS, START, END)
    log.info(f"fx daily: {fx_daily.shape}")

    # Month-end close, monthly returns
    px_m = fx_daily.resample("M").last()
    ret_m = px_m.pct_change().dropna(how="all")

    # Signals at T-1 month
    sig_cs = cs_momentum_signal(px_m).shift(1)
    sig_ts = tsmom_tanh_signal(px_m).shift(1)

    # Align with returns
    idx = ret_m.index
    sig_cs = sig_cs.reindex(idx)
    sig_ts = sig_ts.reindex(idx)

    # IC + backtest per signal
    ic_cs = cross_sectional_ic(sig_cs, ret_m)
    ic_ts = cross_sectional_ic(sig_ts, ret_m)
    bt_cs = bt_ls_tercile(sig_cs, ret_m, COST_RT, ann=12)
    bt_ts = bt_tsmom(sig_ts, ret_m, COST_RT, ann=12)

    cs = {"signal": "momentum_cs_monthly_g10", "universe": "G10 vs USD",
          "freq": "monthly", "cost_rt": COST_RT,
          **ic_summary(ic_cs), **bt_cs}
    cs["gate"] = _gate(cs["ic_tstat"])

    ts = {"signal": "tsmom_monthly_g10", "universe": "G10 vs USD",
          "freq": "monthly", "cost_rt": COST_RT,
          **ic_summary(ic_ts), **bt_ts}
    ts["gate"] = _gate(ts["ic_tstat"])

    results = {"momentum_cs": cs, "tsmom": ts,
               "period_start": str(idx.min().date()),
               "period_end": str(idx.max().date())}
    RESULTS_PATH.write_text(json.dumps(results, indent=2))

    for label, r in (("CS MOMENTUM 12M-1M (Menkhoff)", cs),
                     ("TSMOM TANH 12M (Moskowitz)", ts)):
        print("\n" + "=" * 72)
        print(label)
        print("=" * 72)
        for k, v in r.items():
            print(f"  {k:18s} {v}")
    print("=" * 72)
    return results


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("feasibility run failed")
        sys.exit(1)
