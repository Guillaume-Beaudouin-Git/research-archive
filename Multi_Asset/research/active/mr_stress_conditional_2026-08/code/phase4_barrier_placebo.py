"""Matched placebo for the BARRIER layer (the gross gate is already decided upstream).

Coordinator constraint: persistence ALONE, with zero expectation, buys p(pass).  The
control must preserve mean, distribution and autocorrelation and destroy only the
alignment with the barrier.

Instantiating "circular shift" correctly matters here.  Circularly shifting the *daily
return series* is degenerate: `simulate_campaign` block-bootstraps that series, so a
rotation leaves its own law unchanged except at one seam.  The non-degenerate rotation
is of the **state series against the returns** -- it keeps every trade, every return,
the trade clustering and the state autocorrelation, and destroys exactly one thing:
which sessions get labelled "stress".  That is the alignment the whole thesis rests on.

  PL-0  circular shift of the STATE series (lag >= 60 sessions), Q5 sleeve rebuilt.
        Mean, distribution, autocorrelation of both inputs preserved; alignment killed.
  PL-A  demeaned observed sleeve  - identical path shape, expectation exactly 0.
  PL-B  block-shuffled + demeaned - persistence kept only within 10-day blocks.
  PL-C  block sign-flip           - preserves |returns| and clustering, kills the drift.

PL-0 is the coordinator's control.  PL-A/B/C bound how much of p(pass) is pure geometry.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, "<HOME>/Desktop/Algo_claude_mrstress")

import mr_state as M  # noqa: E402
from Portfolio.admission.barrier import BarrierConfig, simulate_campaign  # noqa: E402

CACHE = Path(sys.argv[1])
RNG = np.random.default_rng(11)
COST = 1.8
VMS = (5, 10, 20, 40)
N_PL = 60


def acf1(x):
    x = np.asarray(x, float) - np.mean(x)
    return float((x[1:] @ x[:-1]) / (x @ x)) if (x @ x) > 0 else np.nan


def build(states, tf="15m", logic="rsi14", theta=25.0, ex="mt"):
    """Return trade table (with session dates) and the daily state series."""
    df = M.rth_bars("GER40", tf)
    op = df["open"].values.astype(float)
    dev = M.compute_dev(df, logic)
    days = pd.DatetimeIndex(df["day"])
    sess = pd.factorize(days)[0]
    s, r, d, e = M.build_trades(op, dev, sess, theta, ex, M.H_BY_TF[tf])
    st = states["GER40"]["P2"].dropna()
    sd = pd.DatetimeIndex(st.index).tz_localize(None).normalize()
    state = pd.Series(st.values, index=sd)
    tdays = pd.DatetimeIndex(days.values[e]).tz_localize(None).normalize()
    return pd.DataFrame(dict(date=tdays, ret=r, side=s)), state


def sleeve(T, state, cal, shift=0, cost=COST):
    """Q5-only net daily sleeve, with the state series circularly shifted by `shift`."""
    stt = pd.Series(np.roll(state.values, shift), index=state.index)
    p = stt.reindex(T.date).values
    q = np.floor(np.clip(p, 0, 0.999999) * 5) + 1
    m = np.isfinite(p) & (q == 5)
    if m.sum() < 30:
        return None
    g = T.ret.values[m]
    dts = pd.DatetimeIndex(T.date.values[m])
    gross = pd.Series(g).groupby(dts).sum()
    ntr = pd.Series(g).groupby(dts).size()
    return ((gross - ntr * cost).reindex(cal).fillna(0.0) * 1e-4).values


if __name__ == "__main__":
    states = {n: M.daily_state(n) for n in M.SPEC}
    cal = pd.DatetimeIndex(states["GER40"].dropna(subset=["P2"]).index).tz_localize(None).normalize()
    T, state = build(states)
    r = sleeve(T, state, cal)
    cfg = BarrierConfig()

    print(f"observed Q5 sleeve (GER40 15m rsi14 th25 mt, net @{COST} bps): n={len(r)}, "
          f"mean {1e4*r.mean():.3f} bps/day, sd {1e4*r.std():.1f}, "
          f"flat {100*(r==0).mean():.1f} %, acf(1) {acf1(r):.4f}", flush=True)

    # ---- PL-0: circular shift of the STATE series --------------------------------
    nS = len(state)
    lags = RNG.choice(np.arange(60, nS - 60), size=N_PL, replace=False)
    pl0 = {vm: [] for vm in VMS}
    stats0 = []
    for lg in lags:
        x = sleeve(T, state, cal, shift=int(lg))
        if x is None:
            continue
        stats0.append((1e4 * x.mean(), acf1(x), 100 * (x == 0).mean()))
        for vm in VMS:
            pl0[vm].append(simulate_campaign(x, cfg, n_paths=1500, mean_block=10.0,
                                             seed=int(lg) % 997, scale=vm).p_pass)
    s0 = np.array(stats0)
    print(f"\nPL-0 sanity: {len(s0)} shifted states | mean bps/day "
          f"{s0[:,0].mean():+.3f} (obs {1e4*r.mean():+.3f}) | acf(1) {s0[:,1].mean():.4f} "
          f"(obs {acf1(r):.4f}) | flat {s0[:,2].mean():.1f} % (obs {100*(r==0).mean():.1f} %)",
          flush=True)

    print("\n### p(pass): observed vs placebos (observed 4000 paths, placebos 1500 each)")
    print(f"{'vm':>4s} {'p_obs':>7s} | {'PL-0 med':>8s} {'PL-0 p95':>8s} {'p_ge':>6s} | "
          f"{'PL-A med':>8s} {'PL-B med':>8s} {'PL-C med':>8s} {'A p_ge':>7s}")
    for vm in VMS:
        obs = simulate_campaign(r, cfg, n_paths=4000, mean_block=10.0, seed=3, scale=vm).p_pass
        v0 = np.array(pl0[vm])
        pls = {"A": [], "B": [], "C": []}
        for k in range(N_PL // 2):
            a = r - r.mean()
            nb, L = int(np.ceil(len(r) / 10)), 10
            st_ = RNG.integers(0, len(r), size=nb)
            idx = (st_[:, None] + np.arange(L)[None, :]).reshape(-1)[:len(r)] % len(r)
            b = r[idx] - r[idx].mean()
            sg = np.repeat(RNG.choice([-1.0, 1.0], size=nb), L)[:len(r)]
            c = r * sg
            c -= c.mean()
            for nm, x in (("A", a), ("B", b), ("C", c)):
                pls[nm].append(simulate_campaign(x, cfg, n_paths=1500, mean_block=10.0,
                                                 seed=200 + k, scale=vm).p_pass)
        A = np.array(pls["A"])
        print(f"{vm:>4d} {obs:>7.3f} | {np.median(v0):>8.3f} {np.percentile(v0,95):>8.3f} "
              f"{(v0>=obs).mean():>6.3f} | {np.median(A):>8.3f} "
              f"{np.median(pls['B']):>8.3f} {np.median(pls['C']):>8.3f} "
              f"{(A>=obs).mean():>7.3f}", flush=True)
