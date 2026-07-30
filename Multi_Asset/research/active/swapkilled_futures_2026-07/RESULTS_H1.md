# RESULTS H1 — Overnight-session drift on real index futures

**Verdict: FALSIFIED as a non-beta edge (PERSONAL_PASS #1 + #2/#5 fail).** N tests: 6 (NQ ov-only,
NQ midweek, spread, + 5-index breadth pooled). Data: `data/overnight_research/nq_rth_daily.parquet`
(NQ RTH-clean 2010-2026) + yfinance cash indices ^NDX/^GSPC/^RUT/^DJI/^GDAXI 2005-2026. Cost: real
futures ~0.7 bps/leg (MNQ), 0 swap.

## Findings

**1. The overnight drift is REAL and STATIONARY** (the one genuine positive):
- NQ overnight-only SR **0.80** net vs intraday-only SR 0.28 — risk-adjusted return concentrated
  overnight, as the literature says (Cooper/Lipson/Bogousslavsky overnight anomaly).
- Regime-stable: NQ overnight SR 2010-14 **1.08** / 2015-19 **0.92** / 2020-22 0.28 / 2023-26 **1.13**;
  P&L share 30/30/10/30 — NOT bull-concentrated. Best regime-stability of any candidate audited this
  cycle (contrast Strategy A). Midweek variant SR 1.14, MaxDD −16%, skew −0.23, kurtosis 8.7 (moderate).

**2. But overnight-only is a BETA SLICE — fails beat-benchmark (#1):**
- NQ overnight-only SR 0.80 **< buy-&-hold 24h SR 0.95**. Levering cannot fix it (Sharpe-invariant).
- Breadth: overnight beats B&H in **1/5** indices (DAX only, and only because DAX intraday is negative).
  NQ/S&P/Russell/Dow: overnight < B&H. → it is the overnight portion of index beta, not alpha.

**3. The two-sided market-neutral harvest (long-overnight / short-intraday) is COST-DEAD (#2/#5):**
- Gross spread 2.08 bps/day, but requires 4 legs/day turnover. Net SR: @0bps **0.26** (weak even gross)
  → @0.7bps/leg **−0.09** → @1.4bps **−0.44**. Negative and decaying across all regimes (2023-26 −0.25).
- DSR fails (negative Sharpe). This is L33b/L43: intraday-flat high-turnover dies on cost, even on
  cheap micro futures.

## The H1 lesson (candidate for L-registry)

**Removing the CFD swap resurrected the overnight sleeve's *absolute* return (CFD-negative →
futures-positive SR 0.80) — confirming the swap WAS the CFD killer — but the personal-account
beat-benchmark gate reveals the sleeve was never alpha, only beta. Vehicle change fixes the sign, not
the nature.** The swap hypothesis (L36) was right about the vehicle and wrong about the edge: for the
directional sleeve the binding constraint was always **beta-dominance**; for the market-neutral spread
it was always **turnover**, never the swap. Mis-attributing a family's death to the removable constraint
(swap) instead of the structural one (beta/turnover) is the trap this session's gate is built to catch.

→ Confirms `overnight_verification_2026-06` ("3 containers all sub-gate, personal book SR 0.68 <
beta-proxy") on the real-futures cost structure. **No H1 sleeve promoted.** Proceed to H3.
