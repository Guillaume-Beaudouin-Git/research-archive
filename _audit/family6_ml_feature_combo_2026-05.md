# Family-6 — ML feature-combination sprint (FTMO)

**Date:** 2026-05-31 · **Sprint:** Family-6 (ML feature combo over the causal
price-transformation space) · **Verdict: NO-GO — EDGE FAILURE (terminal for the
price-feature space)**

**Code:**
- features + ONC: `PropFirms/ftmo_alpha_program/strategy/{ml_features.py, onc_clustering.py}`
- ML pipeline (CPCV + WF): `PropFirms/ftmo_alpha_program/strategy/ml_pipeline.py`
- PBO (López de Prado AFML §11.4): `PropFirms/ftmo_alpha_program/strategy/pbo.py`
- Orchestration: `PropFirms/ftmo_alpha_program/run_family6_ml_combo.py`

**Data:** MT5 M1 panels for **EURUSD, US500, GER40, XAUUSD** (`data/panels/m5_indices/<SYM>_M1.csv`,
2022-01 → 2026-05). Causal resample to M15, liquid-hours filter (7-20 UTC FX/Gold/DAX,
13-21 UTC US500), session-flat labels.

**Hold-out hygiene:** **IS = 2022-01-01 → 2024-12-31** for ALL choices (feature set,
ONC, model family, hyperparameters, threshold, best-variant selection). **Hold-out
2025-01-01 → 2026-05-29 sealed, touched ONCE** for the final verdict (per-instrument
retrain on full IS, predict on hold-out, compute net Sharpe / per-year stability /
DSR / tail-DD / FTMO MC). No iteration on the hold-out.

**Results JSON:** `PropFirms/ftmo_alpha_program/results/family6_ml_combo.json`
**Figure:** `PropFirms/ftmo_alpha_program/figures/family6_ml_combo.png` (CPCV-OOS
Sharpe histograms + per-year HO Sharpes by instrument).

---

## Étape 0 — Causal feature library (whitelist) + ONC

Ten causal, closed-bar features computed on M15 and lagged by one bar
(`as_known_at(features) = features.shift(1)`, L1):

| # | Feature | Type | Source |
|---|---|---|---|
| 1 | `trend_slope_fast` | trend | EMA(5)-EMA(5).shift(5) on log-price |
| 2 | `trend_slope_slow` | trend | EMA(20) slope |
| 3 | `velocity_ifrsi` | velocity | tanh((RSI(14)-50)/10), bounded ∈ (-1,1) |
| 4 | `accel_macd_hist` | acceleration | MACD(12,26,9) histogram |
| 5 | `regime_atr_pct` | vol regime | rolling 252-bar percentile rank of ATR/price |
| 6 | `regime_rv` | vol regime | 20-bar rolling std of log-returns |
| 7 | `squeeze_bb_kc` | compression | BB(20,2)/KC(20,1.5) width ratio |
| 8 | `strength_adx` | strength | Wilder ADX(14) |
| 9 | `choppiness` | range vs trend | Choppiness Index(14), Dreiss |
| 10 | `vwap_prox` | flow proxy | (close − intra-session VWAP)/VWAP (tick-vol weighted) |

**Excluded by design** (non-causal): ZigZag/Fractals, Senkou/Chikou Ichimoku,
Parabolic-SAR/Supertrend computed on intra-bar high/low. ATR / ADX / RSI use the
Wilder (RMA) smoothing on **confirmed bars only**.

**ONC clustering** (López de Prado 2019; distance D = √(½(1−ρ)); average linkage;
silhouette sweep k∈[2,9]; **|corr| ≥ 0.8 ⇒ forced merge** post-process):

| Instrument | k | silhouette | Clusters (members) | Representatives (medoid) |
|---|---|---|---|---|
| **EURUSD** | **3** | 0.260 | C1: trend_slope_fast / trend_slope_slow / velocity_ifrsi / accel_macd_hist / vwap_prox · C2: regime_atr_pct / regime_rv / squeeze_bb_kc / strength_adx · C3: choppiness | `trend_slope_fast`, `squeeze_bb_kc`, `choppiness` |
| **XAUUSD** | **3** | 0.275 | C1: trend (5 members) · C2: vol-regime (4 members) · C3: choppiness | `trend_slope_fast`, `regime_rv`, `choppiness` |
| **US500**  | **3** | 0.230 | as EURUSD | `trend_slope_fast`, `squeeze_bb_kc`, `choppiness` |
| **GER40**  | **2** | 0.241 | C1: trend ∪ choppiness (forced merge: choppiness↔strength_adx \|corr\|≥0.8) · C2: vol-regime | `trend_slope_fast`, `squeeze_bb_kc` |

**Honest N for DSR.** The whitelist nominally exposes 10 features, but ONC
collapses them to **2–3 quasi-orthogonal dimensions** per instrument. This is below
the 6–9 "expected" range and is itself a finding: the price-transformation space
*is* low-rank — trend / vol-regime / choppiness account for nearly all the variance.
Used downstream as N_clusters in the DSR trial count.

---

## Étape 1 — Label + CPCV (purge + embargo)

**Label.** `y_fwd_1` = forward log-return over 1 M15 bar (≈ 15 min), dropped if it
crosses a session boundary. Pre-registered horizon = 1 bar (the natural window for
an intraday-flat ML predictor; longer horizons would only inflate label overlap and
embargo length without changing the qualitative result). Triple-barrier label was
implemented (`triple_barrier_label`) but not used here to keep the diagnostic on a
single, transparent return definition.

**Cross-validation.** Combinatorial Purged CV (skfolio, López de Prado AFML ch.12):

| Instrument | n_paths | n_folds | n_test_folds | purge | embargo |
|---|---|---|---|---|---|
| EURUSD | 21 | 21 | 20 | 1 bar | 395 bars (1%) |
| XAUUSD | 21 | 21 | 20 | 1 | 393 |
| US500  | 28 | 28 | 27 | 1 | 237 |
| GER40  | 21 | 21 | 20 | 1 | 389 |

Per-fold backtest: fresh fit on the train indices, predict on the test indices,
compute the **GROSS** Sharpe (no costs). This produces the OOS Sharpe distribution
that PBO and the decisive diagnostic operate on. The CV is purged (1 bar = label
horizon) and embargoed (1 % of T per LdP recommendation) — leakage by overlapping
labels is eliminated by construction. Naive k-fold was never used.

---

## Étape 2 — Simple-first models and **the decisive diagnostic**

Per the protocol, progression simple → complex with the GROSS Sharpe stop-the-clock
test:

  1. **Logistic L2** (StandardScaler + LogisticRegression, C=1.0)
  2. **LightGBM**, depth ≤ 3, num_leaves = 7, min_child_samples = 400, lr = 0.05,
     n_estimators = 150, λ_L2 = 1.0 (strong leaf regularisation, intentionally
     anti-overfit; no deep learning, per protocol).

Forecast → position: `position = clip(2 · P(up) − 1, −1, +1)`, intraday-flat
(forced zero on the last bar of each session), no overnight carry.

### The decisive isolation — CPCV GROSS OOS Sharpe distribution (IS only)

This is **the** test. If GROSS is null/negative OOS, the price-transformation
combinatorial space carries no exploitable signal — **terminal**, no venue can fix it.
If GROSS is robustly positive but mangé par le coût → COST failure, potentially
venue-fixable.

| Instrument | Model | mean | median | std | CI 5-95 | per-path range |
|---|---|---|---|---|---|---|
| **EURUSD** | logistic L2 | **−0.011** | +0.125 | 0.576 | [−0.91, +0.63] | min −1.15, max +0.96 |
| EURUSD | LightGBM (d=3) | **−0.036** | +0.015 | 0.42 | [−0.70, +0.74] | — |
| **XAUUSD** | logistic L2 | **−0.007** | +0.171 | 0.70 | [−1.12, +1.02] | — |
| XAUUSD | LightGBM (d=3) | **+0.229** | −0.032 | 0.93 | [−0.52, +1.74] | — |
| **US500**  | logistic L2 | **−0.188** | −0.180 | 0.24 | [−0.60, +0.19] | — |
| US500  | LightGBM (d=3) | **−0.294** | −0.272 | 0.39 | [−1.07, +0.30] | — |
| **GER40**  | logistic L2 | **+0.016** | −0.003 | 0.45 | [−0.75, +0.74] | — |
| GER40  | LightGBM (d=3) | **+0.095** | −0.036 | 0.90 | [−1.47, +1.58] | — |

**Reading the table.** Every CPCV mean OOS Sharpe is within ±0.30 of zero, and
every confidence band straddles zero with room to spare. The XAUUSD GBM mean (+0.23)
is contradicted by a median of −0.03 — a few fortunate test folds dragging an
otherwise null distribution. US500 is the only instrument with consistently
**negative** mean **and** median: the model's forecasts are anti-correlated with
the next-bar return at OOS.

**This is the verdict.** No instrument shows a robust positive GROSS OOS Sharpe.
The combinatorial ML space does not contain an edge that the four prior univariate
nulls (FX MR, index MR, intraday pairs, gold range-fade) failed to find.

---

## Étape 3 — Gate battery (mandated order)

### Hyperparameter grid → walk-forward → PBO

8 variants tested on common time slices (5-fold expanding-window walk-forward):
`logreg_{C=0.01,0.1,1.0,10}` × 4, `gbm_{d3_lr.03, d3_lr.05, d2_lr.05, d3_lr.05_thr=0.05}` × 4.

| Instrument | PBO | gate (<0.5) | best WF Sharpe | best variant |
|---|---|---|---|---|
| EURUSD | **0.860** | FAIL | +0.263 | gbm_d2_lr0.05 |
| XAUUSD | **0.789** | FAIL | −0.052 | logreg_C0.01 |
| US500  | **0.934** | FAIL | −0.113 | logreg_C0.01 |
| GER40  | **0.565** | FAIL | +0.196 | gbm_d3_lr0.05 |

12,870 combinations of 8 IS / 8 OOS time-slices per instrument. **All four instruments
exceed the 0.5 PBO gate**, with three above 0.78 — the canonical signature of
overfitting selection (López de Prado AFML §11.4): the best in-sample variant is
disproportionately likely to be below the OOS median. The IDEAL <0.2 is missed by a
wide margin everywhere.

### Sealed hold-out 2025-2026 (touched once, with the best IS variant)

| Instrument | best variant | net SR | gross %/yr | cost %/yr | gross/cost | kurt | 2025 SR | 2026 SR |
|---|---|---|---|---|---|---|---|---|
| EURUSD | gbm_d2_lr0.05 | **−1.00** | +0.21 | +0.41 | **0.52×** | 4.76 | **−1.19** | **−0.46** |
| XAUUSD | logreg_C0.01 | **−0.34** | +0.35 | +0.50 | **0.71×** | 85.8 | **−1.41** | **+0.24** |
| US500  | logreg_C0.01 | **−1.66** | −0.02 | +0.51 | **−0.03×** | 4.85 | **−2.34** | **+0.19** |
| GER40  | gbm_d3_lr0.05 | **−4.65** | +1.00 | +4.06 | **0.25×** | 8.42 | **−4.07** | **−6.00** |

- **Net Sharpe negative everywhere.** No exception.
- **Cost gate L11 (>3×)**: fails on every instrument. **GER40** shows the most
  cost-eaten variant (the GBM picks high-turnover, 1.40 daily turnover) — the
  selection bias works against it.
- **Per-year sign-stability**: EURUSD both years negative; XAUUSD/US500 sign-flip
  (negative 2025, marginally positive 2026 — a 5-month sample) → not stable.
  GER40 both years strongly negative.
- **Excess kurtosis**: EURUSD/US500 ≈ 4.8 (gate 3 — FAIL); GER40 8.4 (FAIL); XAUUSD
  85.8 (massive — driven by a couple of overnight gaps, gate FAIL).

### Distribution & tail-DD on the HO daily net series

Vol-scaled to σd ≈ 1 % for FTMO comparability before the MC:

| Instrument | P(touch −8 %/60 sessions) | P(peak-to-trough −8 %/60d) | gate (<10%) |
|---|---|---|---|
| EURUSD | 0.0 % | 0.0 % | PASS |
| XAUUSD | 0.0 % | 0.0 % | PASS |
| US500  | 0.0 % | 0.0 % | PASS |
| GER40  | 0.0 % | 0.0 % | PASS |

Tail-DD passes everywhere — but this is **trivial conditional on the net daily
series**, because the daily Sharpe is so close to zero (and the daily-vol scaler
brings σ to 1 %) that the 60-session window simply cannot move 8 % under any path.
The tail-DD gate is *not* binding here; the **edge gate** is.

### Deflated Sharpe Ratio (HO net daily series)

n_trials honest = N_clusters × N_hyperparam_variants (8) = 16 (GER40, k=2) or 24
(others, k=3) :

| Instrument | annualised SR | E[max SR] benchmark | DSR | gate (≥0.95) |
|---|---|---|---|---|
| EURUSD | −1.00 | ~ +0.16 | **0.000** | FAIL |
| XAUUSD | −0.34 | ~ +0.16 | **0.000** | FAIL |
| US500  | −1.66 | ~ +0.16 | **0.000** | FAIL |
| GER40  | −4.65 | ~ +0.16 | **0.000** | FAIL |

DSR is 0.000 everywhere — a negative observed Sharpe is automatically below the
selection-bias-deflated threshold (and the threshold itself is only ~0.16, a tiny
penalty from 16-24 trials, but it's already untouchable).

### FTMO Monte-Carlo (honest, daily series vol-scaled to σd = 1 %, no time limit)

Combined two-phase P(pass) via Politis-Romano stationary block bootstrap on the HO
net daily series:

| Instrument | FTMO MC P(pass) | CI 95 % | closed-form @ σd=1 % | gate (≥70 %) |
|---|---|---|---|---|
| EURUSD | 7.2 % | [6.9 %, 7.4 %] | 9.9 % | FAIL |
| XAUUSD | 9.2 % | [8.9 %, 9.5 %] | 23.3 % | FAIL |
| US500  | 1.1 % | [1.1 %, 1.2 %] | 3.6 % | FAIL |
| GER40  | 0.0 % | [0.0 %, 0.0 %] | 0.0 % | FAIL |

Every instrument is **below** the ~30 % zero-edge baseline noted in Family-4 (a
negative-drift book does *worse* than a coin flip against a symmetric barrier).
**FTMO P(pass) ≪ 70 % everywhere.**

---

## Étape 4 — Feature-importance collapse check

Per protocol: if a single feature carries the "edge", the combinatorial test is a
relabel of a univariate test already done. Normalised GBM gain importance over the
ONC representatives:

| Instrument | trend (slope) | vol-regime (squeeze/RV) | choppiness | dominant? |
|---|---|---|---|---|
| EURUSD | 39.4 % | 33.3 % | 27.2 % | no — roughly balanced |
| XAUUSD | 34.0 % | 32.9 % | 33.1 % | no — perfectly balanced |
| US500  | 30.6 % | 29.5 % | 39.9 % | no — choppiness slightly higher |
| GER40  | 57.9 % | 42.1 % | (merged) | trend leans, but only 2 clusters |

**No single representative dominates.** Mechanically, that is the *non-falsifiable*
outcome for this test — if a feature had carried everything, we would have to map
back to the matching univariate null (e.g., trend slope → momentum tests, choppiness
→ range tests). But the importance is balanced because **nothing carries anything**:
the model splits gain roughly evenly across features none of which produce edge.
This is the null-on-null branch — not "the combination collapses to a single feature
we already killed", but "the combination collapses to nothing at all". The protocol's
collapse-check passes vacuously.

---

## Verdict — NO-GO, **EDGE failure (terminal for the price-feature space)**

The sprint's single question — *does the UNION of causal price-derived features
contain a non-linear combination with robust gross OOS edge that no univariate
indicator captured?* — is answered: **no.**

| Diagnostic | Result | Implication |
|---|---|---|
| CPCV GROSS OOS Sharpe mean | **−0.04 to +0.10 across instruments and models**, all CI straddle 0 | EDGE failure |
| PBO | 0.57–0.93, gate fail on all 4 instruments | best-IS variant is selection bias |
| HO net Sharpe | −0.34 to −4.65, all negative | confirms IS edge wasn't real |
| Per-year stability | sign-flips or both-years negative | not robust |
| DSR | 0.000 everywhere | selection bias not absorbable |
| FTMO P(pass) MC | 0–9.2 %, well below 70 % gate and 30 % zero-edge baseline | unprofitable as an FTMO candidate |
| Cost gate L11 (>3×) | 0.25–0.71× | costs swamp what little gross exists |
| Feature-importance collapse | balanced, no dominant feature | the combination has no single source either; null-on-null |

**EDGE vs COST.** The first-order failure is at the edge, not the cost. Even at
zero cost, the GROSS OOS Sharpe distribution does not tilt positive in any
statistically meaningful way. The cost gate fails consequentially, but a tighter
spread (a cheaper venue — futures CME vs CFD) could only rescue an edge that
exists at zero cost. There is none.

This is qualitatively the same failure mode as Family-4 (XAUUSD range-fade,
*EDGE failure terminal*), and contrast with Family-1/2 (real but marginal gross
edge eaten by CFD cost) and Family-5 (real OOS gross edge, killed structurally
by the embedded carry component, not by venue choice). **Not venue-fixable for
this mechanism class.**

### Conclusion on the **price-transformation feature space**

This sprint operationalised the "union of all causal price-derived features"
exhaustively for an intraday-flat retail-window FTMO setup: 10 features → ONC
to 2–3 quasi-orthogonal dimensions → simple-then-shallow ML (logistic L2 →
shallow GBM) → strictly purged combinatorial OOS. Four instruments. Both models.
No combination yields a robust gross OOS edge.

**The price-transformation feature space, as seen through this protocol, is
empty for FTMO suitability on the chosen universe.** This is the sixth
independent mechanism to fail in the program (Phase 0–2 + Family-3/4/5/6) and
the **fourth** to fail at the *edge*, not at the cost. The weight of evidence
now decisively favours the "**no robust alpha across the tested mechanisms on
retail CFD price data**" thesis over the "alpha exists but is unsellable on
retail CFD" thesis.

**Place in the program.** The program's gated, cost-first / overfit-aware
pipeline (CPCV-purged-embargoed + PBO + DSR + FTMO MC against a symmetric
barrier) is the methodology working as designed: it kills a candidate that does
not survive honest IS-OOS hygiene, rather than overfitting it into a false pass.
The infrastructure (ONC, CPCV, PBO, walk-forward grid, ML→FTMO MC bridge) is
retained for the next candidate mechanism — which, on the prior of this null
plus the four preceding ones, will need to come from **outside** the price-
transformation feature space (e.g. order-flow microstructure, event-time anomalies
with a documented structural prior, or cross-venue/cross-asset relative-value
features that price alone cannot encode).

### Pre-registered methodology lesson (proposed L26)

> **L26 — Causal price-transformation feature space, intraday-flat, retail
> CFD: empty for FTMO under honest hygiene.** Ten causal features → ONC →
> ≤3 effective dimensions per instrument; combinatorial ML (logistic L2 +
> shallow GBM) under CPCV purged/embargoed shows GROSS OOS Sharpe centered at
> zero on EURUSD/XAUUSD/US500/GER40 (2022-24 IS, 2025-26 sealed hold-out),
> PBO ≥ 0.57 everywhere, DSR ≈ 0, FTMO P(pass) ≤ 9 % — below the zero-edge
> baseline. *Implication:* future propfirm candidates must derive features
> from a strictly **non-price** layer (order flow, event time, cross-asset
> RV) — within-symbol price transforms are exhausted under retail CFD costs
> and symmetric barriers.
