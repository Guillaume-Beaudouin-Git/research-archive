"""Merge grille_fx_new.csv + grille_asia_new.csv (if present) into the study's single
grille_resultats.csv, and print the headline distribution numbers for RAPPORT.md."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.stats import norm

HERE = Path(__file__).resolve().parent

fx = pd.read_csv(HERE / "grille_fx_new.csv")
frames = [fx]
asia_path = HERE / "grille_asia_new.csv"
if asia_path.exists():
    asia = pd.read_csv(asia_path)
    frames.append(asia)
else:
    asia = None

out = pd.concat(frames, ignore_index=True, sort=False)
out.to_csv(HERE / "grille_resultats.csv", index=False)

n = len(out)
t = out["gross_t"].dropna()
print(f"TOTAL n_cells this study = {n}")
print(f"mean_t={t.mean():.3f} median_t={t.median():.3f}")
print(f"count t>2.5: {(t>2.5).sum()}  count t<-2.5: {(t<-2.5).sum()}")

rng = np.random.default_rng(0)
draws = np.abs(rng.standard_normal((20000, len(t)))).max(axis=1)
print(f"iid E[max|t|] (n={len(t)}): {draws.mean():.3f}  P95={np.percentile(draws,95):.3f}")

prior_n = 1454
combined_n = prior_n + n
p_sidak = 1 - (1 - 0.05) ** (1 / combined_n)
t_needed = norm.isf(p_sidak / 2)
print(f"Combined honest N (prior {prior_n} + this study {n}) = {combined_n}")
print(f"Sidak two-sided t threshold at combined N: {t_needed:.3f} (p<{p_sidak:.2e})")

if asia is not None:
    print("\nAsia canonical cell rows:")
    print(asia[["sym", "n_trades", "gross_t", "long_t", "short_t", "net_t", "session", "n_days"]]
          .to_string(index=False))
