# Position: Prioritize Structure Identification Over Complex Models in Scientific Discovery

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.02632v1
**Captured**: 2026-06-03 06:06 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 33237c666deef0569c88618daaf3389f

## Summary

This position paper argues that in high-dimensional observational settings — exactly where modern ML shines predictively — causal mechanism recovery is generically underdetermined: many mutually incompatible causal structures produce statistically indistinguishable data. Predictive success therefore cannot serve as evidence of correct mechanism discovery. The problem is uniquely aggravated by LLMs, which tend to collapse a large equivalence class of plausible mechanisms into a single fluent narrative, creating an illusion of understanding. The authors propose concrete "mechanistic ML" standards requiring that a claimed mechanism be uniquely identified from data, not merely consistent with it.

## Why it might be useful

This paper speaks directly to the `_automation/alpha_hunt` pipeline, which uses Claude to evaluate and narrate research hypotheses. The LLM "narrative collapse" warning is operational here: when the pipeline explains *why* a signal works (funding rate carry = liquidity premium? = beta compensation? = regime artifact?), the explanation may be rhetorically coherent while remaining mechanistically underdetermined — all three stories fit the same backtested data equally well. This strengthens the existing pre-registration discipline in CLAUDE.md: the mechanical L0/L1/L2 filter correctly bypasses LLM narrative quality, and the HAC+AMTP+DSR stack is a partial empirical guard. More concretely, this paper supports the mandatory audit trigger already flagged for sector_hothand_propfirm (t_HAC=10.38 red flag in `_audit/sector_hothand_audit_2026-05-30.md`): a suspiciously high t-stat is precisely what "underdetermined mechanisms fitted by complex models" look like numerically. For archived signals (MVRV momentum, on-chain netflow), the paper retroactively validates the L12b HAC deflation rejection — those signals had plausible narratives but no uniquely identified mechanism. No direct backtest path; value is methodological.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed

REFERENCE

Good methodological background for the alpha hunt LLM pipeline and pre-registration discipline. Reinforces the principle that narrative coherence from Claude should never substitute for empirical identification — relevant each time a new hypothesis is staged. No immediate test implied.
