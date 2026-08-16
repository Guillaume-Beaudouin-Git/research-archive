# Skewness as a Hidden Driver of Anomaly Returns

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=UVZSXy63MN&source=feedburner
**Captured**: 2026-08-10 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 0f4c4d0a4ce9e649e6f54eba1c97bafe

## Summary
Alpha Architect summarizes behavioral-finance literature showing that investors systematically dislike negative skewness (rare severe losses) and pay a premium for positive skewness (rare large gains), and frames this preference as a candidate explanation for some portion of cross-sectional anomaly returns rather than the anomalies being pure risk-based or purely behavioral mispricing. The excerpt stops before naming which specific anomalies are attributed to skew preference or presenting any empirical test statistics.

## Why it might be useful
Skewness measurement is already a first-class deployed-strategy diagnostic in this project's own lessons: L57 requires reporting the skew and single-session tail of any sleeve run at fixed lot size (a lot-constrained micro-future book flipped skew from +0.99 to -0.49 versus vol-targeted sizing), and L39 requires reporting both daily and monthly skew separately since they can carry opposite signs (daily binds the FTMO barrier, monthly binds the personal book). A literature-level mechanism connecting skew preference to anomaly pricing would strengthen the theoretical grounding for why L57/L39 matter operationally, and is also relevant to Strategy C (NQ ORB, currently sub-PROPFIRM_PASS at Sharpe 0.41) whose binary TP/SL structure (L11b) directly manufactures a skewed payoff — this piece could inform whether that manufactured skew is itself priced/exploitable or just a cost-model artifact.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — a behavioral-finance literature summary with no data, code, or specific test; relevant as theoretical grounding for the project's existing skew-reporting lessons (L39, L57) but not directly testable from this excerpt.
