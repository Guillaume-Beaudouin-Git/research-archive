# UFC — Ultimate Fitting Championships: Clustering Trading Rule Combinations

**Source**: quantocracy (via Investment Idiocy)
**URL**: https://quantocracy.com/redirect.php?key=v3u5RPmnz3&source=feedburner
**Captured**: 2026-06-10 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 32dbb08d10acf1c4b5c0ce59d2113062

## Summary
This is part of a multi-post series from Investment Idiocy on parameter fitting and overfitting in systematic strategies. The first post established a method for clustering combinations of trading rules; this second post extends the framework in a "mega-sized research project on fitting." The competitive "UFC" framing is a structured comparison of fitting methodologies evaluated against one another, likely including walk-forward cross-validation, anchored walk-forward, and parameter-space clustering. The implied thesis is that different fitting approaches have meaningfully different overfitting risk profiles, and that the right choice depends on the strategy's parameter space geometry.

## Why it might be useful
Directly applicable to the D3+D5 portfolio problem (`Futures/research/active/strategy_d/`): D3 has n_test=156 and D5 has n_test=158, both individually failed (Sharpe=-1.08/-1.32), and their portfolio combination is now under study. With n_tests in the hundreds, the AMTP penalty is substantial and the DSR correction (Bailey-LdP, L20) is mandatory before citing any positive result. If this article's clustering methodology can group the D3/D5 parameter combinations by structural similarity before walk-forward, it reduces the effective n_trials in the DSR formula, which could meaningfully change the gate outcome. Concrete action: identify the specific clustering metric used (parameter-space distance vs. out-of-sample return correlation) and assess whether it can be applied to the D3/D5 hypothesis grid in `hypotheses_preregistered.md` before the next modification budget is spent.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — methodology background directly relevant to D3+D5 multiple-testing problem, but requires reading the full series (posts 1 and 2) before drawing actionable conclusions. Useful context before consuming any of the 3-modification budget on D3+D5.
