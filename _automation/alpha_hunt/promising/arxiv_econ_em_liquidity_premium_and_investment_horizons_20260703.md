# Liquidity Premium and Investment Horizons

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.01377v1
**Captured**: 2026-07-03 01:30 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 64d2d49ea3f2b14afc7d222ae29c19fb

## Summary
The authors estimate a Kyle-style price-impact coefficient directly from signed daily equity order flow (CRSP, 2020-2025) and show it forecasts both contemporaneous and one-month-ahead cross-sectional stock returns, confirmed via Fama-MacBeth regressions with Newey-West correction. Rising volume volatility (i.e., widening price impact) predicts lower subsequent returns. The paper's theoretical contribution is to resolve the Constantinides (1986) illiquidity-premium puzzle through an adverse-selection channel rather than a risk-based one: low order flow temporarily widens price impact and depresses prices, and the premium is simply the reversal that follows as prices normalize — not compensation for bearing liquidity risk.

## Why it might be useful
This is directly on-theme with the `execution_cost_sqrt_impact` cluster tracked in `_automation/synthesis/_state.json` (4 papers, "consolidating" status, driving Strategy B's HL market-impact/TWAP sizing work ahead of the ~2026-07-17 mainnet review) — it's a second, independent (equity market, not crypto) confirmation that price-impact/adverse-selection mechanics are return-predictive, reinforcing H006's operational logic even though the asset class differs. Separately, the Fama-MacBeth + Newey-West lag structure is exactly the mandated HAC methodology (toolkit item 2), and the order-flow/illiquidity mechanism is a genuinely different economic driver than anything tried in the archived equities cross-section work (sector reversal Sharpe -0.60 t=-3.7, jt_momentum_cs Sharpe -0.026) — worth flagging as a distinct signal family if `sector_hothand_propfirm` (active, flagged for mandatory audit due to t=10.38) ever needs an orthogonal robustness factor per L38 (beta-orthogonal test).

## Extracted content
No code in the excerpt. Claims: order-flow signal predicts contemporaneous and 1-month-ahead cross-sectional returns; effect "significant" after Newey-West adjustment in Fama-MacBeth regressions (no explicit t-stat or Sharpe given in the abstract). Sample: CRSP daily equity order flow, 2020-2025.

## Action proposed
TEST_LATER — CRSP order-flow data is not free; a yfinance-derived Amihud-illiquidity proxy would need to be built first, and there is no active equities strategy currently at the signal-testing stage (sector_hothand_propfirm is still under audit, not cleared for new factors). Revisit if/when that audit clears or a new equities XS project opens.
