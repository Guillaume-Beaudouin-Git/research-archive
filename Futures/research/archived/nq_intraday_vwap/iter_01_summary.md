## Strategy D iter_01: VWAP Mean Reversion NQ Afternoon

*Generated: 2026-05-21  |  n_tests after: 130*

### 1. Headline verdict

**FAIL — INSUFFICIENT SAMPLE** (automated gates show RESEARCH_PASS but N=19 over 3 years is statistically meaningless)

### 2. Variant comparison (full period 2023-01-01 → 2025-12-11)

| Variant | Sharpe HAC | MaxDD ($) | PF | WF% | N | P(EV≤0) | AMTP | corr(C,D) |
|---------|-----------|----------|-----|-----|---|---------|------|-----------|
| 1a | 21.7 | ~$0 | 2.66 | 75% | 19 | 0.071 | 1.000 | -0.017 |
| 1b (z>2.5) | 0.0 | $0 | — | 0% | 0 | 1.000 | 1.000 | — |
| 1c (wider window) | 10.4 | ~$0 | 1.46 | 50% | 25 | 0.276 | 1.000 | -0.025 |
| 1d (touch exit) | 22.3 | ~$0 | 2.78 | 75% | 19 | 0.063 | 1.000 | -0.017 |

### 3. Trade statistics (best variant 1d)

- **N trades over 3 years: 19** (~6 per year — critically low)
- Win rate: 47.4%
- Avg win: $278.68 | Avg loss: $-90.09
- Ann return on $50K: +1.1% | Ann vol: 1.3%
- Exit reasons: TIME 53%, TP 26%, SL 21%

Walk-forward detail (1d):

| Window | OOS P&L | N trades | Verdict |
|--------|---------|----------|---------|
| 2024-01-01→2024-06-30 | +$181 | 3 | positive |
| 2024-07-01→2024-12-31 | -$410 | 4 | negative |
| 2025-01-01→2025-06-30 | +$1,073 | 2 | positive |
| 2025-07-01→2025-11-30 | +$268 | 2 | positive |

### 4. Root cause analysis

**The entry filter is too restrictive.** Three conditions must simultaneously hold:
1. z-score deviation > 2.0 (extreme — 5% tail under normality)
2. 3 consecutive 5-min bars on same side of VWAP
3. Signal window 12:30–15:00 ET

Over 780 sessions × 30 bars/session = 23,400 signal-window bar-slots, only **19 signals** fired. That is a ~0.08% hit rate, equivalent to once every 40 sessions (roughly once per month).

With 19 trades:
- P(EV≤0) = 0.063 — marginally below 10% but AMTP = **1.000** (certain false positive given n_tests=130)
- Each WF window has 2–4 trades — no meaningful statistics
- Sharpe of 21.7 reflects noise: 9 winning days vs 4 losing days, rest zero

**What the TIME exit pattern reveals:** 53% of trades exit at 15:25 without hitting SL or VWAP. This means price did not return to VWAP within the trading window. The mean-reversion force is weaker than assumed — or the deviation is too extreme to revert fully in the afternoon session.

### 5. Gate check (for record)

**RESEARCH_PASS gates:** All pass *nominally* — but AMTP=1.000 invalidates this.
**PROPFIRM_PASS:** P(EV≤0) 0.063 fails the 0.05 gate.

**Effective verdict: FAIL** — 19 trades is the binding constraint. Any Sharpe estimate with N<50 is unreliable.

### 6. Interpretation and decision

**CASE A — Abandon VWAP reversion for NQ:**
NQ (Nasdaq 100) is a momentum-dominated instrument. In the afternoon, VWAP deviations tend to persist (stop-loss flows, momentum continuation) rather than revert. The TIME exit pattern (53%) confirms this: once NQ is significantly away from VWAP in the afternoon, it often stays there. This is the opposite of the mean-reversion hypothesis.

**CASE B — Relax the signal filter to generate adequate sample:**
Removing the 3-consecutive-bar requirement or reducing z_thresh to 1.5 would generate ~100–200 signals — enough for valid statistics. This requires iter_02.

**Decision: SKIP iter_02.** Reason: the 53% TIME exit rate already signals the hypothesis is weak. Even with more trades, the regime (NQ afternoon = momentum continuation, not reversion) is unfavorable. Research capital better spent on:
- Strategy D alternative spec: opening gap fill (09:30–10:30, fade gaps > 0.8%)
- Or: continue Portfolio Phase 2 (daily monitoring infrastructure)

The **CRITICAL positive finding**: corr(C, D) = **-0.017** — near-zero correlation with Strategy C. Any eventual NQ afternoon strategy would be an excellent diversifier for C. Worth revisiting with a different signal mechanism.

### 7. n_tests update

n_tests: 126 → **130** (+4 variants). All 4 FAIL on sample-size grounds.
