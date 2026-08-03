"""SECTION 2 — does any T-1 state concentrate the US index close continuation?

Pre-registered in ../PREREGISTRATION.md (committed af3fde30, before any data read).
Trade form FROZEN and inherited from `close_continuation_gold_subwindows` TEST A:
z = causal 250d z-score of the last 15 min before the cash close; z>+1 LONG, z<-1
SHORT (disjoint legs, L25); entry at the OPEN of 16:01+d ET, exit at the OPEN of
16:11 ET.  Gross gate cost_rt = 0.  That study already ruled: mechanism CONFIRMED
on US100, edge REJECTED on execution.  The only question here is whether a state
concentrates it enough to clear KU7.

States, all measured at the CLOSE OF t-1 or from the calendar alone:
  US1  close-window participation on t-1  — predicted DOWN (Kyle: impact ~ 1/depth)
  US2  business days to month end         — predicted UP as month-end approaches
  US3  own trailing 5-day sleeve P&L      — predicted UP (inventory persistence)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, "<HOME>/Desktop/Algo_claude")
from common_xcond import (RNG, block_boot_mean, block_boot_slope_p, cache_dir,  # noqa: E402
                          causal_rank, hac, hac_slope, read_m1_cache, walk_forward)

TZ, CL = "America/New_York", 960          # cash close 16:00 ET
K, THETA = 15, 1.0
DELAYS = (0, 1, 2)
Y0, SPLIT = 2018, 2022
COST = 1.8                                 # measured RT, bps (never the `spread` column)
INSTR = ("US100", "US500", "US30")


def panel(cache: Path, name: str) -> pd.DataFrame:
    df = read_m1_cache(cache, name)
    idx = df.index.tz_convert(TZ)
    mod = (idx.hour * 60 + idx.minute).to_numpy()
    day = idx.normalize().tz_localize(None)
    need = sorted({CL - K - 1, CL - 1, CL} | {CL + 1 + d for d in DELAYS} | {CL + 11})
    keep = np.isin(mod, need)
    sub = pd.DataFrame({"day": day[keep], "mod": mod[keep],
                        "open": df["open"].to_numpy()[keep],
                        "close": df["close"].to_numpy()[keep],
                        "high": df["high"].to_numpy()[keep],
                        "low": df["low"].to_numpy()[keep]}
                       ).drop_duplicates(subset=["day", "mod"], keep="last")
    t = sub.pivot(index="day", columns="mod", values=["open", "close", "high", "low"])
    c, o, hi, lo = t["close"], t["open"], t["high"], t["low"]

    # ---- close-window activity, measured on the SAME day then lagged to t-1
    win = (mod >= CL - K) & (mod < CL)
    act = pd.DataFrame({"day": day[win],
                        "tv": df["tick_volume"].to_numpy()[win],
                        "up": (df["high"].to_numpy()[win] > df["low"].to_numpy()[win])
                        }).groupby("day").agg(tv=("tv", "sum"), nupd=("up", "sum"))

    p = pd.DataFrame(index=t.index)
    sig = (c[CL - 1] / c[CL - K - 1] - 1.0) * 1e4
    mu = sig.shift(1).rolling(250, min_periods=100).mean()
    sd = sig.shift(1).rolling(250, min_periods=100).std()
    p["z"] = (sig - mu) / sd
    for d in DELAYS:
        p[f"r{d}"] = (o[CL + 11] / o[CL + 1 + d] - 1.0) * 1e4
    p["zr_entry"] = (hi[CL + 1] == lo[CL + 1]).astype(float)
    p["zr_exit"] = (hi[CL + 11] == lo[CL + 11]).astype(float)
    p = p.join(act)
    p["tv_lag"] = p["tv"].shift(1)                      # US1: strictly t-1
    p["nupd_lag"] = p["nupd"].shift(1)                  # US1 proxy: strictly t-1
    p = p[(p.index.year >= Y0) & (p.index.dayofweek < 5)]

    # US2 : business days remaining in the calendar month (0 = last trading day)
    ym = p.index.to_period("M")
    rank_from_end = p.groupby(ym).cumcount(ascending=False)
    p["bd_to_me"] = rank_from_end.to_numpy()
    p["year"] = p.index.year
    return p


def pnl(p: pd.DataFrame, d: int) -> np.ndarray:
    """Two-sided continuation P&L, disjoint legs (L25).  0 on no-signal days."""
    z, r = p["z"].to_numpy(), p[f"r{d}"].to_numpy()
    pos = np.where(z > THETA, 1.0, np.where(z < -THETA, -1.0, 0.0))
    pos[~np.isfinite(z)] = np.nan
    return pos * r, pos


def buckets(p: pd.DataFrame, state: str):
    if state == "US1":
        v = causal_rank(p["nupd_lag"])
        b = pd.qcut(pd.Series(v), 5, labels=False, duplicates="drop").to_numpy(float)
        return v, b, "down"
    if state == "US1_tv":
        v = causal_rank(p["tv_lag"])
        b = pd.qcut(pd.Series(v), 5, labels=False, duplicates="drop").to_numpy(float)
        return v, b, "down"
    if state == "US2":
        bd = p["bd_to_me"].to_numpy(float)
        b = np.select([bd == 0, bd == 1, bd <= 3, bd <= 6], [4.0, 3.0, 2.0, 1.0], default=0.0)
        return -bd, b, "up"                       # -bd increases towards month end
    if state == "US3":
        raise RuntimeError("US3 is built from the P&L series; handled in main()")
    raise KeyError(state)


def bucket_stats(b, x) -> pd.DataFrame:
    ok = np.isfinite(b) & np.isfinite(x)
    d = pd.DataFrame({"b": np.asarray(b)[ok], "x": np.asarray(x, float)[ok]})
    g = d.groupby("b")["x"]
    out = pd.DataFrame({"n": g.size(), "mean": g.mean()})
    out["t_hac"] = [hac(d.loc[d["b"] == k, "x"].to_numpy())[1] for k in out.index]
    return out


def circular_placebo(b, x, carrier, ndraw: int = 400) -> tuple[float, float]:
    """Matched-autocorrelation placebo: circularly shift the STATE, keep the P&L.
    Preserves the state's own persistence and the P&L's, destroys their alignment."""
    b, x = np.asarray(b, float), np.asarray(x, float)
    n = len(b)
    outs = []
    for _ in range(ndraw):
        k = int(RNG.integers(1, n))
        bb = np.roll(b, k)
        m = (bb == carrier) & np.isfinite(x)
        if m.sum() >= 30:
            outs.append(float(np.nanmean(x[m])))
    if not outs:
        return (np.nan, np.nan)
    return (float(np.median(outs)), float(np.percentile(outs, 95)))


if __name__ == "__main__":
    pd.set_option("display.width", 250, "display.max_columns", 60)
    C = cache_dir()
    OUT = C / "sec2"
    OUT.mkdir(exist_ok=True)
    P = {n: panel(C, n) for n in INSTR}

    print("=== N0 · L60 hygiene at the entry/exit bars, by instrument-year (KU0) ===")
    for n, p in P.items():
        h = p.groupby("year")[["zr_entry", "zr_exit"]].mean().mul(100)
        print(f"  {n}: zr_entry max {h['zr_entry'].max():.2f}%  "
              f"zr_exit max {h['zr_exit'].max():.2f}% (year {h['zr_exit'].idxmax()})")

    print("\n=== N0 · tick_volume availability (US1 viability) ===")
    for n, p in P.items():
        a = p.groupby("year")["tv"].apply(lambda x: float((x > 0).mean() * 100)).round(0)
        print(f"  {n}: {a.to_dict()}")

    print("\n=== reference · the UNCONDITIONAL trade form (gross, cost_rt=0) ===")
    ref = []
    for n, p in P.items():
        for d in DELAYS:
            x, pos = pnl(p, d)
            tr = np.isfinite(x) & (pos != 0)
            m, t, _ = hac(x[tr])
            r = p[f"r{d}"].to_numpy()
            ref.append(dict(instr=n, d=d, n_trades=int(tr.sum()),
                            trades_yr=round(tr.sum() / (p.index.year.nunique()), 1),
                            gross=m, t=t, uncond_r=float(np.nanmean(r)),
                            uncond_t=hac(r)[1], net=m - COST))
    R0 = pd.DataFrame(ref)
    print(R0.round(3).to_string(index=False))
    R0.to_csv(OUT / "u_reference.csv", index=False)

    # ------------------------------------------------------- gradients per state
    rows, bstats = [], []
    for n, p in P.items():
        for d in DELAYS:
            x, pos = pnl(p, d)
            r = p[f"r{d}"].to_numpy()
            tr = np.isfinite(x) & (pos != 0)
            for state in ("US1", "US1_tv", "US2", "US3"):
                if state == "US3":
                    own = pd.Series(np.where(np.isfinite(x), x, 0.0), index=p.index)
                    v = causal_rank(own.rolling(5, min_periods=3).mean().shift(1))
                    b = pd.qcut(pd.Series(v), 5, labels=False,
                                duplicates="drop").to_numpy(float)
                    direction = "up"
                else:
                    v, b, direction = buckets(p, state)
                # L58 matched baseline: unconditional post-close return IN THE BUCKET
                blb = pd.Series(r).groupby(pd.Series(b)).transform("mean").to_numpy()
                xex = pos * (r - blb)
                inc = direction == "up"
                g = hac_slope(x[tr], v[tr])
                ge = hac_slope(xex[tr], v[tr])
                gv = hac_slope(np.abs(x[tr] - np.nanmean(x[tr])), v[tr])
                bs = bucket_stats(b[tr], x[tr])
                bse = bucket_stats(b[tr], xex[tr])
                bsb = bucket_stats(b[tr], blb[tr])
                dq = np.diff(bs["mean"].to_numpy())
                carrier = bs.index.max() if inc else bs.index.min()
                m = tr & (b == carrier)
                mu, tt, _ = hac(x[m])
                lo, hi_, bp = block_boot_mean(x[m])
                pmed, p95 = circular_placebo(b, np.where(tr, x, np.nan), carrier)
                wf = walk_forward(p.index[m], x[m])
                rows.append(dict(
                    instr=n, d=d, state=state, direction=direction, n_trades=int(tr.sum()),
                    slope=g["slope"], t_slope=g["t"], boot_p=block_boot_slope_p(x[tr], v[tr]),
                    r2_mean=g["r2"], r2_var=gv["r2"], t_var=gv["t"],
                    t_excess=ge["t"], mono=int((dq > 0).sum() if inc else (dq < 0).sum()),
                    mono_n=len(dq), carrier=carrier, n_carrier=int(m.sum()),
                    carrier_gross=mu, carrier_t=tt, carrier_bootp=bp,
                    carrier_ci_lo=lo, carrier_ci_hi=hi_,
                    carrier_excess=float(np.nanmean(xex[m])),
                    carrier_net=mu - COST,
                    blb_min=bsb["mean"].min(), blb_max=bsb["mean"].max(),
                    plac_med=pmed, plac_p95=p95, beats_placebo=bool(mu > p95),
                    wf_pos=wf[0], wf_tot=wf[1],
                    sign_ok=bool((g["slope"] > 0) == inc)))
                if d == 1:
                    bb = bs.copy()
                    bb["mean_excess"] = bse["mean"].reindex(bb.index).to_numpy()
                    bb["baseline_BLB"] = bsb["mean"].reindex(bb.index).to_numpy()
                    bb.insert(0, "state", state)
                    bb.insert(0, "instr", n)
                    bstats.append(bb.reset_index())
    G = pd.DataFrame(rows)
    B = pd.concat(bstats, ignore_index=True)
    G.to_csv(OUT / "u_gradient.csv", index=False)
    B.to_csv(OUT / "u_buckets_d1.csv", index=False)

    cols = ["state", "direction", "slope", "t_slope", "boot_p", "r2_mean", "r2_var",
            "t_excess", "mono", "mono_n", "sign_ok", "n_carrier", "carrier_gross",
            "carrier_t", "carrier_net", "plac_p95", "beats_placebo", "wf_pos", "wf_tot"]
    for d in DELAYS:
        print(f"\n=== KU1-KU5 · US100, d={d} (DECISIONAL delay is d=1) ===")
        print(G[(G.instr == "US100") & (G.d == d)][cols].round(3).to_string(index=False))
    print("\n=== replication (instruments already disqualified by TEST A), d=1 ===")
    print(G[(G.instr != "US100") & (G.d == 1)][["instr"] + cols].round(3).to_string(index=False))

    print("\n=== bucket detail at d=1 · level, MATCHED-baseline excess, and the baseline itself ===")
    print(B.round(3).to_string(index=False))

    print("\n=== KU7 · the rule that decides (d=1, cost 1.8 bps RT) ===")
    k = G[(G.d == 1)].copy()
    k["KU7"] = np.where((k.carrier_gross >= 2.8) & (k.carrier_t >= 2.0), "PASS", "FAIL")
    print(k[["instr", "state", "n_carrier", "carrier_gross", "carrier_t",
             "carrier_net", "KU7"]].round(3).to_string(index=False))

    # ---- out-of-sample split on the carrier buckets that came closest
    print("\n=== KU4 bis · pre/post 2022 on the US100 carrier buckets, d=1 ===")
    p = P["US100"]
    x, pos = pnl(p, 1)
    tr = np.isfinite(x) & (pos != 0)
    for state in ("US1", "US2", "US3"):
        if state == "US3":
            own = pd.Series(np.where(np.isfinite(x), x, 0.0), index=p.index)
            v = causal_rank(own.rolling(5, min_periods=3).mean().shift(1))
            b = pd.qcut(pd.Series(v), 5, labels=False, duplicates="drop").to_numpy(float)
            carrier, inc = np.nanmax(b), True
        else:
            v, b, direction = buckets(p, state)
            inc = direction == "up"
            carrier = np.nanmax(b) if inc else np.nanmin(b)
        m = tr & (b == carrier)
        early = m & (p.index.year < SPLIT)
        late = m & (p.index.year >= SPLIT)
        print(f"  {state}: {SPLIT}- n={early.sum():3d} mean={np.nanmean(x[early]):6.2f} "
              f"t={hac(x[early])[1]:5.2f} | {SPLIT}+ n={late.sum():3d} "
              f"mean={np.nanmean(x[late]):6.2f} t={hac(x[late])[1]:5.2f}")
