# Literature Review and Evidence Aggregation: a Toolkit for Applied Micro

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.28848v1
**Captured**: 2026-06-30 02:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 07515ba30c57763897cf4b7cd7f26636

## Summary
This paper provides a practical toolkit for analysts summarizing evidence from a set of prior studies on related effects. Three components: (1) methods to summarize the distribution of prior estimates, (2) prediction of an effect in a new context using covariate-reweighted extrapolation, and (3) correction for publication bias (selectivity). The key empirical finding is that after applying selectivity correction, the true mean effect is only 12–21% of the naïve simple mean across several applied-micro domains. The toolkit is presented as accessible even with as few as three prior studies.

## Why it might be useful
The feasibility pipeline in `_automation/feasibility/` currently screens hypotheses against literature claims at face value. This paper provides the corrective: a 2× or 3× gross Sharpe claimed in a paper should be deflated for publication bias before feeding into the feasibility gate — the true out-of-sample effect may be only ~15% of the advertised mean. This is the academic-literature complement to DSR (Bailey-LdP, L20), which corrects for within-strategy overfitting. Together they form the two-sided correction: AMTP/DSR for our own tests, selectivity correction when citing external literature. Concretely, when the `_automation/synthesis/` synthesis step compares strategy D or ZN Baltussen paper claims against our gates, apply a 5–8× shrinkage factor before treating a cited Sharpe as a prior expectation.

## Extracted content
The author claims: "The mean effect after correcting for selectivity is between 12% and 21% of the simple mean in our empirical examples."

No code, formulas, or specific numeric claims beyond the above in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE
