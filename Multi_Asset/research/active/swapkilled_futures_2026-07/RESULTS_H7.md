# RESULTS H7 — Martingale & Grid (sizing overlays) — CLASSIFIED ARTEFACT

**Verdict: NOT deployable.** MC P(ruin over 3yr) = 36–81% (gate threshold 20%), E[g] ≤ 0 on a no-edge
process. Metric per prereg = ruin probability + E[g], NOT Sharpe (which is the artifact).

## Martingale — MC (risk-based doubling, ruin = −50% DD)

**Fair bet (p=50%, 1:1, isolates pure sizing effect):**

| Variant | P(ruin 1yr) | P(ruin 3yr) | Mean final € |
|---|---|---|---|
| Unbounded | 59.6% | **80.8%** | 11,989 |
| Cap 5 | 40.6% | 61.8% | 12,100 |
| Cap 3 | 12.0% | 35.8% | 12,005 |
| Flat | 0.1% | 6.8% | 11,994 |

Mean final ≈ €12,000 for ALL variants → **martingale creates zero edge**; it only trades P(small win)
for P(catastrophe). More doublings / bigger base = more ruin, same E.

**Real small edge (p=53%, 1:1), 3yr:**

| Variant | P(ruin) | Mean € | Median € |
|---|---|---|---|
| Flat | 0.1% | 17,452 | 17,520 |
| Cap 3 | 6.1% | 20,809 | 21,120 |
| Unbounded | 64.5% | 21,539 | **4,800** |

Flat sizing already captures the edge. Unbounded martingale's higher MEAN is inflated by rare lucky
survivors; the MEDIAN path is −60%. **The edge lives in the signal, not the overlay.**

## Grid

Backtest did not trigger: gold left its 2005 anchor range (×10 up) → rungs never fill. **This IS the
grid's failure mode** — it assumes a range; when price trends away it either stops trading or accumulates
a catastrophic one-sided inventory. Grid = spatial cousin of the temporal martingale: short-gamma,
negative skew, ruin tail. Verdict by short-gamma equivalence + theory (clean backtest not completed —
stated honestly as a limitation).

## Conclusion

Martingale and grid are **sizing overlays that create no expected value** and convert a smooth in-sample
curve into an ~80% ruin tail. Classified ARTEFACT — the exact profile PERSONAL_PASS exists to reject.

**Constructive:** martingale is *anti-Kelly* — it sizes UP after losses (chasing), whereas Kelly sizes to
edge/variance and is provably growth-optimal. For aggressive growth on this account the answer is a
**higher fractional-Kelly on a real edge (H3/H4)**, never a martingale/grid. Aggression = raise the Kelly
fraction, not the after-loss bet.
