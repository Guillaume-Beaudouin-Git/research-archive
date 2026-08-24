"""Funded dynamic-sizing study Q1-Q5. Reuses v2.2 funded engine read-only from main dir."""
import importlib.util, json, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import book_funded_dynamic as B
V, C22, E = B.V, B.C22, B.E
INIT = B.INIT
OUT = HERE.parent / "results"
MAIN = "<HOME>/Desktop/Algo_claude"
_s = importlib.util.spec_from_file_location("yt_stats", f"{MAIN}/yt_strategy_replications/engine/stats.py")
S = importlib.util.module_from_spec(_s); _s.loader.exec_module(S)
N_TRIALS = 8


def cohorts(M, step=21, end="2025-06-30", horizon=504):
    idx = M["dates_idx"]
    last = np.where(idx <= __import__("pandas").Timestamp(end))[0][-1]
    return np.array([i for i in range(0, last + 1, step) if i + horizon < M["n"]])


def run_set(M, WT, ON, cfg, starts, horizon, diag=False):
    surv, extr, mineq, kinds, vmm, isoos = [], [], [], [], [], []
    for s in starts:
        c = dict(cfg, diag=diag)
        r = B.run_funded_dyn(M, int(s), WT, ON, c, horizon=horizon, wd_every=C22.FUNDED_WD_EVERY)
        surv.append(not r["busted"])
        extr.append(0.8 * (r["wd"] + r["residual"]))
        mineq.append(r["min_eq"] / INIT - 1.0)
        kinds.append(r["kind"]); vmm.append(r["vm_mean"])
        isoos.append("IS" if M["dates_idx"][int(s)] < __import__("pandas").Timestamp("2019-01-01") else "OOS")
    surv = np.array(surv); extr = np.array(extr); isoos = np.array(isoos)
    daily = sum(1 for k in kinds if k == "daily"); floor = sum(1 for k in kinds if k == "floor")
    return dict(p_survive=float(surv.mean()), n=len(surv),
                extr_med=float(np.median(extr)), extr_mean=float(extr.mean()),
                extr_med_IS=float(np.median(extr[isoos == "IS"])) if (isoos == "IS").any() else np.nan,
                extr_med_OOS=float(np.median(extr[isoos == "OOS"])) if (isoos == "OOS").any() else np.nan,
                surv_IS=float(surv[isoos == "IS"].mean()) if (isoos == "IS").any() else np.nan,
                surv_OOS=float(surv[isoos == "OOS"].mean()) if (isoos == "OOS").any() else np.nan,
                mineq_p5=float(np.percentile(mineq, 5)) * 100, mineq_worst=float(np.min(mineq)) * 100,
                bust_daily=daily, bust_floor=floor, vm_mean=float(np.mean(vmm)),
                extr_arr=extr)


def block_ci(arr, block=10, nboot=1000):
    rng = np.random.default_rng(0); n = len(arr); nb = int(np.ceil(n / block))
    meds = np.empty(nboot)
    for b in range(nboot):
        idx = np.concatenate([np.arange(s, s + block) % n for s in rng.integers(0, n, nb)])[:n]
        meds[b] = np.median(arr[idx])
    return float(np.percentile(meds, 5)), float(np.percentile(meds, 95))


def main():
    t0 = time.time()
    M = V.load_stack(orb_rt_bps=C22.ORB_RT_BPS)
    WT_df, ON_df = E.build_signals(); WT, ON = E.align_signals(M, WT_df, ON_df)
    st = {h: cohorts(M, horizon=h) for h in (126, 252, 504)}
    res = {"n_trials_dsr": N_TRIALS}

    # ---- validation: baseline vm=1, alpha=0, withdraw-all == canonical run_funded ----
    print("=== VALIDATION run_funded_dyn(baseline) vs canonical V.run_funded ===")
    mism = 0
    for s in st[504][:40]:
        cfg0 = dict(C22.CFG_FUNDED, alpha=0.0, asym=False, c_keep=0.0)
        r1 = B.run_funded_dyn(M, int(s), WT, ON, cfg0, horizon=504, wd_every=C22.FUNDED_WD_EVERY)
        r2 = V.run_funded(M, int(s), WT, ON, C22.CFG_FUNDED, horizon=504, wd_every=C22.FUNDED_WD_EVERY)
        if r1["busted"] != r2["busted"] or abs(r1["wd"] - r2["wd"]) > 1e-6 or abs(r1["residual"] - r2["residual"]) > 1e-6:
            mism += 1
    print(f"  mismatches over 40 cohorts: {mism}  -> {'PASS' if mism == 0 else 'FAIL'}")
    res["validation_mismatches"] = mism

    # ---- configs ----
    CF = dict(C22.CFG_FUNDED)
    B0 = dict(CF, alpha=0.0, asym=False, c_keep=0.0)                    # current regime (withdraw-all)
    B1 = dict(CF, alpha=0.0, asym=False, c_keep=0.20)                   # static vm1 + cushion-retain
    STAT = {f"S_vm{v}": dict(CF, vm=v, alpha=0.0, asym=False, c_keep=0.20) for v in (1.5, 2.0, 2.5)}
    VAR = {}
    for a in (1.0, 2.0, 4.0):
        for asym in (False, True):
            VAR[f"a{a}_asym{int(asym)}"] = dict(CF, vm=1.0, alpha=a, asym=asym, c_keep=0.20,
                                                ramp=0.02, vm_cap=3.0)

    # ---- Q1 diagnostic: worst-day distribution at vm=1.0 + bust composition ----
    B.DIAG["worst_day"].clear()
    d0_252 = run_set(M, WT, ON, B0, st[252], 252, diag=True)
    wd = np.array(B.DIAG["worst_day"])
    res["Q1_diagnostic"] = dict(
        daily_budget=-500.0,
        worst_day_p50=round(float(np.percentile(wd, 50)), 1),
        worst_day_p5=round(float(np.percentile(wd, 5)), 1),
        worst_day_p1=round(float(np.percentile(wd, 1)), 1),
        worst_day_min=round(float(wd.min()), 1),
        frac_days_below_400=round(float((wd < -400).mean()), 4),
        B0_252=dict(p_survive=round(d0_252["p_survive"], 4), extr_med=round(d0_252["extr_med"], 0),
                    bust_daily=d0_252["bust_daily"], bust_floor=d0_252["bust_floor"]))
    print(f"\n=== Q1 diagnostic (vm=1.0) ===")
    print(f"  daily budget -$500 | worst-day loss p50 {np.percentile(wd,50):.0f} p5 {np.percentile(wd,5):.0f} "
          f"p1 {np.percentile(wd,1):.0f} min {wd.min():.0f}  (frac days < -$400: {(wd<-400).mean()*100:.2f}%)")
    print(f"  B0 252d: survive {d0_252['p_survive']*100:.1f}%  extr_med ${d0_252['extr_med']:.0f}  "
          f"busts daily/floor {d0_252['bust_daily']}/{d0_252['bust_floor']}")

    # ---- run all configs at 3 horizons ----
    allcfg = {"B0": B0, "B1": B1, **STAT, **VAR}
    table = {}
    print(f"\n=== survie / extraction médiane par config ===")
    print(f"{'config':<14}{'vmMean':>7} | {'surv6m':>7}{'extr6m':>8} | {'surv12m':>8}{'extr12m':>9}"
          f"{'IS/OOS surv':>13} | {'surv24m':>8}{'extr24m':>9}{'dailyBust':>10}{'minEqW%':>9}")
    for name, cfg in allcfg.items():
        row = {}
        for h in (126, 252, 504):
            row[h] = run_set(M, WT, ON, cfg, st[h], h)
        table[name] = {str(h): {k: (round(v, 4) if isinstance(v, float) else v)
                                for k, v in row[h].items() if k != "extr_arr"} for h in row}
        table[name]["extr_arr_252"] = row[252]["extr_arr"]
        r12 = row[252]
        print(f"{name:<14}{r12['vm_mean']:>7.2f} | {row[126]['p_survive']*100:>6.1f}%${row[126]['extr_med']:>6.0f} "
              f"| {r12['p_survive']*100:>6.1f}%${r12['extr_med']:>7.0f}"
              f"{r12['surv_IS']*100:>5.0f}/{r12['surv_OOS']*100:>4.0f}% | "
              f"{row[504]['p_survive']*100:>6.1f}%${row[504]['extr_med']:>7.0f}"
              f"{r12['bust_daily']:>5}/{r12['bust_floor']:<3}{r12['mineq_worst']:>8.1f}")

    # ---- Q5: dominance vs B0 + matched-static placebo ----
    print(f"\n=== Q5 dominance (12m) vs B0 + placebo static-apparié ===")
    b0 = table["B0"]["252"]
    b0lo, b0hi = block_ci(table["B0"]["extr_arr_252"])
    res["Q5"] = dict(B0=dict(extr_med=round(b0["extr_med"], 0), ci90=[round(b0lo, 0), round(b0hi, 0)],
                             survive=round(b0["p_survive"], 4)))
    verdicts = {}
    for name in list(STAT) + list(VAR):
        t = table[name]["252"]
        lo, hi = block_ci(table[name]["extr_arr_252"])
        dominates = (lo > b0hi) and (t["p_survive"] >= b0["p_survive"] - 0.01) \
            and (t["extr_med_IS"] > b0["extr_med_IS"]) and (t["extr_med_OOS"] > b0["extr_med_OOS"])
        verdicts[name] = dict(extr_med=round(t["extr_med"], 0), ci90=[round(lo, 0), round(hi, 0)],
                              survive=round(t["p_survive"], 4), vm_mean=round(t["vm_mean"], 2),
                              d_extr_vs_B0=round(t["extr_med"] - b0["extr_med"], 0),
                              d_surv_vs_B0=round(t["p_survive"] - b0["p_survive"], 4),
                              dominates_B0=bool(dominates))
        print(f"  {name:<14} vm{t['vm_mean']:.2f} extr ${t['extr_med']:.0f} [{lo:.0f},{hi:.0f}] "
              f"surv {t['p_survive']*100:.1f}% (Δsurv {(t['p_survive']-b0['p_survive'])*100:+.1f}) "
              f"dom_B0={dominates}")
    res["Q5"]["configs"] = verdicts
    res["table"] = {n: {h: table[n][h] for h in ("126", "252", "504")} for n in table}

    (OUT / "q_funded_sizing.json").write_text(json.dumps(res, indent=2, default=str))
    print(f"\nwritten q_funded_sizing.json  [{time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()
