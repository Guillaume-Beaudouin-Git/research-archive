# S_BASIS — DATA-BLOCKED on free sources (no backtest run)

**Date:** 2026-07-10 · **Mission:** `Commodities/research/active/xs_basis_tsmom/`
**Verdict:** the basis (term-structure) leg **cannot be tested cleanly with free data.**
No backtest was run — running one on the available proxy would produce noise, not a verdict.

## What S_BASIS needs vs what free data gives
S_BASIS is the Erb-Harvey commodity carry factor: rank by the **basis / roll-yield**
(front-vs-second-contract term structure), long backwardated / short contango, monthly XS.
It requires a **continuous second-month series** alongside the front, for 24 contracts,
2005-2026.

Two free paths were checked empirically — both fail:

**1. Roll-gap proxy** (`fetch_front_second.py`, Approach C — infer basis from the price jump
at each roll of the continuous =F series). Measured on the 24-contract panel:
- overall coverage **13.5%**;
- **median cross-sectional breadth = 3 tickers/month** (a tercile long/short needs ≥6;
  only **29 / 258** months reach ≥6, only **1** month reaches ≥10);
- **96% of the "valid" values are STALE** — carried forward from a roll up to 3 months old;
  only 4% are genuine month-to-month updates.
→ Unusable: at a typical month-end you have 3 stale basis estimates, not a cross-section.

**2. Individual deferred contracts via yfinance** (e.g. `CLZ26.NYM`). Currently-listed
deferreds return data (CLZ26 from 2017), BUT **every EXPIRED contract 404s** (CLZ15, CLZ12,
CLM18, GCZ15, CLZ22 all "Quote not found"). yfinance drops contracts at expiry → a historical
second-month continuous can only be stitched for the **recent ~2-4y** (currently-listed
chain), not 2005-2026. Too short + recent-only (no pre-2015 regime) + heavy stitching for a
weak N≈6-10 test → not worth building against paid alternatives.

## What would unblock it
A real futures **term-structure** history (front + ≥1 deferred, or a proper continuous-2nd
series with roll dates), e.g.: Nasdaq Data Link continuous-futures (SCF/CHRIS, now largely
premium), Barchart getHistory, CME DataMine, Norgate Data, or a broker futures API with
historical chains. Then: build basis = (F_front − F_second)/F_front annualised, monthly XS,
two-sided + OOS + DSR — a fresh pre-registration.

## Consequence for the mission
With S_TSMOM (dual momentum) **FALSIFIED** (`PHASE_B_RESULTS_dual_momentum.md`), the XS
reversal a **one-sided losers-rebound** (`REVERSAL_RESULTS.md`, archived), and S_BASIS
**data-blocked on free data**, the `xs_basis_tsmom` mission is **exhausted on free data**.
The economically-live axis (basis/roll-yield) is real but **paywalled**. Recommend: park the
mission as BACKLOG(paid-data) — reopen only if a term-structure source is acquired.

## Routing reminder (unchanged)
Even if unblocked, commodity XS basis is monthly/lumpy → **invest-long / personal (or a future
FUTURES prop book), NOT the current FTMO-CFD book** (L24 symmetric-barrier mismatch; L32 CFD
carry uncollectable if ever ported to CFDs).

## n_tests
**Zero** consumed (no test run — a data block is not a test).

---
*2026-07-10. S_BASIS attacked, found data-blocked on free sources (roll-gap proxy breadth 3 /
96% stale; yfinance drops expired contracts). No backtest run; nothing graved.*
