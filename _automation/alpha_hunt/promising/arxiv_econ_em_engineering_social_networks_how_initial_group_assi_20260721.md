# Engineering Social Networks: How Group Assignment Shapes Student Ties

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.17926v1
**Captured**: 2026-07-21 03:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 968cb42ed9190303c2550c3f9a3adcd6

## Summary
The paper exploits random assignment of first-year university students to classrooms and smaller social groups to study how friendship ties form, using phone-call, text, co-location, and social-media data. Rather than modeling each potential link independently (the standard dyadic approach), the authors fit a subgraph-based model that explicitly accounts for triadic closure — the tendency for a friend of a friend to also become a friend. For the smaller social groups, they find that almost the entire effect of group assignment on the resulting network runs through this triadic-closure channel: assignment doesn't just create direct ties, it seeds indirect densification through third parties. The authors argue that dyadic-only models ignoring this higher-order dependence yield biased, misleading predictions about how group-assignment policies shape network outcomes.

## Why it might be useful

Not a trading paper, but its econometric point is a direct methodology parallel for this book: treating correlated, higher-order-dependent observations as if they were independent (dyadic-only) produces biased inference — structurally the same failure mode the project's hard rule "block bootstrap (Politis-Romano) — iid forbidden when trade clusters exist" is designed to prevent. The paper's fix is to model the dependency structure explicitly (a subgraph/triadic model) rather than just bootstrap around it, which is a useful cross-check whenever a current HAC-lag-6 / block-bootstrap setup is revisited: if a strategy's return series has a "triadic" analogue — e.g. correlated position overlap across Strategy A/B/C sharing crypto beta exposure (L11) — a purely pairwise dependency correction could understate the true correction needed and overstate significance. No dataset or signal here; filed as background reading on why naive independence assumptions specifically break down once third-order structure is present, not an action item.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE
