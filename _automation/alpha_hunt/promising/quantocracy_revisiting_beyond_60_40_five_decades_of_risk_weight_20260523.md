# Revisiting Beyond 60/40: Five Decades of Risk-Weighted Allocation [Beyond Passive]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=BNXOFpU1eI&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: ed54f90357cc793100177d5714bec079

## Summary
Beyond Passive revisits the classic 60/40 stock-bond portfolio over a five-decade backtest, focusing on the inflation-correlated regime where the negative stock-bond correlation assumption breaks down. The argument is that risk-weighted (rather than capital-weighted) allocation provides more robust diversification when correlations regime-shift. The piece likely builds toward a risk-parity or ERC-style framework as the proposed replacement, validated across the 2021-2023 inflation shock period.

## Why it might be useful
Directly relevant for the Portfolio framework component of Algo_claude. The QuantInsti "Building a Robust Portfolio with Risk Parity" piece (also retained this run) covers similar ground at an implementation level — the two together form a useful pair for ERC sizing methodology. Current Algo_claude portfolio integration uses ERC for A+B+C with theoretical Sharpe 2.24 and MaxDD -1.0%, but Strategy B is backtest-proxied (testnet funding artificial) so the live correlation matrix is partially synthetic. This article's five-decade lens validates that risk-weighted allocation is robust to regime changes, which is the central concern when sizing A (crypto TSMOM) alongside C (NQ futures) — two very different asset classes that could decorrelate or correlate sharply in stress. Methodology note: the assumption-failure analysis (when does the 60/40 hedge break?) is the kind of stress-test reasoning that should be applied to the A+B+C correlation matrix before live deployment of C.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Read full article to extract the risk-parity formulation and the stress-test methodology for correlation breakdown. If the framework is clean, apply it to the A+B+C ERC weights to verify robustness under correlation shocks. 1-day effort. Counts toward the Portfolio framework workstream, not toward any specific strategy's 3-modification budget.
