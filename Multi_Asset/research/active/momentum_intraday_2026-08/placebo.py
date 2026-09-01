"""
Matched placebo for grid survivors (gross |t|>2.5) -- PREREGISTRATION.md gate 5 / L58 discipline.
Keeps the EXACT set of trigger timestamps, OR widths and bracket distances (same days trade,
same exit mechanics) and only randomly reassigns which triggers get +1 vs -1 direction
(preserving the original long/short COUNT) -- breaks the specific causal (early-move -> later-
move) link while leaving every other feature of the day (volatility regime, bracket width,
timing) untouched. 500 draws, reports the empirical percentile of the observed gross HAC-t.
"""
from __future__ import annotations
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "mr_intraday_grille_2026-08"))
import engine_lib as EL
sys.path.insert(0, str(HERE))
import dataload as DL
import signals as SG

RNG = np.random.default_rng(20260825)
N_DRAWS = 500


def placebo_for_cell(symbol, construction_fn, kwargs, label, capped=False):
    df = DL.load(symbol)
    res = construction_fn(df, bars_per_day=DL.BARS_PER_DAY, symbol=symbol, **kwargs)
    sig, sl, tp, mh = res[0], res[1], res[2], res[3]
    scale = EL.vol_target_scale(df, DL.BARS_PER_DAY[symbol] * 252)
    cost = 0.0  # gross placebo, per mandate constraint 5 (gross first)

    trig_idx = np.where(sig != 0)[0]
    dirs = sig[trig_idx].copy()

    def run_with_dirs(d):
        s = np.zeros_like(sig)
        s[trig_idx] = d
        if capped:
            out = SG.run_cell_capped(df, s, sl, tp, mh, scale, cost, n_trials=1)
        else:
            out = EL.run_cell(df, s, sl, tp, mh, scale, cost, DL.BARS_PER_DAY[symbol] * 252, n_trials=1)
        return out["gross_t"]

    observed_t = run_with_dirs(dirs)
    draws = np.empty(N_DRAWS)
    for i in range(N_DRAWS):
        shuffled = RNG.permutation(dirs)
        draws[i] = run_with_dirs(shuffled)
    draws = draws[np.isfinite(draws)]
    pct = float((draws >= observed_t).mean()) if observed_t >= 0 else float((draws <= observed_t).mean())
    return dict(label=label, symbol=symbol, observed_gross_t=observed_t,
               placebo_mean=float(draws.mean()), placebo_std=float(draws.std()),
               placebo_p95=float(np.quantile(draws, 0.95)), placebo_p05=float(np.quantile(draws, 0.05)),
               empirical_one_sided_p=pct, n_draws=len(draws))


if __name__ == "__main__":
    t0 = time.time()
    rows = []
    for sym in ["EURJPY", "EURGBP", "USDJPY", "GBPUSD"]:
        r = placebo_for_cell(sym, SG.construction_b, dict(K=2, exit_type="X4"),
                             f"B_orb_K2_X4_{sym}", capped=True)
        print(r, flush=True)
        rows.append(r)
    r = placebo_for_cell("XAGUSD", SG.construction_a, dict(K=2, H="8bars", exit_type="X2"),
                         "A_gao_K2_H8_X2_XAGUSD", capped=False)
    print(r, flush=True)
    rows.append(r)
    r = placebo_for_cell("US30", SG.construction_c, dict(g0=1.0, H="rest", exit_type="X2"),
                         "C_gap_US30", capped=False)
    print(r, flush=True)
    rows.append(r)
    out = pd.DataFrame(rows)
    out.to_csv(HERE / "placebo_results.csv", index=False)
    print(f"\nWrote {len(out)} rows -> placebo_results.csv ({time.time()-t0:.0f}s)")
