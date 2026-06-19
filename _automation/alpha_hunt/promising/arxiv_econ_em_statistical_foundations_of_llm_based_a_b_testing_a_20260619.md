# When Can an LLM Replace a Human in an A/B Test? A Surrogacy Framework

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.17165v2
**Captured**: 2026-06-19 03:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 9e84bc167f19454aa0ce31e5a7a88ff6

## Summary

This paper formalizes the conditions under which a treatment effect estimated on LLM-generated responses can recover the average treatment effect that a randomized human-subject experiment would have produced. The authors adapt surrogate endpoint theory (from clinical trials) to the LLM setting, deriving surrogacy and comparability conditions that are jointly weaker than full distributional equivalence. A falsification test for the surrogacy assumption is provided. The paper shows that LLM stochasticity both weakens identification and adds variance at estimation time, but that averaging over multiple LLM draws per unit substantially mitigates both problems. An empirical application to Upworthy headline A/B tests finds that uncalibrated LLM responses recover only 39% of the measured human treatment effect, while nonparametric calibration closes most of this gap. The central finding: LLM-based A/B testing is valid by assumption, human A/B testing is valid by design.

## Why it might be useful

The `_automation/feasibility/` pipeline uses Claude as a proxy for "would a researcher find this alpha hypothesis promising?" — structurally identical to using an LLM as a surrogate for human judgment in an A/B test. The 39% ATE recovery result quantifies the systematic bias in uncalibrated LLM scoring relative to researcher utility. Concretely: if the automation were to use researcher accept/reject verdicts logged in `promising/` and `tested/` as calibration targets, the nonparametric calibration approach described here would provide the statistical basis for adjusting Claude's prior over hypothesis quality. No direct trading signal. The falsification test for the surrogacy assumption is the actionable methodological contribution — it could be run periodically on `_automation/feasibility/` outcomes to detect when the LLM proxy has drifted from researcher preferences (e.g., after model upgrades). This is distinct from all archived trading research and doesn't touch A/B/C strategy mechanics.

## Extracted content

The authors report that raw LLM predictions recover only 39% of human treatment effects on Upworthy headline A/B tests; nonparametric calibration substantially closes the gap between LLM-estimated and human-measured average treatment effects.

## Action proposed

REFERENCE — governs LLM reliability as a proxy evaluator in the automation pipeline; no path to a trading signal in the current book.
