# Edge-improvement PRE-REGISTRATION (frozen BEFORE any backtest)

**Written 2026-06-08, before running a single improvement.** Goal: take the two *real-but-sub-threshold* edges — **Ross Hook (RH, deployable Sharpe 0.44)** and **multi-asset TSMOM (swap-net ~0.05–0.32)** — and test a SMALL, FIXED set of principled, near-zero-free-parameter improvements. The overfitting guard is the point: every variant below adds to the **cumulative honest N (=97 from the two funnel iterations)**; DSR is deflated at N = 97 + (variants run here). No iterating-until-pass, no threshold grids, no per-instrument tuning.

## What the baseline ALREADY does (so I do not re-claim it as new)
The survivors book (`research/ftmo_survivors_book/`) already applies, at zero tuning: per-instrument vol-targeting + portfolio vol-targeting inside TSMOM (`tsmom_regen.strat`), an equity-curve regime gate + vol-derisk overlay, per-sleeve vol-targeting to 1%/day, equal-weight **and** risk-parity combination, leverage fixed ex-ante on IS, real per-leg swap, and DSR at honest N. Its swap sweep already proved the ceiling: **12mo OOS p(pass) ≤ 0.458 even at swap=0/crypto=0; CI-lower never clears 0.50** (`swap_sensitivity/swap_sensitivity.json`).

## The FIXED improvement set (6 variants — each principled, zero forbidden transforms)

| id | improvement | theoretical rationale | free params (all fixed ex-ante) |
|---|---|---|---|
| **B0** | survivors baseline (RH + ETF-proxy TSMOM-swapnet-nocrypto, equal-wt, vt 1%/day, L*-on-IS) | reference point (already counted in prior N; **not** a new trial) | — |
| **I1** | **FTMO-CFD-native TSMOM**: rebuild the TSMOM basket on **FTMO-executable CFDs** (US500/US100/GER40/XAUUSD/BTC, true-UTC) instead of the non-FTMO ETF proxies (GLD/SLV/USO), same 3-lookback+theta+per-inst-vol-target construction, **real CFD swap** (measured non-crypto proxy −3.08/+0.13 bps-night; BTC swept) | (a) **correctness** — GLD/SLV/USO are US ETFs, *not* FTMO-tradable; (b) the ETF basket carries the worst swap legs (USO −22.42 short / SLV −6.88 long) that a two-sided trend book repeatedly pays. Index/metal CFDs financing ≈ the measured −3.08 proxy → **structurally lower swap drag**. | basket = fixed FTMO set; signal = survivors' (60,120,250),θ=0.34; swap = measured proxy |
| **I2** | **RH-alone, optimally vol-targeted** (single best edge, no dilution) | honest check on the √N premise: combining only helps if the 2nd edge is strong enough; if post-swap TSMOM is too weak, **RH-alone may dominate** the diluted book. Must be ruled out, not assumed. | vt 1%/day, 63d, cap 4 (baseline's) |
| **I3** | **ERC (risk-parity) combination** of {RH, I1-TSMOM} vs equal-weight | equal-weight over-weights the higher-vol / higher-correlation sleeve; ERC using realized vol+corr is the theory-correct decorrelated weight given ρ≈+0.20 | 63d cov lookback (fixed) |
| **I4** | **book-level constant-vol targeting** (target the COMBINED book to constant 1%/day *before* leverage) | the baseline vol-targets each *sleeve* then combines, but applies leverage to a vol-*drifting* combined series; a constant-vol book stabilises the barrier-distance → first-passage is path-stabilised (the −5% daily / −10% static floors punish vol spikes) | 63d, cap 4 (fixed) |
| **I5** | **IMPROVED COMBINED BOOK** = RH + I1-TSMOM, ERC (I3) + constant-vol book (I4), L fixed on IS | the synthesis: stack the principled levers (correct instruments + ERC + constant-vol) — the best *honest* engineering of the 2-edge book | inherits I1/I3/I4 |
| **I6** | **BEST-CASE CEILING** = I5 but TSMOM crypto-swap = 0 (most optimistic real-cost) | upper bound: if even the most-favorable real-cost assumption can't clear 0.50, the conclusion is swap-robust and engineering-robust | inherits I5 |

**Variants run here = 6 (I1–I6).** → **cumulative N = 97 + 6 = 103** (primary DSR deflation). I will also report DSR at **N=500** (the survivors' own honest count: RH from a 109-strategy library, TSMOM from a multi-asset program, plus this exercise) — N=103 is a *floor*, not the true count.

## FORBIDDEN (pre-committed to NOT do)
Per-trade stops fit on data; daily winsorize/tail-cap; any parameter chosen because it improves the backtest; cross-sectional concentration that explodes kurtosis; any post-hoc variant added after seeing results.

## METHOD (every variant)
Causal (signal T-1, execute T); real costs (spread×markup, FTMO commissions, **real per-night swap**); strict untouched OOS 2025-01→2026-06; **walk-forward ≥5 expanding folds**; daily/annual Sharpe + 90% CI (block bootstrap); excess kurtosis; per-year sign. Reuse verbatim: `CFDCostModel`, the audit's monotone `firstpassage.cdf_sequential`/`outer_resample_ci`, `dsr`. p(pass) on the FTMO 10k 2-step barrier with 90% outer-bootstrap CI, leverage fixed ex-ante on IS.

## BINDING GATE (decides "works" vs "doesn't")
An improvement **works** only if it lifts the edge on **walk-forward AND full-history** (not just the flattering OOS) **and** gets a horizon's p(pass) **90% CI to clear 0.50** **and** DSR > 0.5 at cumulative N. **If none clears → verdict = these edges are structurally sub-threshold even when honestly, optimally engineered.** Empty/negative is the expected and acceptable result; it will not be padded.
