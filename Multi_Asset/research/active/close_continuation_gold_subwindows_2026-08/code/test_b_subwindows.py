"""TEST B — sub-window decomposition of the gold Globex-reopen hour.

Pre-registered in ../PREREGISTRATION.md.  The E002 candidate (overnight gold) is
UNDERPOWERED with an open family: p(pass) 0.593, IC90 [0.321 ; 0.817], DSR 0.284
post-2021, cost = 49 % of the signal.  Nobody has ever gone finer than H1 on it.

Three questions, decided in advance:
  1. WHERE is the effect inside the reopen hour?  (cumulative minute profile)
  2. WHAT SURVIVES an entry delay of 1 / 5 / 10 / 15 minutes?  (the test that killed GER40)
  3. HOW MUCH is untradable GAP beyond the 17.5 % already measured on H1?

Invariants: exchange clock with DST (L56, Globex reopen 18:00 ET); RAW M1 — the
inherited `step3_performance.py:47` winsorises at 0.5/99.5 INSIDE the constructor and
its consumers therefore carry truncated tails; gross gate cost_rt = 0; HAC(6);
stationary/circular block bootstrap, never iid.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

CACHE = Path(sys.argv[1])
OUT = CACHE / "testB"
OUT.mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(20260802)

REOPEN_ET = 18                 # CME Globex metals/energy reopen, exchange clock
HALT_HOURS = 1                 # settlement halt 17:00-18:00 ET
WINDOW_HOURS = 8               # inherited sleeve window, NOT modified
DELAYS = (0, 1, 2, 3, 5, 10, 15, 20, 30)     # pre-registered
SLEEVES = {"XAUUSD": "2007-01-01", "XAGUSD": "2007-01-01", "USOIL": "2013-01-01"}
NS_MIN = np.int64(60_000_000_000)
COST = {"XAUUSD": 1.84, "XAGUSD": 3.00, "USOIL": 3.67}      # measured RT, bps
COST_TAIL = {"XAUUSD": 3.88}


def hac(x) -> tuple[float, float, int]:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 30:
        return (np.nan, np.nan, len(x))
    m = sm.OLS(x, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return (float(m.params[0]), float(m.tvalues[0]), len(x))


def block_boot_p(x, nboot=2000, L=10) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 30:
        return np.nan
    nb = int(np.ceil(n / L))
    st = RNG.integers(0, n, size=(nboot, nb))
    idx = (st[:, :, None] + np.arange(L)[None, None, :]).reshape(nboot, -1)[:, :n] % n
    m = x[idx].mean(axis=1)
    return float(min(2 * min((m <= 0).mean(), (m >= 0).mean()), 1.0))


def price_at(vals, keys, t, mode, tol_min):
    tol = np.int64(tol_min) * NS_MIN
    if mode == "last":
        i = np.searchsorted(keys, t, side="right") - 1
        ok = (i >= 0) & (t - keys[np.clip(i, 0, len(keys) - 1)] <= tol)
    else:
        i = np.searchsorted(keys, t, side="left")
        ok = (i < len(keys)) & (keys[np.clip(i, 0, len(keys) - 1)] - t <= tol)
    out = vals[np.clip(i, 0, len(keys) - 1)].astype(float)
    out[~ok] = np.nan
    return out


def build(name: str, start: str) -> pd.DataFrame:
    """Session table anchored on the FIRST EXECUTABLE PRINT after the halt.

    The nominal 18:00 ET Globex reopen is NOT when this vehicle starts quoting: the
    broker's own reopen print drifts across eras (see `b_reopen_clock.csv`).  Anchoring
    delays on the wall clock would silently compare different entry conventions across
    the sample, so `t0` = first print at/after 18:00 ET (searched up to 60 min) and every
    delay is measured FROM t0.  The wall-clock version is kept as `pw{d}` for
    traceability against the pre-registration.
    """
    df = pd.read_parquet(CACHE / f"{name}_M1.parquet")
    df = df[df.index >= pd.Timestamp(start, tz="UTC")]
    et = df.index.tz_convert("America/New_York")
    keys = df.index.asi8
    close = df["close"].to_numpy()
    hi, lo, op = df["high"].to_numpy(), df["low"].to_numpy(), df["open"].to_numpy()

    sess = pd.DatetimeIndex(np.unique(et.normalize().tz_localize(None)))
    reopen = (sess + pd.Timedelta(hours=REOPEN_ET)).tz_localize(
        "America/New_York", nonexistent="shift_forward", ambiguous=True).tz_convert("UTC")
    base = reopen.asi8

    out = pd.DataFrame(index=sess)
    out["reopen_utc_hour"] = np.asarray(reopen.hour)
    out["dow"] = sess.dayofweek
    out["year"] = sess.year

    # ---- t0 : the first price this vehicle actually prints at/after the nominal reopen
    i0 = np.searchsorted(keys, base, "left")
    valid = i0 < len(keys)
    t0 = np.full(len(sess), np.nan)
    t0[valid] = keys[i0[valid]]
    lag = (t0 - base) / 60e9
    t0[lag > 60] = np.nan                       # no reopen within an hour -> not a session
    out["t0_lag_min"] = np.where(np.isfinite(t0), lag, np.nan)
    t0i = np.where(np.isfinite(t0), t0, base).astype(np.int64)

    # last print before the halt, and how long the vehicle was dark
    out["p_pre"] = price_at(close, keys, base - HALT_HOURS * 60 * NS_MIN, "last", 120)
    jj = np.searchsorted(keys, base, "left") - 1
    out["dark_min"] = np.where(jj >= 0, (t0i - keys[np.clip(jj, 0, len(keys) - 1)]) / 60e9,
                               np.nan)
    out["halt_bars"] = (np.searchsorted(keys, base, "left")
                        - np.searchsorted(keys, base - HALT_HOURS * 60 * NS_MIN, "left"))

    # ---- prices at t0 + d minutes (the honest, era-robust delay ladder)
    for d in sorted(set(range(0, 61)) | set(DELAYS)):
        out[f"p{d}"] = price_at(close, keys, t0i + d * NS_MIN, "first", 10)
    # ---- wall-clock version, for traceability with the pre-registration
    for d in DELAYS:
        out[f"pw{d}"] = price_at(close, keys, base + d * NS_MIN, "first", 5)

    out["p_end"] = price_at(close, keys, t0i + WINDOW_HOURS * 60 * NS_MIN, "last", 30)
    for d in DELAYS:                       # constant-duration exits (L59 on the exit)
        out[f"pend{d}"] = price_at(close, keys, t0i + (WINDOW_HOURS * 60 + d) * NS_MIN,
                                   "last", 30)
    out.loc[~np.isfinite(t0), ["p_end"] + [f"p{d}" for d in DELAYS]] = np.nan

    # ---- L60 in the entry zone: zero-range and fully frozen bars, first 5 / 60 min from t0
    for tag, span in (("5m", 5), ("60m", 60)):
        a0 = np.searchsorted(keys, t0i, "left")
        a1 = np.searchsorted(keys, t0i + span * NS_MIN, "left")
        zr, fz, nn = np.zeros(len(sess)), np.zeros(len(sess)), np.zeros(len(sess))
        for k in range(len(sess)):
            a, b = a0[k], a1[k]
            if b > a:
                nn[k] = b - a
                zr[k] = (hi[a:b] == lo[a:b]).sum()
                fz[k] = ((hi[a:b] == lo[a:b]) & (close[a:b] == op[a:b])).sum()
        out[f"nbars_{tag}"] = nn
        out[f"zr_{tag}"] = zr
        out[f"frozen_{tag}"] = fz
    return out


def series(out: pd.DataFrame) -> pd.DataFrame:
    s = pd.DataFrame(index=out.index)
    s["gap"] = np.log(out["p0"] / out["p_pre"]) * 1e4
    s["win_cap"] = np.log(out["p_end"] / out["p0"]) * 1e4          # tradable window
    s["win_incl_gap"] = np.log(out["p_end"] / out["p_pre"]) * 1e4  # what H1 measures
    for d in DELAYS:
        s[f"tailfix{d}"] = np.log(out["p_end"] / out[f"p{d}"]) * 1e4
        s[f"taildur{d}"] = np.log(out[f"pend{d}"] / out[f"p{d}"]) * 1e4
        s[f"wallfix{d}"] = np.log(out["p_end"] / out[f"pw{d}"]) * 1e4
    for d in range(0, 61):
        s[f"cum{d}"] = np.log(out[f"p{d}"] / out["p0"]) * 1e4
    for c in ("year", "dow", "halt_bars", "reopen_utc_hour", "t0_lag_min", "dark_min",
              "nbars_5m", "zr_5m", "frozen_5m", "nbars_60m", "zr_60m", "frozen_60m"):
        s[c] = out[c]
    return s


def us_dst_mask(idx: pd.DatetimeIndex) -> np.ndarray:
    """True where the ET reopen maps to 22:00 UTC (US on DST)."""
    loc = (idx + pd.Timedelta(hours=REOPEN_ET)).tz_localize(
        "America/New_York", nonexistent="shift_forward", ambiguous=True).tz_convert("UTC")
    return np.asarray(loc.hour) == 22


if __name__ == "__main__":
    pd.set_option("display.width", 260, "display.max_columns", 90)
    ALL = {}
    for name, start in SLEEVES.items():
        ALL[name] = series(build(name, start))
    for name, s in ALL.items():
        s.to_parquet(OUT / f"{name}_sessions.parquet")

    G = ALL["XAUUSD"]
    core = G.dropna(subset=["gap", "win_cap", "win_incl_gap"])
    print(f"=== B · XAUUSD sessions with a complete window: {len(core)} "
          f"({core.index.min().date()} .. {core.index.max().date()}) ===")

    # ----------- the vehicle's OWN reopen clock (L52: never trust a nominal timestamp)
    print("\n=== B · when does this VEHICLE actually reopen? (minutes after 18:00 ET) ===")
    rc = G.dropna(subset=["t0_lag_min"]).groupby("year").agg(
        n=("t0_lag_min", "size"), med_lag=("t0_lag_min", "median"),
        frac_lag0=("t0_lag_min", lambda s: (s <= 0.5).mean()),
        frac_lag5=("t0_lag_min", lambda s: (s >= 4.5).mean()),
        med_dark_min=("dark_min", "median"),
        halt_quoted=("halt_bars", lambda s: (s > 5).mean()))
    print(rc.round(2).to_string())
    rc.to_csv(OUT / "b_reopen_clock.csv")

    # ------------------------------------------------- KB4 / L60 in the entry zone
    print("\n=== B · KB4 (L60) zero-range / frozen bars in the entry zone, by year ===")
    z = core.groupby("year").apply(lambda g: pd.Series({
        "n_sess": len(g),
        "bars_5m": g["nbars_5m"].mean(),
        "zr_5m_pct": 100 * g["zr_5m"].sum() / max(g["nbars_5m"].sum(), 1),
        "frozen_5m_pct": 100 * g["frozen_5m"].sum() / max(g["nbars_5m"].sum(), 1),
        "zr_60m_pct": 100 * g["zr_60m"].sum() / max(g["nbars_60m"].sum(), 1),
        "halt_quoted": (g["halt_bars"] > 5).mean(),
    }), include_groups=False)
    print(z.round(2).to_string())
    z.to_csv(OUT / "b_l60.csv")

    # ---------------------------------------------------------- KB3 gap decomposition
    print("\n=== B · KB3 gap vs capturable (RAW, no winsorisation) ===")
    rows = []
    for lab, m in (("full", np.ones(len(core), bool)),
                   ("pre2021", core["year"] < 2021),
                   ("post2021", core["year"] >= 2021),
                   ("winter", ~us_dst_mask(core.index)),
                   ("summer", us_dst_mask(core.index)),
                   ("Mon-Fri reopen", core["dow"] < 5),
                   ("Sun reopen", core["dow"] == 6)):
        g = core[m]
        if len(g) < 50:
            continue
        mg, tg, ng = hac(g["gap"])
        mc, tc, _ = hac(g["win_cap"])
        mi, ti, _ = hac(g["win_incl_gap"])
        rows.append(dict(sample=lab, N=ng, gap=mg, t_gap=tg, cap=mc, t_cap=tc,
                         incl=mi, t_incl=ti,
                         gap_share_pct=100 * mg / mi if mi > 0 else np.nan,
                         halt_quoted=g["halt_bars"].gt(5).mean()))
    GD = pd.DataFrame(rows)
    GD.to_csv(OUT / "b_gap.csv", index=False)
    print(GD.round(2).to_string(index=False))

    # ------------------------------------------------- KB6 clock falsification (minute)
    print("\n=== B · KB6 minute profile, winter~summer correlation (ET vs UTC anchor) ===")
    cum_cols = [f"cum{d}" for d in range(1, 61)]
    d_et = us_dst_mask(core.index)
    prof_et_w = core.loc[~d_et, cum_cols].diff(axis=1).mean()
    prof_et_s = core.loc[d_et, cum_cols].diff(axis=1).mean()
    # UTC anchor: fixed 23:00 UTC all year -> in summer that is 19:00 ET, one hour LATE
    utc23 = []
    for name in ["XAUUSD"]:
        df = pd.read_parquet(CACHE / f"{name}_M1.parquet")
        r = (np.log(df["close"]).diff() * 1e4)
        h, mi = df.index.hour, df.index.minute
        sel = (h == 23)
        mm = df.index.month
        w = np.isin(mm, [12, 1, 2]) & sel
        su = np.isin(mm, [6, 7, 8]) & sel
        a = pd.Series(r.to_numpy()[w]).groupby(pd.Series(mi.to_numpy()[w])).mean()
        b = pd.Series(r.to_numpy()[su]).groupby(pd.Series(mi.to_numpy()[su])).mean()
        utc23 = pd.concat([a, b], axis=1).dropna()
    c_et = float(pd.concat([prof_et_w, prof_et_s], axis=1).dropna().corr().iloc[0, 1])
    c_utc = float(utc23.corr().iloc[0, 1])
    print(f"minute profile corr winter~summer  ET-anchored: {c_et:.3f}   "
          f"fixed-23:00-UTC-anchored: {c_utc:.3f}")

    # ------------------------------------------------- KB1/KB2 where is the effect
    print("\n=== B · cumulative profile from the reopen (RAW), bps ===")
    prof = []
    for d in [0, 1, 2, 3, 5, 10, 15, 20, 30, 45, 60]:
        for lab, m in (("full", np.ones(len(core), bool)),
                       ("post2021", core["year"] >= 2021)):
            g = core[m]
            mm, tt, nn = hac(g[f"cum{d}"])
            prof.append(dict(sample=lab, minute=d, N=nn, cum_bps=mm, t=tt))
    P = pd.DataFrame(prof)
    P.to_csv(OUT / "b_profile.csv", index=False)
    print(P.pivot(index="minute", columns="sample",
                  values=["cum_bps", "t", "N"]).round(2).to_string())

    print("\n=== B · KB1/KB2 ENTRY DELAY — the decisive test ===")
    dl = []
    for d in DELAYS:
        for lab, m in (("full", np.ones(len(core), bool)),
                       ("pre2018", core["year"] < 2018),
                       ("post2021", core["year"] >= 2021)):
            g = core[m]
            for conv in ("tailfix", "taildur", "wallfix"):
                mm, tt, nn = hac(g[f"{conv}{d}"])
                dl.append(dict(sample=lab, exit=conv, delay=d, N=nn, m_bps=mm, t=tt,
                               boot_p=block_boot_p(g[f"{conv}{d}"]),
                               net_1p84=mm - COST["XAUUSD"],
                               net_3p88=mm - COST_TAIL["XAUUSD"]))
    DL = pd.DataFrame(dl)
    DL.to_csv(OUT / "b_delay.csv", index=False)
    for conv, desc in (("tailfix", "t0-anchored, fixed window end"),
                       ("taildur", "t0-anchored, constant 8h duration"),
                       ("wallfix", "WALL-CLOCK 18:00 ET anchored (pre-registration literal)")):
        print(f"\n--- exit convention: {conv} ({desc}) ---")
        print(DL[DL.exit == conv].pivot(index="delay", columns="sample",
                                        values=["m_bps", "t", "N"]).round(2).to_string())

    # ------------------------------------------------------------- KB5 concentration
    print("\n=== B · KB5 concentration (drop the best 5 % of sessions) ===")
    conc = []
    for lab, m in (("full", np.ones(len(core), bool)), ("post2021", core["year"] >= 2021)):
        for d in (0, 5, 10):
            x = core.loc[m, f"tailfix{d}"].dropna()
            thr = x.quantile(0.95)
            conc.append(dict(sample=lab, delay=d, n=len(x), mean=x.mean(),
                             mean_ex_top5=x[x < thr].mean(), skew=x.skew(),
                             worst=x.min(), best=x.max(),
                             top5_share_pct=100 * x[x >= thr].sum() / x.sum()
                             if x.sum() != 0 else np.nan))
    C = pd.DataFrame(conc)
    C.to_csv(OUT / "b_concentration.csv", index=False)
    print(C.round(2).to_string(index=False))

    # -------------------------------------- winsorisation: what the inherited code did
    print("\n=== B · winsorisation audit (inherited step3_performance.py:47) ===")
    w = []
    for d in (0,):
        x = core[f"tailfix{d}"].dropna()
        xw = x.clip(*x.quantile([0.005, 0.995]))
        w.append(dict(series=f"tailfix{d}", mean_raw=x.mean(), mean_wins=xw.mean(),
                      sd_raw=x.std(), sd_wins=xw.std(), skew_raw=x.skew(),
                      skew_wins=xw.skew(), worst_raw=x.min(), worst_wins=xw.min()))
    x = core["win_cap"].dropna()
    xw = x.clip(*x.quantile([0.005, 0.995]))
    w.append(dict(series="win_cap", mean_raw=x.mean(), mean_wins=xw.mean(),
                  sd_raw=x.std(), sd_wins=xw.std(), skew_raw=x.skew(),
                  skew_wins=xw.skew(), worst_raw=x.min(), worst_wins=xw.min()))
    W = pd.DataFrame(w)
    W.to_csv(OUT / "b_winsor.csv", index=False)
    print(W.round(3).to_string(index=False))

    # ------------------------------------------------------------- controls: Ag / WTI
    print("\n=== B · controls (same decomposition, silver and WTI) ===")
    ctrl = []
    for name in ("XAGUSD", "USOIL"):
        s = ALL[name].dropna(subset=["gap", "win_cap", "win_incl_gap"])
        for lab, m in (("full", np.ones(len(s), bool)), ("post2021", s["year"] >= 2021)):
            g = s[m]
            mg, tg, ng = hac(g["gap"])
            mi, _, _ = hac(g["win_incl_gap"])
            r = dict(instr=name, sample=lab, N=ng, gap=mg, t_gap=tg, incl=mi,
                     gap_share_pct=100 * mg / mi if mi > 0 else np.nan)
            for d in (0, 5, 10):
                mm, tt, _ = hac(g[f"tailfix{d}"])
                r[f"d{d}"] = mm
                r[f"t{d}"] = tt
            ctrl.append(r)
    CT = pd.DataFrame(ctrl)
    CT.to_csv(OUT / "b_controls.csv", index=False)
    print(CT.round(2).to_string(index=False))
