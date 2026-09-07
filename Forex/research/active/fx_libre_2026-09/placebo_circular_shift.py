"""
Preregistered placebo: circular-shift the deviation_z series by a random large
offset (>10,000 bars) relative to forward_return, same pipeline, 200 draws per
cell -> empirical null distribution of HAC t-stats.

Uses cell_data.pkl produced by run_grid.py (aligned sig/target per cell).
"""
import numpy as np
import pandas as pd
import pickle
import warnings
from fasthac import fast_hac_ols
warnings.filterwarnings("ignore")

with open("cell_data.pkl", "rb") as f:
    cell_data = pickle.load(f)

def hac_ols_t(y, x, lags=6):
    mask = ~(np.isnan(y) | np.isnan(x))
    b, t, se, n = fast_hac_ols(y[mask], x[mask], lags=lags)
    return t

rng = np.random.default_rng(42)
N_DRAWS = 200
MIN_SHIFT = 10000

rows = []
for key, df in cell_data.items():
    tri, freq, lb = key
    sig = df["sig"].values
    target = df["target"].values
    n = len(sig)
    if n < 2 * MIN_SHIFT + 100:
        # scale down min shift proportionally for smaller (60min) samples
        min_shift = max(200, n // 4)
    else:
        min_shift = MIN_SHIFT
    real_t = hac_ols_t(target, sig)
    placebo_ts = []
    for _ in range(N_DRAWS):
        shift = rng.integers(min_shift, n - min_shift) if n > 2 * min_shift else rng.integers(1, n - 1)
        sig_shift = np.roll(sig, shift)
        t = hac_ols_t(target, sig_shift)
        placebo_ts.append(t)
    placebo_ts = np.array(placebo_ts)
    pctile = (np.abs(placebo_ts) < abs(real_t)).mean() * 100
    rows.append(dict(triangle=tri, freq=freq, lookback=lb, real_t=real_t,
                      placebo_mean_t=placebo_ts.mean(), placebo_std_t=placebo_ts.std(),
                      placebo_max_abs_t=np.abs(placebo_ts).max(),
                      pctile_of_real_vs_placebo=pctile))
    print(f"{tri:14s} {freq:6s} lb={lb:3d}  real_t={real_t:+8.3f}  "
          f"placebo mean={placebo_ts.mean():+.3f} std={placebo_ts.std():.3f} "
          f"max|t|={np.abs(placebo_ts).max():.3f}  real is {pctile:.1f}th pct of |placebo|")

out = pd.DataFrame(rows)
out.to_csv("placebo_results.csv", index=False)
print("\nSaved placebo_results.csv")
