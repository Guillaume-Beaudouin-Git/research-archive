# Post-Rejection Follow-Up Sampling: Closing the Evaluation Loop on Filter-Based DEX Systems

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.08228
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: e10d03b809ceb1811f357342f3392553

## Summary
Most algorithmic filter systems never measure the counterfactual outcome of rejected candidates, making it impossible to distinguish true negatives (correctly rejected unprofitable items) from false negatives (missed profitable opportunities). This paper introduces Post-Rejection Follow-Up Sampling (PRFS), a methodology where a separate tracking subsystem monitors rejected tokens' price and liquidity at configurable intervals for up to 24 hours. Applied to the RED-2400 Solana DEX benchmark, only 15.8% of rejections were missed opportunities. The method is presented as general-purpose for any filter-based selection system that generates a binary accept/reject decision flow.

## Why it might be useful
PRFS is directly applicable to the `_automation/alpha_hunt/` pipeline: every research idea rejected by the L0/L1/L2 filters in `_automation/feasibility/` represents an untested counterfactual. Implementing a simple version of PRFS—logging rejected hypothesis IDs with their rejection reason and checking against subsequent peer publications or the n_tests ledger—would calibrate whether the L1 topic-relevance or L2 methodology filters are too conservative. This is the companion methodology paper to RED-2400 (id=2605.12151 in this batch); together they provide both the benchmark and the methodology for building a rejection audit trail. The configurable cadence aspect also mirrors how the alpha_hunt `_seen.json` tracks previously seen items, suggesting PRFS could be implemented as an extension to the existing deduplication infrastructure.

## Extracted content
Specific numeric claim: 15.8% of rejections were missed opportunities (false-negative rate on RED-2400). Code at https://github.com/kamat-fin/RED-2400.

## Action proposed
REFERENCE

Solana DEX domain is not directly relevant; the PRFS methodology as applied to the feasibility pipeline would require assembling a ground-truth outcome dataset for past rejections, which is a longer-term audit project.
