# Honey I Shrunk the Weights (Instead of the Inputs!)

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=OLNyuCIRbq&source=feedburner
**Captured**: 2026-06-18 05:30 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 1cb8ee3b7f6490dd92f71b49ba6a9bae

## Summary
A practitioner's candid post-mortem on applying weight-shrinkage regularization directly to portfolio allocations rather than to the signal inputs. The author — fifth in a rapid series — leads with the disclaimer that the approach does not produce usable results, and frames the post as an honest negative result rather than a cherry-picked backtest showcase. The core question is whether shrinking portfolio weights (e.g., ridge-type penalty on final allocations) achieves something different from shrinking the underlying factors or covariance estimates. The answer appears to be: not usefully so.

## Why it might be useful
The negative-result framing is directly applicable to the A+B portfolio construction question. The current book-level ERC 50/50 allocation between Strategy A (TSMOM, paused) and Strategy B (delta-neutral carry) was derived analytically with SR_A=1.33, SR_B=2.0 proxy, ρ=0.039 — a setting where weight-shrinkage would barely matter given the near-zero correlation and well-separated Sharpes. However, once Strategy D enters the portfolio and the correlation matrix becomes non-trivial, weight regularization will matter. This post documents a failure mode to avoid: applying shrinkage to the output weights without first ensuring signal-level normalization is sound. The CLAUDE.md methodology already requires vol targeting and excess returns before portfolio aggregation — which is the correct order of operations. This confirms the existing approach and warns against shortcutting to weight-layer regularization. Read the full article before considering any ERC-weight modifications for a 3+ strategy book.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE
