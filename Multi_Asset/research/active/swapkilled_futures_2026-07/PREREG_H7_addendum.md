# PRE-REG ADDENDUM — H7 Martingale & Grid (sizing-overlay stress test)

**Date frozen:** 2026-07-15, before any H7 result. **Modified evaluation** (Sharpe is inadmissible here).

## H7 — Do martingale / grid sizing overlays create deployable edge on a €12k account?

- **Null hypothesis (prior):** martingale (double-after-loss) and grid (accumulate against move) are
  **position-sizing overlays, not alpha**. Theory says E[return] is set by the underlying signal, not the
  sizing rule; the overlays only reshape the distribution into **negative-skew / fat-left-tail** (many
  small wins, rare ruin). In-sample Sharpe is therefore an ARTIFACT (smooth up-curve = tail not yet
  realized). This is the exact profile the session gate exists to reject.
- **Why test anyway:** the tail must be *measured*, not asserted. A bounded version may reduce to a
  legitimate capped-mean-reversion strategy — worth distinguishing from the naive (ruin-certain) version.
- **Evaluation metric (frozen — Sharpe explicitly NOT used as pass criterion):**
  1. **Monte Carlo probability of ruin** — P(equity hits −50% DD budget, or −100%) over 1yr and 3yr,
     via block-bootstrap of the real underlying (Politis-Romano, not iid — trends must survive).
  2. **True geometric growth** E[g] after real cost — must be > 0 to deploy.
  3. **Max-DD distribution** (5th/50th/95th pct) from the MC.
  4. Report in-sample Sharpe ONLY to demonstrate its divergence from (1)-(3) (the artifact).
- **Designs (frozen):**
  - **Grid:** on a real trend-capable underlying (gold GC=F daily 2005-2026, + EURUSD deep_history).
    Fixed spacing g, fixed lot/level; buy on −g, take-profit on +g; two variants: (a) UNBOUNDED inventory,
    (b) CAPPED at L levels then flat. Track cash + inventory MtM.
  - **Martingale:** base bet = long-after-down-day on an index (~50% win, near-fair). Bet = base·2^(losses),
    reset on win; variants: K∈{unbounded, cap 3, cap 5}. Account €12k, base = 1% risk.
- **Kill / promote rule (frozen):**
  - PROMOTE only if MC **P(ruin over 3yr) < 20%** AND **E[g] > 0** after cost. Else CLASSIFY as
    artifact (smooth-Sharpe / ruin-tail), NOT deployable.
  - Explicitly test whether the CAPPED versions ≡ a plain mean-reversion strategy stripped of the overlay
    (compare to flat-size mean-reversion): if capped-overlay does not beat flat-size, the overlay adds
    nothing (only tail risk).
- **N:** 1 family test (overlay class).
