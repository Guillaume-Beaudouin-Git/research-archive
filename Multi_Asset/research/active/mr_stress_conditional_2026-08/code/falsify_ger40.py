"""GER40 is the only instrument with a positive stress gradient. Try to kill it.

The pooled breadth distribution is a coin flip (share of positive slopes 0.506),
but GER40 alone shows mean slope +3.47 with 82 % positive.  Either that is Nagel's
mechanism surviving on one instrument, or it is an artefact.  Battery:

  A. state-proxy agreement  - does VIX (Nagel's OWN variable) agree with realised vol?
  B. sub-period stability   - is the whole gradient one crisis (COVID / 2022)?
  C. concentration          - top 1 % / 5 % of the P&L.
  D. STATE-LABEL PERMUTATION - circular block permutation of the daily state series,
     trades untouched.  Preserves trade clustering AND state autocorrelation; the
     only thing destroyed is the alignment between state and return.  This is the
     null the breadth over-dispersion (13 cells at |t|>2.5 vs ~2 expected iid) demands.
  E. L38 beta-orthogonality against a vol-targeted buy-and-hold of GER40.
  F. economics at the MEASURED cost (1.8 bps RT indices) and p(pass) under FTMO
     barriers - reported as an "even if it were real" bound, not a promotion.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "<HOME>/Desktop/Algo_claude_mrstress")

import mr_state as M  # noqa: E402

CACHE = Path(sys.argv[1])
RNG = np.random.default_rng(7)
COST_RT_BPS = 1.8      # measured, COST_AUDIT.md -- never the `spread` column

CELLS = [
    ("primary  5m sma20_z th2.5 ts", "5m", "sma20_z", 2.5, "ts"),
    ("best     15m rsi14  th25  mt", "15m", "rsi14", 25.0, "mt"),
    ("2nd      15m rsi14  th25  ts", "15m", "rsi14", 25.0, "ts"),
    ("3rd      15m rsi14  th20  mt", "15m", "rsi14", 20.0, "mt"),
]


def trades_for(tf, logic, theta, ex, proxy, states):
    df = M.rth_bars("GER40", tf)
    op = df["open"].values.astype(float)
    dev = M.compute_dev(df, logic)
    days = pd.DatetimeIndex(df["day"])
    sess = pd.factorize(days)[0]
    s, r, d, e = M.build_trades(op, dev, sess, theta, ex, M.H_BY_TF[tf])
    st = states["GER40"][proxy]
    pct_bar = pd.Series(st.values, index=st.index).reindex(days).values
    pt = pct_bar[e]
    keep = np.isfinite(pt)
    return (pd.DataFrame(dict(date=days.values[e][keep], side=s[keep], ret=r[keep],
                              pct=pt[keep])),
            pd.Series(st.dropna().values, index=st.dropna().index))


def qof(p):
    return np.floor(np.clip(p, 0, 0.999999) * 5) + 1


if __name__ == "__main__":
    pd.set_option("display.width", 240, "display.max_columns", 30)
    states = {n: M.daily_state(n) for n in M.SPEC}

    for label, tf, logic, theta, ex in CELLS:
        print("\n" + "=" * 100)
        print(f"### GER40 {label}")
        T, stser = trades_for(tf, logic, theta, ex, "P2", states)
        T["q"] = qof(T["pct"].values)
        T["year"] = pd.DatetimeIndex(T["date"]).year
        sl, ts, ps = M.hac_slope(T.ret.values, T.pct.values)
        print(f"n={len(T)}  mean_all={T.ret.mean():.3f}  slope={sl:.3f} (t {ts:.2f}, p {ps:.4f})")

        # ---- A. state-proxy agreement -------------------------------------------
        print("-- A. state proxy agreement (same trades, different state variable)")
        for px_ in ("P1", "P2", "P3"):
            T2, _ = trades_for(tf, logic, theta, ex, px_, states)
            s2, t2, p2 = M.hac_slope(T2.ret.values, T2.pct.values)
            q2 = qof(T2.pct.values)
            m5 = T2.ret.values[q2 == 5]
            nm = {"P1": "VIX (Nagel's own)", "P2": "realised vol", "P3": "intraday disp"}[px_]
            print(f"   {px_} {nm:<20s} slope {s2:7.3f} (t {t2:5.2f}, p {p2:.3f})  "
                  f"Q5 mean {m5.mean():7.3f} (t {M.hac_t(m5):5.2f}, n {len(m5)})")

        # ---- B. sub-period stability --------------------------------------------
        print("-- B. Q5 by year (the gradient must not be one crisis)")
        q5 = T[T.q == 5]
        yr = q5.groupby("year")["ret"].agg(["size", "mean"])
        print("   " + "  ".join(f"{y}:{v['mean']:+.1f}({int(v['size'])})"
                                for y, v in yr.iterrows()))
        print(f"   years with Q5 mean > 0 : {(yr['mean'] > 0).sum()}/{len(yr)}")
        covid = (pd.DatetimeIndex(q5.date) >= "2020-02-15") & (pd.DatetimeIndex(q5.date) <= "2020-06-30")
        print(f"   Q5 all           : n {len(q5):5d}  mean {q5.ret.mean():+7.3f}  t {M.hac_t(q5.ret.values):5.2f}")
        print(f"   Q5 ex-COVID      : n {(~covid).sum():5d}  mean {q5.ret.values[~covid].mean():+7.3f}"
              f"  t {M.hac_t(q5.ret.values[~covid]):5.2f}")
        print(f"   Q5 COVID window  : n {covid.sum():5d}  mean "
              f"{q5.ret.values[covid].mean() if covid.sum() else float('nan'):+7.3f}"
              f"   ({100*covid.sum()/len(q5):.1f} % of Q5 trades)")
        sl2, ts2, ps2 = M.hac_slope(T.ret.values[~((pd.DatetimeIndex(T.date) >= "2020-02-15") &
                                                   (pd.DatetimeIndex(T.date) <= "2020-06-30"))],
                                    T.pct.values[~((pd.DatetimeIndex(T.date) >= "2020-02-15") &
                                                   (pd.DatetimeIndex(T.date) <= "2020-06-30"))])
        print(f"   slope ex-COVID   : {sl2:.3f} (t {ts2:.2f}, p {ps2:.4f})")

        # ---- C. concentration ----------------------------------------------------
        x = np.sort(q5.ret.values)[::-1]
        n1, n5 = max(1, int(0.01 * len(x))), max(1, int(0.05 * len(x)))
        print(f"-- C. concentration of Q5: top1% = {100*x[:n1].sum()/x.sum():.1f} % of P&L, "
              f"top5% = {100*x[:n5].sum()/x.sum():.1f} %, mean ex-top5% = "
              f"{x[n5:].mean():+.3f} bps, WR = {(q5.ret>0).mean():.3f}")

        # ---- D. state-label permutation -----------------------------------------
        sdays = pd.DatetimeIndex(stser.index).tz_localize(None).normalize()
        base = pd.Series(stser.values, index=sdays)
        tdays = pd.DatetimeIndex(T.date).tz_localize(None).normalize()
        nS, L = len(base), 21
        obs_sl, obs_d = sl, q5.ret.mean() - T.ret.values[T.q == 1].mean()
        null_sl, null_d = [], []
        vals = base.values
        for _ in range(2000):
            nb = int(np.ceil(nS / L))
            st_ = RNG.integers(0, nS, size=nb)
            idx = (st_[:, None] + np.arange(L)[None, :]).reshape(-1)[:nS] % nS
            perm = pd.Series(vals[idx], index=base.index)
            p_ = perm.reindex(tdays).values
            ok = np.isfinite(p_)
            if ok.sum() < 200:
                continue
            rr, pp = T.ret.values[ok], p_[ok]
            b = np.polyfit(pp, rr, 1)[0]
            qq = qof(pp)
            if (qq == 5).sum() < 20 or (qq == 1).sum() < 20:
                continue
            null_sl.append(b)
            null_d.append(rr[qq == 5].mean() - rr[qq == 1].mean())
        null_sl, null_d = np.array(null_sl), np.array(null_d)
        print(f"-- D. block permutation of the STATE LABELS (L=21 sessions, {len(null_sl)} draws)")
        print(f"   observed slope {obs_sl:+.3f} | null mean {null_sl.mean():+.3f} "
              f"sd {null_sl.std():.3f} | p(null >= obs) = {(null_sl >= obs_sl).mean():.4f} "
              f"| percentile {100*(null_sl < obs_sl).mean():.1f}")
        print(f"   observed Q5-Q1 {obs_d:+.3f} | null mean {null_d.mean():+.3f} "
              f"sd {null_d.std():.3f} | p(null >= obs) = {(null_d >= obs_d).mean():.4f} "
              f"| percentile {100*(null_d < obs_d).mean():.1f}")

        # ---- E/F. only for the primary cell -------------------------------------
        if label.startswith("primary"):
            daily = q5.groupby(pd.DatetimeIndex(q5.date).normalize())["ret"].sum()
            allday = pd.DatetimeIndex(base.index)
            sleeve = daily.reindex(pd.DatetimeIndex(daily.index.union(
                pd.DatetimeIndex(stser.index).tz_localize(None).normalize()))).fillna(0.0)
            # L38: vol-targeted buy&hold of GER40, session close to close
            df = M.rth_bars("GER40", "5m")
            cc = df.groupby("day")["px"].last()
            bh = np.log(cc).diff() * 1e4
            bh.index = pd.DatetimeIndex(bh.index).tz_localize(None).normalize()
            vt = (bh / bh.rolling(63, min_periods=63).std().shift(1)).dropna()
            J = pd.concat([sleeve.rename("s"), vt.rename("b")], axis=1).dropna()
            import statsmodels.api as sm
            fit = sm.OLS(J.s.values, sm.add_constant(J.b.values)).fit(
                cov_type="HAC", cov_kwds={"maxlags": 6})
            print(f"-- E. L38 beta-orthogonality (n={len(J)}): beta {fit.params[1]:+.4f} "
                  f"(t {fit.tvalues[1]:.2f}), alpha {fit.params[0]:+.3f} bps "
                  f"(t {fit.tvalues[0]:.2f}), R2 = {100*fit.rsquared:.2f} %  "
                  f"[> 30 % would mean 'not a new sleeve']")

            ntr = q5.groupby(pd.DatetimeIndex(q5.date).normalize())["ret"].size().reindex(
                sleeve.index).fillna(0)
            net = sleeve - ntr * COST_RT_BPS
            tpy = ntr.sum() / (len(sleeve) / 252)
            print(f"-- F. economics of the Q5-only sleeve (gate is GROSS; this is downstream)")
            print(f"   trades/yr {tpy:.1f} | gross {sleeve.sum()/(len(sleeve)/252):.1f} bps/yr "
                  f"| net @1.8bps RT {net.sum()/(len(sleeve)/252):.1f} bps/yr")
            print(f"   flat days {100*(sleeve==0).mean():.1f} % | "
                  f"net daily SR {252**0.5*net.mean()/net.std() if net.std()>0 else float('nan'):.2f}")
            try:
                from Portfolio.admission.barrier import BarrierConfig, simulate_campaign
                cfg = BarrierConfig()
                print("   FTMO 2-phase, daily -5 % on equity, STATIC floor -10 %, no time limit:")
                print("     vm   p(pass)  med.days  p_floor  p_daily  p_timeout")
                for vm in (1, 5, 10, 20, 40, 80):
                    res = simulate_campaign(net.values * 1e-4, cfg, n_paths=3000,
                                            mean_block=10.0, seed=1, scale=vm)
                    print(f"    {vm:3d}   {res.p_pass:6.3f}   {res.median_days_to_funded:7.1f}"
                          f"   {res.p_fail_floor:6.3f}   {res.p_fail_daily:6.3f}"
                          f"   {res.p_timeout:6.3f}")
            except Exception as exc:  # pragma: no cover
                print("   barrier sim unavailable:", exc)
