"""Renewal-reward economics of the wall, on the CORRECTED harness and an AUDITED V.

    rate(W) = [ p(W)*(V + fee) - attempts(W)*fee ] / E[cycle days]
    E[cycle days] = p(W)*E[T_f | funded] + (1-p(W))*W

V is the trader's value of ONE delivered funded account. Two corrections vs the first
pass, both established in audit_v.py / audit_v_provenance.py:

  (1) the cited $2,529 is a GROSS extraction (`wd + residual`), not the trader share.
      RECOST itself applies the split separately: `VAL = FEE + 0.8*extr_pooled`
      (`run_recost_v221.py:193`). Trader share of $2,529 is $2,023.
  (2) $2,529 is the OOS half (2020-01 -> 2024-06) of the FULL 4-sleeve book. The
      DEPLOYED book is MONO. Same engine, same windows, gold w=0 and J1 off:
      OOS $1,494 gross, pooled $978 gross.

So the deployed-book V range, trader share, is $347 (MONO/IS) to $1,195 (MONO/OOS),
centred on $782 (MONO/pooled). The first pass's point estimate is ABOVE the entire range.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEE = 107.0          # EUR 99 FTMO $10k Swing at ~1.08; refunded on the 1st payout
SPLIT = 0.80

# Measured directly (tables/v_provenance.csv), trader share = 0.80 * mean extraction.
V_GRID = {
    "MONO / IS  2013-17  (deployed book, weak regime)":        347.0,
    "MONO / POOLED       (deployed book, BASELINE)":           782.0,
    "MONO / OOS 2020-24  (deployed book, strong regime)":     1195.0,
    "FULL 4-sleeve / POOLED (if gold + J1 re-arm)":           1347.0,
    "FULL 4-sleeve / OOS    (if gold + J1 re-arm, strong)":   2105.0,
    "first pass's V (OOS gross, NOT trader share)":           2529.0,
}
V_BASE = 782.0


def table(df: pd.DataFrame, v: float = V_BASE, fee: float = FEE) -> pd.DataFrame:
    out = df.copy()
    out["ev_cycle_usd"] = out["p_campaign"] * (v + fee) - out["avg_attempts"] * fee
    tf = out["mean_days"].where(np.isfinite(out["mean_days"]), out["wall"])
    out["cycle_days"] = out["p_campaign"] * tf + (1 - out["p_campaign"]) * out["wall"]
    out["usd_per_day"] = out["ev_cycle_usd"] / out["cycle_days"]
    out["usd_per_month"] = out["usd_per_day"] * 30.44
    out["exp_days_to_funded"] = out["cycle_days"] / out["p_campaign"].replace(0, np.nan)
    out["exp_fees_to_funded"] = out["avg_attempts"] * fee / out["p_campaign"].replace(0, np.nan)
    return out


def breakeven_V(row, fee: float = FEE) -> float:
    """V at which $/day = 0 for one wall (cycle days > 0 always)."""
    return row.avg_attempts * fee / row.p_campaign - fee if row.p_campaign > 0 else np.inf


def optimal_wall_curve(df: pd.DataFrame, vs: np.ndarray, fee: float = FEE) -> pd.DataFrame:
    rows = []
    for v in vs:
        t = table(df, v=v, fee=fee)
        i = t["usd_per_day"].idxmax()
        rows.append(dict(V=v, best_wall=int(t.loc[i, "wall"]),
                         best_usd_per_day=float(t.loc[i, "usd_per_day"]),
                         usd_per_day_at_91=float(t.loc[t.wall == 91, "usd_per_day"].iloc[0]),
                         any_positive=bool((t["usd_per_day"] > 0).any())))
    return pd.DataFrame(rows)
