"""
mechanism2.py — Phase 3b: the controls that decide the case.

  G. L58 done RIGHT. The first pass compared conditions while letting the STOP
     GEOMETRY move with the condition (pattern-exit = prior extreme / prior close,
     which sits far from entry after a gap and ~at entry without one). That makes
     R-multiples non-comparable across conditions. Redone with an identical
     6-ATR stop in every arm, so the only thing varying is the CONDITION.
  H. Data-source natural experiment: the yfinance "=F" continuous front-month
     series splice contracts at the roll, which manufactures exactly the price
     discontinuity this strategy trades. Compare gap expectancy on yf-sourced
     instruments vs broker-sourced ones (ftmo_panel / M1_resample).
  I. Two-sided (L25) and cost ratio re-evaluated IN THE RECENT REGIME.
  J. Block bootstrap (by instrument x year) on the swap-net expectancy.
"""
from __future__ import annotations
import os, sys, json
import numpy as np, pandas as pd

ROOT = "<HOME>/Desktop/Algo_claude"
AUDIT = f"{ROOT}/Multi_Asset/research/archived/oxfordstrat_109_audit"
sys.path.insert(0, os.path.join(AUDIT, "code"))
os.environ.setdefault("OHLC_DIR", os.path.join(AUDIT, "ohlc"))
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ftmo_lab as lab                                    # noqa: E402
from repro import UNI, ATR_LEN, ATR_STOP                  # noqa: E402
import mechanism as M                                     # noqa: E402

M.PROXY["GER40"] = "US500"          # GER40 has empty lb/sb in the measured table
TM_REP = 10

SRC = pd.read_csv(os.path.join(AUDIT, "ohlc", "_coverage.csv")).set_index("instr")


def simulate_uncond_flat(df, time_index, direction, variant="A", mode="all", flb=20):
    """Identical to the spec EXCEPT the stop is always entry -/+ 6*ATR.
    Removing the pattern exit holds the risk geometry constant across arms."""
    o, h, l, c = (df[x].values for x in ("open", "high", "low", "close"))
    A = lab.atr(df, ATR_LEN).values
    upc = pd.Series(h, index=df.index).rolling(flb).max().shift(1).values
    loc = pd.Series(l, index=df.index).rolling(flb).min().shift(1).values
    n = len(df); idx = df.index; d = direction
    rs, yrs, nights = [], [], []
    for k in range(flb + 1, n - 2):
        if not np.isfinite(A[k]) or A[k] <= 0:
            continue
        if mode in ("gap", "both"):
            ok = ((l[k] > h[k - 1]) if d == 1 else (h[k] < l[k - 1])) if variant == "A" \
                 else ((l[k] > c[k - 1]) if d == 1 else (h[k] < c[k - 1]))
            if not ok:
                continue
        if mode in ("filter", "both"):
            ok = (np.isfinite(upc[k]) and h[k] > upc[k]) if d == 1 else \
                 (np.isfinite(loc[k]) and l[k] < loc[k])
            if not ok:
                continue
        eb = k + 1
        entry = o[eb]
        if not np.isfinite(entry):
            continue
        risk0 = A[k] * ATR_STOP
        stop_lvl = entry - d * risk0
        last = min(eb + time_index, n - 1)
        exit_p = None
        for j in range(eb, last + 1):
            if d == 1 and l[j] <= stop_lvl:  exit_p = stop_lvl; break
            if d == -1 and h[j] >= stop_lvl: exit_p = stop_lvl; break
            if j == last: exit_p = c[j]; break
        rs.append(d * (exit_p - entry) / risk0)
        yrs.append(idx[eb].year)
        nights.append((idx[min(eb + time_index, n - 1)] - idx[eb]).days)
    return np.array(rs), np.array(yrs), np.array(nights)


def l58_flat(variant, tag):
    """Year x instrument x direction matched comparison at CONSTANT geometry."""
    tr = pd.read_parquet(os.path.join(HERE, f"{tag}_trades_point.parquet"))
    tr["year"] = pd.to_datetime(tr["entry"]).dt.year
    w = tr.groupby(["instr", "dir", "year"]).size().rename("w").reset_index()
    res = {}
    cache = {}
    for instr, df in UNI.items():
        for d in (1, -1):
            for mode in ("all", "filter", "gap", "both"):
                r, y, nt = simulate_uncond_flat(df, TM_REP, d, variant=variant, mode=mode)
                if len(r):
                    s = pd.DataFrame({"r": r, "year": y})
                    cache[(instr, d, mode)] = (s.groupby("year")["r"].agg(["mean", "size"]),
                                               float(r.mean()), len(r))
    for mode in ("all", "filter", "gap", "both"):
        tw = tv = 0.0; fn = 0; fv = 0.0
        for (instr, d, m), (by, mu, n) in cache.items():
            if m != mode:
                continue
            fn += n; fv += mu * n
            ww = w[(w["instr"] == instr) & (w["dir"] == d)]
            for _, x in ww.iterrows():
                if x["year"] in by.index:
                    tw += x["w"]; tv += by.loc[x["year"], "mean"] * x["w"]
        res[mode] = dict(matched_expR=tv / tw if tw else np.nan, matched_w=tw,
                         flat_expR=fv / fn if fn else np.nan, flat_n=fn)
    return res


def block_bootstrap(tr, col, n_boot=2000, seed=7):
    """Resample (instrument, year) blocks — trades cluster hard in both."""
    rng = np.random.default_rng(seed)
    tr = tr.copy(); tr["year"] = pd.to_datetime(tr["entry"]).dt.year
    keys = list(tr.groupby(["instr", "year"]).groups.items())
    vals = [tr.loc[ix, col].values for _, ix in keys]
    K = len(vals)
    mus = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.integers(0, K, K)
        mus[b] = np.concatenate([vals[i] for i in pick]).mean()
    return dict(mean=float(tr[col].mean()), p2_5=float(np.percentile(mus, 2.5)),
                p97_5=float(np.percentile(mus, 97.5)),
                p_le_0=float((mus <= 0).mean()), n_blocks=K)


if __name__ == "__main__":
    OUT = {}
    for variant, tag in (("A", "s035"), ("B", "s036")):
        tr = pd.read_parquet(os.path.join(HERE, f"{tag}_trades_point.parquet"))
        tr["year"] = pd.to_datetime(tr["entry"]).dt.year
        sw = M.add_swap(tr)                                # GER40 now mapped
        assert sw["netR_swap"].notna().all(), "unmapped swap leg"
        R = {}

        # actual stop distance vs the nominal 6-ATR risk unit
        d = tr["dir"].values
        gapf = np.where(d == 1, tr["entry_px"], tr["entry_px"])   # placeholder, computed below
        R["geometry"] = dict(
            note="risk0 = 6*ATR is the R denominator; the pattern exit puts the real stop closer",
            risk0_pct_of_px=float((tr["risk0"] / tr["entry_px"]).mean() * 100))

        # --- G. L58 at constant geometry ------------------------------------
        R["l58_flat_geometry"] = l58_flat(variant, tag)

        # --- H. data-source natural experiment ------------------------------
        tr["src"] = [SRC.loc[i, "source"] for i in tr["instr"]]
        tr["srcgrp"] = np.where(tr["src"].str.startswith("yf:"), "yfinance_continuous_futures",
                                "broker_real (ftmo_panel / M1_resample)")
        sw["srcgrp"] = tr["srcgrp"].values
        g1 = tr.groupby("srcgrp")["netR"].agg(["count", "mean", "sum"])
        g2 = sw.groupby("srcgrp")["netR_swap"].agg(["count", "mean", "sum"])
        R["by_source"] = json.loads(g1.join(g2, rsuffix="_swap").reset_index().to_json(orient="records"))
        R["pnl_share_yf_pct"] = float(
            g1.loc["yfinance_continuous_futures", "sum"] / tr["netR"].sum() * 100)

        # per-instrument with source
        pi = tr.groupby(["instr", "src"])["netR"].agg(["count", "mean", "sum"]).reset_index()
        pi = pi.sort_values("sum", ascending=False)
        R["per_instrument"] = json.loads(pi.to_json(orient="records"))

        # --- I. recent-regime re-evaluation ---------------------------------
        rec = sw[pd.to_datetime(sw["entry"]) > pd.Timestamp("2018-12-31")]
        R["recent_2019plus"] = dict(
            n=len(rec),
            twosided_pre_swap=dict(
                long=float(rec.loc[rec["dir"] == 1, "netR"].mean()),
                short=float(rec.loc[rec["dir"] == -1, "netR"].mean()),
                n_long=int((rec["dir"] == 1).sum()), n_short=int((rec["dir"] == -1).sum())),
            twosided_post_swap=dict(
                long=float(rec.loc[rec["dir"] == 1, "netR_swap"].mean()),
                short=float(rec.loc[rec["dir"] == -1, "netR_swap"].mean())),
            expR_post_swap=float(rec["netR_swap"].mean()),
            gross_bps=float(M.bps_of_notional(rec, "grossR").mean()),
            swap_bps=float((rec["swap_R"] * rec["risk0"] / rec["entry_px"] * 1e4).mean()),
            rt_cost_bps=float((rec["cost_R"] * rec["risk0"] / rec["entry_px"] * 1e4).mean()),
        )
        gb = R["recent_2019plus"]["gross_bps"]
        cb = -R["recent_2019plus"]["swap_bps"] + R["recent_2019plus"]["rt_cost_bps"]
        R["recent_2019plus"]["cost_ratio_gross_over_cost"] = float(gb / cb) if cb else np.nan

        full_gb = float(M.bps_of_notional(sw, "grossR").mean())
        full_cb = float((-(sw["swap_R"]) + sw["cost_R"]).mul(
            sw["risk0"] / sw["entry_px"] * 1e4).mean())
        R["full_sample_cost_ratio"] = dict(gross_bps=full_gb, cost_bps=full_cb,
                                           ratio=full_gb / full_cb)

        # --- J. bootstrap ----------------------------------------------------
        R["bootstrap_netR"] = block_bootstrap(tr, "netR")
        R["bootstrap_netR_swap"] = block_bootstrap(sw, "netR_swap")
        recb = sw[pd.to_datetime(sw["entry"]) > pd.Timestamp("2018-12-31")]
        R["bootstrap_recent_swap"] = block_bootstrap(recb, "netR_swap")
        # broker-data-only subset
        brk = sw[sw["srcgrp"].str.startswith("broker")]
        R["bootstrap_broker_only_swap"] = block_bootstrap(brk, "netR_swap")

        OUT[tag] = R
        print("=" * 72); print(tag)
        print(json.dumps(R, indent=1, default=str))

    with open(os.path.join(HERE, "mechanism2.json"), "w") as f:
        json.dump(OUT, f, indent=1, default=str)
