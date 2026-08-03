"""Phase 3 on the one survivor family (GER40 x rsi14 x 15m): the tests that decide.

  1. ENTRY-DELAY sensitivity.  This is what killed the previous GER40 candidate
     (`mr_timezone_repair_2026-08` s3.3B: +3.52 bps -> +0.56 bps, t 1.00 on a 5-min
     delay).  Here: enter at bar j+1 (base), j+2, j+3 -- i.e. 15 and 30 minutes late.
  2. SELECTION.  The permutation test of phase 2 controls for state autocorrelation,
     NOT for having searched 172 forms.  DSR (root `dsr.py`, the only non-broken
     implementation) with a DECLARED trial dispersion measured on the actual search
     family.
  3. COST.  Measured 1.8 bps RT indices; sensitivity to 2.2 (sim v22) and 3.0.
  4. DECISION METRIC.  Size sweep -> p(pass) and time-to-funded under FTMO barriers.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "<HOME>/Desktop/Algo_claude_mrstress")

import mr_state as M  # noqa: E402
from dsr import deflated_sharpe_ratio, estimate_std_sr_trials  # noqa: E402
from Portfolio.admission.barrier import BarrierConfig, simulate_campaign  # noqa: E402

CACHE = Path(sys.argv[1])
COST = 1.8


def cell_trades(instr, tf, logic, theta, ex, proxy, states, delay=1):
    df = M.rth_bars(instr, tf)
    op = df["open"].values.astype(float)
    dev = M.compute_dev(df, logic)
    days = pd.DatetimeIndex(df["day"])
    sess = pd.factorize(days)[0]
    s, r, d, e = M.build_trades(op, dev, sess, theta, ex, M.H_BY_TF[tf], delay=delay)
    st = states[instr][proxy]
    pct = pd.Series(st.values, index=st.index).reindex(days).values[e]
    ok = np.isfinite(pct)
    return pd.DataFrame(dict(date=days.values[e][ok], side=s[ok], ret=r[ok],
                             pct=pct[ok], q=np.floor(np.clip(pct[ok], 0, .999999) * 5) + 1))


def q5_daily(T, calendar, cost=COST):
    """Net daily return series (fraction) of the Q5-only sleeve, flat days included."""
    q5 = T[T.q == 5]
    dts = pd.DatetimeIndex(q5.date).tz_localize(None).normalize()
    gross = q5.groupby(dts)["ret"].sum()
    ntr = q5.groupby(dts)["ret"].size()
    net = (gross - ntr * cost).reindex(calendar).fillna(0.0)
    return net * 1e-4


if __name__ == "__main__":
    pd.set_option("display.width", 240, "display.max_columns", 30)
    states = {n: M.daily_state(n) for n in M.SPEC}
    cal = pd.DatetimeIndex(states["GER40"].dropna(subset=["P2"]).index).tz_localize(None).normalize()

    FAM = [("15m", "rsi14", 25.0, "mt"), ("15m", "rsi14", 25.0, "ts"),
           ("15m", "rsi14", 20.0, "mt"), ("15m", "rsi14", 20.0, "ts"),
           ("5m", "sma20_z", 2.5, "ts")]

    # ---------------------------------------------------------------- 1. DELAY
    print("### 1. ENTRY-DELAY SENSITIVITY  (Q5 only, GROSS, cost = 0)")
    print(f"{'form':<26s} {'delay':>5s} {'n_Q5':>6s} {'mean':>8s} {'t':>6s} "
          f"{'slope':>8s} {'t_sl':>6s} {'nL':>5s} {'mL':>8s} {'nS':>5s} {'mS':>8s}")
    for tf, logic, th, ex in FAM:
        for dl in (1, 2, 3):
            T = cell_trades("GER40", tf, logic, th, ex, "P2", states, delay=dl)
            q5 = T[T.q == 5]
            if len(q5) < 30:
                continue
            L, S = q5.ret[q5.side > 0].values, q5.ret[q5.side < 0].values
            sl, ts, _ = M.hac_slope(T.ret.values, T.pct.values)
            print(f"{tf+' '+logic+' th'+str(th)+' '+ex:<26s} {dl:>5d} {len(q5):>6d} "
                  f"{q5.ret.mean():>8.2f} {M.hac_t(q5.ret.values):>6.2f} {sl:>8.2f} {ts:>6.2f} "
                  f"{len(L):>5d} {L.mean() if len(L) else np.nan:>8.2f} "
                  f"{len(S):>5d} {S.mean() if len(S) else np.nan:>8.2f}")

    # ------------------------------------------------------- 2. SELECTION / DSR
    print("\n### 2. SELECTION — the search family that produced the winner")
    fam_sr, fam_rows = [], []
    for tf in M.TF_MIN:
        for logic in M.THETAS:
            for th in M.THETAS[logic]:
                for ex in ("ts", "mt"):
                    T = cell_trades("GER40", tf, logic, th, ex, "P2", states)
                    if len(T) < 100 or (T.q == 5).sum() < 30:
                        continue
                    nd = q5_daily(T, cal)
                    sr = (252 ** 0.5 * nd.mean() / nd.std()) if nd.std() > 0 else np.nan
                    fam_sr.append(sr)
                    fam_rows.append((tf, logic, th, ex, int((T.q == 5).sum()), sr))
    fam_sr = np.array([x for x in fam_sr if np.isfinite(x)])
    print(f"GER40 search family: {len(fam_sr)} forms | Q5-only net SR: "
          f"mean {fam_sr.mean():.3f}, sd {fam_sr.std(ddof=1):.3f}, "
          f"min {fam_sr.min():.3f}, max {fam_sr.max():.3f}")
    print("top 6 by net Sharpe:")
    for row in sorted(fam_rows, key=lambda z: -(z[5] if np.isfinite(z[5]) else -9))[:6]:
        print(f"   {row[0]:>4s} {row[1]:<10s} th{row[2]:<5} {row[3]}  nQ5={row[4]:<5d} SR={row[5]:.3f}")

    best = max(fam_rows, key=lambda z: (z[5] if np.isfinite(z[5]) else -9))
    Tb = cell_trades("GER40", best[0], best[1], best[2], best[3], "P2", states)
    nd = q5_daily(Tb, cal)
    print(f"\nbest form = GER40 {best[0]} {best[1]} th{best[2]} {best[3]}  "
          f"(net SR {best[5]:.3f}, {len(nd)} sessions, {100*(nd==0).mean():.1f} % flat)")
    for ntr_ in (len(fam_sr), 184):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            std_dec = estimate_std_sr_trials(fam_sr, periods_per_year=252, n_obs=len(nd))
        res = deflated_sharpe_ratio(nd.values, n_trials=ntr_, periods_per_year=252,
                                    rf=0.0, std_sr_trials=std_dec)
        print(f"   DSR (n_trials={ntr_:>3d}, std_sr_trials={res['std_sr_trials']:.3f} "
              f"[{res['std_sr_trials_source']}]): SR {res['sharpe']:.3f} vs "
              f"E[max SR] {res['sr_benchmark']:.3f}  ->  DSR = {res['dsr']:.4f}  "
              f"{'PASS' if res['passed'] else 'FAIL'}")

    # -------------------------------------------------------------- 3. COST
    print("\n### 3. COST SENSITIVITY (Q5-only sleeve, best form)")
    yrs = len(nd) / 252
    for c in (0.0, 1.8, 2.2, 3.0):
        x = q5_daily(Tb, cal, cost=c)
        sr = 252 ** 0.5 * x.mean() / x.std() if x.std() > 0 else np.nan
        print(f"   cost {c:>4.1f} bps RT: {1e4*x.sum()/yrs:>7.1f} bps/yr, net SR {sr:>6.3f}")

    # ------------------------------------------------- 4. DECISION METRIC
    print("\n### 4. DECISION METRIC — p(pass) and time-to-funded, FTMO 2-phase")
    print(f"   sleeve: {len(nd)} sessions, {100*(nd==0).mean():.1f} % flat, "
          f"ann. {1e4*nd.sum()/yrs:.0f} bps, worst day {1e4*nd.min():.0f} bps, "
          f"skew {pd.Series(nd[nd!=0]).skew():.2f}")
    cfg = BarrierConfig()
    print("     vm   p(pass)  med.days  p_floor  p_daily  p_timeout")
    for vm in (1, 5, 10, 20, 30, 40, 60, 80, 120):
        r = simulate_campaign(nd.values, cfg, n_paths=4000, mean_block=10.0, seed=3, scale=vm)
        print(f"    {vm:4d}   {r.p_pass:6.3f}   {r.median_days_to_funded:7.1f}   "
              f"{r.p_fail_floor:6.3f}   {r.p_fail_daily:6.3f}   {r.p_timeout:6.3f}")
