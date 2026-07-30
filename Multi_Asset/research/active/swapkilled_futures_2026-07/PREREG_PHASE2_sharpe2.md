# PRE-REG — Phase 2: push the book toward Sharpe ≥ 2 (ideally 2.5)

**Date frozen:** 2026-07-15, before any Phase-2 result. Anti-overfit guards frozen FIRST because chasing
a high Sharpe is the maximum-overfit-risk activity (the roll-audit just cut 1.51→1.02).

## The governing math (no illusions)
Portfolio Sharpe ≈ s̄·√(N / (1+(N−1)ρ̄)). To reach 2.5 from sleeves of s̄≈0.7, ρ̄≈0.1 needs **N≈13
independent sleeves**; at ρ̄=0 needs N≈13. Levers, in order of honesty:
1. **Breadth** — more genuinely-decorrelated gate-passed sleeves (each OOS + placebo + roll-clean).
2. **Regime classifier** — raise each sleeve's Sharpe by trading only in its favorable regime (must be
   OOS-validated, ≤2 params, no per-sleeve tuning).
3. **Robust weights** — risk-parity/ERC only (NO mean-variance optimization — it overfits ρ̄).
4. **Negative-correlation hedge** — a sleeve with ρ<0 to the book lifts the ratio more than its own Sharpe.

## Anti-overfit guards (frozen, non-negotiable)
- Every sleeve: TRAIN/OOS split; report OOS Sharpe only. Placebo where selection is involved.
- Regime classifier: ONE global spec (same params all sleeves); OOS-validated; report Sharpe WITH vs
  WITHOUT filter — keep only if OOS-improving on held-out data, not in-sample.
- **DSR on the FINAL book Sharpe at honest N** (all sleeves+filters tried = trials). Report it.
- Roll-clean data for commodity sleeves (deep_history), per the L5 lesson.
- **Report the honest ceiling even if < 2.5.** A fabricated 2.5 is worse than an honest 1.6. The number
  must survive the same scrutiny that killed H4.
- Crisis-correlation stress: report book DD assuming ρ→1 in a stress, not just in-sample DD.

## Plan
1. Broaden: split the 4 OOS-stationary spreads into separate sleeves + H3 + add rates-carry, vol-carry,
   more calendar-flow sleeves. Measure full corr matrix + risk-parity Sharpe (breadth ceiling).
2. Add the regime classifier (Kaufman efficiency-ratio / mean-reversion regime) to the spread grids
   (operationalizes the H8 kill-switch). Measure OOS Sharpe lift.
3. Iterate toward N sleeves needed; stop when DSR-deflated OOS book Sharpe plateaus. Report where it lands.

**Success = highest HONEST DSR-deflated OOS book Sharpe. Target 2.5; report the real number.**
