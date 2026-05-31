# Statistical Arbitrage via Cointegrated Pairs — Indian Equity Market 2015-2025 (EPAT Project)

**Source**: quantinsti
**URL**: https://blog.quantinsti.com/cointegrated-pairs-trading-indian-equity-market-epat-project/
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[trading_topic, methodology], L2_OK
**Hash**: 4dd1a3ca8ab99b22da993565c1f0fd4f

## Summary
An EPAT student project by Shant Tondon constructing a statistical arbitrage strategy on the Indian equity market over the 2015-2025 period. The methodology uses the Engle-Granger cointegration test to screen pairs, employs z-score thresholds for mean-reversion entry and exit signals, explicitly models round-trip transaction costs per leg, and validates results with walk-forward backtesting. Portfolio-level risk controls are applied to manage concurrent open positions. No specific net Sharpe or annual return figures are available from the excerpt alone.

## Why it might be useful
Pairs cointegration on equities has been exhaustively tested and permanently archived in this repo: a full universe scan found 0 out of 19 candidates qualifying under the Engle-Granger test, and the Gatev distance variant produced Sharpe -0.44 with t=-2.5 (see CLAUDE.md archived equities section). This item does not open a new test path on equities. The methodological value is as a reference for the Commodities XS — Basis + TSMOM active research (`Commodities/research/active/xs_basis_tsmom/`): commodity futures calendar basis spreads exhibit much more stable stationarity than equity pairs due to the arbitrage-enforced roll relationship. If a basis spread fails the Engle-Granger test in that research, this project's transaction cost modelling approach — accounting for both legs of each basis trade — would be directly reusable. Any spread significance test must still apply HAC lag-6 given that basis signals can have half-lives exceeding 30 days (risk of L12b HAC deflation).

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — Pairs cointegration on equities is archived (0/19 qualify). Relevant only as cost-modelling reference for Commodities XS basis spreads.
