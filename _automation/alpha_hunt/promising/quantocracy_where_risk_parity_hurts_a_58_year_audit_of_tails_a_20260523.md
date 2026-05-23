# Where Risk Parity Hurts: A 58-Year Audit of Tails and Drawdowns [Beyond Passive]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=nVuBJux3Gm&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic, metrics], L2_OK
**Hash**: 8eca161eb2ba38871e4d2e7a294ccf93

## Summary
A 58-year synthetic audit of inverse-volatility allocation across SPY, TLT, and GLD (back to 1968) reveals that risk parity's advertised diversification breaks down in stagflation and rising-rate regimes, where equity and bond volatility correlate positively. The extended historical dataset quantifies which specific macro tail events account for most of the strategy's historical drawdowns — a more honest accounting than the 2006-present backtest window typically used.

## Why it might be useful
CLAUDE.md documents a theoretical A+B+C portfolio using ERC sizing achieving Sharpe 2.24 and MaxDD -1.0%. This audit is a direct warning: ERC sizing assumes decorrelated vol across strategies, but Strategy A (crypto, high vol) and Strategy B (near-zero vol delta-neutral) could experience vol correlation spikes during crypto-specific macro stress events. The specific risk: verify that Portfolio/state/portfolio_state.py ERC model doesn't use static vol covariance — it should use realized daily vol targeting as in Strategy A. The 58-year methodology (synthetic historical extension) is also relevant if Strategy A backtesting ever extends beyond available crypto data.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Read full article for the macro regimes where ERC hurts. Cross-check against crypto vol spike dates (e.g., 2022 crypto crash). Verify portfolio_state.py ERC covariance assumption. Half-day effort.
