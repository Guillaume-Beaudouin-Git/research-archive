"""WS-A Gate A: zero-edge baseline per firm (quantifies edge needed) + multi-seed 90% CI for a
modest Sharpe-0.6 grind on the key firms. Committed runner. -> results/gateA.txt"""
import numpy as np
from barrier_engine import best_p, synth_shape
from run_barrier_matrix import FIRMS, firm_dict, T3

if __name__ == "__main__":
    print("ZERO-EDGE baseline p(pass<=3mo) per firm (Sharpe 0, kurt 4) — shows barrier asymmetry:", flush=True)
    for fk, ft in FIRMS.items():
        d = synth_shape(0.0, kurt=4, skew=-0.3, n=1000, seed=21)
        p, L = best_p(d, firm_dict(ft), T3, Ls=(1.5, 2, 2.5, 3, 4), npaths=5000, seed=5)
        print(f"  {fk:26s} zero-edge={p:.3f} @L{L}", flush=True)

    print("\nMODEST GRIND (Sharpe 0.6, kurt 4) — 12-seed 90% CI on key firms:", flush=True)
    for fk in ["FTMO_2step", "The5ers_1step(5%DD)", "Gen_1step_static_loose", "Instant_1step_generous"]:
        firm = firm_dict(FIRMS[fk]); vals = []
        for s in range(12):
            d = synth_shape(0.6, kurt=4, skew=-0.3, n=1000, seed=100 + s)
            vals.append(best_p(d, firm, T3, Ls=(2, 2.5, 3, 3.5, 4), npaths=4000, seed=s)[0])
        lo, md, hi = np.percentile(vals, 5), np.percentile(vals, 50), np.percentile(vals, 95)
        flag = "CLEARS 0.50" if lo > 0.50 else ("straddles" if hi > 0.50 else "below 0.50")
        print(f"  {fk:26s} median={md:.3f} 90%CI=[{lo:.3f}, {hi:.3f}]  -> {flag}", flush=True)
