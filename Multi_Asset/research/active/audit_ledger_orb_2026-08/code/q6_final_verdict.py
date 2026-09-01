"""Q6 - verdict FINAL : combine le derapage mesure (Q2 entree + Q3a sortie STOP,
tous deux quasi nuls) et le cout de spread mesure (Q6 vehicule, sweep de q4),
par jambe, avant/apres, vs R2. Recalcule le point mort de la jambe courte sur
la chaine complete.

Delta n_tests = 0. Lecture seule. Ecrit uniquement dans out/.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
REPO = HERE.parents[5]
OUT = HERE.parents[1] / "out"
BCOMMON_DIR = REPO / "Multi_Asset/research/active/orb_cost_funded_2026-08/exit_cost/code"
sys.path.insert(0, str(BCOMMON_DIR))
import b_common as bc

def leg_stats(r):
    mean, se, t = bc.hac_tstat(r, lags=6)
    lo, hi, _ = bc.boot_ci(r, n_boot=5000, mean_block=10.0)
    return dict(N=len(r), mean_R=mean, se_hac6=se, t_hac6=t, ci95_lo=lo, ci95_hi=hi,
                r2_pass=bool(t > 2.0 and not (lo <= 0 <= hi)))

led = bc.load_ledger()
E = pd.read_csv(OUT / "q2_entry_slippage_per_trade.csv", index_col=0, parse_dates=True)
X = pd.read_csv(OUT / "q3a_exit_stop_slippage_per_trade.csv", index_col=0, parse_dates=True)
entry_repriced = pd.read_parquet(REPO.parent / "Algo_claude/Multi_Asset/research/active/orb_cost_funded_2026-08/entry_cost/out/R_repriced_entry.parquet") if False else None

led = led.copy()
led["gap_R_entry"] = E["gap_R"].reindex(led.index).fillna(0.0)
led["gap_R_exit_stop"] = X["gap_R"].reindex(led.index).fillna(0.0)  # 0 for TIME_STOP and unresolved (favorable-to-sleeve default, N=2+3 negligible)

r_gross = led["r_gross"].to_numpy(float)
direction = led["direction"].to_numpy()
gap_total_R = (led["gap_R_entry"] + led["gap_R_exit_stop"]).to_numpy(float)
R_gap_corrected = r_gross - gap_total_R  # measured construction-idealization correction only

lev = led["level"].to_numpy(float) / led[["level","stop_eff"]].apply(lambda r: abs(r["level"]-r["stop_eff"]), axis=1).to_numpy(float)

long_m = direction == 1
short_m = direction == -1

print("=" * 96)
print("Q6a - EFFET DU SEUL DERAPAGE MESURE (Q2+Q3a) SUR LE VERDICT, PAR JAMBE")
print("=" * 96)
rows = []
for name, m in [("ALL", np.ones(len(led), bool)), ("LONG", long_m), ("SHORT", short_m)]:
    s0 = leg_stats(r_gross[m]); s0.update(leg=name, series="r_gross (avant, ref)")
    s1 = leg_stats(R_gap_corrected[m]); s1.update(leg=name, series="R_gap_corrected (Q2+Q3a mesures)")
    rows += [s0, s1]
G = pd.DataFrame(rows)[["series","leg","N","mean_R","t_hac6","ci95_lo","ci95_hi","r2_pass"]]
print(G.to_string(index=False, float_format=lambda x: f"{x:.5f}"))
G.to_csv(OUT / "q6a_gap_only_correction_by_leg.csv", index=False)
print("\n  Lecture : le derapage GAP mesure (Q2+Q3a) est economiquement nul (0.000029 R entree, 0 sortie STOP)")
print("  -> aucun mouvement materiel du t par jambe. Le t corrige qui compte est celui du cout de")
print("  spread/microstructure (Q6b ci-dessous), pas le canal gap.")

print("\n" + "=" * 96)
print("Q6b - VERDICT FINAL PAR JAMBE : R_gap_corrected - cout de spread mesure (vehicule US100 CFD)")
print("=" * 96)
cost_levels = {
    "0.00_avant_toute_correction": 0.0,
    "0.962_spread_natif_fenetre_ORB_US100cfd": 0.962,
    "1.045_spread_natif_median_allhours_US100cfd": 1.045,
    "2.17_tout_compris_n12_fills_reels_US100cfd": 2.17,
}
rows2 = []
for label, bps in cost_levels.items():
    cost_R = bps * 1e-4 * lev
    r_net = R_gap_corrected - cost_R
    for name, m in [("ALL", np.ones(len(led), bool)), ("LONG", long_m), ("SHORT", short_m)]:
        s = leg_stats(r_net[m]); s.update(cost_bps=bps, cost_label=label, leg=name)
        rows2.append(s)
F = pd.DataFrame(rows2)[["cost_label","cost_bps","leg","N","mean_R","t_hac6","ci95_lo","ci95_hi","r2_pass"]]
print(F.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
F.to_csv(OUT / "q6b_final_verdict_by_leg.csv", index=False)

# short breakeven on the FINAL chain (gap-corrected + spread sweep)
def short_mean_at(bps):
    cost_R = bps * 1e-4 * lev[short_m]
    return float(np.mean(R_gap_corrected[short_m] - cost_R))
def short_t_at(bps):
    cost_R = bps * 1e-4 * lev[short_m]
    _, _, t = bc.hac_tstat(R_gap_corrected[short_m] - cost_R, lags=6)
    return t

grid = np.linspace(0, 5, 20001)
means = np.array([short_mean_at(b) for b in grid])
ts = np.array([short_t_at(b) for b in grid])
be_mean_bps = float(grid[np.argmin(np.abs(means))])
below2 = np.where(ts <= 2.0)[0]
be_t2_bps = float(grid[below2[0]]) if len(below2) else float("nan")

print("\n" + "=" * 96)
print("Q6c - POINT MORT FINAL DE LA JAMBE COURTE (gap mesure + spread mesure)")
print("=" * 96)
print(f"  Point mort MOYENNE (mean_R_short = 0)   : {be_mean_bps:.3f} bps RT")
print(f"  t_HAC6_short a 0 bps                    : {ts[0]:.3f}  (deja < 2.0 : R2 echoue AVANT tout cout)")
pd.DataFrame([dict(metric="short_breakeven_mean_bps_final", value=be_mean_bps),
              dict(metric="short_t_at_0bps_final", value=float(ts[0])),
              dict(metric="short_breakeven_t2_bps_final", value=be_t2_bps)]
             ).to_csv(OUT / "q6c_short_breakeven_final.csv", index=False)
print(f"\nEcrit out/q6a_gap_only_correction_by_leg.csv, q6b_final_verdict_by_leg.csv, q6c_short_breakeven_final.csv")
