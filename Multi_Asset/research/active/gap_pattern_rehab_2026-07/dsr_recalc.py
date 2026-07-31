"""
dsr_recalc.py — Phase 2: published DSR gate vs corrected DSR (./dsr.py, commit 8f1c60ad).

The audit's `ftmo_lab.gate_dsr` computed
    e_max = sqrt(2 ln N) * (1 - gamma/sqrt(2 ln N))
and compared it DIRECTLY to the annualised Sharpe. That expression is
E[max of N *standard* normals] — it is in units of sigma_SR. Comparing it to a
Sharpe is only valid if sigma_SR == 1.0 annualised, i.e. if the backtest were
exactly one year long. Here T ~ 5300 trades at ~200 trades/yr => the sampling
noise floor alone is sqrt(tpy/T) ~ 0.19, ~5x smaller.

This script:
  1. reproduces the published benchmark (to prove the diagnosis),
  2. recomputes E[max SR] with a MEASURED trial dispersion,
  3. reports the DSR at several plausible family counters N1.
"""
from __future__ import annotations
import os, sys, json, math
import numpy as np, pandas as pd

ROOT = "<HOME>/Desktop/Algo_claude"
sys.path.insert(0, ROOT)
from dsr import (deflated_sharpe_ratio, estimate_std_sr_trials,  # noqa: E402
                 sampling_noise_floor_sr, _expected_max_sr)

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "repro_summary.json")))


def published_emax(n):
    g = 0.5772156649
    root = math.sqrt(2.0 * math.log(n))
    return root * (1.0 - g / root)


rows = []
for tag in ("s035", "s036"):
    d = S[tag]
    grid = np.array(d["grid_sharpes"])
    g = pd.read_csv(os.path.join(HERE, f"{tag}_grid_metrics.csv"))
    best = g.loc[g["sharpe"].idxmax()]
    tr = pd.read_parquet(os.path.join(HERE, f"{tag}_trades_best.parquet"))
    r = tr["netR"].values
    T = len(r)
    ppy = int(round(float(best["tpy"])))          # annualisation = trades/yr (ftmo_lab convention)

    floor = sampling_noise_floor_sr(T, ppy)
    sd_obs = float(grid.std(ddof=1))
    sd_used = estimate_std_sr_trials(grid, periods_per_year=ppy, n_obs=T)

    for n_trials, label in ((9, "N=9 own 3x3 grid"),
                            (18, "N=18 gap family A+B"),
                            (109, "N=109 audit cohort (strategies)"),
                            (981, "N=981 audit cohort x 9 cells")):
        out = deflated_sharpe_ratio(r, n_trials=n_trials, periods_per_year=ppy, rf=0.0,
                                    mean_sr_trials=0.0, std_sr_trials=sd_used)
        rows.append(dict(strat=tag, n_trials=n_trials, label=label,
                         sharpe=out["sharpe"], sd_used=sd_used, sd_obs=sd_obs, floor=floor,
                         emax_corrected=out["sr_benchmark"],
                         emax_published=published_emax(n_trials),
                         dsr=out["dsr"], passed_095=out["passed"],
                         skew=out["skewness"], exkurt=out["excess_kurtosis"],
                         T=T, ppy=ppy))

df = pd.DataFrame(rows)
df.to_csv(os.path.join(HERE, "dsr_recalc.csv"), index=False)
pd.set_option("display.width", 220)
print(df.round(4).to_string(index=False))

print("\n--- diagnosis of the published gate ---")
for tag in ("s035", "s036"):
    d = S[tag]
    print(f"{tag}: published SR_obs={d['best_sharpe']:.3f} vs E_max_published(N=9)="
          f"{published_emax(9):.3f} -> FAIL (as reported).")
    grid = np.array(d["grid_sharpes"])
    g = pd.read_csv(os.path.join(HERE, f"{tag}_grid_metrics.csv"))
    T = int(g.loc[g['sharpe'].idxmax(), 'trades']); ppy = int(round(g.loc[g['sharpe'].idxmax(), 'tpy']))
    sd = estimate_std_sr_trials(grid, periods_per_year=ppy, n_obs=T)
    print(f"      implicit sigma_SR of the published gate = 1.000 (dimensionless E[max] used as SR)")
    print(f"      measured sigma_SR across the 9 trials    = {grid.std(ddof=1):.4f}"
          f"  (floor sqrt({ppy}/{T}) = {sampling_noise_floor_sr(T, ppy):.4f}, used {sd:.4f})")
    print(f"      corrected E[max SR] at N=9 = {_expected_max_sr(9, 0.0, sd):.4f}")
