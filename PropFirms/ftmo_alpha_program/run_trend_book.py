"""
run_trend_book.py — diversified daily trend-following book (FTMO-Swing-actionable)
===================================================================================
Canonical CTA: one trend signal diversified across many markets; Sharpe comes from
diversification, not tuning. Anti-overfit: textbook variants (TSMOM / Donchian / MA-cross),
per-instrument vol-scaled, equal-risk book, honest cost (CFD swap ~1 bp/day held + spread on
flips), judged on the untouched hold-out 2025-2026.

Universe: ready daily panels (equity sectors/regions, FX, commodities, BTC). Most map to FTMO
CFDs (US/EU indices, FX majors, oil, platinum). Commodity ETFs carry roll drag → signal-proxy
only (L5). Requires the FTMO Swing account (trend holds over weekends).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
PAN = REPO / "data" / "panels"
OOS_START = "2025-01-01"
HOLD_COST_BPS = 1.0      # net swap/markup per day held (conservative, two-sided book)
FLIP_BPS = 3.0           # spread per position flip


def load_daily():
    frames = []
    for f in ["equity_panel.csv", "fx_panel.csv", "softs_metals.csv"]:
        df = pd.read_csv(PAN / f, parse_dates=["Date"]).set_index("Date")
        frames.append(df)
    btc = pd.read_csv(PAN / "btc_full.csv", parse_dates=["Date"]).set_index("Date")
    frames.append(btc)
    P = pd.concat(frames, axis=1).sort_index()
    P = P[~P.index.duplicated()].astype(float)
    return P.loc["2008-01-01":]


def vol_scaled_positions(P, signal, target_vol=0.10, lev_cap=2.0):
    """Per-instrument: position = sign(signal) scaled to target annual vol (causal)."""
    R = P.pct_change()
    vol = R.rolling(63).std().shift(1) * np.sqrt(252)
    pos = np.sign(signal) * (target_vol / vol).clip(upper=lev_cap)
    return pos.where(P.notna() & signal.notna())


def book_backtest(P, signal, rebal=5):
    R = P.pct_change()
    pos = vol_scaled_positions(P, signal)
    # rebalance every `rebal` days (reduce turnover/cost)
    mask = np.zeros(len(P), bool); mask[::rebal] = True
    pos = pos.where(pd.Series(mask, index=P.index), np.nan).ffill()
    posL = pos.shift(1)
    # equal-weight across available instruments each day
    navail = posL.notna().sum(axis=1).clip(lower=1)
    gross = (posL * R).sum(axis=1) / navail
    turn = (pos - pos.shift(1)).abs().sum(axis=1) / navail
    held = posL.abs().sum(axis=1) / navail
    cost = turn * (FLIP_BPS / 1e4) + held * (HOLD_COST_BPS / 1e4)
    net = (gross - cost).dropna()
    return net


def sh(r, span=None):
    r = r.loc[:OOS_START] if span == "is" else (r.loc[OOS_START:] if span == "oos" else r)
    r = r.dropna()
    return float(r.mean() / r.std() * np.sqrt(252)) if len(r) > 30 and r.std() > 0 else 0.0


def tsmom(P, k):       # time-series momentum: sign of trailing k-day return
    return P.pct_change(k)

def donchian(P, k):    # breakout: +1 if at k-day high, -1 if at k-day low
    hi = P.rolling(k).max().shift(1); lo = P.rolling(k).min().shift(1)
    return (P > hi).astype(float) - (P < lo).astype(float)

def macross(P, fast, slow):
    return P.rolling(fast).mean() - P.rolling(slow).mean()


def main() -> int:
    P = load_daily()
    print("=" * 80)
    print("DIVERSIFIED TREND BOOK — daily, cross-asset, FTMO-Swing-actionable")
    print(f"universe: {P.shape[1]} instruments, {P.index.min().date()} → {P.index.max().date()}, "
          f"hold-out from {OOS_START}")
    print("=" * 80)
    print(f"{'variant':22} {'IS_sharpe':>10} {'OOS_sharpe':>11}")
    nets = {}
    for k in [50, 100, 200]:
        n = book_backtest(P, tsmom(P, k)); nets[f"TSMOM {k}d"] = n
        print(f"{'TSMOM '+str(k)+'d':22} {sh(n,'is'):>10.2f} {sh(n,'oos'):>11.2f}")
    for k in [50, 100]:
        n = book_backtest(P, donchian(P, k)); nets[f"Donchian {k}d"] = n
        print(f"{'Donchian '+str(k)+'d':22} {sh(n,'is'):>10.2f} {sh(n,'oos'):>11.2f}")
    n = book_backtest(P, macross(P, 20, 100)); nets["MA 20/100"] = n
    print(f"{'MA-cross 20/100':22} {sh(n,'is'):>10.2f} {sh(n,'oos'):>11.2f}")

    # ensemble of the textbook variants (standard CTA: average the signals' books) — not tuning
    ens = pd.concat([nets["TSMOM 100d"], nets["TSMOM 200d"], nets["Donchian 100d"], nets["MA 20/100"]], axis=1).mean(axis=1)
    print(f"\n{'ENSEMBLE (avg books)':22} {sh(ens,'is'):>10.2f} {sh(ens,'oos'):>11.2f}")
    print(f"\nNet of {HOLD_COST_BPS}bp/day swap + {FLIP_BPS}bp/flip spread. Diversification across "
          f"{P.shape[1]} markets is the Sharpe lever, not tuning.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
