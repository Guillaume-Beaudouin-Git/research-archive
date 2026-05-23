# SPX VRP Angle C — Post-Mortem
*Date: 2026-05-23 | Verdict: Phase 1 FAIL → ARCHIVE*
*n_tests: global ~320 → 321 (+1)*

---

## Summary

Short ATM straddle conditioned on VIX_z > 1.0 fails the IC gate. Within the elevated-VIX
regime, VIX_z has **zero additional predictive power** over variance swap P&L (IC = −0.009,
t_HAC = −0.14 vs gate > 3.5). The 2020-2025 sub-period has negative mean outcome (−70.78
variance pts) due to COVID and 2022 inflation — exactly the regimes when the trigger fires.

| Gate | Threshold | Value | Result |
|------|-----------|-------|--------|
| IC direction | > 0 | −0.009 | **FAIL** |
| HAC(30) t-stat | > 3.5 | −0.144 | **FAIL** |
| Sub-period stability | all > 0 | IC(2020-25) = −0.002 | **FAIL** |
| VRP magnitude pre-flight | ≥ 2.0 vol pts | 3.42 | PASS |
| Events/yr | ≥ 30 | 33.8 | PASS |

---

## Root Cause

Conditioning on VIX_z > 1.0 selects exactly the periods when realized vol can exceed
implied vol (COVID: VIX 60 → RV 100%+; 2022: sustained VIX 25–35 with RV above VIX).
Selection paradox: the threshold picks the danger zone, not the profit zone.

The static VRP exists (unconditional IC = +0.152, t = 3.671 across all states) but
conditioning on z > 1.0 destroys it. This parallels the VIX term-carry finding: the
premium is a static factor, not a timeable signal.

---

## Side Finding (NOT tested here — new hypothesis)

Unconditional IC = +0.152, t = 3.671. Using VIX_z as a **continuous position scaler**
rather than a binary threshold would be a different hypothesis. Requires new n_tests budget
and explicit chat GO. Do not re-test under the same mission scope.

---

## Files

- `phase0_bootstrap.md` — data availability, signal design, cost model
- `phase1/phase1_ic_results.md` — full IC tables, sub-period breakdown, root cause analysis
- `phase1/phase1_postmortem_diagnostic.md` — unconditional IC anatomy, regime diagnostics
- `phase1/scripts/ic_test.py` — reproducible IC computation
- `phase1/data/` — cached VIX + SPX daily (2000–2026, from Yahoo Finance v8)

---

## Lesson Reference

Generalizes Lesson from VIX term carry (5b): timing the static VRP via threshold doesn't
work. The premium is harvested unconditionally at scale, not conditionally on elevated
implied vol.
