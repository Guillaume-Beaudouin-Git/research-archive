# FINAL BOOK — Growth engine (futures), €12k IBKR

**Date:** 2026-07-16. Deliverable of the growth-engine goal. Objective = geometric growth, minimize ruin.
**Status: PROMISING, needs external audit + real-option validation before deploy.**

## The book (3 components, all positive-skew / ruin-aware)

| Component | Vehicle (€12k) | Unlevered SR | ann | Role |
|---|---|---|---|---|
| **Bond month-end** | ZN / micro-yield futures (cheap leverage; NOT TLT-on-margin) | **0.91** | 4.8% | growth base, flow-alpha, β≈0 |
| **Trend / TSMOM** | ~9 micros (M2K/MCL/MHG/micro-yield/M6E/M6A/M6B…) | 0.47 | 1.5% | growth core, crisis-alpha, +skew |
| **Convexity (long-straddle after compression)** | options on ES/NQ/CL/GC | ~+5%/yr | — | tail-safe (bounded loss, +skew ~1), PROVISIONAL |

**Combined trend+bonds: SR 1.02, corr 0.01** (diversification lifts SR; the key finding). Convexity adds
~5%/yr and hard tail-protection.

## Growth-vs-ruin frontier (trend+bonds core, cheap futures leverage)
| Kelly frac | leverage | growth/yr (+convexity) | 1yr ruin (hist-resampled) | realized vol |
|---|---|---|---|---|
| ¼ | 4× | **23% (28%)** | 0% | ~25% |
| ½ | 8× | **39% (44%)** | 0% | ~50% |
| full | 16× | 52% (57%) | 5% | ~100% |

**Recommended: ¼-to-½ Kelly (4-8×) → ~23-44%/yr.** This IS the honest 30-80% target range — reached by
DIVERSIFICATION (SR→1.0) + cheap futures leverage, not by a single hot edge.

## Why this reaches the target when trend-alone (10%/yr) did not
- Growth = SR²/2. Trend alone SR 0.47 → 11%/yr. **Combined book SR 1.02 → 52%/yr** (the square matters).
- On FUTURES, leverage costs ≈ risk-free (embedded in basis) → the Sharpe IS monetizable (unlike the
  ETF book killed by 6% margin cost).

## Mandatory honest caveats (engrave)
1. **"Minimize ruin" ≠ "no big drawdowns".** At ½-Kelly (8×) the book runs ~50% annualized vol → routine
   −30-40% drawdowns. Ruin (→zero) is controlled; deep DDs are the price of the growth.
2. **MC ruin is HISTORICAL-resampled** (2008-2026 block bootstrap) → real beyond-sample tail is worse than
   the 0% shown. Size to ¼-Kelly if genuinely ruin-averse.
3. **Trend is regime-dependent** (WF folds −0.30 to +1.13). The combined SR 1.02 leans on the bond sleeve;
   in a bond-hostile + trendless regime the book is weaker.
4. **Convexity is PROVISIONAL** — first-order approximation without real option prices; validate on ES/NQ
   option chains (bid-ask, smile) before including.
5. **€12k granularity**: at 8× = ~€98k notional / 9 micros ≈ 1 micro each (deployable); at 16× chunky.
6. **External audit REQUIRED** before deploy (per plan) — not yet run on this book.

## Deployment sequence
1. External-agent audit of trend+bonds engine (look-ahead, MC-ruin stress, €12k sizing).
2. Validate convexity on real ES/NQ options.
3. Paper-trade at ¼-Kelly (4×, ~23%/yr, ~25% vol) → scale to ½-Kelly if live matches backtest.
4. Bond base runs in parallel (near-free). Re-consolidate as capital grows.

---
## ⚠️ CORRECTION 2026-07-16 — TWO EXTERNAL AUDITS: headline NOT-CONFIRMED
**Convexity sleeve: FALSIFIED** — real option chains show the VRP multiple k is HIGHER at compression
entry (mean-reversion-loaded IV vs depressed RV), exactly where net EV goes negative. The strategy's own
entry condition works against its edge. DROPPED. (Bid-ask was fine — QQQ 2.1%; k was the killer.)

**Trend+bonds book: NOT-CONFIRMED for "~23-44%/yr @ 0% ruin deployable at €12k".** Ingredients real
(look-ahead-clean, reproduces exact, month-end = genuine flow-alpha t=4.0, dodged 2022, β_TLT 0.12). BUT:
1. **"0% ruin" is an artifact** — MC used a −80% bar (IBKR margin-calls at −30/−50%) AND a 20d block
   bootstrap that ERASES serial dependence. Real: at 8× the historical path hit **maxDD −73%, worst day
   −31%**; realistic-bar bust prob at 8× = −50%:3% / −40%:9% / −30%:18%. A 2×-worse shock WIPES the account.
2. **Granularity trap** — at €12k, the SAFE ¼-Kelly (4×) = 0.45 micro-lots/sleeve → cannot diversify;
   1-lot/sleeve only at ~8× (the unsafe band). The diversification (= the thesis) requires unsafe leverage.
3. **Bond vehicle unvalidated** — effect measured on TLT (20y price ETF); deploy claim is ZN/micro-yield
   (10y / yield instruments, different). Magnitude NOT re-verified on the tradable future.

**Honest reality at €12k:** either ~10-15%/yr low-lev under-diversified, or ~30%/yr at 8× with REAL 9-18%
bust probability + −73% historical DD. NO fast-growth-at-zero-ruin version exists. Month-end flow-alpha is
the one solid piece → build on it, on the real ZN/micro-yield future, at honest leverage. Both audit
verdicts: `tasks` transcripts; reproduction/look-ahead/growth-math CONFIRMED, headline NOT-CONFIRMED.
