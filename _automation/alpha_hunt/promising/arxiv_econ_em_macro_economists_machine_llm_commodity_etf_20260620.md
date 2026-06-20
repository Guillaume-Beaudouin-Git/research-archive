# Multi-Agent LLM Framework for Macro-Driven Commodity ETF Allocation

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2606.08283
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[metrics, methodology], L2_OK
**Hash**: 88bd925e400eca7038523f67bd645c77

## Summary
The paper tests whether LLM agents improve commodity ETF portfolio construction when information is held fixed across strategies. Four agents receive identical FRED macro z-scores: a Hawkish Agent (inflation/tightening prior), a Dovish Agent (growth/easing prior), a Debate Agent, and a deterministic z-score Rule Agent. All route signals through the same portfolio engine. Across 124 weekly rebalancing dates spanning the 2023 U.S. rate peak and the 2024 easing cycle, the deterministic rule agent matches or outperforms all LLM variants on Sharpe, suggesting that macro z-scores contain the relevant signal and LLM interpretation adds noise rather than value in this information-constrained setting.

## Why it might be useful
The Commodities XS research (`Commodities/research/active/xs_basis_tsmom/`) is testing TSMOM + BASIS signals across 24 continuous futures contracts. The macro z-score approach here is directly complementary: if FRED macro data (already available via FRED DTB3 + interbank rates) is fed into a regime overlay on the TSMOM signal, this paper's finding ("rule agent wins") suggests a simple macro-conditioned signal threshold beats LLM wrapper. More importantly, the paper's experimental design (124 rebalances, fixed information set) is a clean template for Phase B testing in the Commodities XS pipeline. The finding also aligns with L15 (regime overlays on strong signals add little).

## Extracted content
The authors state: "across 124 weekly rebalancing dates spanning the 2023 U.S. rate peak and the 2024 easing cycle, the deterministic z-score Rule Agent each receive identical FRED macro z-scores." Finding: "deterministic z-score Rule Agent matches or outperforms all LLM variants." The paper uses commodity-related ETFs (specific tickers not given in abstract).

## Action proposed
TEST_LATER

After Commodities XS Phase A (data fetch + roll validation) completes, use this paper's macro z-score conditioning as Phase B enhancement. Test: do FRED macro z-scores (already available, see CLAUDE.md Data sources) improve Sharpe on the TSMOM + BASIS combo? Use the "rule agent only" design — no LLM wrapper needed. ~1 day to integrate FRED macro z-scores into the existing `xs_basis_tsmom/` pipeline.
