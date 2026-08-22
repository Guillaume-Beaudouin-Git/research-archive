# v2 LONGLIST — 27 backtested configs in the uncovered spaces, one-line kill each

Output (3). All causal, real-cost, untouched-OOS. None clears DSR>0.5 at cumulative N=97; none beats the noise floor (OOS Sharpe 2.13). Numbers: `results/v2_all_trials.csv`. The 70 iter-1 burned configs are listed at the bottom as pre-excluded (never re-tested).

## A. MULTI-LEG RELATIVE VALUE (≥3 legs) — 10 configs
*Premise: cost dilutes across legs, so a thin price-RV edge might survive. Result: the gross RV edges are absent/tiny, so dilution rescues nothing.*

| config | IS | OOS | FTMO-compliant? | kill |
|---|--:|--:|---|---|
| xsrev_idxgold k5 / k10 / k20 | −0.12/+0.04/−0.02 | −0.75/−0.52/−0.88 | **no** (corr-index L/S hedge) | no cross-sectional reversion among indices+gold; cost-negative; hedging-rule violation anyway |
| xsmom_idxgold k20 / k60 | −0.32/−0.46 | +0.65/+1.50 | **no** (hedge) | OOS-luck (IS<0, 4-6/20 yrs+, 2024 negative); non-compliant |
| equity_vs_gold k10 / k20 | −0.14/+0.09 | −0.36/−0.82 | yes (cross-asset) | equity-vs-gold ratio doesn't revert net of cost; the one compliant RV — and it's flat-to-negative |
| butterfly_nasdaq (US100 vs US500/US30) | −0.67 | −0.26 | **no** (hedge) | 3-leg index relative-strength doesn't revert; non-compliant |
| triangular_eurgbp (EUR/GBP 3-leg) | −3.80 | −6.00 | partial | triangular residual (~bp) ≪ 3-leg cost → cost-killed by an order of magnitude |
| rv_sleeve (combo) | −2.98 | −3.42 | mixed | inherits the cost-killed legs; combining negatives stays negative |

## B. REGIME / CALENDAR CONDITIONING of the proven (sub-threshold) TSMOM edge — 7 configs
*Premise: trading TSMOM only in a favorable regime lifts Sharpe via selectivity. Result: selectivity either leaves the same sub-threshold premium or destroys it (L15: regime overlays give only sub-threshold lift).*

| config | IS | OOS | kill |
|---|--:|--:|---|
| tsmom_trendstr0.5 | +0.55 | +1.26 | loose filter ≈ unconditioned TSMOM → the **already-known sub-threshold premium** (step-2), DSR 0.10, not new |
| tsmom_trendstr1.0 | +0.68 | +0.21 | tighter filter destroys OOS (over-selective); exkurt blows up |
| tsmom_trendstr1.5 | −0.13 | −0.06 | too selective → no trades, no edge |
| tsmom100_trendstr1 | +0.20 | +0.74 | sub-threshold; exkurt 34 |
| tsmom_monthend (±3d) | +0.15 | +0.30 | settlement-window conditioning removes most of the signal; nothing left |
| tsmom_quarterend | −0.10 | +0.08 | dead |
| tsmom_dow_TWT (Tue–Thu) | +0.03 | +0.72 | day-of-week is noise (re-confirms iter-1 D3 kill); OOS-luck |

## C. SUB-60MIN INDEX INTRADAY REVERSION (15/30min) — 10 configs
**KEY NEW STRUCTURAL FINDING (iter-1 could not establish this — it was daily-only):** index intraday returns at 15/30min do **NOT mean-revert**. The session-fade **GROSS** (pre-cost) IS Sharpe is **negative for all 8 index×freq combos** (−0.07 to −0.70). There is no reversion mechanism to harvest *before costs even enter* — and real CFD costs (≥1-tick slip + spread×3) then bury every version.

| config | IS net | OOS net | gross IS | kill |
|---|--:|--:|--:|---|
| sessfade30 US500/US100/US30/GER40 (1 trade/day) | −2.40/−2.34/−1.17/−0.91 | −0.25/−0.05/+0.12/−0.67 | **all <0** | no gross intraday reversion; 1 trade/day still cost-negative |
| sessfade30_sleeve | −1.96 | −0.22 | <0 | diversifying no-edge legs stays no-edge |
| sessfade30_eb4_sleeve (late entry) | −2.16 | −2.09 | <0 | later entry = less signal, same cost |
| sessfade15_sleeve | −1.69 | −0.99 | <0 | higher frequency = more cost, no more edge |
| zfade6_30m_sleeve (med turnover) | −6.47 | −4.16 | <0 | turnover×cost catastrophic |
| zfade_bigbar_30m_sleeve (selectivity) | −6.41 | −5.61 | <0 | fading only big bars doesn't add gross edge; still cost-suicide |
| fadeprev_30m_sleeve (fade every bar) | −8.55 | −6.75 | <0 | ~14 round-trips/day × ~2.75 bps ≈ 95%/yr cost drag — documented cost wall |

---

## Pre-excluded (BURNED in iteration 1 — never re-tested; cumulative N includes all 70)
The full iter-1 longlist (`research/ftmo_candidate_funnel/LONGLIST.md`): **66 funnel configs** — daily z-fade/RSI2/gap-fade MR (FX, idx, XAU, BTC), daily TSMOM & Donchian & long-only-MA, FX cross-sectional reversal/momentum, turn-of-month / Nov-Apr / day-of-week seasonality, pre-FOMC/NFP/CPI/ECB & post-FOMC events, **vol-regime conditioning (low-vol-long, high-vol-trend)** — plus **16 dead families** (G10 carry, ORB, VWAP-MR, fix-window, 2-leg pairs/cointegration, VRP, on-chain, commodity carry, PEAD, overnight-premium, weekly crypto TSMOM, round-number) — plus the **4 step-2 variants** (vol-targeted TSMOM, broadened low-vol, combo). **All burned. None re-tested in v2.** v2 deliberately avoided vol-regime conditioning (burned as F1/F2) and used trend-strength / calendar / session conditioning instead.
