# PRE-REGISTRATION (frozen before results) — Intraday momentum / continuation, FTMO universe

**Date frozen:** 2026-08-25. **Isolation:** dedicated worktree
`<HOME>/Desktop/Algo_claude_mom`, branch `claude/momentum-intraday`, off
`origin/main`. No git write ops outside this branch. Writes confined to this folder. Local
gitignored caches (`data/deep_history_utc/`) read by **absolute path** from the main working dir,
read-only, since a fresh worktree does not carry them.

## 0. Why this study, and the decisive question

The sister family (intraday mean-reversion) is closed: 1,526 cells, zero survivors, invariant
across instrument, conditioner and universe extension (`mr_univers_complet_2026-08/RAPPORT.md`).
Its own literature pass named intraday **momentum** (Gao-Han-Li-Zhou: first-half-hour predicts
last-half-hour) as the one adjacent, un-swept mechanism — explicitly flagged, not folded into the
MR kill (`mr_univers_complet_2026-08/RAPPORT.md` §V5). `_meta/lessons_registry.md` L33b already
put ONE momentum cell (Gao time-of-day) at gross≈0 → net −3bps (t −6) — a mechanical kill, but a
single construction, not a swept family.

**The decisive tension**: the ORB sleeve armed in FTMO production (`FU_ORB_RISK=0.0025`, account
<ACCOUNT_ID>) is intraday momentum by construction (opening-range breakout) and its own ledger
(`PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet`, N=4013, NQ futures,
2010-2026) is gross two-sided **positive**: long HAC-t ≈ +2.7 (n=2156), short HAC-t ≈ +1.3
(n=1857) — recomputed in this study with the repo's own `engine.stats.hac_tstat(lags=6)` for a
consistent yardstick (§7). This study's job is to place that ledger inside the distribution this
grid produces, on the FTMO **CFD** universe (the ORB ledger is NQ **futures**, out of scope per
constraint), and answer: is the family alive, or is the ORB a lucky draw from a dead family?

## 1. Universe (FTMO-tradable, `data/deep_history_utc`, true-UTC, verified by DST peak-hour
shift this session: US100 peak volume hour 15 UTC in January vs 14 UTC in July — the expected
1-hour EST/EDT shift for a fixed 9:30 ET cash open; confirms true-UTC labeling, no fix needed)

**Core 9** (full grid): US100, US500, US30, GER40 (indices) · EURUSD, GBPUSD, USDJPY (FX majors)
· XAUUSD, XAGUSD (metals). **Extension 7** (canonical-construction only, per mandate's
width-over-depth rule and the sister study's own precedent for universe-extension blocks):
EURJPY, EURGBP, AUDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD.

Session windows (UTC), identical to `mr_intraday_grille_2026-08/dataload.py` (kept identical so
any contrast is about the mechanism, not a new session-design axis): indices 13:30-20:00 (26
bars/day @15min, verified mode), FX 07:00-16:00 (36 bars/day), metals 12:00-20:00 (32 bars/day).
No futures (out of scope, per mandate constraint 1).

Bar size: **15-min**, same convention as the sister family — keeps the two families comparable
and keeps the cell count tractable at this width. Sub-5-min excluded by construction (L63 —
bid-ask rebound floor, `gap_pattern_rehab` §L60 lesson).

## 2. Costs — native, measured, GROSS-FIRST (mandate constraint 5)

Reused verbatim from `mr_intraday_grille_2026-08/dataload.py::COST_RT_BPS` (measured 2026-08-19,
provenance logged there) + `mr_univers_complet_2026-08` for the 7 crosses:

| sym | bps RT | sym | bps RT | sym | bps RT |
|---|--:|---|--:|---|--:|
| US100 | 1.045 | EURUSD | 0.313 | XAUUSD | 2.037 |
| GER40 | 1.017 | GBPUSD | 0.338 | XAGUSD | 7.05 |
| US500 | 1.07  | USDJPY | 0.379 | EURJPY | 0.457 |
| US30  | 0.86  | EURGBP | 0.608 | AUDJPY | 0.654 |
| AUDUSD| 0.602 | USDCAD | 0.427 | USDCHF | 0.651 |
| NZDUSD| 0.874 | | | | |

**Every cell is run gross (cost=0) first.** Net cost is only charged to cells with
`gross_bps_per_trade > 0` (mandate constraint 5) — cost-negative cells are reported gross-only,
net left NaN with a note, never silently costed. Gate L33b, **recalibrated to ≈1.4bps gross/trade**
(not the stale >3bps, which was calibrated on the wrong, 2.1×-too-expensive index cost table) is
reported per cell as a pass/fail flag, not used to skip cells.

## 3. Volume — declared invalid for indices/metals, measured this session (mandate constraint 7)

Checked directly this session: 15-min `tick_volume==0` fraction inside the liquid session — US100
55%, XAUUSD 57%, **EURUSD 0%** (verified: constraint 7's "50-55% null" is an indices/metals fact,
FX ticks are fully populated in `deep_history_utc`). Consequence: **no volume-weighted movement
definition and no volume-based conditioner on indices/metals** (would silently condition on the
zero/nonzero-tick_volume dummy, not on real activity). A volume-weighted return construction would
be technically valid on FX only, but is **not run** here (budget declared, not silently dropped —
this grid conditions on realized volatility instead, which is populated everywhere and is
Gao's own alternate conditioner).

## 4. Engine — reused, not rebuilt

`yt_strategy_replications/engine/{backtest,indicators,stats}.py` (tracked canonical library) via
`mr_intraday_grille_2026-08/engine_lib.py`'s `run_cell`/`leg_metrics`/`bars_to_session_end`/
`vol_target_scale`/`trade_daily` (imported read-only — this study only adds new signal
constructions, exactly as `engine_lib.py`'s own docstring frames its role for MR). Signal at
bar-close t → execution at open t+1 (T-1/T hard rule), enforced centrally by
`engine.backtest.run_backtest_vectorized`. Entries are **only permitted when the required holding
window fits inside the remaining session bars** (`bars_to_session_end` guard) — guarantees
intraday-flat (mandate constraint 3) with zero cross-day bleed, identical mechanism the MR study
already used and validated.

HAC Newey-West lag-6 (`engine.stats.hac_tstat`), DSR (`engine.stats.deflated_sharpe_ratio`,
`n_trials` = running cumulative count, see §9), 5-fold walk-forward (`engine.stats.fold_metrics`),
daily-aggregated P&L annualised at **252** (L47 — never by intraday bars/year). Daily vol targeting
per `engine_lib.vol_target_scale` (63-bar-equivalent: `k=20` session-bar realized vol, shift-1,
cap 3×), identical convention to the MR study.

## 5. The movement/signal grid — width over depth, naive round parameters, nothing optimised

Four independent **movement** constructions (what counts as "the move"), each swept over few,
round parameter values — no fitting, no post-hoc selection before the full sweep is done.

**A — Gao early-window return** (the literature's own construction): `window_ret = close[K-1]/open[0]-1`
over the session's first `K` bars; sign → direction; entry at bar `K` open (right after the window
closes). `K ∈ {2, 4}` (30min / 60min). Unconditional sign (no threshold — Gao's own construction is
unconditional; a magnitude gate is tested separately as a conditioner, §8).

**B — ORB breakout** (mechanically identical to the production sleeve): opening range = first `K`
bars' high/low; first subsequent bar whose **close** clears OR-high (long) or OR-low (short) is the
trigger; entry at next bar open. `K ∈ {2, 4}`.

**C — Gap continuation** (trade WITH the gap — the mirror image of the sister study's gap-**fade**
S2, so the two studies together cover both signs of the same event): session-open gap vs prior
session close, normalized by a 20-session rolling σ of gaps (causal, shift-1); `|gap| ≥ g0·σ` triggers,
direction = sign(gap). `g0 ∈ {0.5, 1.0}`.

**D — Prior-session range-position persistence**: `pos = (prior_close − prior_low)/(prior_high −
prior_low)`; `pos ≥ p_hi` → long next session, `pos ≤ p_lo` → short. `(p_hi,p_lo) ∈ {(0.8,0.2), (0.9,0.1)}`.

**Continuation horizon** `H` (independent axis, applied to A/B/C where declared): `{8 bars fixed,
rest-of-session}` — "rest of session" = `session_bars_mode(instrument) − K`, enforced via the
`bars_to_session_end` guard so it never bleeds into the next day. ORB (B) uses rest-of-session only
(matches the production sleeve's time-stop-to-close convention; the 8-bar-fixed variant is **not
covered** for B, declared not silently dropped — budget).

**Exit** (independent axis from entry, per mandate): `X1` time-stop only (`sl_dist=tp_dist=BIG`,
matches Gao/Lehmann's literal no-stop construction) · `X2` ATR bracket, **asymmetric 1×SL /
1.5×TP** (matches the production ORB's stop/target ratio, not MR's symmetric 1:1) · `X4` (B only)
range-based bracket, SL=0.5×OR-width, TP=1.5×OR-width (mirrors the CLAUDE.md Strategy C spec:
"TP 1.5R, SL min(0.5R,20pts)" applied to the CFD OR-width instead of futures points).

**Entry style**: all four constructions above are stop/market entries at the trigger bar's next
open (no pullback-wait variant — declared not covered; a pullback-confirm entry inverts the
mechanism into a different, untested hybrid and is flagged for a future session, not folded in
here to keep the axis count inside the ≤3-modification discipline per construction).

## 6. Conditioning axes (mandate constraint: Gao conditions on high-vol/high-volume days — not
optional)

Applied to construction **A**'s canonical cell (`K=2, H=rest, X1`) and **C**'s canonical cell
(`g0=1.0, H=rest, X1`), each instrument, reported as tercile/day splits (not multiplied into the
full grid, to keep the budget bounded — same discipline the MR study used for its own conditioner
sub-blocks):
- **Realized-volatility tercile** (20-session rolling σ, causal) — the volume-based conditioner
  Gao actually uses is invalid here (§3); vol is its populated proxy, also literature-standard.
- **Day-of-week** (Mon-Fri).
- **Gap-size tercile** (construction C only — |gap|/σ terciles).

## 7. Cross-sectional lead-lag (mandate axis: which index leads)

Construction A canonical (`K=2`) computed on each of the 4 indices as the LEADER; signal applied
to trade each OTHER index's continuation window (same session, timestamp-aligned). 4×3 = 12
ordered pairs, `H=rest`, `X1`.

## 8. ORB reference placement (not a new grid cell — a fixed external comparator)

`PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet` (N=4013, NQ futures,
2010-2026, `r_gross` column = R-multiple) recomputed with this study's own `engine.stats.hac_tstat`
for a same-yardstick comparison: pooled/long/short HAC-t. **Not counted toward this grid's n (§9)**
— it is the existing production ledger, not a new hypothesis test drawn from this sweep; comparing
it is the placement exercise itself. Reported as the ORB's **percentile rank inside this grid's own
`long_t`/`short_t`/`both_t` empirical distributions**, plus inside construction B specifically
(same mechanism family) since B is the closest same-family analogue on the CFD universe.

## 9. n_tests accounting (mandate constraint 9)

Prior family total (MR, closed): **1,526**. This grid's own cell count (§5-§7, computed before any
result is read): A 72 + B 36 + C 72 + D 36 + cross-sectional 12 + FX-cross extension 14 +
conditioning 99 = **341**. Combined honest N after this session: **1,526 + 341 = 1,867**. Two-sided
Šidák threshold at N=1,867: `t* ` such that `1-(1-2*(1-Φ(t*)))^(1/1867)=0.05` → recomputed in
`RAPPORT.md` (§9 there), reported alongside the naive N=341-only threshold for transparency. DSR
`n_trials` in the engine calls uses the **cumulative 1,867**, not just this grid's 341.

## 10. Gates (pre-registered, decisive)

1. **Gross two-sided (L25):** both legs' HAC-t > 0, pooled HAC-t > 2.5, BEFORE any cost is charged.
2. **L33b gross floor:** gross bps/trade > ≈1.4bps (recalibrated) — reported, not used to skip.
3. **Net:** at measured native cost, Sharpe > 1.0 AND DSR > 0.5 (cumulative n_trials).
4. **Walk-forward:** ≥5 folds, WF score > 50%.
5. **Placebo (L58/L61/L62 discipline):** any cell clearing gross `|t|>2.5` gets (a) a matched
   circular block-shuffle placebo (500 draws, block=20 sessions, shuffles which day's early-window
   value pairs with which day's continuation return — breaks the specific causal link, preserves
   each series' own autocorrelation) reporting an empirical percentile, and (b) if the cell uses a
   symmetric-ish tight bracket (X2/X4), **M1 tie-break resolution** via
   `audit_moteur_bracket_2026-08/m1_resolver.py` (imported, not rewritten) before the cell is
   trusted — never compared to a naive iid/block-bootstrap placebo per L62.
6. **Comparison to max-under-H0:** Monte-Carlo (20,000 draws) of the expected count and expected
   max of `|t|` over N=341 iid draws, reported alongside the observed distribution — the sister
   study's own falsifier, reused identically.

## 11. Pre-registered directional hypothesis

**Honest prior, stated before running anything**: L33b (one Gao cell, gross≈0) and the MR family's
own momentum-flip check (also gross-negative, different construction — z-score extreme continuation,
not window-return) both point toward this family also being dead on 15-min CFD bars. The ORB
ledger's positive NQ-futures t-stats are the one piece of evidence pointing the other way, on a
different venue (futures, not CFD) and a different, coarser trigger (range breakout at any time of
day, not a fixed early-window boundary). **A clean "family dead, ORB is a lucky draw at percentile
X" is an explicitly acceptable, useful outcome** (mandate) and is the prior's expectation; a
genuine multi-instrument, multi-construction positive neighbourhood would be the surprise.

## 12. What gets written

`grille_resultats.csv` (one row per cell, every axis as a column — instrument, construction, K/g0/p,
H, exit, gross_sr/t/dsr/wf per leg, net_sr/t where cost-eligible, n_trades, gross_bps_per_trade,
avg_bars_held, frac_sl/tp/time). `RAPPORT.md` (t-distribution numbers, H0 comparison, ORB placement,
decisive verdict). This file (frozen, not edited after cells are run — amendments go in a dated
addendum section at the bottom of `RAPPORT.md`, never a silent edit here).
