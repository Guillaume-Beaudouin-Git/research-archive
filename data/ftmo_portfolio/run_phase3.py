"""Phase 3 — cohort Monte Carlo on the exact simulator.

Usage: python3 run_phase3.py GRID_IS | FINAL <vol_mult> <breaker> | STRESS ...
Design grid on IS cohorts (2013-10 -> 2019-12, weekly starts);
validation on OOS cohorts (2020-01 -> 2025-12) with the chosen config.
"""
import sys
import numpy as np
import pandas as pd
import config as C
import simulator as S

def load_days(swap_mul=1.0, spread_mul=1.0):
    m5 = pd.read_parquet(C.CACHE / "sim_m5.parquet")
    sL = pd.read_parquet(C.CACHE / "panel_swapL.parquet") * swap_mul
    sS = pd.read_parquet(C.CACHE / "panel_swapS.parquet") * swap_mul
    mu = pd.read_parquet(C.CACHE / "panel_mult.parquet")
    rt = pd.read_csv(C.OUT / "phase0_rt_cost_bps.csv", index_col=0).iloc[:, 0] * spread_mul
    D = S.build_days(m5, sL, sS, mu, rt)
    try:
        orb = pd.read_parquet(C.CACHE / "orb_e7_R15.parquet")["R"]
        idx = pd.DatetimeIndex(D.dates)
        D.orb_R = orb.reindex(idx).fillna(0.0).to_numpy(float)
    except Exception as e:
        print("orb load skipped:", e)
    return D


def align(D):
    WT = pd.read_parquet(C.CACHE / "sim_WT.parquet")
    ON = pd.read_parquet(C.CACHE / "sim_ON.parquet")["on"]
    idx = pd.DatetimeIndex(D.dates)
    WTa = WT.reindex(idx).fillna(0.0).to_numpy(float)
    ONa = ON.reindex(idx).fillna(0.0).to_numpy(float)
    return WTa, ONa


def cohort_eval(D, WT, ON, cfg, starts, retries):
    res = []
    for i0 in starts:
        r = S.run_funnel(D, i0, WT, ON, cfg, wall_days=C.MISSION_HORIZON_CAL_DAYS,
                         retries=retries)
        res.append(r)
    df = pd.DataFrame(res)
    out = dict(p_funded=df["funded"].mean(), n=len(df),
               med_t=df.loc[df.funded, "t"].median() if df.funded.any() else np.nan,
               mean_attempts=df["attempts"].mean())
    return out, df


def starts_range(D, lo, hi, step=5):
    idx = pd.DatetimeIndex(D.dates)
    sel = np.where((idx >= lo) & (idx <= hi))[0]
    return sel[::step]


BASE = dict(target=C.PHASE1_TARGET, on_w=0.35, breaker_frac=0.30, orb_risk=0.0025,
            taper_buf=0.04, glide=0.5, quantize=True,
            daily_realize=False, weekend_flat=False, pace=1, p2_mult=0.8,
            max_cal_days=C.MISSION_HORIZON_CAL_DAYS)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "GRID_IS"
    D = load_days()
    WT, ON = align(D)
    if mode == "GRID_IS":
        vols = [float(x) for x in (sys.argv[2].split(",") if len(sys.argv) > 2
                                   else ["1.0", "1.5", "2.0", "3.0"])]
        st = starts_range(D, "2013-10-01", "2019-12-31", step=5)
        rows = []
        for vm in vols:
            cfg = dict(BASE, vol_mult=vm)
            r1, _ = cohort_eval(D, WT, ON, cfg, st, retries=False)
            rR, _ = cohort_eval(D, WT, ON, cfg, st, retries=True)
            rows.append(dict(vol_mult=vm, p1try=r1["p_funded"], med_t_1try=r1["med_t"],
                             pRetry=rR["p_funded"], med_t_R=rR["med_t"],
                             attempts=rR["mean_attempts"]))
            print(rows[-1], flush=True)
        pd.DataFrame(rows).to_csv(C.OUT / "phase3_grid_is.csv", index=False)
    elif mode == "DIAG":
        vols = [float(x) for x in sys.argv[2].split(",")]
        st = starts_range(D, "2013-10-01", "2019-12-31", step=5)
        for vm in vols:
            cfg = dict(BASE, vol_mult=vm)
            outs = []
            for i0 in st:
                r = S.run_attempt(D, i0, WT, ON, cfg)
                outs.append((r["outcome"], r["days_used"]))
            o = pd.DataFrame(outs, columns=["outcome", "days"])
            tab = o.groupby("outcome").agg(n=("days", "size"), med_days=("days", "median"))
            tab["pct"] = (tab["n"] / len(o) * 100).round(1)
            print(f"--- P1-only outcomes @vol_mult={vm} ---")
            print(tab.to_string(), flush=True)
    elif mode == "DIAG2":
        vm = float(sys.argv[2])
        st = starts_range(D, "2013-10-01", "2019-12-31", step=5)
        for dr in (False, True):
            for wf in (False, True):
                cfg = dict(BASE, vol_mult=vm, daily_realize=dr, weekend_flat=wf)
                outs = [S.run_attempt(D, i0, WT, ON, cfg)["outcome"] for i0 in st]
                vc = pd.Series(outs).value_counts(normalize=True).round(3)
                print(f"dr={int(dr)} wf={int(wf)} ->", vc.to_dict(), flush=True)
    elif mode == "GRID2":
        st = starts_range(D, "2013-10-01", "2019-12-31", step=5)
        rows = []
        vms = [float(x) for x in sys.argv[2].split(",")]
        p2s = [float(x) for x in sys.argv[3].split(",")]
        onws = [float(x) for x in (sys.argv[4].split(",") if len(sys.argv) > 4 else ["0.35"])]
        paces = [int(x) for x in (sys.argv[5].split(",") if len(sys.argv) > 5 else ["1"])]
        for vm in vms:
            for p2 in p2s:
                for onw in onws:
                    for pace in paces:
                        cfg = dict(BASE, vol_mult=vm, p2_mult=p2, on_w=onw, pace=pace)
                        rR, _ = cohort_eval(D, WT, ON, cfg, st, retries=True)
                        rows.append(dict(vm=vm, p2=p2, onw=onw, pace=pace,
                                         p=rR["p_funded"], med_t=rR["med_t"],
                                         att=rR["mean_attempts"]))
                        print(rows[-1], flush=True)
        f = C.OUT / "phase3_grid2_is.csv"
        pd.DataFrame(rows).to_csv(f, index=False, mode="a", header=not f.exists())
    elif mode == "FDIAG":
        vm = float(sys.argv[2]); p2m = float(sys.argv[3])
        pace = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        glide = float(sys.argv[5]) if len(sys.argv) > 5 else BASE["glide"]
        pace_k = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
        cfg = dict(BASE, vol_mult=vm, p2_mult=p2m, pace=pace, glide=glide,
                   pace_k=pace_k)
        st = starts_range(D, "2013-10-01", "2019-12-31", step=5)
        recs = []
        for i0 in st:
            start_date = D.dates[i0]
            c1 = dict(cfg); c1["target"] = C.PHASE1_TARGET
            r1 = S.run_attempt(D, i0, WT, ON, c1)
            rec = dict(p1=r1["outcome"], d1=r1["days_used"], p2="-", d2=0)
            if r1["outcome"] == "pass":
                j = min(r1["last_idx"] + 3, D.n - 1)
                c2 = dict(cfg); c2["target"] = C.PHASE2_TARGET
                c2["vol_mult"] = vm * p2m
                r2 = S.run_attempt(D, j, WT, ON, c2)
                rec["p2"] = r2["outcome"]; rec["d2"] = r2["days_used"]
                rec["tot_days"] = (D.dates[min(r2['last_idx'], D.n-1)] - start_date).days
            recs.append(rec)
        df = pd.DataFrame(recs)
        print(f"== FDIAG vm={vm} p2m={p2m} pace={pace} (first attempt only) ==")
        print("P1:", df.p1.value_counts(normalize=True).round(3).to_dict())
        dfp = df[df.p1 == "pass"]
        print("P2 | P1 passed:", dfp.p2.value_counts(normalize=True).round(3).to_dict())
        ok = dfp[dfp.p2 == "pass"]
        if len(ok):
            print(f"both-pass: {len(ok)/len(df)*100:.1f}% of cohorts | tot days p50={ok.tot_days.median():.0f} p90={ok.tot_days.quantile(.9):.0f} | within 182d: {(ok.tot_days<=182).mean()*100:.0f}%")
    elif mode == "NOLIMIT":
        vm = float(sys.argv[2])
        cfg = dict(BASE, vol_mult=vm, max_cal_days=3650)
        st = starts_range(D, "2013-10-01", "2024-06-30", step=5)
        res = [S.run_funnel(D, i0, WT, ON, cfg, wall_days=3650, retries=False) for i0 in st]
        df = pd.DataFrame(res)
        print("NO-LIMIT 1-try p(funded):", df.funded.mean().round(3), "n=", len(df),
              "med_t:", df.loc[df.funded, "t"].median())
    elif mode == "OOS":
        vm = float(sys.argv[2]); br = float(sys.argv[3]) if len(sys.argv) > 3 else 0.30
        cfg = dict(BASE, vol_mult=vm, breaker_frac=br)
        st = starts_range(D, "2020-01-01", "2025-12-15", step=5)
        r1, d1 = cohort_eval(D, WT, ON, cfg, st, retries=False)
        rR, dR = cohort_eval(D, WT, ON, cfg, st, retries=True)
        print("OOS 1-try:", r1); print("OOS retry:", rR)
        d1.to_csv(C.OUT / f"phase3_oos_1try_v{vm}.csv", index=False)
        dR.to_csv(C.OUT / f"phase3_oos_retry_v{vm}.csv", index=False)
    elif mode == "FULL":
        vm = float(sys.argv[2]); br = float(sys.argv[3]) if len(sys.argv) > 3 else 0.30
        lo = sys.argv[4] if len(sys.argv) > 4 else "2013-10-01"
        hi = sys.argv[5] if len(sys.argv) > 5 else "2025-12-15"
        cfg = dict(BASE, vol_mult=vm, breaker_frac=br)
        st = starts_range(D, lo, hi, step=5)
        r1, d1 = cohort_eval(D, WT, ON, cfg, st, retries=False)
        rR, dR = cohort_eval(D, WT, ON, cfg, st, retries=True)
        print("FULL 1-try:", r1); print("FULL retry:", rR)
        idx = pd.DatetimeIndex(D.dates)
        d1["start"] = idx[st]; dR["start"] = idx[st]
        d1.to_csv(C.OUT / f"phase3_full_1try_v{vm}_{lo[:4]}.csv", index=False)
        dR.to_csv(C.OUT / f"phase3_full_retry_v{vm}_{lo[:4]}.csv", index=False)
