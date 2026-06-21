# Forward-Looking Stress Testing Under Macro Scenarios: Stable SVaR Estimation

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.07575
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 2501390378195836476653f225da50b4

## Summary
The GPR-HS framework for Stressed VaR is extended to handle forward-looking macro scenarios required by CCAR and ICAAP regulation. Traditional parametric SVaR becomes numerically unstable under extreme shocks; GPR-HS provides stability across three regulatory-style scenarios by conditioning historical simulation on macro forecasts rather than past observations.

## Why it might be useful
The propfirm book guardrails (MAX_DAILY_DD=2.8%, MAX_TOTAL_DD=5.5% in execution/__init__.py:46-47) are fixed-percentage rules without macro conditioning. GPR-HS stress scenarios could inform more dynamic guardrails: computing SVaR conditioned on BTC bear-macro scenarios (FRED macro data available) would give a principled upper bound on daily DD rather than the current empirical percentages. The sector_hothand_propfirm strategy (under mandatory audit for t_HAC=10.38) would also benefit from stress-scenario VaR to confirm FTMO MaxDD<-10% holds under adverse conditions. Requires macro scenario construction and GPR fitting: 2-3 days.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Apply GPR-HS stress scenarios to sector_hothand_propfirm as part of the mandatory t_HAC=10.38 audit to verify MaxDD<-10% under stress; 2-3 days.
