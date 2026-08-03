"""SECTION 1 — does any T-1 state concentrate the gold Globex-reopen drift?

Pre-registered in ../PREREGISTRATION.md (committed af3fde30, before any data read).
Trade form FROZEN and inherited: t0 = first executable print at/after 18:00 ET
(exchange clock, DST), entry t0+d, exit t0+8h.  RAW M1.  Gross gate cost_rt = 0.

States, all strictly pre-t0 and all of a nature OTHER than price amplitude:
  GS1  pre-halt participation  (tick_volume over the last quoted hour) — predicted DOWN
  GS2  scheduled darkness      (hours the vehicle was dark)            — predicted UP
  GS3  pre-halt close location (scale-free CLV of the last 15 min)     — predicted UP
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, "<HOME>/Desktop/Algo_claude")
from common_xcond import (NS_MIN, block_boot_mean, block_boot_slope_p,  # noqa: E402
                          cache_dir, causal_rank, hac, hac_slope, price_at,
                          quintile_table, read_m1_cache, walk_forward)

REOPEN_ET, WINDOW_H = 18, 8
DELAYS = (0, 1, 5, 10, 15)
DECISION_START = "2021-01-01"
COST_MID, COST_TAIL = 1.84, 3.88


def build(cache: Path) -> pd.DataFrame:
    df = read_m1_cache(cache, "XAUUSD")
    et = df.index.tz_convert("America/New_York")
    keys = df.index.asi8
    close, hi, lo = (df[c].to_numpy() for c in ("close", "high", "low"))
    tv = df["tick_volume"].to_numpy()

    sess = pd.DatetimeIndex(np.unique(et.normalize().tz_localize(None)))
    base = (sess + pd.Timedelta(hours=REOPEN_ET)).tz_localize(
        "America/New_York", nonexistent="shift_forward", ambiguous=True
    ).tz_convert("UTC").asi8

    out = pd.DataFrame(index=sess)
    out["dow"], out["year"] = sess.dayofweek, sess.year

    # --- t0 : first print this vehicle actually makes at/after the nominal reopen
    i0 = np.searchsorted(keys, base, "left")
    ok0 = i0 < len(keys)
    t0 = np.where(ok0, keys[np.clip(i0, 0, len(keys) - 1)], np.nan).astype(float)
    lag = (t0 - base) / 60e9
    t0[~np.isfinite(lag) | (lag > 60)] = np.nan
    good = np.isfinite(t0)
    t0i = np.where(good, t0, base).astype(np.int64)
    out["t0_lag_min"] = np.where(good, lag, np.nan)

    # --- prices along the window and along the two matched anchor blocks (BL-A)
    for d in DELAYS:
        out[f"p{d}"] = price_at(close, keys, t0i + d * NS_MIN, "first", 10)
        out[f"pend{d}"] = price_at(close, keys, t0i + (WINDOW_H * 60 + d) * NS_MIN, "last", 30)
    out["p_end"] = price_at(close, keys, t0i + WINDOW_H * 60 * NS_MIN, "last", 30)
    out["p_a2"] = price_at(close, keys, t0i + 2 * WINDOW_H * 60 * NS_MIN, "last", 30)
    out["p_a3"] = price_at(close, keys, t0i + 3 * WINDOW_H * 60 * NS_MIN, "last", 30)

    # --- everything below is measured BEFORE the halt, i.e. strictly before entry
    j = np.searchsorted(keys, base, "left") - 1          # last print before the halt
    okj = j >= 0
    jc = np.clip(j, 0, len(keys) - 1)
    t_last = keys[jc].astype(float)
    out["p_pre"] = np.where(okj, close[jc], np.nan)
    out["dark_h"] = np.where(okj, (base - t_last) / 3.6e12, np.nan)      # GS2

    a60 = np.searchsorted(keys, (t_last - 60 * NS_MIN).astype(np.int64), "left")
    a15 = np.searchsorted(keys, (t_last - 15 * NS_MIN).astype(np.int64), "left")
    n = len(sess)
    tvs, nupd, clv, prer = (np.full(n, np.nan) for _ in range(4))
    for k in range(n):
        if not okj[k]:
            continue
        a, b = a60[k], jc[k] + 1
        if b > a:
            tvs[k] = tv[a:b].sum()                                        # GS1
            nupd[k] = float((hi[a:b] > lo[a:b]).sum())                    # GS1 proxy
            prer[k] = np.log(close[b - 1] / close[a]) * 1e4               # contamination ctrl
        a, b = a15[k], jc[k] + 1
        if b > a:
            h, l = hi[a:b].max(), lo[a:b].min()
            if h > l:
                clv[k] = (close[b - 1] - l) / (h - l)                     # GS3
    out["tv_pre"], out["nupd_pre"], out["clv_pre"], out["pre_ret"] = tvs, nupd, clv, prer

    # --- L60 hygiene in the entry and exit zones
    for tag, off in (("entry", 0), ("exit", WINDOW_H * 60)):
        a = np.searchsorted(keys, t0i + off * NS_MIN, "left")
        b = np.searchsorted(keys, t0i + (off + 5) * NS_MIN, "left")
        z, nn = np.zeros(n), np.zeros(n)
        for k in range(n):
            if b[k] > a[k]:
                nn[k] = b[k] - a[k]
                z[k] = (hi[a[k]:b[k]] == lo[a[k]:b[k]]).sum()
        out[f"zr_{tag}"] = np.where(nn > 0, 100 * z / np.where(nn > 0, nn, 1), np.nan)

    return out[good]


def series(o: pd.DataFrame) -> pd.DataFrame:
    s = pd.DataFrame(index=o.index)
    s["year"], s["dow"] = o["year"], o["dow"]
    for d in DELAYS:
        s[f"r{d}"] = np.log(o["p_end"] / o[f"p{d}"]) * 1e4       # fixed exit clock
        s[f"rdur{d}"] = np.log(o[f"pend{d}"] / o[f"p{d}"]) * 1e4  # constant duration (L59)
    s["a2"] = np.log(o["p_a2"] / o["p_end"]) * 1e4
    s["a3"] = np.log(o["p_a3"] / o["p_a2"]) * 1e4
    s["bl_a"] = np.nanmean(np.c_[s["a2"], s["a3"]], axis=1)      # matched baseline (L58)
    s["r24"] = np.log(o["p_a3"] / o["p0"]) * 1e4                 # 'was it just an up day'
    s["excess"] = s["r0"] - s["bl_a"]
    s["excess10"] = s["r10"] - s["bl_a"]
    return s


STATES = {
    # name: (column, direction of the pre-registered gradient, discrete?)
    "GS1_participation":  ("tv_pre", "down", False),
    "GS1p_quote_updates": ("nupd_pre", "down", False),
    "GS2_darkness":       ("dark_h", "up", True),
    "GS3_close_location": ("clv_pre", "up", False),
}


def state_and_buckets(o: pd.DataFrame, col: str, discrete: bool):
    """Return (continuous state for the slope, integer bucket labels).

    `dark_h` is a 3-level STRUCTURAL variable (weekday halt / post-holiday /
    weekend), so it gets its own levels: qcut collapses it to a single bin.
    Everything else is a causal trailing-window rank, bucketed by qcut so that
    ties cannot smear a 'quintile' across half the sample.
    """
    raw = np.asarray(o[col], float)
    if discrete:
        st = np.select([raw < 2, raw < 40], [0.0, 1.0], default=2.0)
        st[~np.isfinite(raw)] = np.nan
        return st, st
    st = causal_rank(o[col])
    b = pd.qcut(pd.Series(st), 5, labels=False, duplicates="drop").to_numpy(float)
    return st, b


def bucket_means(b, r) -> pd.DataFrame:
    ok = np.isfinite(b) & np.isfinite(r)
    d = pd.DataFrame({"b": np.asarray(b)[ok], "r": np.asarray(r, float)[ok]})
    g = d.groupby("b")["r"]
    out = pd.DataFrame({"n": g.size(), "mean": g.mean()})
    out["t_hac"] = [hac(d.loc[d["b"] == k, "r"].to_numpy())[1] for k in out.index]
    return out


def spearman(a, b) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 50:
        return np.nan
    return float(pd.Series(a[ok]).corr(pd.Series(b[ok]), method="spearman"))


def run(o: pd.DataFrame, s: pd.DataFrame, tag: str, out: Path) -> pd.DataFrame:
    rows, quints = [], []
    r0, ex = s["r0"].to_numpy(), s["excess"].to_numpy()
    absdev = np.abs(r0 - np.nanmean(r0))
    for name, (col, direction, discrete) in STATES.items():
        st, b = state_and_buckets(o, col, discrete)
        g_lvl, g_exc = hac_slope(r0, st), hac_slope(ex, st)
        g_var = hac_slope(absdev, st)                       # L54: the variance side
        q, qe = bucket_means(b, r0), bucket_means(b, ex)
        inc = direction == "up"
        dq = np.diff(q["mean"].to_numpy())
        rows.append(dict(
            sample=tag, state=name, direction=direction, n=g_lvl["n"],
            slope=g_lvl["slope"], t_slope=g_lvl["t"], boot_p=block_boot_slope_p(r0, st),
            spearman=spearman(st, r0),
            r2_mean=g_lvl["r2"], r2_var=g_var["r2"], t_var=g_var["t"],
            slope_excess=g_exc["slope"], t_excess=g_exc["t"],
            q_lo=q["mean"].iloc[0], q_hi=q["mean"].iloc[-1],
            mono=int((dq > 0).sum() if inc else (dq < 0).sum()), mono_n=len(dq),
            qe_lo=qe["mean"].iloc[0], qe_hi=qe["mean"].iloc[-1],
            sign_ok=bool((g_lvl["slope"] > 0) == inc),
        ))
        qq = q.copy()
        qq["mean_excess"] = qe["mean"].reindex(qq.index).to_numpy()
        qq.insert(0, "state", name)
        qq.insert(0, "sample", tag)
        quints.append(qq.reset_index())
    R = pd.DataFrame(rows)
    pd.concat(quints, ignore_index=True).to_csv(out / f"g_quintiles_{tag}.csv", index=False)
    R.to_csv(out / f"g_gradient_{tag}.csv", index=False)
    return R


if __name__ == "__main__":
    pd.set_option("display.width", 240, "display.max_columns", 60)
    C = cache_dir()
    OUT = C / "sec1"
    OUT.mkdir(exist_ok=True)

    o = build(C)
    s = series(o)
    keep = np.isfinite(s["r0"])
    o, s = o[keep], s[keep]
    print(f"sessions with a full window: {len(s)}  {s.index.min().date()}..{s.index.max().date()}")

    dec = s.index >= pd.Timestamp(DECISION_START)
    od, sd = o[dec], s[dec]

    print("\n=== N0 · reproduction of the inherited level (gross, cost_rt=0) ===")
    for tag, ss in (("full", s), ("post2021", sd)):
        for d in (0, 10):
            m, t, n = hac(ss[f"r{d}"])
            print(f"  {tag:9s} d={d:<3d} mean={m:6.2f} bps  t_HAC={t:5.2f}  N={n}")

    print("\n=== N0 · L60 hygiene (zero-range % in the 5 min at entry / exit) ===")
    h = od.groupby("year")[["zr_entry", "zr_exit"]].mean().round(2)
    print(h.to_string())

    print("\n=== N0 · tick_volume availability by year (GS1 viability) ===")
    print(o.groupby("year")["tv_pre"].apply(lambda x: float((x > 0).mean() * 100)).round(1).to_string())

    print("\n=== N0 · contamination: is a state secretly an amplitude? ===")
    ap = np.abs(od["pre_ret"].to_numpy())
    for nm, col in (("GS1", "tv_pre"), ("GS1p", "nupd_pre"), ("GS3", "clv_pre")):
        v = od[col].to_numpy(float)
        ok = np.isfinite(v) & np.isfinite(ap)
        print(f"  corr({nm}, |pre-halt return|) = {np.corrcoef(v[ok], ap[ok])[0,1]:+.3f}")

    print("\n=== KG1/KG2/KG3/KG5 · GRADIENTS (decisional sample post-2021, GROSS) ===")
    Rd = run(od, sd, "post2021", OUT)
    print(Rd.round(4).to_string(index=False))
    print("\n--- full sample, traceability only (carries no verdict) ---")
    Rf = run(o, s, "full", OUT)
    print(Rf[["state", "slope", "t_slope", "r2_mean", "r2_var", "t_excess",
              "q_lo", "q_hi", "mono", "mono_n"]].round(4).to_string(index=False))

    print("\n=== quintile detail, post-2021 (level and MATCHED-baseline excess) ===")
    print(pd.read_csv(OUT / "g_quintiles_post2021.csv").round(3).to_string(index=False))

    # ---- carrier-bucket economics + walk-forward + residualised re-test
    print("\n=== KG4/KG7 · carrier bucket: economics, walk-forward, residualisation ===")
    eco = []
    for name, (col, direction, discrete) in STATES.items():
        st, b = state_and_buckets(od, col, discrete)
        lv = np.nanmax(b) if direction == "up" else np.nanmin(b)
        sel = b == lv
        for d in (0, 10):
            r = sd[f"r{d}"].to_numpy()
            m = sel & np.isfinite(r)
            if m.sum() < 40:
                continue
            x = r[m]
            yrs = (sd.index[m].max() - sd.index[m].min()).days / 365.25
            per_yr = len(x) / max(yrs, 1e-9)
            mu, t, _ = hac(x)
            lo, hi_, bp = block_boot_mean(x)
            sr = mu / x.std(ddof=1) * np.sqrt(per_yr)          # L47: sqrt(obs/yr)
            net = mu - COST_MID
            srn = net / x.std(ddof=1) * np.sqrt(per_yr)
            _, tn, _ = hac(x - COST_MID)
            pos, tot, folds = walk_forward(sd.index[m], x)
            eco.append(dict(state=name, d=d, n=int(m.sum()), trades_yr=round(per_yr, 1),
                            gross=mu, t_gross=t, boot_p=bp, ci_lo=lo, ci_hi=hi_,
                            sr_gross=sr, net_mid=net, t_net=tn, sr_net=srn,
                            net_tail=mu - COST_TAIL, bps_yr_net=net * per_yr,
                            wf_pos=pos, wf_tot=tot, folds=np.round(folds, 2).tolist()))
    E = pd.DataFrame(eco)
    E.to_csv(OUT / "g_carrier_economics.csv", index=False)
    print(E.round(3).to_string(index=False))

    print("\n=== reference: the UNCONDITIONAL sleeve on the same sample ===")
    for d in (0, 10):
        x = sd[f"r{d}"].dropna().to_numpy()
        yrs = (sd.index.max() - sd.index.min()).days / 365.25
        per_yr = len(x) / yrs
        mu, t, _ = hac(x)
        pos, tot, folds = walk_forward(sd.dropna(subset=[f"r{d}"]).index, x)
        print(f"  d={d:<3d} n={len(x)} trades/yr={per_yr:.0f} gross={mu:.2f} t={t:.2f} "
              f"SR_gross={mu/x.std(ddof=1)*np.sqrt(per_yr):.2f} "
              f"net={mu-COST_MID:.2f} SR_net={(mu-COST_MID)/x.std(ddof=1)*np.sqrt(per_yr):.2f} "
              f"bps/yr_net={(mu-COST_MID)*per_yr:.0f} WF={pos}/{tot} {np.round(folds,2).tolist()}")

    # ---- GS2 detail: the three structural darkness levels, spelled out
    print("\n=== GS2 detail · structural darkness levels (post-2021) ===")
    st2, b2 = state_and_buckets(od, "dark_h", True)
    for lv, lab in ((0.0, "weekday halt (~1h)"), (1.0, "post-holiday (~25h)"),
                    (2.0, "weekend / Sunday reopen (~49h+)")):
        m = (b2 == lv) & np.isfinite(sd["r0"].to_numpy())
        if m.sum() == 0:
            print(f"  level {lv:.0f} {lab:34s} n=0")
            continue
        x = sd["r0"].to_numpy()[m]
        mu, t, _ = hac(x)
        exm = np.nanmean(sd["excess"].to_numpy()[m])
        print(f"  level {lv:.0f} {lab:34s} n={m.sum():4d} dark_h median="
              f"{np.nanmedian(od['dark_h'].to_numpy()[m]):7.2f}  gross={mu:6.2f} t={t:5.2f}"
              f"  excess_BL-A={exm:6.2f}")

    # ---- contamination: GS1 residualised on |pre-halt return|
    print("\n=== KG1 contamination control · GS1 residualised on |pre-halt return| ===")
    import statsmodels.api as smapi
    v = causal_rank(od["tv_pre"])
    ap = np.abs(od["pre_ret"].to_numpy())
    ok = np.isfinite(v) & np.isfinite(ap)
    res = np.full(len(v), np.nan)
    fit = smapi.OLS(v[ok], smapi.add_constant(ap[ok])).fit()
    res[ok] = fit.resid
    for lab, xx in (("GS1 raw rank", v), ("GS1 residualised", res),
                    ("|pre-halt return| alone", ap)):
        g = hac_slope(sd["r0"].to_numpy(), xx)
        print(f"  {lab:26s} slope={g['slope']:8.3f}  t={g['t']:6.2f}  R2_mean={g['r2']:.5f}")

    # ---- L38 orthogonality + DSR, on the reference sleeve and on the best cell
    print("\n=== L38 (beta to vol-targeted buy&hold) + DSR (root dsr.py) ===")
    from dsr import deflated_sharpe_ratio, estimate_std_sr_trials
    # L38 needs a buy&hold that is DISJOINT from the sleeve: r24 mechanically
    # contains the window, so it is reported only as a contaminated upper bound.
    bh = (sd["a2"] + sd["a3"]).to_numpy()         # the other 16h of the same cycle
    bh_c = sd["r24"].to_numpy()
    fam = []
    cells = {"UNCONDITIONAL d=0": np.isfinite(sd["r0"].to_numpy())}
    for name, (col, direction, discrete) in STATES.items():
        st, b = state_and_buckets(od, col, discrete)
        lv = np.nanmax(b) if direction == "up" else np.nanmin(b)
        cells[f"{name} carrier"] = (b == lv) & np.isfinite(sd["r0"].to_numpy())
    for lab, m in cells.items():
        x = sd["r0"].to_numpy()[m]
        yrs = (sd.index[m].max() - sd.index[m].min()).days / 365.25
        ppy = max(int(round(len(x) / yrs)), 2)
        fam.append(np.nanmean(x) / np.nanstd(x, ddof=1) * np.sqrt(ppy))
    sd_tr = estimate_std_sr_trials(fam, periods_per_year=250, n_obs=len(sd))
    for lab, m in cells.items():
        x = sd["r0"].to_numpy()[m]
        r2s = []
        for y in (bh[m], bh_c[m]):
            ok = np.isfinite(x) & np.isfinite(y)
            r2s.append(float(np.corrcoef(x[ok], y[ok])[0, 1] ** 2) if ok.sum() > 50 else np.nan)
        r2, r2c = r2s
        yrs = (sd.index[m].max() - sd.index[m].min()).days / 365.25
        ppy = max(int(round(len(x) / yrs)), 2)
        d = deflated_sharpe_ratio(x[np.isfinite(x)] / 1e4, n_trials=6,
                                  periods_per_year=ppy, rf=0.0,
                                  std_sr_trials=sd_tr)
        print(f"  {lab:34s} n={len(x):4d} SR={d['sharpe']:5.2f} DSR={d['dsr']:.3f} "
              f"skew={d['skewness']:+.2f}  R2_vs_BH_disjoint={r2:6.1%}"
              f"  (R2_vs_BH_24h_contaminated={r2c:5.1%})")
    print(f"  (std_sr_trials declared = {sd_tr:.3f}, n_trials = 6 primary states)")

    s.to_parquet(OUT / "g_series.parquet")
    o.to_parquet(OUT / "g_sessions.parquet")
