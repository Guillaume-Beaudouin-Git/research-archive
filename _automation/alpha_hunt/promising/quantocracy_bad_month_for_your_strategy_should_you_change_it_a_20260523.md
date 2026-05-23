# Bad Month for Your Strategy? Should You Change It? [Alvarez Quant Trading]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=Vp2lBvtsR2&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 29a0db9da65406ceab4d9e84ebc4223d

## Summary
A decision framework for when a strategy's recent underperformance justifies parameter changes versus when it's simply normal variance that should be tolerated. The article presents criteria for distinguishing "expected drawdown within the strategy's historical distribution" from "evidence of regime change or structural failure" that warrants intervention.

## Why it might be useful
Directly relevant to Strategy A (crypto TSMOM, PAUSED after propfirm breach): the propfirm breach was a MaxDD breach, which is an external constraint rather than evidence of strategy failure. CLAUDE.md already validates the methodology (Sharpe 1.33 OOS, MaxDD -6.9%) and labels the status as "methodology validated, awaiting new propfirm deployment." This framework could formalize the decision criteria for when to actually modify Strategy A versus when to simply redeploy with the same parameters. Also ties to the "Max 3 modifications" hard rule — the framework should prevent reflexive modifications after a bad period. Pair with the EGARCH and regime-filtering items in this run.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Decision framework for modification vs. patience. Read before considering any modification to Strategy A — aligns with the 3-modification cap hard rule.
