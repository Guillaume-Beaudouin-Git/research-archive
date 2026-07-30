# PRE-REG ADDENDUM — H8 Hard-capped grid under short-horizon ruin constraint

**Date frozen:** 2026-07-15, before any H8 result. Metric = P(ruin) + E[g] (Sharpe = artifact, reported
only to show divergence).

## H8 — When does a hard-capped grid have positive EV within a <30% / ≤1yr ruin budget?

- **Question:** user horizon 6-12 months, ruin (−50% DD) must stay < 30%. Literature (arXiv 2506.11921):
  grid EV = 0 on a random walk, positive only with genuine mean-reversion (> n²/8−n/4 oscillations). Test
  this directly under the user's constraint.
- **Design (frozen):**
  - Grid: fixed log-spacing g, hard inventory cap L levels, lot notional = leverage·acct0/L (so full
    inventory = leverage·acct0). Buy one lot per down-step, take-profit one lot per up-step. Fee 5 bps RT.
    acct0 = €12,000. Ruin = equity ≤ 50% acct0.
  - Processes: **(a) GBM zero-drift** (random walk) at vol ∈ {15%, 40%, 80%} ann; **(b) Ornstein-Uhlenbeck**
    on log-price, half-life ∈ {5, 20, 60} d, same vols. OU = genuine mean-reversion.
  - Horizons: 126 d (6mo) and 252 d (1yr). npath ≥ 2000, block/param MC.
  - Grid params swept: g ∈ {1%, 2%}, L ∈ {8, 15}, leverage ∈ {1×, 2×}.
- **Promote rule (frozen):** a (process, grid) config is "usable within constraint" iff **P(ruin ≤1yr) <
  30% AND E[final] > acct0 (net fee)**. Report the config frontier.
- **Decisive contrasts (pre-registered):**
  - (C1) On GBM (random walk), even ruin-compliant configs must show **E[final] ≈ acct0** → confirms
    zero EV (the trap: bounded ruin ≠ profit).
  - (C2) On OU, E[final] > acct0 only when mean-reversion is strong relative to g/vol → quantify the
    half-life/vol boundary where grid EV turns positive AND ruin stays < 30%.
  - (C3) Report Sharpe of a typical profitable path to show it overstates (smooth-then-tail).
- **Deployment note:** a positive-EV OU config is only actionable if a REAL underlying with that
  mean-reversion exists (cointegrated spread / range regime) — the repo's pairs work (0/12 OOS coint)
  is the binding reality check. H8 characterizes the math; sourcing the OU underlying is the open problem.
- **N:** 1 family test (grid-MC characterization).
