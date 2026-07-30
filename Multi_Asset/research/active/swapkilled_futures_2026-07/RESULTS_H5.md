# RESULTS H5 — Pre-FOMC drift (equity) — FALSIFIED

**Verdict: FALSIFIED (fails #1 beat-benchmark, K4 placebo, K5 tail).** Data: ^GSPC/^NDX 2003-2026,
FOMC dates 2004-2026 (182). Signal: long index day before announcement.

- Sleeve SR **0.20** (S&P) / 0.23 (NDX) — **< B&H 0.57 / 0.76** → beta slice, fails #1 (K2).
- Placebo: pre-FOMC day 12.0 bps vs random p95 17.8 bps → **does NOT exceed** (p=0.190). Not special.
- **Kurtosis 728, skew +12.9** → the apparent drift is 1-2 outlier FOMC days, not a stable edge. DSR N=4 = 0.
- Regime: 2004-2014 SR −0.05 (absent), 2015-2026 SR 0.54 but t_HAC only 1.75 (<2.5) and outlier-driven.

**Lesson confirmed:** concentration-beats-beta works only on **low-baseline-drift underlyings** (H3 bonds,
H4 commodities). Equity's strong baseline drift means an event-concentrated equity sleeve is just a weak
beta slice — same failure mode as H1 overnight. Consistent with the post-2015 decay literature and L42.
No promote. Proceeding to H6 (FX month-end flow) — FX is near-zero-drift → eligible for the pattern.
