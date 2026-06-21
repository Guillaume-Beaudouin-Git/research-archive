# DeXposure-Claw: Forecast-Grounded Agentic System for DeFi Credit Risk Supervision

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.19501
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 40fa72a7d03728dc3a3abdb7bf66599c

## Summary
DeFi supervision by LLM agents suffers from over-reading weak signals and recommending high-stakes interventions. DeXposure-Claw addresses this by routing LLM decisions through structured evidence: a graph time-series foundation model forecasts exposure networks, deterministic monitors convert forecasts to typed alerts, and data-health gates constrain escalation before generating auditable supervisory tickets. The system achieves better false-intervention control than baseline LLM agents on 5 years of DeFi weekly data. The architecture separates forecasting (foundation model), monitoring (deterministic rules), and action (gated LLM) into distinct layers.

## Why it might be useful
The three-layer architecture (foundation model forecasts → deterministic monitors → gated action) is directly applicable to Strategy B's kill switch logic: the current kill switch checks a STOP file on each run, but the DeXposure-Claw pattern suggests adding an intermediate deterministic monitor layer between raw HL market data and the kill switch trigger. For example, a deterministic monitor checking HMSTR open interest, funding rate z-score, and liquidity depth could gate the kill switch trigger more precisely than a binary STOP file. The data-health gate concept is also relevant to the `_automation/alpha_hunt/` pipeline where data quality from Reddit scraping in 429 error states could contaminate the L1/L2 filters without a health check layer. Code at https://github.com/EVIEHub/DeXposure-Claw.

## Extracted content
Code at https://github.com/EVIEHub/DeXposure-Claw. Technical claim: better false-intervention control than baseline LLM agents on 5 years of DeFi weekly data.

## Action proposed
TEST_LATER

Implementing a deterministic monitor layer for Strategy B's kill switch (checking HMSTR OI, funding z-score, liquidity depth) is a concrete 1-day implementation; defer until before mainnet deployment decision ~2026-07-17.
