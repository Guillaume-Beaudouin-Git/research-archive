# Multi-Asset Daily Pullback Framework with Trend Filter and Volatility Sizing

**Source**: quantpedia
**URL**: https://quantpedia.com/testing-an-ai-assisted-research-workflow-for-multi-asset-pullback-strategy-discovery/
**Captured**: 2026-06-17 15:00 UTC
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: 8eb1d334efe1ee7acaa916c50874e713

## Summary
The paper constructs a systematic short-term mean-reversion framework that enters long positions after consecutive down-days across multiple asset classes, filtered by a 200-day moving average to avoid buying into structural downtrends. The test universe covers six liquid ETFs spanning equities, fixed income, currencies, gold, and commodities over 2006–2025, with volatility-adjusted position sizing and equal-weight allocation across concurrent signals. The authors run parameter sweeps over MA window length, number of consecutive down-days required, and holding period, and benchmark against short-term RSI variants to assess robustness. A secondary contribution is a case study on integrating LLM tools (ChatGPT and Claude) into the quantitative research workflow itself, including hypothesis generation and chart interpretation.

## Why it might be useful
The most direct collision in the archives is "equity indices_swing Sprint 1+2 (100 tests, best Sharpe 0.45 at futures cost, costs kill at ETF level)" — that project tested short-term swing entries on indices ETFs and found the edge too thin to survive realistic costs. This paper uses the same ETF vehicle and daily frequency, so the same cost-kill concern applies: if the reported Sharpe is in the 0.4–0.6 range at ETF transaction costs, the result won't generalize. **The decisive test**: fetch the actual paper metrics (Sharpe, MaxDD, win-rate, avg hold days) from the full article, then rerun the cost sensitivity replacing ETF costs (~0.08% RT) with commodity futures costs (~0.015% RT, using the GC/CL/GS contracts already in the Commodities XS universe). The 200-day MA trend filter is a concrete innovation over the archived sprint: it makes the pullback long-only above the trend line, which should reduce left-tail exposure and could bring the MDD within RESEARCH_PASS bounds (<25%). If futures-adjusted Sharpe clears 0.7, this is the cheapest possible entry point for the Commodities XS active research (Phase A is still at data fetch; running a daily-freq pullback baseline costs zero additional data).

## Extracted content
No code, formulas, or specific numeric claims (Sharpe, MaxDD, win-rate) in the excerpt. Full article needed — the URL is freely accessible and quantpedia articles typically include full backtest tables.

## Action proposed
TEST_LATER

Full article is a prerequisite: the excerpt gives mechanism and methodology but zero performance numbers. Read the article (~30 min), extract the core metrics, then run a quick cost-sensitivity pass on commodity futures (GC=F, CL=F, GS=F from the Commodities XS dataset) replacing the ETF cost assumption — this is a 2-3h exercise, well below a full backtest. If the futures-cost Sharpe clears 0.7 AND the holding period is short enough to avoid swap drag issues, this could be a legitimate fast-path baseline for the Commodities XS active research before the more complex monthly CS basis+TSMOM framework (Moskowitz/Erb-Harvey) is built.
