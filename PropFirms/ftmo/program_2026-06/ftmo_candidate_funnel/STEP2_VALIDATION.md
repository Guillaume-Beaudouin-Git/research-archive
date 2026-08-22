# Step 2 — Powered walk-forward validation of the funnel's leads

**Date:** 2026-06-08 · Resolves the three caveats the 17-month OOS couldn't: power (walk-forward + full history), honest FTMO floors (intraday-aware), and the F1-is-beta question. Pre-registered candidates only (the funnel's leads + 4 new improvement variants). Honest cumulative **N = 70** (66 funnel trials + 4 new). Code: `step2_validation.py`; data: `results/step2_validation.{csv,json}`.

## Verdict: the leads are **real but sub-threshold — none is FTMO-viable.** Confirmed NO-GO.

The 17-month OOS (2025-26) **flattered** these strategies; it did not handicap them. With full statistical power the picture inverts.

| candidate | full-hist Sharpe | OOS Sharpe | exk | WF folds (6) | %folds+ | worst fold | DSR full (prim/lenient) | p_funded intraday (1×/2×) | new? |
|---|--:|--:|--:|---|--:|--:|--:|--:|:--:|
| TSMOM_K200_voltgt | **0.70** | 1.68 | 6.8 | [.41,.93,.29,.79,.10,1.87] | **6/6** | +0.10 | 0.000 / 0.093 | 0.46 / 0.46 | ✓ |
| TSMOM_K200_voltgt06 | **0.70** | 1.68 | 6.7 | same | **6/6** | +0.10 | 0.000 / 0.036 | 0.46 / 0.46 | ✓ |
| COMBO tsmom+lowvol | 0.55 | 1.59 | 17.6 | [.10,.97,-.11,1.24,.68,1.61] | 5/6 | −0.11 | 0.000 / 0.024 | 0.49 / 0.47 | ✓ |
| TSMOM_K200 (funnel) | 0.48 | 1.80 | 12.0 | [.11,.77,.24,.49,.04,1.96] | 6/6 | +0.04 | 0.000 / 0.014 | 0.47 / 0.47 | — |
| F1_lowvol_broad | 0.42 | 1.98 | 11.0 | [.27,.60,-.72,.58,.43,1.47] | 5/6 | −0.72 | 0.000 / 0.001 | 0.30 / 0.28 | ✓ |
| TSMOM_K100 | 0.34 | 1.17 | 12.2 | [.01,.19,-.17,1.17,.14,1.56] | 5/6 | −0.17 | 0.000 / 0.002 | 0.43 / 0.42 | — |
| TSMOM_XAU | 0.27 | 1.62 | 7.5 | [.03,.29,-.25,-.02,-.04,1.42] | **3/6** | −0.25 | 0.000 / 0.001 | 0.41 / 0.40 | — |
| F1_lowvol_IDX | 0.54 | 1.08 | 9.5 | [.45,-.69,1.24,1.04,.54,.89] | 5/6 | −0.69 | 0.000 / 0.016 | 0.27 / 0.26 | — |

### 1. Power kills the "near-miss." Full-history Sharpe is 0.27–0.70, not 1.6–1.8.
The OOS Sharpes (1.6–1.8) were a **2025 trend-regime artifact** — look at the last walk-forward fold of every TSMOM row (1.4–2.0) vs the middle folds (0.0–0.8). On the full 12–20-year history the best candidate manages **Sharpe 0.70**. The multiple-testing benchmark at N=70 is **0.84** (consistent full-sample σ_SR=0.35) or **1.74** (stricter OOS σ_SR=0.73). **0.70 < both → DSR ≈ 0 under either deflation.** More data did not rescue a hidden edge; it *revealed* the edge is a mediocre ~0.5–0.7-Sharpe trend premium — real, but far under the bar.

### 2. The vol-target fix worked — and still isn't enough.
The one genuine improvement: per-instrument vol-targeting (`TSMOM_K200_voltgt`) lifted full-history Sharpe 0.48→**0.70**, cut excess kurtosis 12→**6.8**, and held **6/6 walk-forward folds positive** (worst +0.10) at maxDD 17–29%. That is a legitimately *better-behaved* trend basket — borderline **RESEARCH_PASS** (Sharpe ≈0.70, WF 100%). But it **fails PROPFIRM_PASS** (needs Sharpe>1.0, maxDD<10%) and **fails DSR**, and its honest **p_funded ≈ 0.46** sits right on the lumpy-momentum ceiling (L24: 44–54%). It is a research-grade sleeve, not an FTMO challenge entry.

### 3. F1 low-vol-drift is **not alpha — it is sub-beta.** Killed.
Regression of F1 daily returns on US500 (HAC lag-6): **α = +1.4%/yr, t(α) = 0.82** (insignificant), β = 0.30. And F1's own Sharpe (**0.54**) is *below* simply buying-and-holding US500 (**0.73**) over the same window. F1_broad: t(α)=1.03, also insignificant. The "cleanest shape" in the funnel was dampened equity beta that *underperforms the index it dampens.* There is no timing alpha to neutralise — the lead is dead.

### 4. Intraday-aware floors confirm the funnel's p_funded was optimistic.
Feeding the FTMO first-passage the daily **intraday MAE** (from High/Low) instead of close-to-close drops p_funded by ~5pts (TSMOM_K200 0.523 → **0.474**) — the close-only series genuinely under-counted −5%-daily / −10%-static breaches, exactly as flagged. All finalists are **robust to 2× cost** (trend is low-turnover), so cost is not the binding constraint — *distribution shape vs the symmetric barrier* is (L24).

### 5. No decorrelated sleeve set exists.
The TSMOM variants are near-collinear (ρ 0.63–0.94). F1 is decorrelated from TSMOM (ρ 0.15) — but F1 is dead. So the only non-dead content is a **single trend bet**, sub-threshold. Matrix: `results/step2_corr.csv`.

---

## What this means
- **The funnel's "0 certified survivors" is upgraded from "couldn't certify on short OOS" to "verified sub-threshold under full power."** This is a firmer, more useful negative.
- **The single most defensible artifact** is the vol-targeted multi-asset TSMOM basket (`TSMOM_K200_voltgt`): a real ≈0.70-Sharpe, 6/6-fold-positive, 2×-cost-robust trend premium. Park it as a **research-grade diversifier**, not an FTMO challenge candidate — it cannot beat a symmetric ±target/floor barrier (p_funded ≈0.46) and is DSR-insignificant at honest N.
- **Consistent with the registry:** trend/momentum is lumpy and a poor symmetric-barrier fit (L24); long-only low-vol is beta (registry long-only-beta kill); event drift doesn't replicate OOS. Nothing here reopens a closed door.

## Honest next step (if pursued)
The only avenue with any signal left is **not a better strategy but a better container**: the ≈0.70-Sharpe trend basket is FTMO-incompatible *because of the symmetric barrier*, but would be fine in a personal book or a trailing-DD/EOD firm (Apex/Tradeify-style) where the floor isn't symmetric to the target. That is a *container* decision, already covered by the repo's personal-book and Apex notes — **not** a new strategy search on this universe, which is now exhausted at the daily frequency with real costs.
