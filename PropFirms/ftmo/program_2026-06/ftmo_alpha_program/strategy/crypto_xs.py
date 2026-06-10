"""
crypto_xs.py — cross-sectional crypto screen harness (170+ token, 8h funding+price panel)
==========================================================================================

Minimal-gate research screen (FTMO criteria dropped). A strategy "passes" only if it is:
  (1) causal (signals lagged, weights applied next bar), (2) net of realistic crypto cost
  (0.17% round-trip on turnover), (3) net-positive on the UNTOUCHED hold-out (2025-2026),
  not just in-sample. Dollar-neutral long-short → escapes the long-only beta dominance (L11).

Data: data/funding_carry/prices/<TOK>_8h.csv (OHLC) + data/funding_carry/<TOK>_funding.csv
(funding_rate_1h). 8h bars; longs PAY funding when funding>0.
"""
from __future__ import annotations

import glob
import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

REPO = __import__("pathlib").Path(__file__).resolve().parents[3]
FC = REPO / "data" / "funding_carry"
BARS_PER_YEAR = 365 * 3          # 8h bars
COST_RT = 0.0017                 # crypto round-trip (CLAUDE.md); one-way = half
OOS_START = "2025-01-01"


def load_panel(min_bars: int = 300):
    closes, funds = {}, {}
    for p in glob.glob(str(FC / "prices" / "*_8h.csv")):
        tok = os.path.basename(p).replace("_8h.csv", "")
        df = pd.read_csv(p, parse_dates=["timestamp"]).set_index("timestamp")
        if len(df) >= min_bars:
            closes[tok] = df["close"]
    for p in glob.glob(str(FC / "*_funding.csv")):
        tok = os.path.basename(p).replace("_funding.csv", "")
        df = pd.read_csv(p, parse_dates=["timestamp"]).set_index("timestamp")
        funds[tok] = df["funding_rate_1h"]
    C = pd.DataFrame(closes).sort_index()
    F = pd.DataFrame(funds).sort_index().reindex(C.index).reindex(columns=C.columns)
    C = C[~C.index.duplicated()]; F = F[~F.index.duplicated()]
    return C, F


def _weights_from_signal(sig_row: pd.Series, q: float) -> pd.Series:
    """Dollar-neutral equal-weight: long top-q quantile, short bottom-q. Gross exposure = 1."""
    s = sig_row.dropna()
    if len(s) < 10:
        return pd.Series(0.0, index=sig_row.index)
    n = max(1, int(len(s) * q))
    order = s.sort_values()
    short, long = order.index[:n], order.index[-n:]
    w = pd.Series(0.0, index=sig_row.index)
    w[long] = 0.5 / len(long)
    w[short] = -0.5 / len(short)
    return w


@dataclass
class XSResult:
    ret: pd.Series          # net 8h portfolio return
    turnover_yr: float
    metrics_is: dict
    metrics_oos: dict


def xs_backtest(C: pd.DataFrame, F: pd.DataFrame, signal: pd.DataFrame,
                rebal_bars: int = 3, q: float = 0.2, include_funding: bool = False) -> XSResult:
    """
    Long-short dollar-neutral cross-sectional backtest. `signal` must already be causal
    (known at the bar it is indexed on); weights are applied to the NEXT bar's return.
    """
    R = C.pct_change()
    F8 = F * 8.0                                  # 8h funding (longs pay when >0)
    idx = C.index
    rebal = np.zeros(len(idx), dtype=bool); rebal[::rebal_bars] = True

    W = pd.DataFrame(np.nan, index=idx, columns=C.columns)
    for i in np.flatnonzero(rebal):
        W.iloc[i] = _weights_from_signal(signal.iloc[i], q).values
    W = W.ffill().fillna(0.0)

    Wlag = W.shift(1)
    gross = (Wlag * R).sum(axis=1)
    fund_pnl = -(Wlag * F8).sum(axis=1) if include_funding else 0.0
    turn = W.diff().abs().sum(axis=1)
    cost = turn * (COST_RT / 2.0)
    net = (gross + fund_pnl - cost).dropna()
    turn_yr = float(turn.reindex(net.index).fillna(0).mean() * BARS_PER_YEAR)

    def m(r):
        r = r.dropna()
        if len(r) < 30 or r.std() == 0:
            return {"n": len(r), "sharpe": 0.0, "ann_ret": 0.0}
        return {"n": int(len(r)), "sharpe": float(r.mean() / r.std() * np.sqrt(BARS_PER_YEAR)),
                "ann_ret": float(r.mean() * BARS_PER_YEAR)}
    return XSResult(net, turn_yr, m(net.loc[:OOS_START]), m(net.loc[OOS_START:]))


# ── signal builders (all causal: indexed on the bar where the info is known) ──
def sig_momentum(C, k):           # trailing k-bar return → long winners
    return C.pct_change(k)

def sig_reversal(C, k):           # short-term reversal → long losers (fade)
    return -C.pct_change(k)

def sig_carry(F):                 # long low-funding / short high-funding (collect funding)
    return -F

def sig_funding_mom(F, k):        # funding momentum (rising funding)
    return F - F.shift(k)
