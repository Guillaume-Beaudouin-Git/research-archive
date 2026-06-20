# MadEvolve: LLM-Driven Evolutionary Optimization of Bitcoin Trading Strategies

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.23007
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 2a04cfbff1cf9337cf59d68aca32e2b2

## Summary
MadEvolve adapts the DeepMind Alpha-Evolve framework (evolutionary algorithm guided by LLM mutation proposals) to algorithmic trading, demonstrated on Bitcoin trading strategy optimization. The LLM proposes mutations to trading rule code, an evolutionary selector retains the best performers on backtests, and the cycle repeats across generations. On the authors' simulation environment, MadEvolve achieves statistically significant improvements over baseline trading algorithms. The approach treats strategy parameters and logic as code strings that LLMs can mutate, rather than traditional hyperparameter search.

## Why it might be useful
This paper is directly relevant to the `_automation/` infrastructure. The current alpha_hunt pipeline stages candidate strategies, but the actual strategy modification process is manual. MadEvolve's LLM-mutation framework could be integrated into the feasibility pipeline (`_automation/feasibility/`) as a code-level optimizer for strategies that pass Level A (IC gate) but fail Level B (WF). However, the 3-modifications-per-strategy hard rule in CLAUDE.md critically constrains this: automated LLM mutation that runs unchecked would blow through the modification budget in one run. Any adaptation must count each LLM-proposed mutation as a strategy modification for DSR purposes. The paper's approach also risks overfitting within backtests (the evolutionary pressure selects on in-sample performance), which is exactly the issue that AMTP and walk-forward validation guard against.

## Extracted content
"MadEvolve, a general-purpose algorithm optimization framework inspired by DeepMind's Alpha-Evolve." Applied to Bitcoin trading. "On our simulation and backtesting setup, we achieve significant improvements over baseline trading algorithms." The framework mutates algorithm code strings via LLM proposals. No specific Sharpe or WF statistics given in abstract.

## Action proposed
REFERENCE

Interesting infrastructure concept but blocked by the 3-modification hard rule and AMTP requirements. If adapted, each LLM mutation must count as a modification and trigger DSR recalculation. Cross-reference with L20 (DSR mandatory for n_mod ≥ 2). Could be useful for the _automation/synthesis/ pipeline as a controlled experiment generator, but not as a live strategy optimizer.
