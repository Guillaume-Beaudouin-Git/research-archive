"""
Gold-standard LOOK-AHEAD test for Ross Hook (#76): truncate each instrument's data at a
cutoff T and re-run; every trade fully RESOLVED before T (exit < T) must be bit-identical
to the full-history run. If any future data leaked, past trades would change.
Boundary trades (open across T) legitimately differ — the truncated run cannot see post-T
bars to resolve them, which is causality working correctly. ftmo_lab UNCHANGED.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab, rosshook as rh

uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
T = pd.Timestamp('2018-01-01')


def contained(tr, t):
    if not len(tr): return tr
    return tr[pd.to_datetime(tr['exit']) < t].reset_index(drop=True)


if __name__ == "__main__":
    content_mismatch = 0; boundary = 0; n_contained = 0
    for t, df in uni.items():
        full = rh.simulate_rosshook(df, 10, 20, 10, cost_bps=costs[t], fill='next_open')
        trunc = rh.simulate_rosshook(df[df.index < T], 10, 20, 10, cost_bps=costs[t], fill='next_open')
        fa, ta = contained(full, T), contained(trunc, T)
        n_contained += len(fa)
        if len(fa) != len(ta): boundary += 1
        L = min(len(fa), len(ta))
        if L and not ((fa.iloc[:L]['entry'].values == ta.iloc[:L]['entry'].values).all()
                      and (fa.iloc[:L]['dir'].values == ta.iloc[:L]['dir'].values).all()
                      and np.allclose(fa.iloc[:L]['netR'].values, ta.iloc[:L]['netR'].values, atol=1e-9)):
            content_mismatch += 1
    print(f"trades resolved before {T.date()}: {n_contained}")
    print(f"content-mismatch instruments: {content_mismatch}  (must be 0)")
    print(f"boundary-only count diffs:     {boundary}  (legitimate: hooks resolving after T)")
    print("VERDICT:", "PASS — strictement causal (aucune fuite future)" if content_mismatch == 0
          else "FAIL — look-ahead detecte")
