# STRATEGY REGISTER — everything tested (2026-07), DO NOT RE-TEST identically

Consolidated ledger of the two research arcs (Sharpe-quest + growth-engine), personal-account €12k IBKR.
Each row: family · what was tried · honest verdict · why. **Do not re-test these exact specs without new
data or a materially different construction.**

## Arc 1 — Sharpe-maximization book (swap-killed families + Phase-2 push)
| # | Family | Verdict | Why (engrave) |
|---|---|---|---|
| H1 | Overnight index drift (futures) | ❌ | Real+stationary but beta-slice (fails beat-benchmark); MN spread cost-dead on turnover |
| **H3** | **Month-end Treasury** | ✅ **KEEP** | Flow-alpha, SR ~0.9-1.1, β≈0, cost-immune, roll-clean, OOS-confirmed. THE anchor sleeve |
| H4 | Commodity seasonality | ❌ | Roll artifact: yfinance SR 1.13 → roll-clean 0.47, placebo fails. DROPPED |
| H5 | Pre-FOMC drift (equity) | ❌ | Beta-slice, fails placebo, kurtosis 728 (outlier-driven), decayed |
| H6 | Month-end FX flow (Melvin-Prins) | ❌ | SR 0.05 on clean FX, decayed post-2015 |
| H7 | Martingale / grid (mechanical) | ⛔ | Sizing overlays, zero EV, ruin 36-81%, anti-Kelly |
| H8 | Grid on mean-reverting spread | ⚠ | Needs real MR underlying + trend kill-switch; found 4 (below) but modest |
| **H9** | **Cointegrated-spread grids** | ✅ weak | WTI-Brent/Corn-Wheat/Gaso-Crude/HeatOil-Crude OOS-stationary; SR ~0.4-0.7, DD-heavy, €12k-blocked (full futures) |
| — | Short-vol carry (regime-filtered) | ⚠ | SR 1.11 was clip-inflated 3× (real -73% DD); tiny weight only |
| — | Trend/CTA sleeve | ✅ hedge | crisis-alpha, +monthly skew; low SR |
| — | Kaufman ER regime filter | ❌ | HURTS (flattens before reversion) |
| — | z-score MR on spreads | ❌ | Does not beat the grid |
| — | Equity sector factor L/S | ❌ | Dead (SR 0.04, factors crowded) |
| — | Equity calendars (FOMC-week, ToM) | ❌ | Beta-slice, fail beat-benchmark |
| — | FX/rates carry (incl FRED) | ❌ | Weak/regime-dependent, dead post-GFC (L31) |
| — | Strategy B crypto delta-neutral carry | ❌ | Walk-forward NEGATIVE (mean SR −1.55, hedge not neutral) |
| — | PCA-residual ETF stat-arb (Avellaneda-Lee) | ❌ | Negative even GROSS (HFT-arbitraged post-2010) |
| — | COT hedging-pressure | ❌ | SR 0.24, regime-decayed (2023-26 SR −1.08) |
| — | Broad month-end expansion (13 sleeves) | ❌ | In-sample 2.11 → OOS 1.79 (overfit, demonstrated) |
| — | Disaggregated futures curve (free?) | ❌ | Not free on Yahoo (404 on contract months) |

**Arc-1 conclusion:** book Sharpe ~2.0 achievable & OOS-confirmed, BUT **un-monetizable at €12k** — high
Sharpe on low-vol book returns 2-3%/yr, and retail ETF margin (~6%) makes leverage net-negative. **A high
Sharpe is only monetizable with cheap leverage (futures) or institutional borrow.** The 2.5 target is not
honestly reachable with retail free-data (16 families).

## Arc 2 — Growth engine (futures, cheap leverage)
| # | Family | Verdict | Why |
|---|---|---|---|
| **H1g** | **Diversified TSMOM** | ✅ core | SR 0.35-0.47 (modern trend drought, AQR-consistent); +monthly skew; crisis-alpha |
| H2g | Donchian breakout | ❌ weaker | SR 0.16-0.32 |
| H5g | Ensemble TSMOM+breakout | ❌ | corr 0.88, no benefit |
| A | Pyramiding overlay | ❌ | Trades Sharpe↓ (0.46→0.36) for skew↑; growth ∝ SR² → net-negative. 3rd sizing-overlay refuted |
| **B** | **Conditional long-convexity (straddle after vol-compression)** | ✅ small | Real edge on liquid-options futures (ES/NQ/CL/GC), +skew ~1, ruin-safe; but ~5-12%/yr, PROVISIONAL (no real option prices) |

**Arc-2 conclusion & THE law:** **growth = SR²/2.** No single retail directional edge (SR 0.4) grows fast.
BUT the **combined book (trend + bond-month-end, uncorrelated) = SR ~1.0 → ~40-52%/yr at ½-full Kelly on
cheap futures leverage** — reaches the honest target via DIVERSIFICATION, not a hot edge. Pyramiding and
naive long-vol do not help. See FINAL_BOOK.md.

## Universal lessons (engrave, apply everywhere)
1. **Growth = SR²/2**; Sharpe needs cheap leverage to monetize (futures yes, retail-ETF-margin no).
2. **Sizing overlays create no edge** (martingale, grid, pyramiding all refuted) — only signal + Kelly do.
3. **Headline Sharpes inflate 2-3×** (Ross Hook 1.5→0.44, A beta, gold-silver beta, H4 roll, ShortVol clip,
   B WF-negative, book 2.11→1.79). Always deflate: DSR + OOS + roll-clean + external audit.
4. **Diversification of uncorrelated modest edges is the real lever** (SR 0.5+0.9 → 1.0).
5. **Retail directional futures/forex edges are SR 0.35-0.47** (modern trend drought); positive-skew but weak.
6. **"Minimize ruin" ≠ "no drawdowns"**: aggressive Kelly = 50% vol, −40% DDs, ruin controlled not absent.
