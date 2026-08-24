"""
Phase 3 — robustness (PREREG section 1-3, K1/K4). On the CORE non-crypto futures
universe, cash-account fractional sizing:
  * parameter grid (plateau check) + component ablations -> distinct DSR trials
  * cost stress x1/x2/x3 (same signal, not new trials)
  * IS/OOS split + sequential-block walk-forward (K4: <0.5 OOS or >=2/5 sign-flips)
  * stationary block bootstrap CIs (L=20)
  * monthly correlation to ES (equity-beta / crisis-alpha proxy)
DSR (K1) is computed in funnel_dsr.py from the full trial ledger.
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd

from engine import Params, load_universe, simulate, build_costs, load_specs
from metrics import equity_metrics, block_bootstrap, daily_returns
import trials

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
CORE = ["NQ", "ES", "GC", "CL", "6E", "6A", "6B"]
START, END = "2014-01-01", "2026-06-12"

specs = load_specs()
PER_SIDE, ROLL_BP, MULT = build_costs(specs)
DATA = load_universe(CORE)


def run_cfg(p: Params, cost_mult: float = 1.0, start=START, end=END):
    cs = {s: PER_SIDE[s] * cost_mult for s in CORE}
    rb = {s: ROLL_BP[s] * cost_mult for s in CORE}
    res = simulate(DATA, p, 100_000, cs, rb, MULT, start=start, end=end)
    em = equity_metrics(res["equity"], rf_annual=0.0)
    return em, daily_returns(res["equity"]), res


def sig(p: Params):
    return (p.ema_len, p.breakout, p.atr_stop_mult, p.pyramid_step_atr, p.max_adds, p.long_only, p.trend_filter)


def main():
    seen, grid_rows = {}, []

    def add(p, name, dsr_count=True):
        s = sig(p)
        if s in seen:
            return seen[s]
        em, dr, _ = run_cfg(p)
        seen[s] = (name, em, dr)
        trials.log_trial("P3", name, em["sharpe"], em["cagr"], em["max_drawdown"], notes=str(s), dsr_count=dsr_count)
        return seen[s]

    print("=== parameter grid (cash fractional, two-sided) — plateau check ===")
    for ema in (50, 100, 150, 200):
        for bk in (10, 20, 40, 55):
            _, em, _ = add(Params(ema_len=ema, breakout=bk), f"grid_ema{ema}_bk{bk}")
            grid_rows.append((ema, bk, em["sharpe"]))
            print(f"  EMA{ema:3d} bk{bk:2d}  Sharpe={em['sharpe']:5.2f}  MDD={em['max_drawdown']:6.1%}")
    for st in (2.0, 3.0, 4.0):
        for pyr in (0.5, 1.0):
            _, em, _ = add(Params(atr_stop_mult=st, pyramid_step_atr=pyr), f"grid_stop{st}_pyr{pyr}")
    gsh = [g[2] for g in grid_rows]
    print(f"  GRID Sharpe plateau: min={min(gsh):.2f} max={max(gsh):.2f} (base EMA100/bk20={seen[sig(Params())][1]['sharpe']:.2f})")

    print("\n=== component ablations ===")
    abls = {
        "base_twosided": Params(),
        "no_ema_filter": Params(trend_filter=False),
        "no_pyramid": Params(max_adds=0),
        "long_only": Params(long_only=True),
        "stop_4x": Params(atr_stop_mult=4.0),
        "long_only_no_pyr": Params(long_only=True, max_adds=0),
    }
    abl_out = {}
    for name, p in abls.items():
        _, em, dr = add(p, name)
        abl_out[name] = em
        print(f"  {name:18s} Sharpe={em['sharpe']:5.2f}  CAGR={em['cagr']:6.1%}  MDD={em['max_drawdown']:6.1%}  "
              f"vol={em['ann_vol']:.3f}  skew={em['skew']:5.2f}  Calmar={em['calmar']:.2f}")

    # candidates carried into deep robustness
    candidates = {"base_twosided": Params(), "long_only": Params(long_only=True)}

    print("\n=== cost stress x1/x2/x3 (same signal; not new DSR trials) ===")
    cost_stress = {}
    for name, p in candidates.items():
        row = {}
        for cm in (1.0, 2.0, 3.0):
            em, _, _ = run_cfg(p, cost_mult=cm)
            row[f"x{int(cm)}"] = round(em["sharpe"], 3)
            if cm > 1.0:
                trials.log_trial("P3", f"{name}_cost_x{int(cm)}", em["sharpe"], dsr_count=False, notes="cost stress")
        cost_stress[name] = row
        print(f"  {name:14s} Sharpe x1={row['x1']}  x2={row['x2']}  x3={row['x3']}")

    print("\n=== IS/OOS split (2014-2019 | 2020-2026) ===")
    isoos = {}
    for name, p in candidates.items():
        em_is, _, _ = run_cfg(p, start="2014-01-01", end="2019-12-31")
        em_oos, _, _ = run_cfg(p, start="2020-01-01", end=END)
        isoos[name] = dict(IS=round(em_is["sharpe"], 3), OOS=round(em_oos["sharpe"], 3))
        print(f"  {name:14s} IS Sharpe={em_is['sharpe']:.2f}  OOS Sharpe={em_oos['sharpe']:.2f}")

    print("\n=== sequential-block walk-forward (K4) — fixed pre-registered params ===")
    blocks = [("2014", "2015"), ("2016", "2017"), ("2018", "2019"), ("2020", "2021"), ("2022", "2023"), ("2024", "2026")]
    wf = {}
    for name, p in candidates.items():
        shs = []
        for a, b in blocks:
            em, _, _ = run_cfg(p, start=f"{a}-01-01", end=f"{b}-12-31")
            shs.append(round(em["sharpe"], 2))
        pos = sum(s > 0 for s in shs); flips = sum(s < 0 for s in shs)
        k4 = "FAIL" if (min(shs) < 0.5 and flips >= 2) else ("WEAK" if flips >= 2 else "OK")
        wf[name] = dict(block_sharpes=shs, positive=pos, neg=flips, k4=k4)
        print(f"  {name:14s} blocks {shs}  pos={pos}/6  neg={flips}  K4={k4}")

    print("\n=== block bootstrap CIs (L=20, 2000 resamples) ===")
    boot = {}
    for name, p in candidates.items():
        _, dr, _ = run_cfg(p)
        bb = block_bootstrap(dr, n_boot=2000, block=20)
        boot[name] = {"sharpe": [round(bb.loc[0.025, "sharpe"], 2), round(bb.loc[0.5, "sharpe"], 2), round(bb.loc[0.975, "sharpe"], 2)],
                      "maxdd": [round(bb.loc[0.975, "max_dd"], 3), round(bb.loc[0.5, "max_dd"], 3), round(bb.loc[0.025, "max_dd"], 3)]}
        print(f"  {name:14s} Sharpe 95% CI [{boot[name]['sharpe'][0]}, {boot[name]['sharpe'][2]}] median {boot[name]['sharpe'][1]}")

    print("\n=== monthly corr to ES (equity-beta / crisis-alpha proxy) ===")
    es_m = np.log(DATA["ES"]["close"]).resample("ME").last().diff()
    corr_es = {}
    for name, p in candidates.items():
        _, dr, res = run_cfg(p)
        strat_m = res["equity"]["equity"].resample("ME").last().pct_change()
        j = pd.concat([strat_m.rename("s"), es_m.rename("es")], axis=1).dropna()
        j = j[j.index >= "2014-01-01"]
        down = j[j["es"] < 0]
        corr_es[name] = dict(monthly_corr=round(float(j["s"].corr(j["es"])), 3),
                             avg_ret_es_down_months=round(float(down["s"].mean()), 4))
        print(f"  {name:14s} monthly corr to ES={corr_es[name]['monthly_corr']:.2f}  "
              f"avg strat ret in ES-down months={corr_es[name]['avg_ret_es_down_months']:+.2%}")

    json.dump(dict(grid=grid_rows, ablations={k: v for k, v in abl_out.items()},
                   cost_stress=cost_stress, isoos=isoos, wf=wf, boot=boot, corr_es=corr_es),
              open(RESULTS / "p3_summary.json", "w"), indent=2, default=str)
    print("\nsaved results/p3_summary.json")


if __name__ == "__main__":
    main()
