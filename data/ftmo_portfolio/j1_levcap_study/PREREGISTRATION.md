# PRE-REGISTRATION — J1 régime-aware leverage cap (FROZEN before results)

Study dir: `data/ftmo_portfolio/j1_levcap_study/`. Worktree `claude/j1-leverage-cap` off
local HEAD f2cb555. Baseline = v2.2 frozen stack (commit 605f4a4, SHAs in
`../v23_j1_study/baseline_pin.json`). Engine = clone of `j1_engine.py` (EQUIV 462/462) with ONE
added hook (`cfg["j1_lev_cap"]`), exactly mirroring the existing `j1_band` hook precedent.

## Motivation (from Q1, measured before this pre-reg)
J1 sizing is `notional_J1 = w_jpy · scale · eq`, `w_jpy ∈ [0,1.5]`, `scale ≈ vm(14) · taper · glide · pace`.
`w_jpy` saturates at 1.5 whenever `rvj ≤ 6.67%`. Measured procyclicality (active J1 days):
- rvj P0-20 (compression): realized leverage median **21.1×** (max 29.1×), w_jpy 100% at 1.5 cap.
- rvj P80-100 (high vol): median **11.7×** (max 16.0×).
- 65% of active J1 days >15×; 30% >20×.
- **HONEST CAVEAT (Q1):** the worst in-sample weekend gaps were NOT concentrated in compression:
  −$2,822 (Grexit 2015-06-29, rvpct 0.38), −$871 (NK missile 2017, rvpct 0.41), −$633 (SVB 2023,
  rvpct 0.95). They were high-NOTIONAL events across vol regimes → a **regime-agnostic hard
  leverage cap is expected to dominate a compression-only cap on tail reduction.** This is why
  the variant family is weighted toward hard caps.

## Hypothesis
A leverage cap reduces J1's left-tail/gap exposure. Open question (the central trade-off):
does it do so WITHOUT destroying the +7.6 pts p(pass) / +$88 EV diversification value that the
v2.3 ablation proved J1 contributes? J1's value is its decorrelated variance that paces the
funnel; if that variance IS the tail, the cap cannot separate them.

## Pre-registered variants (≤4, FROZEN)
Baseline: full book, `j1_lev_cap=0` (off) — must reproduce pooled 87.01 / 462 cohorts (EQUIV gate).

- **V1 — LCAP8**: `j1_lev_cap = 8.0` (cap `|notional_J1|/eq ≤ 8×`, applied at 22:05 target, pre-margin-cap).
- **V2 — LCAP10**: `j1_lev_cap = 10.0`.
- **V3 — LCAP12**: `j1_lev_cap = 12.0`.
- **V4 — COMPRESS**: root-cause comparator. `w_jpy ×= 0.5` when `rvj` is in the bottom-20th
  percentile of its TRAILING 504-day (2y) distribution, lagged 1 day (causal, T-1; no look-ahead).
  Implemented as a precomputed multiplier on `WT[:,1]` (arms-style, like A_raw), NOT an engine hook.

Hook placement: cap applied to `tgt[1]` immediately after it is computed at s==4 (22:05), AFTER
recording `j1_tgt_raw`, BEFORE the `j1_band` hold-logic and BEFORE the proportional margin cap.
Sign-preserving: `tgt[1] = sign(tgt[1]) · min(|tgt[1]|, Lc·eq)`.

## Metrics (per arm)
- **Triplet**: `p_pooled` (challenge), `attempts`, `EV` (VAL=$1,422, FEE=$96 — v2.3 convention).
- **Left tail (PRIMARY)**: worst single-day J1 P&L; worst weekend gap (`gap_pnl_jpy` min);
  J1-attributable gap-bust count & share; book worst day.
- **Leverage**: realized J1 leverage median / p95 / max; frac >15×, >20× (confirms cap binds).
- **Diversification preservation**: book vol/day; J1 risk share; J1 vs rest-of-book corr.
- **Paired deltas vs baseline**: Δp, ΔEV with 90% paired circular block-bootstrap CI
  (blocks=10, draws=3000, seed=23 — identical to v2.3 `aggregate.py`).

## Decision rule (FROZEN, ASYMMETRIC — we trade EV for tail, but not unlimited)
A variant is **ADOPTED as the recommended systematic rule** iff BOTH hold:
1. **TAIL improves materially** (point estimates): worst weekend gap reduced AND J1 gap-bust
   share reduced vs baseline.
2. **p/EV not significantly destroyed**: Δp 90% CI is NOT entirely below **−2.0 pts**, AND
   ΔEV 90% CI is NOT entirely below **−$40**. (We tolerate a modest give-up; we reject any cap
   that CI-significantly guts the +7.6 pt / +$88 diversification value.)
Among variants passing 1+2, choose the one with the **lowest leverage cap** (max tail reduction)
that still passes (2).
**If NO variant passes (2)** — every cap that cuts the tail also CI-sig-destroys p/EV — the
honest verdict is: *the cap cannot separate the tail from the diversification; J1's decorrelated
variance IS the gap exposure.* Report that; do not adopt by default.

## Q4 (decision-facing, reported regardless of verdict)
With the recommended cap (or, if none adopted, with LCAP10 as illustration): what would today's
J1 leverage/notional be in the current regime (vs 18× / $180k)? Is a 3-5 yen intervention loss
under the capped notional tolerable vs the $500 daily / $1,000 floor? Explicitly separate
backtest-derived (retrospective) from prospective risk judgment (the coordinated-intervention
gap is out-of-sample; the engine's worst gap ≈ 2.5 yen understates it).

## Trial accounting
+5 arms (baseline-equiv + V1..V4) to the v2-program ledger. 1 fixed decision rule, 0 post-hoc
arms, thresholds frozen above. Author≠auditor: if any variant is ADOPTED, an independent audit
sub-agent re-checks EQUIV, the hook, and the paired deltas before the recommendation stands.

FROZEN. Any change after the first results run invalidates this pre-registration.
