# Sharpe Ratio Distribution: When Normal's A No-Go, Why Not SHASHo? [Krzysztof Ozimek]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=cm1HfBmj7K&source=feedburner
**Captured**: 2026-08-17 06:30 UTC
**Filters passed**: L1=[trading_topic, metrics], L2_OK
**Hash**: cf046e179890421bca9ae71025280bdc

## Summary
The author engages with a 2026 treatment by Lopez de Prado et al. of the Sharpe ratio ESTIMATOR's sampling distribution, which is conventionally assumed Normal (centered on the true Sharpe, with a variance term derived from skew/kurtosis corrections). The piece proposes using the SHASHo (sinh-arcsinh) distribution family instead of the Normal approximation, presumably because realized Sharpe estimates from finite, skewed, fat-tailed return series don't actually follow a symmetric bell curve — the SHASHo family can flex its own skew and tail-weight parameters to fit the empirical shape better than a Normal-with-corrected-variance hack.

## Why it might be useful
This is core methodology territory rather than a strategy idea. CLAUDE.md already reports confidence intervals under what is presumably a Normal-approximation assumption — Strategy A's excess-return Sharpe is stated as 0.566 with "IC95 [-0.50, 1.63] — contient zéro" — and if the true sampling distribution of that estimator is meaningfully skewed/fat-tailed (which is plausible for a long-only crypto TSMOM book with known negative-skew crash risk), a Normal CI could be miscalibrated in either direction. It also bears on L58 (placebo baselines must match the unconditional expectation, not just look plausible) and on the DSR machinery (L20, mandatory from N_mod≥2) that CLAUDE.md's Methodology toolkit already leans on — DSR itself typically assumes a specific (often Normal-ish) reference distribution for the Sharpe estimator, so a better-fitting distribution family could tighten or loosen the DSR threshold used across the 321-test ledger.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt beyond the named distribution (SHASHo) and the cited source (Lopez de Prado et al., 2026). Full article needed for the actual density/estimator formulas.

## Action proposed
TEST_LATER — re-deriving Strategy A's IC95 under a SHASHo (or otherwise skew/kurtosis-flexible) fit instead of the Normal approximation is a legitimate 1-3 day methodology task (needs the full paper's parameterization plus a fit against Strategy A's live return series), but it's not blocking: the existing Normal-approximation IC95 already contains zero, so the qualitative conclusion (not yet statistically distinguishable from a null Sharpe) is unlikely to flip either way.
