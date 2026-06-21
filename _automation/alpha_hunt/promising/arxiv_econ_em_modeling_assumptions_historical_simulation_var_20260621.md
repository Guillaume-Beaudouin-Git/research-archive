# Unifying Historical Simulation, FHS, and Hybrid VaR Under a Common Modeling Framework

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.10066
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 7ad8939ed9c6d8feae28737243c2d860

## Summary
This paper unifies Historical Simulation (HS), Filtered Historical Simulation (FHS), and Hybrid VaR methods under a single modeling framework by explicitly parameterizing the asset return model and extracting innovation increments from historical data. The unification reveals that plain HS makes an implicit iid assumption on returns that is violated under persistent volatility, while FHS with GARCH residuals is consistent even under volatility persistence. The framework clarifies which conditional and unconditional independence assumptions each variant implicitly makes, providing a theoretical basis for choosing among the methods.

## Why it might be useful
This framework is directly applicable to the drawdown simulation methodology in `Portfolio/risk/trailing_dd_simulator.py`: if the simulator uses historical simulation of daily returns to estimate propfirm pass probability, the implicit iid assumption identified here would cause it to underestimate tail risk during volatile regimes (exactly when propfirm evaluation periods are most dangerous). The FHS-with-GARCH consistency result suggests that adding a GARCH filter to the return innovations in `trailing_dd_simulator.py` before resampling would improve the accuracy of propfirm pass-rate estimates, particularly for Strategy A where the 28-day vol window may not be sufficient to filter out persistent vol regimes. The framework also clarifies that the "calibrated trade-based generator" in L22d (mandatory for SL-capped strategies) should use FHS-filtered residuals rather than raw returns.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Adding GARCH-filtered FHS to `Portfolio/risk/trailing_dd_simulator.py` is a concrete 1-2 day enhancement to the propfirm pass-rate estimation; implement when FTMO propfirm challenge planning resumes for any strategy.
