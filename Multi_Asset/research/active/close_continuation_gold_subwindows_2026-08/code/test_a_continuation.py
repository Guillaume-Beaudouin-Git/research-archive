"""TEST A — is the post-close CONTINUATION of index closing pressure a mechanism?

Pre-registered in ../PREREGISTRATION.md before any data was read in this worktree.
The SIGN is already known from `mr_timezone_repair_2026-08` (the fade loses, i.e. the
pressure continues).  A re-confirmation on that same sample proves nothing, so the
evidence here comes from four places decided in advance:

  1. GRADIENT   — does the post-close return scale with signal intensity?  No threshold,
                  therefore no degree of freedom.  This is the mechanism test (K1/K2).
  2. PLACEBO    — the same trade form anchored every 30 min inside the session (K4).
                  If continuation exists at every anchor it is generic intraday momentum,
                  not a CLOSING-pressure effect.
  3. EXECUTION  — entry delayed 1/2/3/5 minutes (K3).  This is what killed GER40.
  4. OUT-OF-SAMPLE — 2018-2021 vs 2022-2026 (K6).

Invariants: exchange clock with DST (L56); gross gate cost_rt=0; disjoint legs (L25);
delay+1 on entry AND exit, no barrier fills anywhere (L59); L58 baseline = unconditional
expectation of the same trade form; circular block bootstrap (never iid).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

CACHE = Path(sys.argv[1])
OUT = CACHE / "testA"
OUT.mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(20260802)
NBOOT, BLOCK = 2000, 5

# instrument -> (tz, cash open mod, cash close mod, first usable year)
SPEC = {
    "US500": ("America/New_York", 570, 960, 2018),
    "US100": ("America/New_York", 570, 960, 2018),
    "US30":  ("America/New_York", 570, 960, 2018),
    "GER40": ("Europe/Berlin",    540, 1050, 2014),
}
US = ["US500", "US100", "US30"]
SIG_WINS = (15, 30, 60)
THETAS = (0.5, 1.0, 1.5)
DELAYS = (0, 1, 2, 3, 5)
SPLIT_YEAR = 2022          # pre-registered out-of-sample cut


# --------------------------------------------------------------------- stats
def hac_t(x) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 20:
        return np.nan
    m = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return float(m.tvalues[0])


def hac_slope(y, x) -> tuple[float, float, int]:
    y, x = np.asarray(y, float), np.asarray(x, float)
    ok = np.isfinite(y) & np.isfinite(x)
    y, x = y[ok], x[ok]
    if len(y) < 50:
        return (np.nan, np.nan, len(y))
    m = sm.OLS(y, sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return (float(m.params[1]), float(m.tvalues[1]), len(y))


def _boot_idx(n: int, nboot: int = NBOOT, L: int = BLOCK) -> np.ndarray:
    nb = int(np.ceil(n / L))
    starts = RNG.integers(0, n, size=(nboot, nb))
    offs = np.arange(L)
    return (starts[:, :, None] + offs[None, None, :]).reshape(nboot, -1)[:, :n] % n


def block_boot_mean(x) -> tuple:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 20:
        return (np.nan, np.nan, np.nan)
    means = x[_boot_idx(len(x))].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return (lo, hi, min(2 * min((means <= 0).mean(), (means >= 0).mean()), 1.0))


def block_boot_excess(r, mask) -> tuple:
    """L58: bootstrap of mean(r[mask]) - mean(r), panel resampled JOINTLY."""
    r, m = np.asarray(r, float), np.asarray(mask, bool)
    if m.sum() < 20:
        return (np.nan, np.nan, np.nan)
    idx = _boot_idx(len(r))
    A, M = r[idx], m[idx]
    with np.errstate(invalid="ignore"):
        d = np.nanmean(np.where(M, A, np.nan), axis=1) - A.mean(axis=1)
    d = d[np.isfinite(d)]
    if len(d) < 100:
        return (np.nan, np.nan, np.nan)
    lo, hi = np.percentile(d, [2.5, 97.5])
    return (lo, hi, min(2 * min((d <= 0).mean(), (d >= 0).mean()), 1.0))


# ---------------------------------------------------------------- data layer
def pivot_mods(name: str, mods) -> pd.DataFrame:
    tz, om, cl, y0 = SPEC[name]
    df = pd.read_parquet(CACHE / f"{name}_M1.parquet")
    idx = df.index.tz_convert(tz)
    mod = (idx.hour * 60 + idx.minute).to_numpy()
    day = idx.normalize().tz_localize(None)
    keep = np.isin(mod, sorted(set(mods)))
    sub = pd.DataFrame({"day": day[keep], "mod": mod[keep],
                        "open": df["open"].to_numpy()[keep],
                        "close": df["close"].to_numpy()[keep],
                        "high": df["high"].to_numpy()[keep],
                        "low": df["low"].to_numpy()[keep]})
    sub = sub.drop_duplicates(subset=["day", "mod"], keep="last")
    t = sub.pivot(index="day", columns="mod", values=["open", "close", "high", "low"])
    t = t[(t.index.year >= y0) & (t.index.dayofweek < 5)]
    return t


def zscore(s: pd.Series) -> np.ndarray:
    mu = s.shift(1).rolling(250, min_periods=100).mean()
    sd = s.shift(1).rolling(250, min_periods=100).std()
    return ((s - mu) / sd).to_numpy()


def close_panel(name: str) -> pd.DataFrame:
    """Signals + post-close forward returns for every pre-registered entry delay."""
    tz, om, cl, y0 = SPEC[name]
    mods = ([cl - 61, cl - 31, cl - 16, cl - 1, cl] +
            [cl + 1 + d for d in DELAYS] + [cl + 11] +
            [cl + 11 + d for d in DELAYS])
    t = pivot_mods(name, mods)
    c, o, hi, lo = t["close"], t["open"], t["high"], t["low"]
    p = pd.DataFrame(index=t.index)
    for K in SIG_WINS:
        p[f"sig{K}"] = (c[cl - 1] / c[{15: cl - 16, 30: cl - 31, 60: cl - 61}[K]] - 1.0) * 1e4
        p[f"z{K}"] = zscore(p[f"sig{K}"])
    # entry at close+1+d ; two exit conventions (L59 applies to both)
    for d in DELAYS:
        e = o[cl + 1 + d]
        p[f"rFIX{d}"] = (o[cl + 11] / e - 1.0) * 1e4        # fixed exit clock
        p[f"rDUR{d}"] = (o[cl + 11 + d] / e - 1.0) * 1e4    # constant 10-min duration
    p["gap_entry"] = (o[cl + 1] / c[cl] - 1.0) * 1e4
    p["zr_entry"] = (hi[cl + 1] == lo[cl + 1]).astype(float)
    p["zr_exit"] = (hi[cl + 11] == lo[cl + 11]).astype(float)
    p["rng_entry"] = ((hi[cl + 1] - lo[cl + 1]) / o[cl + 1] * 1e4)
    p["year"] = p.index.year
    return p


# ------------------------------------------------------------- measurements
def threshold_cell(z, r, yr, theta) -> dict | None:
    ok = np.isfinite(z) & np.isfinite(r)
    z, r, yr = z[ok], r[ok], yr[ok]
    up, dn = z > theta, z < -theta
    if up.sum() < 25 or dn.sum() < 25:
        return None
    # CONTINUATION: z>theta -> LONG (+r), z<-theta -> SHORT (-r).  Disjoint legs (L25).
    rL, rS = r[up], -r[dn]
    both = np.concatenate([rL, rS])
    unc = r.mean()
    exU = block_boot_excess(r, up)                     # long leg edge = cond_up - uncond
    exD = block_boot_excess(r, dn)                     # short leg edge = -(cond_dn - uncond)
    bB = block_boot_mean(both)
    yrs = pd.Series(both).groupby(pd.Series(np.concatenate([yr[up], yr[dn]]))).mean()
    return dict(theta=theta, n_days=len(r), uncond=unc, uncond_t=hac_t(r),
                nL=int(up.sum()), mL=rL.mean(), tL=hac_t(rL),
                nS=int(dn.sum()), mS=rS.mean(), tS=hac_t(rS),
                n_both=len(both), m_both=both.mean(), t_both=hac_t(both),
                boot_p=bB[2],
                exL=r[up].mean() - unc, exL_p=exU[2],
                exS=-(r[dn].mean() - unc), exS_p=exD[2],
                yrs_pos=int((yrs > 0).sum()), yrs_tot=len(yrs))


def quintiles(z, r) -> pd.Series:
    ok = np.isfinite(z) & np.isfinite(r)
    z, r = z[ok], r[ok]
    q = pd.qcut(pd.Series(z), 5, labels=False, duplicates="drop")
    return pd.Series(r).groupby(q).mean()


if __name__ == "__main__":
    pd.set_option("display.width", 250, "display.max_columns", 80)
    panels = {n: close_panel(n) for n in SPEC}

    # ---------------------------------------------------------------- L60 / hygiene
    hyg = []
    for n, p in panels.items():
        for y, g in p.groupby("year"):
            hyg.append(dict(instr=n, year=int(y), n=len(g),
                            zr_entry_pct=100 * g["zr_entry"].mean(),
                            zr_exit_pct=100 * g["zr_exit"].mean(),
                            rng_entry_bps=g["rng_entry"].mean(),
                            cov_r0=g["rFIX0"].notna().mean(),
                            cov_r5=g["rFIX5"].notna().mean()))
    H = pd.DataFrame(hyg)
    H.to_csv(OUT / "a_hygiene.csv", index=False)
    print("=== A · L60 hygiene at the entry/exit bars (K7: die if >5% any year) ===")
    print(H.groupby("instr")[["zr_entry_pct", "zr_exit_pct", "rng_entry_bps",
                              "cov_r0", "cov_r5"]].agg(["mean", "max"]).round(2).to_string())

    # ------------------------------------------------- K1/K2 GRADIENT (no threshold)
    grad, quint = [], []
    for n, p in panels.items():
        for K in SIG_WINS:
            z, r = p[f"z{K}"].to_numpy(), p["rFIX0"].to_numpy()
            b, t, nn = hac_slope(r, z)
            # tradeable linear form: position proportional to z (clipped at 3 sd)
            pnl = np.clip(z, -3, 3) * r
            grad.append(dict(instr=n, K=K, slope_bps_per_sd=b, t_slope=t, n=nn,
                             lin_pnl=np.nanmean(pnl), lin_t=hac_t(pnl)))
            qs = quintiles(z, r)
            quint.append(dict(instr=n, K=K, **{f"Q{i+1}": v for i, v in enumerate(qs)}))
    G = pd.DataFrame(grad)
    Q = pd.DataFrame(quint)
    G.to_csv(OUT / "a_gradient.csv", index=False)
    Q.to_csv(OUT / "a_quintiles.csv", index=False)
    print("\n=== A · K1 GRADIENT: slope of post-close return on signal z (no threshold) ===")
    print(G.round(3).to_string(index=False))
    print("\n=== A · K2 quintiles of z -> mean post-close return (bps) ===")
    Q["Q5_Q1"] = Q["Q5"] - Q["Q1"]
    Q["mono"] = [sum(np.diff([r[f"Q{i+1}"] for i in range(5)]) > 0) for _, r in Q.iterrows()]
    print(Q.round(3).to_string(index=False))

    # pooled US: equal-weight daily average of the z-sized PnL (handles cross-corr)
    pool = {}
    for K in SIG_WINS:
        cols = []
        for n in US:
            p = panels[n]
            cols.append(pd.Series(np.clip(p[f"z{K}"], -3, 3) * p["rFIX0"], index=p.index))
        s = pd.concat(cols, axis=1).mean(axis=1).dropna()
        pool[K] = dict(K=K, n=len(s), mean=s.mean(), t=hac_t(s), boot_p=block_boot_mean(s)[2])
    P = pd.DataFrame(pool).T
    P.to_csv(OUT / "a_pooled_linear.csv", index=False)
    print("\n=== A · pooled US, z-sized (no threshold) daily PnL — the honest gradient test ===")
    print(P.round(3).to_string(index=False))

    # ------------------------------------------------------- threshold cells + K6 + K3
    rows = []
    for n, p in panels.items():
        for K in SIG_WINS:
            for th in THETAS:
                for d in DELAYS:
                    for exitc in ("FIX", "DUR"):
                        for lab, msk in (("all", slice(None)),
                                         ("2018_2021", p["year"] < SPLIT_YEAR),
                                         ("2022_2026", p["year"] >= SPLIT_YEAR)):
                            pp = p if lab == "all" else p[msk]
                            if len(pp) < 150:
                                continue
                            st = threshold_cell(pp[f"z{K}"].to_numpy(),
                                                pp[f"r{exitc}{d}"].to_numpy(),
                                                pp["year"].to_numpy(), th)
                            if st:
                                rows.append(dict(instr=n, K=K, delay=d, exitc=exitc,
                                                 period=lab, **st))
    R = pd.DataFrame(rows)
    R.to_csv(OUT / "a_cells.csv", index=False)
    print(f"\n=== A · {len(R)} threshold cells written ===")

    base = R[(R.delay == 0) & (R.exitc == "FIX") & (R.period == "all")]
    print("\n--- traceability only (discovery sample, NOT evidence) ---")
    print(base[["instr", "K", "theta", "nL", "mL", "tL", "nS", "mS", "tS",
                "m_both", "t_both", "boot_p", "exL", "exL_p", "exS", "exS_p",
                "uncond", "yrs_pos", "yrs_tot"]].round(3).to_string(index=False))

    print("\n--- K3 EXECUTION: entry delayed d minutes (fixed exit clock, period=all) ---")
    ex = R[(R.exitc == "FIX") & (R.period == "all") & (R.theta == 1.0)]
    print(ex.pivot_table(index=["instr", "K"], columns="delay",
                         values=["m_both", "t_both"]).round(2).to_string())

    print("\n--- K6 OUT-OF-SAMPLE: 2018-2021 vs 2022-2026 (d=0, FIX) ---")
    sp = R[(R.delay == 0) & (R.exitc == "FIX") & (R.period != "all") & (R.theta == 1.0)]
    print(sp.pivot_table(index=["instr", "K"], columns="period",
                         values=["m_both", "t_both", "n_both"]).round(2).to_string())

    # ------------------------------------ per-minute decomposition of the 10-min hold
    dec = []
    for n in SPEC:
        p = panels[n]
        for K in SIG_WINS:
            z = p[f"z{K}"].to_numpy()
            prev = None
            for d in DELAYS:
                st = threshold_cell(z, p[f"rFIX{d}"].to_numpy(), p["year"].to_numpy(), 1.0)
                if st is None:
                    continue
                dec.append(dict(instr=n, K=K, delay=d, m_tail=st["m_both"],
                                t_tail=st["t_both"],
                                m_segment=(prev - st["m_both"]) if prev is not None else np.nan))
                prev = st["m_both"]
    D = pd.DataFrame(dec)
    D["share_kept"] = D["m_tail"] / D.groupby(["instr", "K"])["m_tail"].transform("first")
    D.to_csv(OUT / "a_perminute.csv", index=False)
    print("\n=== A · per-minute decomposition (m_tail = two-sided from entry d to close+11) ===")
    print(D[D.K == 15].round(3).to_string(index=False))

    # --------------------------------------------------------- K4 PLACEBO ANCHORS
    plc, pooled_non = [], []
    for n in US + ["GER40"]:
        tz, om, cl, y0 = SPEC[n]
        anchors = list(range(om + 60, cl - 29, 30)) + [cl]
        mods = sorted({a + o for a in anchors for o in (-61, -31, -16, -1, 1, 11)})
        t = pivot_mods(n, mods)
        c, o = t["close"], t["open"]
        for K in SIG_WINS:
            nonclose_pnl = []
            for a in anchors:
                if a - K - 1 not in c.columns:
                    continue
                sig = (c[a - 1] / c[a - K - 1] - 1.0) * 1e4
                r = (o[a + 11] / o[a + 1] - 1.0) * 1e4
                z = zscore(sig)
                st = threshold_cell(z, r.to_numpy(), t.index.year.to_numpy(), 1.0)
                if st:
                    plc.append(dict(instr=n, K=K, anchor=a, is_close=(a == cl), **st))
                    if a != cl:
                        rr = r.to_numpy()
                        ok = np.isfinite(z) & np.isfinite(rr)
                        s = pd.Series(np.where(z[ok] > 1.0, rr[ok],
                                               np.where(z[ok] < -1.0, -rr[ok], np.nan)),
                                      index=t.index[ok])
                        nonclose_pnl.append(s)
            if nonclose_pnl:
                agg = pd.concat(nonclose_pnl, axis=1).mean(axis=1).dropna()
                pooled_non.append(dict(instr=n, K=K, n_days=len(agg), mean=agg.mean(),
                                       t_hac=hac_t(agg), boot_p=block_boot_mean(agg)[2]))
    PL = pd.DataFrame(plc)
    PL.to_csv(OUT / "a_placebo.csv", index=False)
    PN = pd.DataFrame(pooled_non)
    PN.to_csv(OUT / "a_placebo_pooled_nonclose.csv", index=False)
    print("\n=== A · K4 PLACEBO: same trade form at 30-min anchors, ALL pre-registered K ===")
    for (n, K), g in PL.groupby(["instr", "K"]):
        g = g.sort_values("m_both", ascending=False).reset_index(drop=True)
        rk = int(g.index[g.is_close][0]) + 1
        non = g[~g.is_close]
        cm = float(g.loc[g.is_close, "m_both"].iloc[0])
        ct = float(g.loc[g.is_close, "t_both"].iloc[0])
        print(f"{n:6s} K={K:2d}: close rank {rk:2d}/{len(g)}  m={cm:6.2f} t={ct:6.2f} "
              f"| non-close mean {non['m_both'].mean():6.2f}  p95 {np.percentile(non['m_both'],95):6.2f} "
              f"| anchors t>2: {(non.t_both>2).sum()}/{len(non)}")
    print("\n--- generic-momentum control: pooled NON-CLOSE anchor PnL, daily series ---")
    print(PN.round(3).to_string(index=False))

    # ------------------------------------------------------------------ economics
    print("\n=== A · economics of the best surviving cell (cost 1.8 bps RT, indices) ===")
    eco = []
    for n in US:
        p = panels[n]
        for K in SIG_WINS:
            for d in (0, 1, 2, 5):
                st = threshold_cell(p[f"z{K}"].to_numpy(), p[f"rFIX{d}"].to_numpy(),
                                    p["year"].to_numpy(), 1.0)
                if st is None:
                    continue
                yrs = (p.index[-1] - p.index[0]).days / 365.25
                tpy = st["n_both"] / yrs
                eco.append(dict(instr=n, K=K, delay=d, trades_yr=tpy,
                                gross_bps=st["m_both"], net_bps=st["m_both"] - 1.8,
                                net_bps_yr=(st["m_both"] - 1.8) * tpy,
                                t_gross=st["t_both"]))
    E = pd.DataFrame(eco)
    E.to_csv(OUT / "a_economics.csv", index=False)
    print(E[E.K == 15].round(2).to_string(index=False))
