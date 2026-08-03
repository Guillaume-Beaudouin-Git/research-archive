"""
Stage A2 — three diagnostics that decide WHY the family dies.

The nature of a kill decides whether the family is ever reopenable
(CLAUDE.md reopening policy): a VEHICLE kill is reopenable, a MECHANICAL kill
is not. Stage A showed every half-life far above the K1 gate; that alone reads
as a vehicle kill. These three measurements test whether that reading is right.

D1. Frequency stability (microstructure-noise falsification).
    Bid-ask bounce manufactures spurious fast mean reversion. If half-life in
    TIME units is stable across sampling intervals the dynamics are real; if it
    GROWS with the interval, the fast reversion seen at M5 is partly noise and
    the true half-life is even longer than measured.

D2. Is there a fast-reverting sub-population? Median half-life could hide a
    tradable minority of windows. Fraction of formation windows with
    HL <= 480 min (the K1 gate), per pair.

D3. THE GROSS GATE (K3), and the one that separates the two kill natures.
    Conditional on |z| >= 2 out-of-sample, does the residual actually revert?
    At ZERO cost. Upper deviations (z >= +2) and lower deviations (z <= -2) are
    DISJOINT trade samples, so this is also the L25 two-sided test -- neither
    side is the sign flip of the other.
    L58: compared against the state-matched unconditional expectation of the
    same trade form (same windows, same horizon, no |z| condition).

    If D3 is ~0 at zero cost, the spread is a random walk: the deviations never
    converge, and no vehicle, cost or horizon can rescue that.
"""
import os
import numpy as np
import pandas as pd
import statsmodels.api as sm

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage_a_halflife import _read, STAGE_B, ou_halflife, survey_pair, UNIV, START, END

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/outputs"

FORM_DAYS, TRADE_DAYS = 20, 5
Z_IN = 2.0
HORIZONS = [12, 48, 144, 288]          # M5 bars: 1h, 4h, 12h, 24h


def hac_t(x, lags=6):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 30 or x.std() == 0:
        return np.nan
    return float(sm.OLS(x, np.ones(len(x))).fit(
        cov_type="HAC", cov_kwds={"maxlags": lags}).tvalues[0])


def pair_series(a, b):
    df = pd.concat([_read(a, ["close"]).loc[START:END]["close"].rename("A"),
                    _read(b, ["close"]).loc[START:END]["close"].rename("B")],
                   axis=1).dropna()
    df["lA"] = np.log(df["A"]); df["lB"] = np.log(df["B"])
    df["day"] = df.index.normalize()
    return df


def d1_frequency(panel5):
    """Half-life at M5/M15/M30/H1, with the window bar-minimum scaled by
    sampling interval so the comparison is like-for-like."""
    rows = []
    import stage_a_halflife as SA
    base_min = SA.MIN_BARS
    for a, b, g in STAGE_B:
        rec = {"A": a, "B": b, "group": g}
        for f, sm_ in [("5min", 5), ("15min", 15), ("30min", 30), ("60min", 60)]:
            SA.MIN_BARS = max(120, int(base_min * 5 / sm_))
            p = panel5 if f == "5min" else panel5.resample(f).last().dropna(how="all")
            r = survey_pair(p[a], p[b], sm_, do_adf=False)
            rec[f"hl_{f}"] = r["hl_med_min"] if r else np.nan
        rows.append(rec)
    SA.MIN_BARS = base_min
    return pd.DataFrame(rows)


def d2_d3(a, b, group):
    df = pair_series(a, b)
    days = np.array(sorted(df["day"].unique()))
    hl_ok = hl_tot = 0
    up, dn, base = {h: [] for h in HORIZONS}, {h: [] for h in HORIZONS}, {h: [] for h in HORIZONS}

    for k in range(FORM_DAYS, len(days) - 1, TRADE_DAYS):
        f = df[df["day"].isin(days[k - FORM_DAYS:k])]
        t = df[df["day"].isin(days[k:k + TRADE_DAYS])]
        if len(f) < 800 or len(t) < 200:
            continue
        x, y = f["lB"].values, f["lA"].values
        xm, ym = x.mean(), y.mean()
        vx = ((x - xm) ** 2).sum()
        if vx <= 0:
            continue
        beta = ((x - xm) * (y - ym)).sum() / vx
        a0 = ym - beta * xm
        res_f = f["lA"] - a0 - beta * f["lB"]
        mu, sd = float(res_f.mean()), float(res_f.std())
        if not np.isfinite(sd) or sd <= 0:
            continue

        # D2 -- half-life of THIS formation window vs the K1 gate
        hl, _, _ = ou_halflife(res_f, 5)
        hl_tot += 1
        if np.isfinite(hl) and hl <= 480:
            hl_ok += 1

        # D3 -- out-of-sample residual path, formation params only (K9)
        r = ((t["lA"] - a0 - beta * t["lB"]).values - mu) / sd     # z, OOS
        rb = r * sd * 1e4                                          # residual, bps
        z = r
        n = len(z)
        for h in HORIZONS:
            if n <= h:
                continue
            fwd = rb[h:] - rb[:-h]        # change in residual over h bars
            z0 = z[:-h]
            # reversion is a DECREASE in |residual|: sign so that >0 = reverts
            up[h].append(-fwd[z0 >= Z_IN])     # deviation above: revert = fall
            dn[h].append(+fwd[z0 <= -Z_IN])    # deviation below: revert = rise
            base[h].append(-np.sign(z0) * fwd) # L58 state-matched baseline

    out = {"A": a, "B": b, "group": group,
           "hl_frac_le_gate": hl_ok / hl_tot if hl_tot else np.nan,
           "n_windows": hl_tot}
    for h in HORIZONS:
        u = np.concatenate(up[h]) if up[h] else np.array([])
        d = np.concatenate(dn[h]) if dn[h] else np.array([])
        bs = np.concatenate(base[h]) if base[h] else np.array([])
        both = np.concatenate([u, d]) if len(u) + len(d) else np.array([])
        out[f"h{h}_n"] = len(both)
        out[f"h{h}_mean_bps"] = float(both.mean()) if len(both) else np.nan
        out[f"h{h}_t"] = hac_t(both)
        out[f"h{h}_up_mean"] = float(u.mean()) if len(u) else np.nan
        out[f"h{h}_up_t"] = hac_t(u)
        out[f"h{h}_dn_mean"] = float(d.mean()) if len(d) else np.nan
        out[f"h{h}_dn_t"] = hac_t(d)
        out[f"h{h}_base_bps"] = float(bs.mean()) if len(bs) else np.nan
    return out


if __name__ == "__main__":
    import stage_a_halflife as SA
    print("panel ...", flush=True)
    p5 = SA.load_panel("5min")

    print("\nD1 frequency stability ...", flush=True)
    d1 = d1_frequency(p5)
    d1.to_csv(f"{OUT}/d1_freq_stability.csv", index=False)
    print(d1.to_string(index=False))
    r = d1[["hl_5min", "hl_15min", "hl_30min", "hl_60min"]].median()
    print("\nmedian across Stage-B pairs:")
    print(r.to_string())
    print(f"ratio H1/M5 = {r['hl_60min'] / r['hl_5min']:.2f}"
          "   (>1 => M5 half-life biased SHORT by microstructure noise)")

    print("\nD2 + D3 ...", flush=True)
    rows = [d2_d3(a, b, g) for a, b, g in STAGE_B]
    d = pd.DataFrame(rows)
    d.to_csv(f"{OUT}/d3_gross_reversion.csv", index=False)

    print("\n--- D2: fraction of formation windows with HL <= 480 min (K1 gate) ---")
    print(d[["A", "B", "group", "hl_frac_le_gate", "n_windows"]].to_string(index=False))

    print("\n--- D3: GROSS reversion after |z|>=2, OOS, zero cost (bps) ---")
    for h in HORIZONS:
        c = [f"h{h}_n", f"h{h}_mean_bps", f"h{h}_t", f"h{h}_base_bps"]
        s = d[["A", "B"] + c].copy()
        print(f"\nhorizon {h} bars ({h*5/60:.0f}h):")
        print(s.to_string(index=False))
        print(f"  POOLED mean={d[f'h{h}_mean_bps'].mean():.3f} bps  "
              f"baseline={d[f'h{h}_base_bps'].mean():.3f} bps  "
              f"pairs with t>2.5: {(d[f'h{h}_t'] > 2.5).sum()}/{len(d)}")

    print("\n--- L25 two-sided, DISJOINT legs (horizon 144 bars = 12h) ---")
    print(d[["A", "B", "group", "h144_up_mean", "h144_up_t",
             "h144_dn_mean", "h144_dn_t"]].to_string(index=False))
