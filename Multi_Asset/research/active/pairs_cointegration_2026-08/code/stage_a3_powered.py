"""
Stage A3 — properly powered re-test of the three L25 survivors.

Why this exists. D3 measured reversion on OVERLAPPING windows (horizon 144-288
M5 bars, stepped one bar at a time) with HAC lag-6. The magnitudes in bps are
unbiased, but the t-stats are NOT: the effective autocorrelation length is at
least the horizon itself, so N_eff << N and lag-6 HAC understates the variance
by a wide margin (L12b, the ETH-netflow lesson: t 2.58 -> HAC 0.11). A t of 13
on 228k overlapping observations is an artefact of the overlap, not evidence.

So: rebuild NON-OVERLAPPING trades (one position at a time, no re-entry while
open), delay+1 on entry AND exit (K7/L59), and put a stationary block bootstrap
on the trade series instead of trusting any t-stat.

Costs, both legs, honest: RT per leg from COST_AUDIT + carry at 1.5 bps per
night held for the PAIR (L28), counted per UTC date boundary crossed.

L38 orthogonality: regress the sleeve's daily P&L on the daily returns of each
leg. R^2 > 30% => this is directional exposure wearing a spread's clothes.
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage_a_halflife import _read, START, END
from stage_b_strategy import COST_RT

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/outputs"

FORM_DAYS, TRADE_DAYS = 20, 5
Z_IN, Z_OUT, H_MAX = 2.0, 0.5, 288      # 24h maximum hold
CARRY_BPS_NIGHT = 1.5                    # L28, for the PAIR (both legs)

CANDIDATES = [("UKOIL", "USOIL"), ("AUDUSD", "USDCAD"), ("AUDUSD", "NZDUSD")]


def series(a, b):
    df = pd.concat([_read(a, ["open", "close"]).loc[START:END].add_prefix("A_"),
                    _read(b, ["open", "close"]).loc[START:END].add_prefix("B_")],
                   axis=1).dropna()
    for c in "AB":
        df[f"l{c}c"] = np.log(df[f"{c}_close"])
        df[f"l{c}o"] = np.log(df[f"{c}_open"])
    df["day"] = df.index.normalize()
    return df


def trades(a, b):
    df = series(a, b)
    days = np.array(sorted(df["day"].unique()))
    cA, cB = COST_RT[a], COST_RT[b]
    out = []
    for k in range(FORM_DAYS, len(days) - 1, TRADE_DAYS):
        f = df[df["day"].isin(days[k - FORM_DAYS:k])]
        t = df[df["day"].isin(days[k:k + TRADE_DAYS])]
        if len(f) < 800 or len(t) < 200:
            continue
        x, y = f["lBc"].values, f["lAc"].values
        xm, ym = x.mean(), y.mean()
        vx = ((x - xm) ** 2).sum()
        if vx <= 0:
            continue
        beta = ((x - xm) * (y - ym)).sum() / vx
        a0 = ym - beta * xm
        rf = f["lAc"] - a0 - beta * f["lBc"]
        mu, sd = float(rf.mean()), float(rf.std())
        if not np.isfinite(sd) or sd <= 0:
            continue
        z = ((t["lAc"] - a0 - beta * t["lBc"]).values - mu) / sd
        lAo, lBo = t["lAo"].values, t["lBo"].values
        ts, dayv = t.index, t["day"].values
        n = len(z)
        i, ei, side = 0, -1, 0
        while i < n - 1:
            if side == 0:
                if abs(z[i]) >= Z_IN:
                    side = -1 if z[i] > 0 else 1     # fade the deviation
                    ei = i + 1                        # delay+1: next bar OPEN
                    i = ei
                    continue
            else:
                if abs(z[i]) <= Z_OUT or (i - ei) >= H_MAX or i == n - 2:
                    xi = i + 1
                    gross = side * ((lAo[xi] - lAo[ei]) -
                                    beta * (lBo[xi] - lBo[ei])) * 1e4
                    nights = len(pd.unique(dayv[ei:xi + 1])) - 1
                    cost = cA + abs(beta) * cB + CARRY_BPS_NIGHT * nights
                    out.append({"t": ts[xi], "side": side, "gross": gross,
                                "net": gross - cost, "cost": cost,
                                "bars": xi - ei, "nights": nights,
                                "dir": "up" if side == -1 else "dn",
                                "beta": beta})
                    side, ei = 0, -1
            i += 1
    return pd.DataFrame(out).set_index("t") if out else pd.DataFrame()


def block_boot(x, n=5000, mean_block=10, seed=0):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 30:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    N = len(x)
    p = 1.0 / mean_block
    means = np.empty(n)
    for j in range(n):
        idx = np.empty(N, dtype=np.int64)
        i = rng.integers(N)
        for k in range(N):
            idx[k] = i
            i = rng.integers(N) if rng.random() < p else (i + 1) % N
        means[j] = x[idx].mean()
    return float(np.percentile(means, 2.5)), float(x.mean()), float(np.percentile(means, 97.5))


def orthogonality(tr, a, b):
    """L38: how much of the sleeve is just directional exposure to its legs?"""
    import statsmodels.api as sm
    px = pd.concat([_read(a, ["close"]).loc[START:END]["close"].rename("A"),
                    _read(b, ["close"]).loc[START:END]["close"].rename("B")],
                   axis=1).dropna()
    d = np.log(px).resample("1D").last().dropna().diff().dropna()
    pnl = tr["net"].resample("1D").sum()
    j = pd.concat([pnl.rename("y"), d], axis=1).dropna()
    j = j[j["y"] != 0]
    if len(j) < 60:
        return np.nan
    X = sm.add_constant(j[["A", "B"]].values)
    return float(sm.OLS(j["y"].values, X).fit().rsquared)


if __name__ == "__main__":
    rows = []
    for a, b in CANDIDATES:
        tr = trades(a, b)
        if tr.empty:
            continue
        up = tr[tr.dir == "up"]["gross"].values
        dn = tr[tr.dir == "dn"]["gross"].values
        lo_g, m_g, hi_g = block_boot(tr["gross"].values)
        lo_n, m_n, hi_n = block_boot(tr["net"].values)
        lo_u, m_u, hi_u = block_boot(up)
        lo_d, m_d, hi_d = block_boot(dn)
        r2 = orthogonality(tr, a, b)
        rows.append({
            "pair": f"{a}/{b}", "n_trades": len(tr),
            "median_bars": float(tr["bars"].median()),
            "median_nights": float(tr["nights"].median()),
            "cost_bps": float(tr["cost"].mean()),
            "gross_bps": m_g, "gross_lo": lo_g, "gross_hi": hi_g,
            "net_bps": m_n, "net_lo": lo_n, "net_hi": hi_n,
            "up_n": len(up), "up_gross": m_u, "up_lo": lo_u, "up_hi": hi_u,
            "dn_n": len(dn), "dn_gross": m_d, "dn_lo": lo_d, "dn_hi": hi_d,
            "L38_r2": r2,
        })
        print(f"{a}/{b}: {len(tr)} non-overlapping trades", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(f"{OUT}/a3_powered_candidates.csv", index=False)
    pd.set_option("display.width", 200)
    print("\n=== GROSS (cost=0) and NET, block-bootstrap 95% CI, bps/trade ===")
    print(df[["pair", "n_trades", "median_bars", "median_nights", "cost_bps",
              "gross_bps", "gross_lo", "gross_hi",
              "net_bps", "net_lo", "net_hi"]].to_string(index=False))
    print("\n=== L25 two-sided, DISJOINT trade samples (GROSS bps) ===")
    print(df[["pair", "up_n", "up_gross", "up_lo", "up_hi",
              "dn_n", "dn_gross", "dn_lo", "dn_hi"]].to_string(index=False))
    print("\n=== L38 beta-orthogonality (R^2 of daily P&L on leg returns) ===")
    print(df[["pair", "L38_r2"]].to_string(index=False))
