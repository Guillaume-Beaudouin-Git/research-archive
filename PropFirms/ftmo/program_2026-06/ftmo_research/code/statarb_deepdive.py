"""
statarb_deepdive.py — Pairs / stat-arb deep-dive for FTMO.

The two-sided-by-construction family: long A / short B cancels beta, so the test
that killed every other family (one-sided long-beta) cannot apply. The relevant
killers here are different and specific:
  (a) cost on TWO legs + rebalancing
  (b) spread half-life (need hours..few days, not >30d as equity pairs)
  (c) OOS cointegration stability (relations break — the classic stat-arb killer)
  (d) short-CFD financing if the hold is multi-day (the overnight trap returning)

Pipeline: 1H aligned closes -> EG cointegration (ADF) + OU half-life + OOS
stability -> spread z-score MR backtest with 2-leg cost + overnight financing,
two-sided-in-spread -> DSR on total pairs x params.
"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from pathlib import Path
from statsmodels.tsa.stattools import adfuller

SA = Path("/sessions/blissful-upbeat-newton/mnt/outputs/sa")
COSTS = json.load(open(SA / "costs.json"))

PAIRS = [
    ("US100", "US500"), ("US500", "US30"), ("US100", "US30"),
    ("EURUSD", "GBPUSD"), ("AUDUSD", "NZDUSD"), ("USDCAD", "USDCHF"),
    ("EURUSD", "USDCHF"), ("GBPUSD", "AUDUSD"),
    ("USDJPY", "EURJPY"), ("EURJPY", "AUDJPY"), ("USDJPY", "AUDJPY"),
    ("XAUUSD", "AUDUSD"), ("XAUUSD", "USDCHF"), ("AUDJPY", "NZDUSD"),
    ("GER40", "EURUSD"), ("EURUSD", "EURGBP"), ("GBPUSD", "EURGBP"),
    ("US100", "GER40"),
]


def load_pair(a, b):
    A = pd.read_parquet(SA / f"{a}_1h.parquet")["close"].rename(a)
    B = pd.read_parquet(SA / f"{b}_1h.parquet")["close"].rename(b)
    df = pd.concat([A, B], axis=1).dropna()
    return df


def ou_half_life(spread: pd.Series) -> float:
    s = spread.dropna()
    lag = s.shift(1)
    d = (s - lag).dropna()
    lag = lag.loc[d.index]
    beta = np.polyfit(lag.values, d.values, 1)[0]      # d_t = beta*s_{t-1}
    phi = 1 + beta
    if not (0 < phi < 1):
        return np.nan
    return float(-np.log(2) / np.log(phi))             # in bars (=hours)


def eg_pvalue(logA, logB):
    """Engle-Granger: OLS hedge ratio then ADF on residual. Returns (beta, p)."""
    X = np.vstack([np.ones(len(logB)), logB.values]).T
    coef, *_ = np.linalg.lstsq(X, logA.values, rcond=None)
    resid = logA.values - X @ coef
    p = adfuller(resid, maxlag=24, autolag=None)[1]
    return coef[1], resid, p


if __name__ == "__main__":
    rows = []
    for a, b in PAIRS:
        df = load_pair(a, b)
        if len(df) < 2000:
            rows.append((a, b, len(df), np.nan, np.nan, np.nan, np.nan, np.nan)); continue
        logA = np.log(df[a]); logB = np.log(df[b])
        beta, resid, p_full = eg_pvalue(logA, logB)
        hl = ou_half_life(pd.Series(resid))
        corr = df[a].pct_change().corr(df[b].pct_change())
        # OOS stability: beta on first half, ADF on second-half residual
        n = len(df); h = n // 2
        X1 = np.vstack([np.ones(h), logB.values[:h]]).T
        c1, *_ = np.linalg.lstsq(X1, logA.values[:h], rcond=None)
        resid_oos = logA.values[h:] - (c1[0] + c1[1] * logB.values[h:])
        p_oos = adfuller(resid_oos, maxlag=24, autolag=None)[1]
        rows.append((a, b, n, corr, beta, p_full, hl, p_oos))
    T = pd.DataFrame(rows, columns=["A", "B", "n", "ret_corr", "beta",
                                    "EG_p_full", "HL_hours", "EG_p_OOS"])
    T.to_csv(SA / "coint_screen.csv", index=False)
    pd.set_option("display.width", 200)
    print("=== Cointegration + half-life + OOS stability (1H bars) ===")
    print("coint if EG_p<0.05; tradeable HL ~ hours..~72h; OOS-stable if EG_p_OOS<0.05 too")
    print(T.round(3).to_string(index=False))
    print("\nPairs cointegrated FULL (p<0.05):",
          T[(T.EG_p_full < 0.05)][["A", "B"]].apply(lambda r: f"{r.A}/{r.B}", axis=1).tolist())
    print("Pairs cointegrated FULL **and** OOS (both p<0.05):",
          T[(T.EG_p_full < 0.05) & (T.EG_p_OOS < 0.05)][["A", "B"]].apply(lambda r: f"{r.A}/{r.B}", axis=1).tolist())
