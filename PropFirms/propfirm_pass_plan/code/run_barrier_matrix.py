"""
run_barrier_matrix.py — WS-A. p(pass<=3mo) of a *fixed modest honest shape* across barrier
archetypes. Shows that the barrier (firm rules), not just alpha, drives p(pass). Committed runner.
Outputs results/firm_barrier_matrix.csv. Firm params are REPRESENTATIVE 2026 archetypes spanning the
rule space — verify exact current numbers before purchase (see PLAN.md / sources).
"""
import os, csv, numpy as np
from barrier_engine import sim_challenge, best_p, outer_ci, synth_shape

T3 = 63  # ~3 months
FIRMS = {
 # key:                         (steps, targets,        maxdd, daily, dd_type,    daily_type, min_days, consistency)
 "FTMO_2step":                  (2, [0.10, 0.05], 0.10, 0.05, "static",   "hard", 4, None),
 "FTMO_1step":                  (1, [0.10],        0.10, 0.03, "trailing", "hard", 4, None),
 "The5ers_1step(5%DD)":         (1, [0.08],        0.05, None, "static",   "soft", 0, 0.50),
 "FundedNext_1step":            (1, [0.10],        0.06, 0.03, "static",   "hard", 0, 0.40),
 "Gen_1step_static_loose":      (1, [0.10],        0.10, None, "static",   "soft", 3, None),
 "Gen_1step_static_8":          (1, [0.08],        0.08, None, "static",   "soft", 3, None),
 "Gen_2step_no_daily":          (2, [0.10, 0.05], 0.10, None, "static",   "soft", 4, None),
 "Topstep_futures(trail)":      (1, [0.06],        0.04, 0.02, "trailing", "soft", 2, 0.50),
 "Instant_1step_generous":      (1, [0.09],        0.12, None, "static",   "soft", 0, None),
}
def firm_dict(t):
    return dict(steps=t[0], targets=t[1], maxdd=t[2], daily=t[3], dd_type=t[4],
                daily_type=t[5], min_days=t[6], consistency=t[7])

SHAPES = {"SR0.4_k4": (0.4, 4, -0.3), "SR0.6_k4": (0.6, 4, -0.3),
          "SR0.6_k8": (0.6, 8, -0.5), "SR0.8_k4": (0.8, 4, -0.3)}

if __name__ == "__main__":
    os.makedirs("../results", exist_ok=True)
    rows = []
    print(f"{'firm':26s} | " + " ".join(f"{s:>9s}" for s in SHAPES), flush=True)
    for fk, ft in FIRMS.items():
        firm = firm_dict(ft); cells = {}
        for sk, (sr, ku, sk_) in SHAPES.items():
            d = synth_shape(sr, kurt=ku, skew=sk_, n=1000, seed=11)
            p, L = best_p(d, firm, T3, Ls=(1.5, 2, 2.5, 3, 4), npaths=5000, seed=3)
            cells[sk] = p
            rows.append(dict(firm=fk, shape=sk, p_pass=round(p, 3), bestL=L))
        print(f"{fk:26s} | " + " ".join(f"{cells[s]:9.3f}" for s in SHAPES), flush=True)
    with open("../results/firm_barrier_matrix.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["firm", "shape", "p_pass", "bestL"]); w.writeheader(); w.writerows(rows)
    print("\nsaved results/firm_barrier_matrix.csv", flush=True)
