# PRE-REGISTRATION (FROZEN before any price-outcome contact) — Event-driven, defined-risk, FTMO-targeted
**Date frozen:** 2026-06-20 · **Author:** research session · **Auditor:** separate subagent (post-hoc).
**Type:** STRICT preliminary exploration. Reimplemented engine (NOT the repo's audited engine) → a POSITIVE is only a
CANDIDATE to revalidate in a Claude Code session against the audited engine; a robust NEGATIVE is definitive.
**Mandate:** §4 rank-2 family (concentrated, defined-risk, scheduled-event) from
`ftmo_profile_study/STUDY_FTMO_COMPATIBLE_PROFILE_2026-06-20.md`. The event family fits §4 ONLY if risk is truly
capped at entry (else the event shock = large intraday excursion m → violates the funded daily barrier).

> Frozen before opening any price file. Events, instruments, windows, surprise definition, gates and hypotheses
> are fixed. **Anti-mining rule (binding):** if at any point I widen the event list, add instruments, or sweep
> windows to find a winner, I STOP and report — each addition is a new registry trial and invalidates the contract.
> No git HEAD ops (shared working dir); live book read-only; nothing deployed.

## 1. Phase-0 sweep (L48) — what is already known, NOT to be re-mined
- **Post-FOMC drift (bonds):** KILLED `data/personal_book/post_fomc_drift/report.md` — dead post-2015, sign-inverts
  2022 (L33 regime trap), DSR≤0.02 @N=101. (Treasuries, Gate-0 excluded — distinct from equity/gold intraday.)
- **Savor-Wilson announcement-day premium (US500):** KILLED `…/announcement_premium/report.md` — drift accrues
  OFF announcement days, β=−3.15bp t=−0.28. (Daily close-to-close LONG-only hold — distinct from intraday surprise.)
- **Pre-FOMC equity drift:** known real (L42) but origin report not in repo; it is an OVERNIGHT drift (not intraday-flat).
- **Therefore the only untested, §4-relevant cell:** the **intraday, surprise-conditioned, two-sided, defined-risk
  reaction** of equity indices + gold to scheduled US releases. That, and only that, is this study.

## 2. Events (EXACT, FIXED = 3) and instruments (EXACT, FIXED = 3)
Calendar: `data/deep_history_utc/calendar/economic_calendar_2018_2026_full.csv` (TradingView, ISO-UTC, with
`actual/forecast/previous`; provenance in `calendar_gap_report.md`). Release dates are published months ahead →
signal timing is look-ahead-safe by construction (L1/L26).
- **CPI** = event name exactly `Inflation Rate MoM` (USD), 08:30 ET (12:30/13:30 UTC). N≈100.
- **NFP** = `Non Farm Payrolls` (USD), 08:30 ET. N≈102.
- **FOMC** = `Fed Interest Rate Decision` (USD), 14:00 ET (18:00/19:00 UTC). N≈68 (rate surprise mostly 0 → FOMC
  used mainly for the event-TIME excursion test, not the surprise-direction test).
- **Instruments:** US500, US100, XAUUSD (most liquid macro-sensitive instruments held true-UTC M1). No others.
- **Sample:** 2018-01 → 2026-06 (calendar coverage). Per-instrument M1 from `data/deep_history_utc`.

## 3. Surprise (FIXED definition)
`s_raw = actual − forecast`; standardized **causally** per event type: `s = s_raw / rolling_std(s_raw, trailing 12,
shifted 1)`. Sign convention recorded as-is; the slope estimate gives the economic direction. Events with missing
actual/forecast dropped (count logged).

## 4. Windows (FIXED — NO sweep)
5-min bars aligned to each release. `t0` = the 5-min bar whose start = release minute (floor to 5-min).
- **Release bar** = [t0, t0+5min): the impact bar (NOT tradable — measured for HEV-1 / HEV-4 only).
- **Tradable post-release window** = enter at **open of t0+5min** (the bar AFTER the release bar — avoids the
  impact bar), exit at **t0+60min** (fixed H=60min) or a hard stop, whichever first. Intraday-flat (swap-free).
- **Pre-FOMC window** (HEV-3 only) = [prior US cash close → FOMC release]; overnight by nature.
- One window each. No alternative horizons are tested (anti-mining).

## 5. Hypotheses (pre-registered, directional)
- **HEV-1 (sanity / positive control, NOT tradable):** the release-bar return loads on the standardized surprise
  (HAC-t large). Confirms the surprise is real and the timestamp is correct. Expected PASS.
- **HEV-2 (THE tradable test — two-sided, defined-risk):** the **post-release** [t0+5min → t0+60min] return,
  entered after the impact bar in the surprise direction, is net-positive. Gate set §6. Two legs (positive- vs
  negative-surprise) must BOTH contribute (L25). Honest prior: priced-in within the release bar → post-release drift
  ≈ 0 or unstable → **expected FAIL**; a small underreaction is the only way it passes.
- **HEV-3 (pre-FOMC drift, directional positive control, L42):** equity cumret [prior close → FOMC] > placebo
  (non-FOMC Wednesdays). Expected PASS but OVERNIGHT → flagged not-§4-clean (informational only).
- **HEV-4 (defined-risk falsification, constraint 4 — possibly the headline):** the release-bar |move| and the
  post-entry adverse excursion in ATR units; **P(release-bar move > 1×ATR / > stop distance)**. If holding through
  the release bar routinely gaps a hard stop, "defined risk" is illusory on naked CFD → only options qualify; the
  §4-compatible version MUST enter post-impact (HEV-2). Quantifies whether the family can fit §4 at all without options.

## 6. Gates (pre-registered thresholds)
1. **Edge (HEV-2):** pooled HAC lag-6 t-stat **> 2.5** on the per-event signed return.
2. **Two-sided (L25):** positive-surprise leg AND negative-surprise leg both net-positive (sign-consistent).
3. **Regime stability (L31/L33):** sign-stable across sample halves (2018-21 / 2022-26), each |t| ≥ 1.0. A sign-flip
   = the regime trap → reject (the exact failure mode that killed post-FOMC drift).
4. **Net of cost:** net-positive at measured spread AND at 2 bps (indices) / 3 bps (XAU) RT; per-event gross must
   exceed 3× cost (L11b binary-event gate, N-independent).
5. **DSR:** Bailey-LdP with **heavy cumulative penalty** — `n_trials = 110` (program counter ~101 + this study's
   ~9 cells) per the program convention (L20). DSR must exceed the within-study noise floor to even be a candidate.
6. **§4 mapping:** defined-risk confirmed (HEV-4: stop not gapped for the post-impact entry), presence ≤0.4
   (≈3 events/mo → trivially yes), intraday-m ≤1.5 (from the excursion test), two-sided ⇒ tail-decorrelated.

## 7. Costs & method
RT = one quoted spread (measured per instrument from the `spread` column) + stress 2 bps (indices) / 3 bps (XAU).
Intraday-flat ⇒ no swap. Excess-return/RF immaterial intraday. HAC Newey-West lag-6; DSR Bailey-LdP; split-half
regime test; per-leg decomposition; unconditional-drift control (compare event reaction to same-clock non-event days).

## 8. What the deliverable states
Per-event/instrument tables (HEV-1 release-bar loading, HEV-2 post-release net + two-sided + regime split, HEV-3
pre-FOMC control, HEV-4 excursion/gap-through-stop), the §4 verdict, and an explicit confidence tag: **POSITIVE ⇒
CANDIDATE for audited-engine revalidation (Claude Code), not a conclusion; NEGATIVE ⇒ definitive.** No deployment.
