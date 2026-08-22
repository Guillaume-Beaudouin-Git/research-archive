# FTMO 10k 2-step — Candidate Funnel: SHORTLIST (survivors)

**Date:** 2026-06-08 · **Gate:** Deflated Sharpe (Bailey–López de Prado) **> 0.5 on untouched OOS (2025-01-01 → 2026-06-05)**, deflated at the **true trial count N = 66**.
**Universe:** FTMO-executable only — 10 FX majors/crosses, XAUUSD, US500/US100/US30/GER40, BTCUSD (no perps/options).
**Costs:** real per-bar feed spread × 3.0 retail markup + FTMO commission (FX ≈0.9 bps, idx ≈1.0 bps, XAU ≈1.3 bps, BTC ≈8.5 bps incl. 0.065% RT) + slippage; charged on turnover. Causal (signal ≤ T-1, trade T).

---

> **Follow-up (Step 2, `STEP2_VALIDATION.md`):** the leads below were re-tested with full power (walk-forward + full-history DSR + intraday-aware floors). Result is *firmer*: the near-miss TSMOM-K200's strong OOS was a 2025 trend-regime artifact — its full-history Sharpe is **0.70**, below the N-deflated bar; F1 low-vol-drift is **sub-beta** (HAC t(α)=0.82, Sharpe 0.54 < buy-hold 0.73). **Verified sub-threshold, not merely uncertified.**

## ⛔ Headline: **0 candidates are DSR-certified. The honest shortlist is EMPTY.**

Under the binding gate — DSR > 0.5 on the untouched 2025-26 OOS, deflated at the real N = 66 — **no candidate clears the bar.** Per the brief ("if fewer than 5 clear DSR>0.5, OUTPUT FEWER — do not pad"), the certified shortlist has **zero** entries.

This is robust to the one free modelling choice in DSR (the trial-Sharpe dispersion `std_sr_trials`):

| Deflation of the E[max] benchmark | σ_SR used | OOS Sharpe bar | # clearing DSR>0.5 |
|---|---|--:|--:|
| **Repo `dsr.py` default (ultra-conservative)** | 1.00 | **2.38** | **0** |
| **PRIMARY — data-driven, OOS-consistent** | 0.729 | **1.74** | **0** |
| Lenient — full-sample dispersion (optimistic) | 0.350 | 0.83 | 5 (conditional only) |

Two of three defensible deflations give **0**; only the *most lenient* (using long-sample Sharpe dispersion to deflate a short-sample OOS result — an inconsistent mixing of samples) yields any names. **The empty certified shortlist is the answer.**

**Why nothing clears:** the cross-sectional dispersion of the 66 trials' OOS Sharpes is **σ_SR = 0.73**, which is *below* the pure-sampling-noise standard error of a 370-day annualised Sharpe (≈ √(252/370) ≈ 0.83). In plain terms: the spread of OOS results across 66 strategies is statistically indistinguishable from 66 coin-flips. The best OOS Sharpe observed (1.80) is exactly what the luckiest of 66 noise draws would produce. A 17-month OOS simply cannot certify skill against a 66-wide search.

**The verdict is airtight precisely because N is honest.** At N=66 the best candidate (TSMOM-K200) scores DSR 0.45. It would only cross 0.5 if N were *understated* to ≈40 — which the brief explicitly forbids ("if N is understated the >0.5 bar is fake"). Counting every per-pair leg and every K/threshold sub-parameter actually run — the honest, larger N — is what (correctly) keeps the near-miss out. N=66 is itself a floor (implicit param choices add un-counted DoF), so the true bar is *at least* this high.

---

## ◐ CONDITIONAL watchlist (clears only the lenient deflation — NOT certified, advance to fuller validation only)

These 5 clear DSR>0.5 **only** under the optimistic full-sample-σ deflation (bar 0.83). They are reported because the brief asks for the decorrelation artifact and because they are the least-implausible leads — **but each carries a disqualifying honesty flag.** None should be taken to a paid challenge on this evidence.

| Rank | id | Mechanism | Sharpe IS | Sharpe OOS | exkurt (full / OOS) | yrs+ | p_funded@1% | DSR primary / lenient | Honest flag |
|---|---|---|--:|--:|--:|--:|--:|--:|---|
| 1 | `B1.tsmom.k200` | TSMOM basket (US500/US100/GER40/XAU/BTC), K=200, vol-tgt, 2-sided | **0.40** | 1.80 | 12.0 / 1.8 | 14/20 | **0.52** | 0.45 / 0.83 | **lumpy momentum** (L24); OOS inflated by a strong 2024-25 trend regime; lost 2021 (−2%) & **2022 (−17%)** |
| 2 | `B2.tsmom100.XAUUSD` | Gold TSMOM, K=100, 2-sided | 0.12 | 1.62 | 7.5 / 5.9 | 13/20 | 0.44 | 0.41 / 0.79 | single-asset concentration; OOS = gold's +50%/yr 2025; IS Sharpe ≈ 0 |
| 3 | `A1.zfade10.AUDUSD` | Daily z-score(10) mean-reversion, AUDUSD | **−0.13** | 1.47 | 39.0 / 40.0 | 11/20 | 0.23 | 0.21 / 0.68 | **negative IS** = pure OOS luck; **exkurt 40** (not FTMO-suited); p_funded 0.23 |
| 4 | `A1.zfade10.USDJPY` | Daily z-score(10) mean-reversion, USDJPY | −0.08 | 1.43 | 28.5 / 9.1 | 13/20 | 0.22 | 0.21 / 0.62 | **negative IS** = OOS luck; p_funded 0.22 |
| 5 | `B1.tsmom.k100` | TSMOM basket, K=100 | 0.29 | 1.17 | 12.2 / 1.2 | 14/20 | 0.47 | 0.18 / 0.57 | duplicate of #1 (ρ=0.64); lumpy |

Artifacts: `results/all_trials.csv` (full 66), `results/all_trials.json` (incl. per-year), `results/summary.json`.

### Mutual-correlation matrix — conditional watchlist (full-sample daily net returns, business days)
```
                    k200   XAU   AUDz   JPYz   k100
B1.tsmom.k200       1.00   0.48   0.04  -0.01   0.64
B2.tsmom.XAU        0.48   1.00  -0.01  -0.02   0.71
A1.zfade.AUDUSD     0.04  -0.01   1.00   0.25  -0.01
A1.zfade.USDJPY    -0.01  -0.02   0.25   1.00  -0.02
B1.tsmom.k100       0.64   0.71  -0.01  -0.02   1.00
```
### Tail / stress correlation (worst-decile days of the equal-weight book)
```
                    k200   XAU   AUDz   JPYz   k100
B1.tsmom.k200       1.00   0.39  -0.08  -0.16   0.65
B2.tsmom.XAU        0.39   1.00  -0.08  -0.19   0.56
A1.zfade.AUDUSD    -0.08  -0.08   1.00   0.30  -0.04
A1.zfade.USDJPY    -0.16  -0.19   0.30   1.00  -0.14
B1.tsmom.k100       0.65   0.56  -0.04  -0.14   1.00
```
**Decorrelation structure:** there are really only **two** independent bets here — a **trend cluster** (k200 ≈ XAU ≈ k100, ρ 0.48–0.71, tail ρ 0.39–0.65) and a **FX-MR cluster** (AUDz ≈ JPYz, ρ 0.25). Trend and FX-MR are mutually ~0 (and slightly *negative* in the tail — a genuine diversification sign). Greedy max-decorrelation pick of ≤5: `[k200, AUDUSD-z, USDJPY-z, XAU, k100]` — but k100 is redundant with k200, so the real decorrelated content is **3 sleeves at most: {trend basket, AUDUSD-MR, USDJPY-MR}**, and the two MR legs are OOS-luck. p_funded sizing sweep for these is in `results/chosen_pfunded_sweep.json`.

---

## The single defensible lead for fuller validation (NOT a recommendation to trade)

If forced to carry one hypothesis forward, it is the **multi-asset TSMOM-K200 basket** (`B1.tsmom.k200`): it is the only watchlist member with a positive IS Sharpe (0.40), a low *OOS* kurtosis (1.8), 14/20 positive years, p_funded ≈ 0.52 at 1% daily-vol sizing, and a −10%-floor-friendly two-sided design (it shorts down-trends). **But** its full-sample kurtosis is 12, it lost ~17% in 2022, its OOS strength is a 2024-25 trend-regime artifact (IS Sharpe only 0.40), and it is exactly the "lumpy momentum / poor symmetric-barrier fit" the repo flagged in L24. It is a near-miss (DSR 0.45), not an edge.

**Honourable mention (did not even make the conditional list):** `F1.lowvolLong_IDX` — long indices only when trailing vol is below its 1-yr median — has the most *FTMO-shaped* return profile of anything tested: IS 0.49 / OOS 1.08 (consistent), maxDD 18%, **every year 2020-2026 positive incl. 2022**, ann-vol 7.7%. It fails DSR (0.13 primary / 0.48 lenient) and is **beta-tinged** (it is long equities in calm regimes), so it inherits the long-only-beta problem the registry already kills — but it is the cleanest *shape* and the best low-kurtosis lead for a redesigned, beta-neutralised version.

**Bottom line:** This triage returns **no validated FTMO sleeve.** The honest deliverable is an empty certified shortlist plus a transparent near-miss list — which is the correct, conservative outcome for a search this wide on a 17-month hold-out. See `LIMITATIONS.md` for why, and `LONGLIST.md` for the full kill table.
