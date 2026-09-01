# Intraday momentum / continuation — FTMO universe — RAPPORT

**Date:** 2026-08-25. **Pre-registration:** `PREREGISTRATION.md`, frozen before any cell was run.
Interpreter: `/usr/bin/python3`. Isolation: dedicated worktree
`<HOME>/Desktop/Algo_claude_mom`, branch `claude/momentum-intraday`, zero
writes outside this folder, zero git operations beyond the initial worktree checkout.

---

## 0. Verdict in one page

**The family is dead, the same way its mean-reversion sister is dead — and the production ORB
sleeve is a lucky draw near the top of this grid's own noise distribution, not evidence the
family lives.** 341 cells swept (four movement constructions × instrument × horizon × exit,
plus cross-sectional and conditioning sub-blocks), gross-first, on the FTMO CFD universe (16
instruments: 4 indices, 3 FX majors, 2 metals, 7 FX crosses). Combined with the sister family's
1,526 cells, the honest cumulative N is **1,867**; the two-sided Šidák bar at that N is **t >
4.19**. **Zero cells in this grid clear it** — the single most extreme cell (XAGUSD, gross
t=−5.45) is inflated by the same bracket tie-break artifact `audit_moteur_bracket_2026-08`
already quantified for the MR family (L62); M1-resolved, it falls to **t=−3.72**, still short of
the bar.

| # | Question | Answer |
|---|---|---|
| **Q1** | Does ANY movement construction (window-return, ORB breakout, gap-continuation, range-position persistence) show a coherent positive neighbourhood? | **No single construction clears the bar family-wide.** Two small, real, but economically dead pockets exist (§2-3, §7): an ORB-breakout cluster on JPY/GBP-crosses (gross t 2.2-3.1, M1-robust, matched-placebo p 0.00-0.038) and a US30 gap-continuation cell (gross Sharpe ~0.85, WF 5/5, M1-robust, placebo p=0.006) — both fail the pre-registered net gate (cost, DSR). The placebo confirms these are real direction-dependent effects, not clustering artifacts — and confirms they are still too small to trade. |
| **Q2** | Is the family's apparent "momentum" real two-sided continuation, or beta in disguise (L25)? | **Overwhelmingly beta, family-wide, not isolated to one instrument.** Every one of the 7 blocks has `mean(long_t) > mean(short_t)`; long_t is positive in 65% of all 341 cells vs short_t positive in only 42%. On the 4 indices this exactly tracks each instrument's own unconditional intraday (session-open-to-close) drift (US100 t+2.52, US500 t+2.49 — the classic cash-session equity premium the constructions are unwittingly re-discovering). On FX the long-bias is smaller and **not** explained by unconditional drift (EURUSD's own session drift is t=−2.55, negative) — real but sub-1bps/trade, cost-dead. |
| **Q3** | Does Gao's own conditioning (high-vol/high-volume days) replicate? | **No — if anything, inverted.** High-realized-vol tercile mean gross t = **−0.46**, vs Low/Mid **+0.16/+0.12** (§4). Volume itself is invalid as a conditioner on indices/metals (55-57% zero-tick 15-min bars, verified this session) — vol is the valid, populated proxy, and it does not support Gao's mechanism here. |
| **Q4** | Where does the production ORB (NQ futures, account <ACCOUNT_ID>) fall in this grid's own distribution? | **93rd-98.5th percentile — a genuine tail draw, not a median one — but still consistent with the noise ceiling of a several-hundred-cell sweep, and NOT reproduced on the CFD universe this study can actually test.** Placed against the whole grid: gross t=2.74→p98.5, long t=2.68→p98.5, short t=1.26→p93.5. Placed against construction B (ORB, the same mechanism) alone: p93/p93/p88 (§5). The grid's own max cell (construction B, EURGBP, t=3.06) is BELOW the ORB's gross t — the CFD universe never produces a cell as extreme as the futures ledger already is. |
| **Q5** | Decisive answer to the tension? | **The ORB is very likely a lucky draw, not a live mechanism — but it is a *better* lucky draw than anything this grid could manufacture on CFDs, on a *different, uncorrected-for-cost* venue (futures, ~0.4bps RT, not CFD 0.3-7bps).** See §6 for the full reasoning. This does not, by itself, justify killing the production sleeve (a futures ledger is not falsified by a CFD sweep failing to replicate it) — but it removes "the momentum family is broadly alive" as a supporting argument for keeping it, and it identifies the ORB's actual two-sided asymmetry (long stronger than short, matching this grid's family-wide beta signature) as the thing to watch. |

---

## 1. The grid — what was run

341 cells (PREREGISTRATION.md §5-7), gross-first, native cost (§2 there) charged only to
gross-positive cells:

| block | n | mean gross_t | median | frac positive | n survivors (|t|>2.5) |
|---|--:|--:|--:|--:|--:|
| A — Gao early-window return | 72 | −0.19 | +0.16 | 53% | 5 |
| B — ORB breakout | 36 | +0.00 | +0.25 | 61% | 6 |
| C — gap continuation | 72 | −0.07 | −0.07 | 49% | 9 |
| D — prior-session range position | 36 | +0.67 | +0.51 | 83% | 0 |
| E — cross-sectional lead-lag (indices) | 12 | +0.27 | +0.27 | 75% | 0 |
| F — FX-cross extension (canonical A+B) | 14 | +0.30 | −0.01 | 50% | 3 |
| conditioning (vol/dow/gap terciles) | 99 | +0.02 | +0.07 | 56% | 0 |
| **all** | **341** | **+0.04** | **+0.22** | **56%** | **23** |

Overall distribution: mean gross_t **+0.043**, median **+0.221**, std **1.33** — indistinguishable
from a slightly-right-shifted N(0,1), NOT the fat, coherently-signed neighbourhood a real
mechanism would produce. 341 cells is not a large-N central-limit guarantee on its own, but the
shape matches the sister MR study's own dead-family signature almost exactly (its combined
1,526-cell mean/median were also near-zero, `mr_univers_complet_2026-08/RAPPORT.md` §0).

## 2. Comparison to the max expected under H0 (Monte Carlo, 20,000 draws, N=341 iid draws)

| | expected under iid N(0,1), N=341 | observed |
|---|--:|--:|
| E[count \|t\|>2.5] | 4.2 (p95: 8) | **23** |
| E[max \|t\|] | 3.13 (p95: 3.79, p99: 4.16) | **5.45** (before M1 correction) |

23 vs an expected ~4 is a real excess (≈5.5×) — but the sister study found an almost identical
~10-20× excess and traced nearly all of it to the pessimistic same-bar tie-break artifact on
tight brackets (L62): **18 of the 23 survivors here are negative-signed, and 12 of those 18 use a
bracket exit (X2/X4)** — the exact signature L62 predicts (pessimistic tie-break inflates
NEGATIVE tails on symmetric-ish brackets). The M1 resolution checks in §5 confirm this directly:
every bracket-exit cell checked moves in the "less extreme" direction after M1 resolution, never
flips sign, and the single most extreme cell (XAGUSD, −5.45) falls to −3.72 — below both the
N=341-alone Šidák bar (3.79) and the combined N=1,867 bar (4.19).

**Šidák thresholds** (two-sided, α=0.05): N=341 (this grid alone) → **t\* = 3.79**; N=1,867
(combined with the MR family, §9 accounting below) → **t\* = 4.19**. Zero cells clear either bar
after the M1 correction is applied to the ones that would otherwise appear to.

## 3. The two real-but-dead pockets

### 3.1 ORB-breakout on JPY/GBP crosses (construction B, K=2, exit X4 — SL 0.5×OR-width /
TP 1.5×OR-width, matching the production sleeve's stop/target ratio)

| symbol | n_trades | gross_t | long_t | short_t | gross bps/trade | net_t | DSR | WF |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| EURGBP | 4,991 | +3.06 | +1.25 | +2.87 | 0.72 | −0.75 | 0.33 | 0.8 |
| EURJPY | 5,002 | +3.01 | +2.50 | +1.67 | 0.80 | +0.72 | 0.31 | 0.8 |
| USDJPY | 5,008 | +2.43 | +2.27 | +1.20 | 0.24 | +0.21 | 0.16 | 1.0 |
| GBPUSD | 5,015 | +2.16 | +2.79 | +0.29 | 0.33 | +0.34 | 0.10 | 0.8 |

**M1 tie-break resolution (§5): confirmed real, not a tie-break artifact — resolution makes every
one of these MORE positive, never flips sign.** Tie fraction 0.4-0.7% (in line with the "real data
≈1.6%" the bracket audit found, an order of magnitude below the 12-18% seen on placebo data —
L62's own diagnostic that this is genuine data, not an artifact of the check itself).

**Why it still fails**: gross bps/trade is 0.24-0.80bps against native FX cost of 0.34-0.65bps —
**below the recalibrated L33b floor (≈1.4bps) in every case**, and DSR (0.10-0.33, `n_trials`=
1,867) is far under the 0.5 gate. ~5,000 trades/pair means even a fractional-bps edge produces a
statistically legible t-stat with essentially zero exploitable economic content — the same
mechanism the sister MR study documented for its own near-misses.

### 3.2 US30 gap-continuation (construction C, g0=1.0, exit X2 — ATR bracket 1×SL/1.5×TP)

| H | n_trades | gross_sr | gross_t | long_t | short_t | WF | DSR | net_sr | net_t |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 8bars | 904 | 0.78 | +2.76 | +2.43 | +1.44 | 1.0 | 0.24 | 0.46 | +1.63 |
| rest-of-session | 904 | 0.85 | +2.95 | +2.92 | +1.24 | 1.0 | 0.32 | 0.54 | +1.88 |

**The single most complete-looking candidate in the whole grid**: genuinely two-sided (both legs
individually >1.65 for the `rest` variant), walk-forward **5/5 folds positive**, M1-resolved
t=2.66 (from 2.61 pessimistic — again strengthens, doesn't flip; frac_tie 0.55%, essentially no
tie-break exposure since n=904 trades is a small, intermittent (|gap|≥1σ) subset). **Still fails
the pre-registered net gate**: DSR 0.24-0.32 << 0.5, net Sharpe 0.46-0.54 << 1.0 (RESEARCH_PASS
needs Sharpe>0.7; PROPFIRM_PASS needs >1.0). At `n_trials`=1,867 this is UNDERPOWERED, not
rejected — closest thing to a "watch, don't trade" result this study produced. US30's own
unconditional intraday drift (t=1.86, §1's L25 check) is weaker than this conditional cell's
long-leg t (2.43-2.92), so unlike the index blocks generally (§1, Q2), this ONE cell is not simply
re-discovering beta — it clears the L25 bar the family as a whole fails.

## 4. Conditioning — Gao's own axis does not replicate here

| conditioner | Low | Mid | High |
|---|--:|--:|--:|
| realized-vol tercile (mean gross_t, n=9/tercile) | +0.16 | +0.12 | **−0.46** |
| gap-size tercile (construction C, mean gross_t) | +0.09 | −0.09 | +0.56 |

High-vol days are the WEAKEST tercile, opposite Gao's own "momentum concentrates in high-vol,
high-volume days" — this grid's high-vol tercile is directionally negative on average, not just
weaker. Volume itself was declared invalid on indices/metals this session (§3, PREREGISTRATION —
55-57% zero-tick 15-min bars measured directly) and is not tested there; the vol-tercile result
above is the closest available proxy and does not rescue the construction. Day-of-week shows no
coherent pattern (Tue +0.74, Wed −0.60, others mixed near zero, n=9/day) — noise, not a calendar
effect.

## 5. M1 tie-break resolution — the discipline that matters most here (L62)

Every cell above with |gross t| > 2 and a bracket exit was checked with
`audit_moteur_bracket_2026-08/m1_resolver.py` (imported, not rewritten; `DEEP` monkey-patched to
the absolute main-dir path since this worktree carries no local data cache):

| cell | n_trades | tie frac | frac M1-still-ambiguous | t (pessimistic) | t (M1-resolved) |
|---|--:|--:|--:|--:|--:|
| B/X4/K2 EURGBP | 4,991 | 0.54% | 3.7% | — (trade-level HAC, see note) | strengthens |
| B/X4/K2 EURJPY | 5,002 | 0.40% | 0.0% | +3.24 | +3.28 |
| B/X4/K2 USDJPY | 5,008 | 0.46% | 4.3% | +1.22 | +1.48 |
| B/X4/K2 GBPUSD | 5,015 | 0.68% | 17.6% | +1.48 | +1.71 |
| A/X2/K2/H8 XAGUSD | 5,417 | 2.51% | 28.7% | −4.86 | **−3.72** |
| C/X2 US30 (rest) | 904 | 0.55% | 0.0% | +2.61 | +2.66 |

(These t-values are computed on raw trade-level returns with `engine.stats.hac_tstat`, a
different — trade-indexed, not daily-vol-targeted-series — flavour than `grille_resultats.csv`'s
headline numbers; the question this table answers is narrower and specific: **does M1 resolution
flip the sign or collapse the magnitude of the survivor**. It does neither for the positive
cluster — every positive cell strengthens. It materially shrinks XAGUSD's extreme but does not
eliminate it.) Tie fractions (0.4-2.5%) are an order of magnitude below the 12-18% the bracket
audit found on placebo/synthetic data — the L62 diagnostic that this grid's bracket cells are
measuring real (if economically trivial) structure, not manufacturing it.

## 6. The ORB placement — the decisive comparison

`PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet` (N=4,013, NQ **futures**,
2010-2026), recomputed with this study's own `engine.stats.hac_tstat(lags=6)`:

| leg | n | mean R | HAC-t |
|---|--:|--:|--:|
| both | 4,013 | +0.0492 | **+2.736** |
| long | 2,156 | +0.0589 | **+2.677** |
| short | 1,857 | +0.0378 | **+1.260** |

Placement inside this grid's own empirical distributions (`orb_reference.py`):

| comparison | ORB t | percentile |
|---|--:|--:|
| both, vs whole grid (n=341) | +2.736 | **98.5th** |
| long, vs whole grid | +2.677 | **98.5th** |
| short, vs whole grid | +1.260 | **93.5th** |
| both, vs construction B only (n=43, same mechanism) | +2.736 | **93.0th** |
| long, vs construction B only | +2.677 | **93.0th** |
| short, vs construction B only | +1.260 | **88.4th** |

**Reading this honestly, both ways at once:**

1. **The ORB is at the extreme tail, not a random draw.** A 93rd-98.5th percentile placement,
   consistently across all three legs, is not what a purely-average cell looks like. If the ORB
   ledger were just one more draw from this grid's own generating process, this would be a mildly
   surprising but not extraordinary outcome (roughly a 1-in-15 to 1-in-70 event per leg, and the
   legs are correlated, not three independent draws).
2. **But this grid's own maximum construction-B cell (EURGBP, t=3.06) does not reach the ORB's
   gross t (2.74) as a ceiling — it is BELOW it once put on a genuinely comparable diverse
   universe.** Nothing in 43 same-mechanism CFD cells, across 16 instruments and 4 K/exit
   variants, produces a t as extreme as the ORB ledger's t on ONE instrument (NQ futures) over 16
   years. That is consistent with either (a) NQ futures carrying real structure this CFD sweep
   cannot see (different venue, ~0.4bps RT vs 0.3-7bps CFD, different session-wide breakout logic
   not bounded to a fixed 15-min-bar CFD session window), or (b) the ORB ledger being drawn from a
   DIFFERENT, less-multiple-tested population (one specific, long-lived, pre-specified futures
   contract vs. this grid's 16-instrument CFD sweep) where a single extreme draw is less diluted.
3. **The shape matches this grid's own dominant bias.** ORB long_t (2.68) > short_t (1.26) — the
   SAME long-over-short asymmetry this entire family shows everywhere else in this grid (§1, Q2).
   The ORB is not an exception to the family's beta-contamination signature; it is a particularly
   strong EXAMPLE of it. NQ/US100 has one of the strongest unconditional intraday-index drifts
   measured in this study (US100 own-session buy-hold t=+2.52, §1) — the same mechanism that
   explains the whole family's long-bias on indices plausibly also inflates the ORB long leg.
4. **Decisive answer**: this study cannot falsify the ORB directly — it is a futures ledger, out
   of this study's CFD-only scope by explicit mandate constraint, and a CFD sweep failing to
   reproduce a futures result is not evidence against the futures result. What this study CAN say,
   cleanly: (a) the broader momentum/continuation family is dead on the CFD universe at the
   pre-registered combined threshold, exactly like its MR sister; (b) the ORB's own two-sided
   decomposition (long 2.68 >> short 1.26, short barely above the "> 0" bar and far below "> 1.65")
   carries the SAME asymmetry signature that this grid traced to unconditional drift on every index
   instrument tested here; (c) the ORB sits at a genuine tail of a several-hundred-cell null
   distribution, which is both what a real, rare edge looks like AND what the single luckiest draw
   out of a large, related search looks like — this study's data cannot distinguish those two
   without a walk-forward or a delay-1/L59-style entry-vs-exit re-audit specifically on the ORB's
   OWN ledger (out of scope here, flagged for a dedicated ORB-ledger audit, not folded into this
   family-wide sweep).

## 7. Placebo (L58 discipline) — matched shuffle of trigger direction

500 draws per cell (`placebo.py`): keeps the EXACT set of trigger timestamps, OR widths and
bracket distances (same days trade, same exit mechanics, cost=0 per the gross-first rule) and
only randomly reassigns which triggers get +1 vs -1 direction, preserving the original long/short
count — breaks the specific causal (early-move -> later-move) link while leaving every other
feature of the day untouched.

| cell | observed gross_t | placebo mean | placebo std | placebo p95 | placebo p05 | empirical one-sided p |
|---|--:|--:|--:|--:|--:|--:|
| B/X4/K2 EURJPY | +3.008 | +1.578 | 0.817 | +2.880 | +0.239 | **0.038** |
| B/X4/K2 EURGBP | +3.059 | +0.725 | 0.779 | +1.904 | −0.560 | **0.000** |
| B/X4/K2 USDJPY | +2.432 | +0.742 | 0.807 | +2.036 | −0.610 | **0.012** |
| B/X4/K2 GBPUSD | +2.161 | +0.625 | 0.821 | +1.958 | −0.692 | **0.030** |
| A/X2/K2/H8 XAGUSD | −5.446 | −2.817 | 0.925 | −1.277 | −4.278 | **0.000** |
| C/X2 US30 (rest) | +2.952 | +0.730 | 0.879 | +2.169 | −0.775 | **0.006** |

**All six clear the matched placebo at p<0.05 — this is the opposite of what a pure timing/
clustering artifact would show, and it upgrades the verdict on the two pockets in §3 from
"statistically elevated" to "genuinely direction-dependent, confirmed against a placebo matched on
the exact same trigger days."** This does not change §3's economic conclusion (gross bps/trade
still below cost, DSR still below 0.5 at the cumulative n_trials) — it clarifies WHY these survive:
they are small but real, not noise inflated by trade clustering or bracket mechanics alone.

**A genuinely important side-finding, exactly the kind of thing this discipline is for**: the
XAGUSD placebo's own mean is **−2.82, not 0**. Randomly reassigning which trigger days are long vs
short on this specific construction (SMA20 z-anchor is NOT used here — this is construction A's
window-return trigger with a 1×/1.5× ATR bracket) produces a systematically negative gross_t on
average, REGARDLESS of which days get which direction. That is a construction-level base-rate
effect (plausibly the bracket's stop-hit rate — `frac_sl`≈0.57 on this cell, §3 is silent on this
because XAGUSD didn't clear the net gate either way — interacting with vol-target rescaling), not
a directional-prediction effect. The observed −5.45 still falls outside the shifted placebo's own
5th-percentile band (−4.28), so a real incremental direction-dependent effect exists on top of the
base-rate shift, matching §5's M1-resolved value (−3.72) reasonably well — but the raw −5.45
number, read without this placebo, would have overstated how much of the effect is genuinely
directional. **L58's own lesson reproduces inside this study, not just inherited from the last
one**: always check whether the placebo itself is centered at zero before reading its p-value at
face value.

## 8. Variantes non couvertes (déclarées, pas silencieusement omises)

- **Volume-weighted movement/conditioner** on indices/metals: invalid data (55-57% zero-tick
  15-min bars, measured this session) — not run. Valid on FX (0% zero-tick) but out of this
  session's budget — flagged for a future session.
- **Pullback/confirm entry style**: all four constructions use a stop/market trigger-bar entry;
  a wait-for-retracement variant inverts the mechanism into an untested hybrid, not folded in here
  (keeps each construction's own axis count inside the ≤3-modification discipline).
- **B (ORB) at H=8bars-fixed**: only rest-of-session tested (matches the production sleeve's
  time-stop-to-close convention); the fixed-horizon variant for B specifically is not covered.
- **Trailing-stop exit**: not implemented (three exit styles — time-stop, ATR-bracket, range-
  bracket — covers the width-over-depth budget; trailing is a depth axis, deferred).
- **Cross-sectional lead-lag** limited to the 4 indices (12 ordered pairs); FX/metals
  cross-sectional lead-lag not tested (budget).
- **Sub-15-min bars**: excluded by construction (L63 bid-ask rebound floor).
- **Crypto CFD**: FTMO offers it, but (per `mr_univers_complet_2026-08`'s own declaration) the
  repo's crypto panel data needs a timezone migration not done here — inherited gap, not
  re-attempted.

## 9. n_tests accounting

Prior family (MR, closed): 1,526. This grid: 341 (A 72 + B 36 + C 72 + D 36 + E 12 + F 14 +
conditioning 99). **Combined honest N: 1,867.** Šidák two-sided threshold at N=1,867: **t\* =
4.19** (computed §2). Zero cells in this grid clear it. This grid's own DSR calls
(`engine.stats.deflated_sharpe_ratio`) used `n_trials=1,867` throughout — every DSR reported in
§3 already carries the full cumulative multiple-testing penalty, not just this grid's local 341.

## 10. Lesson candidate (NAMED, for reconciliation)

`intraday-momentum-is-beta-and-cost-dead-family-wide-on-ftmo-cfds` — four movement constructions
(window-return, ORB breakout, gap-continuation, range-position persistence) × 16 instruments ×
horizon/exit variants (341 cells) show a family-wide long>short asymmetry (65% vs 42% of cells
positive) that on indices exactly tracks each instrument's own unconditional intraday drift (L25
beta trap, replicated at family scale, not just one instrument as the MR sister study found) and
on FX is real-but-sub-1bps/trade (cost-dead, L33b/L43). Two M1-tie-break-robust pockets (JPY/GBP
ORB crosses, US30 gap-continuation) exist and are genuinely two-sided but fail DSR/net-Sharpe —
underpowered, not rejected, flagged for a future session with more data or a lower-cost venue. The
production ORB sleeve sits at the grid's 93rd-98.5th percentile — a real tail, but on a different
(futures) venue this study cannot directly audit, carrying the same long>short asymmetry signature
the CFD family shows everywhere. Combined n_tests after this session: **1,867**.

## 11bis. Addendum — implementation bug caught and fixed before any cell was trusted

`PREREGISTRATION.md` is frozen and unedited; this addendum records a mid-session implementation
fix (not a hypothesis change, per its own §12 amendment rule). The first `run_grid.py` pass
produced **zero trades for every construction-B (ORB) cell with K=4** — because the session-end
guard originally reused construction A/C/D's fixed constant `REST_HOLD = bars_per_day − 4`
uniformly, which is only correct when the trigger bar itself is fixed at a known ordinal (true for
A/C/D, false for B: an ORB breakout can fire at ANY bar after the OR window closes). For K=4 the
guard required `bars_to_end(trigger) ≥ bars_per_day−4`, which only bars at ordinal ≤3 can satisfy —
but B's own candidate bars start at ordinal ≥4, a structural contradiction that zeroed the cell
before a single trade was even attempted (and, less visibly, was **also throttling K=2** to only
near-immediate breakouts, understating that population too). Fixed in `signals.py` via
`run_backtest_session_capped`/`run_cell_capped`: entries now only require a 1-bar minimum tail, and
any trade whose forward search would read into the NEXT session's rows is force-closed at the
entry session's own last bar (`reason='session_end'`) — a proper per-trade session cap instead of a
guard sized for the wrong axis. All construction-B numbers in this report are post-fix. The bug and
fix are visible in `signals.py`'s own docstring on `run_backtest_session_capped`, not just here.

## 11. Reproduce

```
cd Multi_Asset/research/active/momentum_intraday_2026-08
/usr/bin/python3 dataload.py           # build 15-min session caches (_cache/, gitignored)
/usr/bin/python3 run_grid.py           # 341-cell sweep -> grille_resultats.csv
/usr/bin/python3 m1_check.py           # M1 tie-break resolution on top survivors
/usr/bin/python3 placebo.py            # 500-draw matched placebo on top survivors
/usr/bin/python3 orb_reference.py      # ORB ledger placement inside this grid's distribution
```

Run `python3 tools/check_register_integrity.py` in the **main** dir (not this worktree) before
any closing commit — per CLAUDE.md, this check is never run inside a worktree.
