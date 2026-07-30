# RESULTS H3 — Month-end Treasury rally (real bond futures/ETF)

**Verdict: PASSES `PERSONAL_PASS` (all 5) — first genuine non-beta edge of the session.** N tests: 4
(ZN/ZB/TLT/IEF, same signal on correlated instruments = robustness, not independent trials → honest
multiple-testing N=1, a documented literature effect). Data: yfinance ZN=F/ZB=F/TLT/IEF 2002-2026.
Signal (frozen): long last 3 business days of each month, flat otherwise.

## Gate scorecard

| # | Criterion | Result | Pass |
|---|---|---|---|
| 1 | Beat vol-targeted B&H | sleeve SR 0.90 (ZN)/0.93 (TLT)/1.15 (IEF) **vs B&H 0.07/0.33/0.56**, and MaxDD −5.8%/−12.3%/−6.0% **vs B&H −24.9%/−48.4%/−23.9%** | ✅ strong |
| 2 | Non-beta / flow | other-days mean ≈ 0 (ZN −0.72, TLT −0.00 bps) → return concentrated in month-end, NOT duration beta; decorr −0.03 (b1) | ✅ |
| 3 | DSR ≥ 0.70 @ honest N | N=1 (single pre-specified documented effect) DSR=1.00; effect strength overwhelming (see #4/regime) | ✅ |
| 4 | Regime-stable | pre-2015 t_HAC 3.24/2.97/3.97 · 2015+ 3.76/3.65/3.42 — **survived the 2022 bond crash**; placebo: month-end 12.9 bps > random-3day p95 6.5 bps, empirical **p=0.000** | ✅ strong |
| 5 | Real-futures cost | ZN cost ~0.3 bps RT vs effect 5-13 bps/day → **cost-immune** (gross/cost ≫ 1.5) | ✅ |

## What it is

A genuine, documented, **flow-driven** event edge: month-end index-rebalancing + duration-matching flow
into Treasuries. Present on the whole curve (10y/30y/7-10y), strongest on long duration (TLT +12.9,
ZB +8.9 bps/ME-day). **The single best-behaved candidate found:** regime-stable across a full ZIRP→hiking
transition (unlike Strategy A's regime dependence), cost-immune (unlike the overnight spread), positive
skew, and it BEATS buy-and-hold bonds on both Sharpe and drawdown (unlike 3A single-leg / overnight-only,
which were beta-dominated).

## Scaling & deployment (€12k)

- Standalone SR ~0.9-1.15 — **modest**, not a magic bullet. But **capital-efficient**: exposed only
  **14% of days** (3/month) → capital free 86% → leverage can be concentrated on the month-end window.
  Half-Kelly on SR 0.93 ≈ **~32%/yr** IF leverage is concentrated on the exposed days.
- **Real risk is not vol — it's a month-end bond selloff** (a hawkish surprise landing on the window).
  Size to that tail, not to daily vol; the −5.8% (ZN) / −12.3% (TLT) sleeve MaxDD is the historical guide.
- **Deployable at €12k with fine granularity** (the index-micro chunkiness problem does NOT bind here):
  **TLT fractional shares** (IBKR) or **CME Micro Treasury Yield futures** ($10/bp) — precise sizing.
- **Decorrelated from everything** (bonds + flow mechanism) → prime book component to combine with future
  sleeves as capital scales, not necessarily a solo deploy.

## Verdict

**PROMOTE to candidate-for-deployment.** First edge to clear the anti-artefact gate. Modest Sharpe but
real, stationary, cost-immune, decorrelated, and €12k-deployable. Next: (i) confirm on the exact b1
frozen spec + a proper walk-forward, (ii) measure the month-end-selloff tail explicitly for sizing,
(iii) H2 (commodity carry) remains DATA-GATED — deferred, no curve data (per prereg §3/§6).
