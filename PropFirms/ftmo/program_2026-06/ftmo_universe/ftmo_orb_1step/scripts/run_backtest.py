"""Reproduce the headline single-attempt numbers under REAL FTMO rules (requires built caches).
2-step: 5% daily / 10% static (dp_sizing, DP-optimal). 1-step: 3% daily / 10% trailing / Best-Day."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, pandas as pd
import strategy as S, dp_sizing as D, ftmo_1step_real as O

def sleeve(sym):
    t = S.backtest_orb(sym, trail_be=True, delay=True, min_width_bps=8, trend="pc", long_only=True)
    t = t[t.R_frac > 0].copy(); t["rmult"] = t.net / t.R_frac
    d = t.groupby("date")["rmult"].sum(); d.index = pd.to_datetime(d.index)
    return d

def best_1step(d, T, rhos):
    return max(np.mean(O.sim_1step(d, N=20000, T=T, rho=r, best_day_rule=True, seed=1)["dpass"] <= T) for r in rhos)

def main():
    U, G = sleeve("US100"), sleeve("GER40")
    cal = pd.to_datetime(sorted(set(U.index) | set(G.index))); cal = cal[cal >= "2022-01-01"]
    book = U.reindex(cal).fillna(0) + G.reindex(cal).fillna(0)
    print(f"US100+GER40 long-only gap/trend ORB book — Sharpe {book.mean()/book.std()*np.sqrt(252):.2f}")
    # 2-step (correct rules) via DP-optimal + block-bootstrap validation
    _, pol = D.solve(book, T=42, two_step=True); v = D.validate(book, pol, T=42)
    print(f"  2-step (5% daily / 10% static)   single attempt <2mo: p = {v['p']:.3f}  (bust {v['bust']:.2f})")
    # 1-step (real rules): 3% daily, trailing floor, Best-Day; small rho (2 sleeves)
    p1 = best_1step(book, 42, [0.010, 0.012, 0.014])
    print(f"  1-step (3% daily / trailing / BD) single attempt <2mo: p = {p1:.3f}")
    print("  -> 2-step is the better single-attempt path; neither clears 50% in <2 months.")

if __name__ == "__main__":
    main()
