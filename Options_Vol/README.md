# Options_Vol — SPX VRP, archived

One study: `research/archived/vrp_spx_angle_c/` — short ATM straddle conditioned on VIX z-score.
Failed the Phase 1 IC gate: conditioning on `VIX_z > 1.0` adds zero predictive power over variance
swap P&L once already in an elevated-VIX regime (IC = -0.009, t_HAC = -0.14 against a 3.5 gate),
and the 2020-2025 sub-period is negative in the regimes the trigger actually fires in (COVID, 2022
inflation). See `POSTMORTEM.md` and `phase1/phase1_postmortem_diagnostic.md` for the full
diagnostic before proposing a related VRP conditioning hypothesis.

A separate, more recent VRP options line (SPY iron condor, real option chains) was falsified and is
tracked under `research_artifacts/` and the personal-book research notes (`2026-07`) — retail VRP
in this repo is cost-dead across both the CFD-adjacent options-vol angle here and the SPY chain
test. Check both before reopening.
