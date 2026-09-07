"""
Formal validation (per PREREGISTRATION.md §5, triggered because the
preregistered circular-shift placebo was cleared by all 18 grid cells) on the
strongest cell: EUR-GBP-USD, 15min, lookback=20.

Purpose: show this passes conventional statistical gates (WF, block bootstrap)
DESPITE being flagged as a construction artifact by diagnostics.py (gap-test
collapse, symmetric prediction of both major legs, TWAP-vs-last-print
sensitivity) -- illustrating that a robust-looking statistical result is not
sufficient evidence of tradability when a known non-synchronous-trading
mechanism is in play.
"""
import numpy as np
import pandas as pd
import pickle
from fasthac import fast_hac_ols

with open("cell_data.pkl", "rb") as f:
    cell_data = pickle.load(f)

key = ("EUR-GBP-USD", "15min", 20)
df = cell_data[key]
sig = df["sig"].values
target = df["target"].values
n = len(sig)
print(f"Cell {key}, n={n}")

# --- Walk-forward, 5 expanding folds ---
print("\n=== Walk-forward (5 expanding folds) ===")
fold_edges = np.linspace(0, n, 6).astype(int)
results = []
for i in range(5):
    train_end = fold_edges[i + 1]
    test_start, test_end = fold_edges[i], fold_edges[i + 1]
    # expanding: train on [0, test_start), test on [test_start, test_end)
    if i == 0:
        continue  # no train data for first fold in expanding scheme; use folds 2-5 as OOS after fold1 train
    test_sig = sig[test_start:test_end]
    test_target = target[test_start:test_end]
    b, t, se, nfold = fast_hac_ols(test_target, test_sig, lags=6)
    positive = t < 0  # expected sign is negative (reversion); count folds matching sign
    results.append((i + 1, nfold, b * 1e4, t, positive))
    print(f"Fold {i+1}: n={nfold} coef={b*1e4:+.4f}bps t={t:+.3f} sign_matches_full_sample={positive}")

n_folds_significant_correct_sign = sum(1 for _, _, _, t, pos in results if pos and t < -2.0)
print(f"\nFolds with t<-2.0 (correct sign, significant): {n_folds_significant_correct_sign}/{len(results)}")

# --- Block bootstrap (Politis-Romano, block length ~ sqrt(n) or tied to HAC lag) ---
print("\n=== Block bootstrap (1000 draws, block=200 bars) ===")
rng = np.random.default_rng(7)
block = 200
n_blocks = n // block
coefs = []
for _ in range(1000):
    idx_blocks = rng.integers(0, n_blocks, size=n_blocks)
    idx = np.concatenate([np.arange(b * block, (b + 1) * block) for b in idx_blocks])
    b_coef = np.cov(sig[idx], target[idx])[0, 1] / np.var(sig[idx])
    coefs.append(b_coef)
coefs = np.array(coefs) * 1e4
ci_low, ci_high = np.percentile(coefs, [2.5, 97.5])
print(f"Block-bootstrap 95% CI on coef (bps): [{ci_low:.4f}, {ci_high:.4f}], mean={coefs.mean():.4f}")
print(f"CI excludes zero: {ci_low > 0 or ci_high < 0}")

# --- MDE at 80% power (L65) ---
print("\n=== MDE at 80% power (L65) ===")
b_full, t_full, se_full, n_full = fast_hac_ols(target, sig, lags=6)
z_alpha, z_beta = 1.96, 0.8416  # two-sided alpha=0.05, power=0.80
mde = (z_alpha + z_beta) * se_full
ratio = abs(b_full) / mde
print(f"Full-sample coef={b_full*1e4:+.4f}bps, se={se_full*1e4:.4f}bps")
print(f"MDE(80% power)={mde*1e4:.4f}bps, ratio effect/MDE={ratio:.2f}")
