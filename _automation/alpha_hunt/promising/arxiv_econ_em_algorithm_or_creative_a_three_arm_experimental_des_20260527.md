# Algorithm or Creative? Decomposing Algorithmic vs. Content Effects in Platform A/B Tests

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.23706v1
**Captured**: 2026-05-27 12:08 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 67ef13f72739f6aca137aec8558406e2

## Summary
Standard two-arm A/B tests on advertising platforms conflate two distinct channels: the direct effect of creative content on users, and the indirect effect of how the platform's delivery algorithm routes impressions. This paper proposes a three-arm design — adding an arm that exposes the algorithm to treatment metadata while serving identical creative to users — to separately identify algorithmic (routing) and creative (content) effects. In a live Meta campaign, roughly 75% of female impression share reallocation was attributable to the algorithm, not the creative; a conventional two-arm test understated the algorithmic channel by a factor of two.

## Why it might be useful
This paper is about digital advertising experimentation, not financial markets. The L1 "topic_relevance" match reflects terminology overlap ("algorithm," "platform") rather than substantive relevance. There is no connection to Strategies A, B, C, or D, nor to any methodology in CLAUDE.md (HAC, walk-forward, DSR). The closest stretch would be using similar three-arm reasoning to decompose execution algorithm effects from signal effects in live trading (e.g., in Strategy C, separating VWAP confirmation signal quality from execution slippage), but the paper provides no financial methodology for this.

## Extracted content
The authors report "+2.07 ppt increase in female impression share via algorithmic channel" and "-0.68 ppt via creative channel" in a live Meta campaign. Algorithmic channel represents ~75% of total reallocation.

## Action proposed
REFERENCE
