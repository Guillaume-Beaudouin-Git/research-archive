# CausalAlpha: Real-Time Geopolitical Risk Index from OSINT for Causal Discovery in Financial Markets

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.07049v1
**Captured**: 2026-06-08 06:05 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: e440c604a5eddd3fb728b1051eddb0c2

## Summary

The paper introduces a framework that ingests Telegram OSINT channels in real time, applies NLP to score five geopolitical risk (GPR) sub-categories (political instability, energy media, conflict, etc.), and then uses the Peter-Clark (PC) algorithm to recover a directed acyclic graph (DAG) of causal dependencies between those GPR scores and financial variables (commodity prices, equity indices, credit spreads). The key methodological distinction versus Granger causality is that PC removes spurious edges by conditioning on third variables, yielding directed rather than merely predictive relationships. The two most robust causal paths found across all four DAG specs and three significance levels are: (i) political instability and energy coverage → conflict coverage (conflict is the narrative sink), and (ii) at α=0.05, conflict coverage → ΔXLE (energy sector equities). Critically, a structural VAR on the full macro panel shows that the dynamic transmission from these NLP signals to financial prices is statistically weak at daily frequency — the signals propagate mainly within the media narrative layer rather than into market prices.

## Why it might be useful

The SVAR finding — that geopolitical NLP signals are weak at daily frequency — is direct empirical validation of our decision to archive L17 (F&G velocity as momentum proxy) and L18 (Wikipedia attention velocity at zero IC). Both those paths were closed partly on the argument that news-derived signals lack transmission power at the frequency we trade; this paper provides a rigorous causal-discovery confirmation of exactly that hypothesis. For the active Commodities XS (xs_basis_tsmom) research, the one robust causal edge found — conflict coverage → ΔXLE — is worth noting: if GPR surges above a threshold, it would flag a potential regime for energy contracts (CL=F, NG). However, L15 establishes that regime overlays deliver only ~1.7%/yr lift on strategies with Sharpe > 1.0, so this path is low-priority unless our commodity Sharpe lands below RESEARCH_PASS threshold. The more actionable takeaway is methodological: the paper demonstrates block-bootstrap validated PC/DAG as a superior alternative to Granger causality for separating direct causal edges from conditioning artifacts. If we ever test a macro overlay on any strategy (regime filter for Strategy A TSMOM, or on the ZN Baltussen bond momentum research), replacing Granger causality tests with PC/DAG would reduce false-positive causal edges — concretely, this means using `causallearn` or `pcalg` in Python rather than `statsmodels.tsa.stattools.grangercausalitytests`.

## Extracted content

The author claims:
- "Two findings emerge as globally robust across all DAG specifications at alpha = 0.10: political instability and energy media coverage independently and causally precede conflict coverage."
- "At the strictest significance level (alpha = 0.05), conflict coverage causally precedes energy sector equity returns (delta XLE)."
- "A Structural VAR on the core macro panel confirms that dynamic transmission from geopolitical NLP signals to financial market prices is statistically weak at daily frequency."
- 500 block-bootstrap resamples used for DAG significance testing — consistent with Politis-Romano methodology.
- Framework is deployed on Google Cloud Run (production, real-time) — code is open-source.

No Python code or formulas in the excerpt. Full article and GitHub repo needed to extract the DAG estimation implementation.

## Action proposed

REFERENCE

The main result is effectively negative for signal trading (weak daily-frequency transmission confirmed by SVAR), which aligns with our existing L15/L17/L18 conclusions and does not open a new trading path. The causal discovery methodology (PC/DAG via `causallearn`) is a useful future tool for regime-overlay validation, but there is no direct actionable test today: commodity research (xs_basis_tsmom) is still in Phase A (data fetch not complete), and adding a GPR overlay on top of an unvalidated base signal would violate the 3-modifications budget constraint. File as methodology reference; revisit if xs_basis_tsmom passes RESEARCH_PASS and a regime filter is being evaluated.
