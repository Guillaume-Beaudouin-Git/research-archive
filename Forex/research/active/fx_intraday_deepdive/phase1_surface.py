"""
phase1_surface.py — bulletproof H1's cost-kill: is the gross<cost failure structural across windows,
or an artifact of the primary (asian_start=23, exit=12) choice? Sweep asian_start x exit on the PRIMARY
European pool. Each cell is a falsification-robustness variant and counts toward N (honest inflation).

Also: delay 0/1/2/3 on the primary cell (F4 check) and a recent-regime (>=2016) cost/net check.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm

import fx_intraday_lib as L
import funnel_lib as F

RES = Path(__file__).parent / "results"


def nw_t(s, maxlags=6):
    s = pd.Series(s).dropna().to_numpy()
    if len(s) < 30 or s.std() < 1e-18:
        return 0.0
    return float(sm.OLS(s, np.ones(len(s))).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags}).tvalues[0])


def pool_cell(syms, asian_start_hh, exit_hh, delay_bars=1, since=None):
    """Equal-weight gross sign-portfolio + cost, on the primary pool, for one (start,exit,delay) cell."""
    daily_gross, daily_net, gpt, cpt = {}, {}, [], []
    for s in syms:
        t = L.session_table(s, asian_start_hh=asian_start_hh, open_hh=7, exit_hh=exit_hh, delay_bars=delay_bars)
        sig = (-t["asian_ret"]) / t["asian_ret"].shift(1).rolling(60, min_periods=20).std(ddof=0)
        t = t.assign(x=sig).dropna(subset=["x", "trade_ret"])
        if since is not None:
            t = t[t.index >= pd.Timestamp(since)]
        if len(t) < 100:
            continue
        pos = np.sign(t["x"])
        gross = pos * t["trade_ret"]                                    # delayed-entry trade leg
        cost = 0.5 * F.rt_cost_fraction(s, t["sp_entry"].to_numpy(), t["entry_px"].to_numpy()) \
             + 0.5 * F.rt_cost_fraction(s, t["sp_exit"].to_numpy(), t["exit_px"].to_numpy())
        daily_gross[s] = gross.rename(s); daily_net[s] = (gross - cost).rename(s)
        gpt.append(float(gross.mean()) * 1e4); cpt.append(float(cost.mean()) * 1e4)
    G = pd.concat(daily_gross.values(), axis=1).mean(axis=1)
    Nn = pd.concat(daily_net.values(), axis=1).mean(axis=1)
    return dict(g_sharpe=round(F.ann_sharpe(G), 3), g_t=round(nw_t(G), 2), n_sharpe=round(F.ann_sharpe(Nn), 3),
                gross_bps=round(float(np.mean(gpt)), 3), cost_bps=round(float(np.mean(cpt)), 3),
                ratio=round(float(np.mean(gpt) / np.mean(cpt)), 3), days=int(G.dropna().shape[0]))


def main():
    out = {"surface": {}, "delay": {}, "recent": {}}
    starts, exits = [22, 23, 0], [10, 11, 12, 13, 15]
    print(f"{'start':>5s} {'exit':>4s} | {'gSh':>6s} {'g_t':>5s} {'nSh':>7s} {'gross':>6s} {'cost':>6s} {'ratio':>6s}")
    best = None
    for a in starts:
        for e in exits:
            c = pool_cell(L.PRIMARY, a, e)
            out["surface"][f"a{a:02d}_e{e:02d}"] = c
            print(f"{a:>5d} {e:>4d} | {c['g_sharpe']:>6.2f} {c['g_t']:>5.2f} {c['n_sharpe']:>7.2f} "
                  f"{c['gross_bps']:>6.2f} {c['cost_bps']:>6.2f} {c['ratio']:>6.3f}")
            if best is None or c["ratio"] > best[1]["ratio"]:
                best = (f"a{a:02d}_e{e:02d}", c)
    print(f"\nBEST gross/cost ratio cell: {best[0]} -> ratio {best[1]['ratio']} "
          f"(gross {best[1]['gross_bps']} bps, cost {best[1]['cost_bps']} bps) | bar = 1.5")
    # F4 delay sweep on primary cell (23,12)
    print("\nDelay sweep on primary cell (asian23/exit12):")
    for dl in [0, 1, 2, 3]:
        c = pool_cell(L.PRIMARY, 23, 12, delay_bars=dl)
        out["delay"][f"d{dl}"] = c
        print(f"  delay+{dl}: gSh {c['g_sharpe']:>5.2f} g_t {c['g_t']:>5.2f} gross {c['gross_bps']:>5.2f} bps")
    # recent regime (>=2016) at best cell
    a, e = int(best[0][1:3]), int(best[0][5:7])
    cr = pool_cell(L.PRIMARY, a, e, since="2016-01-01")
    out["recent"] = {"cell": best[0], **cr}
    print(f"\nRecent regime >=2016 at best cell {best[0]}: gross {cr['gross_bps']} bps, cost {cr['cost_bps']} bps, "
          f"ratio {cr['ratio']}, net_sharpe {cr['n_sharpe']}")
    (RES / "phase1_surface.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
