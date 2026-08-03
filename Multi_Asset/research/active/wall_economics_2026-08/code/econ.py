"""Renewal-reward pricing of the self-imposed wall.

A "cycle" = one campaign run under a wall of W calendar days. It ends either
  * FUNDED at T_f days (probability p), or
  * ABANDONED at day W (probability 1-p) -> a fresh challenge is bought.

Cost per cycle = attempts(W) x fee. FTMO refunds the challenge fee on the first
payout, so a funded cycle recovers exactly one fee.

    rate(W) = [ p(W) * (V + fee) - attempts(W) * fee ] / E[cycle days]
    E[cycle days] = p(W) * mean_days_funded(W) + (1 - p(W)) * W

`rate` is dollars per CALENDAR DAY of hunting. It is the quantity the wall trades:
a longer wall buys p(W) at the price of E[cycle days]. Maximising p(W) alone, or
minimising duration alone, both give the wrong wall.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEE = 107.0          # FTMO $10k Swing challenge, EUR 99 at ~1.08
FEE_REFUND = True    # spec_v22.yaml funded.withdrawals.fee_refund: "1er payout"

# Value of a delivered funded account (trader share, measured ledger).
V_SCENARIOS = {
    "pessimistic  (ORB-off branch, 2y)": 1262.0,
    "validation window (VAL)":           1381.0,
    "BASELINE (v2.2.1 OOS 2y, measured costs)": 2529.0,
    "spec era default (v2.2 OOS 2y)":    2632.0,
    "optimistic (0.61bps branch, 2y)":   2897.0,
    "memory anchor $197/mo x 24m":       4728.0,
}
V_BASE = 2529.0


def rate(p: float, attempts: float, mean_days_funded: float, wall: float,
         v: float = V_BASE, fee: float = FEE, refund: bool = FEE_REFUND) -> float:
    cycle = p * mean_days_funded + (1.0 - p) * wall
    if cycle <= 0:
        return np.nan
    gain = p * (v + (fee if refund else 0.0)) - attempts * fee
    return gain / cycle


def table(df: pd.DataFrame, v: float = V_BASE, fee: float = FEE) -> pd.DataFrame:
    out = df.copy()
    out["ev_cycle_usd"] = [
        r.p_campaign * (v + (fee if FEE_REFUND else 0.0)) - r.avg_attempts * fee
        for r in df.itertuples()]
    out["cycle_days"] = [
        r.p_campaign * (r.mean_days if np.isfinite(r.mean_days) else r.wall)
        + (1 - r.p_campaign) * r.wall for r in df.itertuples()]
    out["usd_per_day"] = out["ev_cycle_usd"] / out["cycle_days"]
    out["usd_per_month"] = out["usd_per_day"] * 30.44
    # unconditional expected calendar days to a funded account (geometric renewal)
    out["exp_days_to_funded"] = out["cycle_days"] / out["p_campaign"].replace(0, np.nan)
    out["exp_fees_to_funded"] = out["avg_attempts"] * fee / out["p_campaign"].replace(0, np.nan)
    return out


def optimal_wall(df: pd.DataFrame, v: float, fee: float = FEE) -> tuple[int, float]:
    t = table(df, v=v, fee=fee)
    i = t["usd_per_day"].idxmax()
    return int(t.loc[i, "wall"]), float(t.loc[i, "usd_per_day"])
