# Research method — how a study runs here

This describes the research cycle used under `<AssetClass>/research/active/` and
`<AssetClass>/research/archived/`. It does not describe the live system
(`docs/ARCHITECTURE.md`) or the strategies themselves (root `README.md`, `_meta/lessons_registry.md`).

## 1. The cycle

```
PREREGISTRATION.md  →  code runs once, unmodified  →  RESULTS.md (verdict)  →  [AMENDMENT.md, if the verdict must be revisited]
      frozen                                              never edited            never replaces — appended
```

**Pre-registration.** Before any return is computed on the sample under test, a
`PREREGISTRATION.md` is committed. It freezes: the instrument, the exact price series and column,
the entry/exit rule, the cost and swap numbers, the inference method, the placebo design, and —
critically — numbered **kill rules** and **confirmation rules**, each with a numeric threshold
decided in advance. A study that changes its own kill rule after seeing the result is not a study,
it is curve-fitting with paperwork.

**Execution.** The code runs once against the frozen spec. Diagnostics not in the confirmation
list are allowed and often required (see step 4), but they are declared secondary and non-decisive
*in the pre-registration itself*, before they are computed — so a secondary diagnostic cannot be
promoted to a decision after the fact.

**Verdict.** `RESULTS.md` reports every pre-registered rule against its measured value, in a table,
whether the result is favourable or not. The verdict follows mechanically from the table; it is not
a separate judgment call.

**Amendment, never an edit.** If new information means a past verdict needs revisiting — a data
source turned out to be wrong, a mechanism was misread, a downstream consumer changed — the fix is
a new `AMENDMENT` document that states what the frozen document said, what changed, and why. The
original file is not rewritten. This preserves the audit trail: anyone can see what was believed at
the time a decision was made, not just what is believed now.

## 2. Worked example: `Multi_Asset/research/active/gold_cpi_eve_2026-08/`

This is a complete, closed cycle — two commits, no amendment needed because the verdict was a
clean rejection.

**The reopening.** A prior study (`exogenous_predictors_2026-08`) had found one instructed
hypothesis — XAUUSD entered at the close before the US CPI release — significant on N=65
(2021-2026 only, because the input calendar file only went back to 2020). Per the reopening
policy (root `README.md`, `_meta/lessons_registry.md`), a kill of *power* (sample truncated by an
input file, not by the mechanism itself) is reopenable, and only on that exact angle. The angle
written down before touching data: extend the sample using the BLS's own archived release
calendar, back to 2007.

**The frozen spec** (`PREREGISTRATION.md`, committed `30fa8a9a`, before any return was computed on
the extended sample): instrument `XAUUSD`, long-only at the prior close, cost 1.84 bps RT + 1.518
bps one-night swap, HAC lag-6 inference, block bootstrap (block=3, seed 7), a day-of-month matched
placebo, DSR at `n_trials=80`. Seven numbered confirmation conditions, six numbered kill rules, one
explicitly named "regime, not pass/fail" fallback.

**Execution and verdict** (`RESULTS.md`, committed `31182a2b`): 232 events recovered from BLS
archives (100% concordance against three independent sources; the previously-used calendar file
was only 90.9% accurate and wrong specifically for dates after 2025-09). Full result:

| condition | required | measured | |
|---|---|--:|---|
| walk-forward ≥ 4/5 folds net-positive | ≥ 4/5 | 4/5 frozen, 3/5 expanding | ambiguous |
| pure OOS 2007-2019: gross > 0 and t ≥ 2.0 | t ≥ 2.0 | t = 0.40 | fail |
| full sample t_HAC ≥ 2.5 | ≥ 2.5 | 1.53 | fail |
| placebo p ≤ 0.05 | ≤ 0.05 | 0.0994 | fail |
| block bootstrap p ≤ 0.05 | ≤ 0.05 | 0.339 | fail |
| DSR ≥ 0.95 (n_trials=80) | ≥ 0.95 | 0.0000 | fail |
| gross/cost ≥ 3 | ≥ 3 | 3.37 | pass |
| **kill rule R4: full-sample t_HAC < 2.0** | triggers below 2.0 | **1.53** | **triggered** |

**Verdict: REJECTED.** The pre-registered fallback ("regime, not noise") was itself tested, not
assumed: regressing the event return on the CPI level known at entry gave t = -0.10, R² = 0.0001 —
refuted, not confirmed. The report states plainly what the rejection does *not* prove (CPI does
move gold — the pre-event drift leg, +8.45 bps, t=1.84, was never itself a pre-registered
candidate, and promoting it now would be exactly the data-mining the pre-registration forbids). The
calendar-event family is closed on this angle.

This is the pattern to look for in any dossier: a frozen numeric table, a verdict that follows from
it mechanically, and an explicit statement of what was *not* shown.

## 3. Amendment example: `data/ftmo_portfolio/v22/AMENDEMENT_RAPPORT_MESURE_s9.md`

A prior report had pre-registered a kill rule for the live book ("if measured ORB execution cost
> 1.5 bps, ORB is switched off"). A later spec revision (v2.2, commit `605f4a4`) restructured the
book so the challenge no longer depends on ORB P&L at all — the pre-registered kill condition became
structurally inapplicable. Rather than editing the original report, `AMENDEMENT_RAPPORT_MESURE_s9.md`
quotes the original §9 verbatim, states explicitly that it is superseded, and gives the new decision
rule. The file even notes that the host report itself is not in this repository (a team workspace
document) and that the amendment is the canonical record until the two are synchronised — an
explicit acknowledgment of an imperfect but auditable state, rather than a silent rewrite.

## 4. The gates

Two thresholds recur across every study, defined in `CLAUDE.md`:

| Gate | Sharpe | Max drawdown | Walk-forward |
|---|---|---|---|
| RESEARCH_PASS | > 0.7 | < -25% | > 50% of folds positive |
| PROPFIRM_PASS | > 1.0 | < -10% | > 60% of folds positive |

A study passing RESEARCH_PASS is a candidate for further work, not for capital. Only
PROPFIRM_PASS-grade results are considered for the funded account, and even then only after the
admission criterion in §6.

## 5. Multiple testing

Every study declares `n_trials` before running (it is a pre-registration field, not a post-hoc
correction) and reports either a Šidák-corrected p-value or a Deflated Sharpe Ratio (DSR,
Bailey-López de Prado; implementation at `dsr.py`, root) against that count. Two ledgers track how
many tests have accumulated: `_meta/n_tests_ledger.md` holds the frozen historical global count
(321, fixed 2026-05-30) and the rule for reconciling it; each research programme opened since then
keeps its own local running count, reconciled into the ledger at the programme's close. Sub-totals
that overlap are never added together — only the sequential milestones are additive. `dsr.py`'s
default risk-free rate is `0.0`: a documented past bug (`rf` defaulting to `0.02`) had silently
charged 50 bps of annual carry to a position held 60 minutes, producing a materially wrong Sharpe;
see `_meta/lessons_registry.md` and the memory entry it points to for the fix.

Instrumentation bugs in the DSR calculation itself have produced wrong thresholds before, and are
worth checking rather than assuming: the 164-test funnel in `PropFirms/ftmo/program_2026-06/top10_test/`
hardcoded `std_sr_trials=1.0` (`framework.py:118`), which demanded an observed Sharpe of 2.57 to
pass instead of the correct 1.27 — a threshold twice as high as it should have been, biasing the
whole funnel toward false negatives. This is tracked as defect #1 in
`Multi_Asset/research/active/reaudit_vehicule_2026-08/PREREGISTRATION.md` and re-examined in
`Multi_Asset/research/active/carto_reouverture_2026-08/CARTOGRAPHIE.md`. The general lesson: a
DSR pass/fail is only as good as the `std_sr_trials` estimate behind it — a hardcoded placeholder
value is not a calibration.

`dsr.py` (root) changed its own `rf` default from `0.02` to `0.0` on 2026-08-04, documented in the
module docstring: passing a non-zero `rf` double-subtracts the cash rate on returns that are
already excess (this repo's hard rule), and for event strategies `rf/periods_per_year` conflates
annualisation with risk-free accrual — measured to turn a Sharpe of +0.38 into -12.1 for a position
held 60 minutes at 4 events/year. The default is now `0.0` with a warning on any non-zero override.

CPCV (Combinatorial Purged Cross-Validation) is available as a second, orthogonal diagnostic
(`Portfolio/validation/`) — it is not a substitute for walk-forward, it estimates whether a single
walk-forward path was a lucky draw from the distribution of possible paths. See
`Portfolio/validation/README.md` for the worked proof-of-concept on Strategy A and the explicit
per-strategy scope restrictions (not applicable below a minimum sample size).

## 6. Placebos

A placebo is not optional decoration on a significant result — several false positives in this
repository's history cleared every standard gate (HAC t-stat, bootstrap, walk-forward) and were
only caught by a matched placebo, because the artifact lived in path-dependent sizing or in
calendar structure the other tests cannot see. The recurring designs:

- **Matched-calendar placebo**: resample the same trade shape at calendar dates outside the tested
  window, matched on the property that could confound it (day-of-month, autocorrelation, duty
  cycle). The gold CPI-eve study above uses a day-of-month-matched placebo.
- **A placebo needs its own sanity check.** `_meta/lessons_registry.md` L58 records a placebo that
  produced a false PASS because its baseline pool was itself biased by an interacting exclusion
  window (an auction blackout pushed the placebo pool into a seasonal trough) — the fix is to check
  the placebo pool's mean against the *unconditional* expectation of the same trade shape, not just
  to run the placebo and trust it.
- **Vary the seed and the block length** where randomization is involved (block bootstrap), and
  report both, rather than the single draw that happened to run.

## 7. Walk-forward

Expanding-window, minimum 5 folds — a single train/test split is treated as inadmissible evidence,
independent of how good it looks. A confirmation rule stated in terms of walk-forward
(`≥ 4/5 folds net-positive`) is checked on both a frozen-block and an expanding-window
partition where the two can disagree, as in the worked example above (4/5 vs 3/5) — the
pre-registration decides in advance how to read a split verdict, rather than picking whichever
partition passes after the fact.

## 8. Reading a dossier quickly

A well-formed `research/active/<study>/` or `research/archived/<study>/` folder has, at minimum:
`PREREGISTRATION.md` (or an equivalent frozen-spec section at the top of the results file for
older studies that predate the convention), a `RESULTS.md` with a verdict table like the one
above, and the code that produced the numbers in `code/`. `_meta/research_active.md` indexes the
currently open studies with paths and one-line status; `_meta/lessons_registry.md` is the
compressed cross-study record of what each closure established as a general rule, not just a
verdict on one instrument.
