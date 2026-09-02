"""Shared loader for the ORB decision-dossier analysis (desk_orb_2026-09).

Ledger: PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet
N=4013, 2010-06-07 -> 2026-05-29. Reproduces the per-trade leverage cost model used
in audit_ledger_orb_2026-08 (lev = level / |level - stop_eff|, cost_R = bps*1e-4*lev),
validated below against the published t-stats (ALL 1.530 / LONG 1.693 / SHORT 0.542 at 0.962 bps).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

LEDGER_PATH = (
    "<HOME>/Desktop/Algo_claude/PropFirms/ftmo/program_2026-06/"
    "ftmo_research/audit/nq_v2_trades.parquet"
)

SPREAD_NATIVE_BPS = 0.962  # mesuré, fenêtre ORB, native FTMO (orb_cost_funded_2026-08 AMENDEMENT n1)
COST_LOW_BPS = 1.69   # point mort jambe courte (audit_ledger_orb_2026-08 §6, levier par trade)
COST_HIGH_BPS = 2.17  # point mort two-sided agrégé (Sum(R) -> ~0, audit_ledger_orb_2026-08 §6)


def load_ledger() -> pd.DataFrame:
    df = pd.read_parquet(LEDGER_PATH)
    df = df.sort_index()
    df["lev"] = df["level"] / (df["level"] - df["stop_eff"]).abs()
    return df


def cost_R(df: pd.DataFrame, cost_bps: float) -> pd.Series:
    """Round-trip spread cost expressed in R units, per-trade leverage (not median lev)."""
    return cost_bps * 1e-4 * df["lev"]


def net_R(df: pd.DataFrame, cost_bps: float) -> pd.Series:
    return df["r_gross"] - cost_R(df, cost_bps)


def hac_t(x: pd.Series, lags: int = 6) -> tuple[float, float, float, float, int]:
    """Return (mean, se, t, n) via HAC lag-6 Newey-West, one-sample (intercept-only OLS)."""
    x = x.dropna().values
    n = len(x)
    if n < 3:
        return np.nan, np.nan, np.nan, np.nan, n
    X = np.ones((n, 1))
    model = sm.OLS(x, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    mean = model.params[0]
    se = model.bse[0]
    t = model.tvalues[0]
    return mean, se, t, n


def block_bootstrap_ci(x: np.ndarray, n_boot: int = 5000, block: int = 10, seed: int = 42):
    rng = np.random.default_rng(seed)
    n = len(x)
    means = np.empty(n_boot)
    n_blocks = int(np.ceil(n / block))
    for b in range(n_boot):
        idx = []
        for _ in range(n_blocks):
            start = rng.integers(0, n)
            idx.extend([(start + k) % n for k in range(block)])
        idx = idx[:n]
        means[b] = x[idx].mean()
    return np.percentile(means, 2.5), np.percentile(means, 97.5)


if __name__ == "__main__":
    df = load_ledger()
    r_net = net_R(df, SPREAD_NATIVE_BPS)
    for leg, mask in [("ALL", slice(None)), ("LONG", df["direction"] == 1), ("SHORT", df["direction"] == -1)]:
        sub = r_net[mask] if leg != "ALL" else r_net
        mean, se, t, n = hac_t(sub)
        print(f"{leg:6s} n={n:5d} mean={mean:+.4f} t_hac6={t:+.3f}")
