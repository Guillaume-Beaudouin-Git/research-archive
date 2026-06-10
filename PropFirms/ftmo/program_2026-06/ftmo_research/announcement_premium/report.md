# REPORT — US500 Macro Announcement Premium (Savor-Wilson 2013)

**Study ID:** `announcement_premium` · **Date:** 2026-06-10
**Contract:** `HYPOTHESIS.md`, frozen and committed **before any price data** (commit `88cc29e`)
**Verdict: NO-GO — all five pre-registered kill criteria fail, DSR ≈ 0. MC p(pass) not run (per contract §8).**

---

## 1. Headline

The Savor-Wilson announcement premium is **absent** on US500 over the realized sample
(2021-09-15 → 2026-06-05, 1,218 trading days, 149 announcement days). Announcement days
earned **+0.50 bp/day** (excess, close-to-close) vs **+3.65 bp/day** on non-announcement
days — the event-day differential is **negative** (β = −3.15 bp, t_HAC = −0.28). The
2021–26 equity drift accrued **off** announcement days. The strategy is dead before
statistics: gross +0.49%/yr does not even cover the swap leg alone (~0.98%/yr), let alone
spread. The pre-declared expectation ("honest negative is the deliverable") is confirmed,
and more strongly than expected: not a decayed-but-positive premium — a sign-flipped one.

## 2. Pre-registered gates (any one ⇒ NO-GO)

| Gate | Rule (frozen) | Result | Value |
|---|---|---|---|
| K1 | t_HAC(β event-day) ≥ 2.5 | **FAIL** | β = −3.15 bp, t = −0.28, p = 0.78 (Šidák m=4: 1.00) |
| K2 | SR_net(strategy) > SR_net(scaled B&H, w̄=12.2%) | **FAIL** | −0.399 vs +0.056 |
| K3 | ≥2021 block: sign-stable AND t ≥ 1.0 | **FAIL** | t = −0.28 (< 1.0) |
| K4 | ann net ≥ 2 × ann cost drag (8 bps RT + swap) | **FAIL** | net −2.97%/yr vs cost 3.46%/yr (gross +0.49%/yr) |
| K5 | not 100%-concentrated in one type with N < 40 | **FAIL** | only positive contributor = FOMC, N = 38 < 40; rest-β = −9.9 bp ≤ 0 |
| DSR | program convention > 0.95 (L20) | **FAIL** | 5.9e-09 (program, N=101) / 2.5e-04 (within-study) |

**K4 sensitivity (frozen, not selection):** net −2.35%/yr @6 bps, −2.97%/yr @8 bps,
−3.59%/yr @10 bps — fails at every spread level; gross < 1× costs everywhere.

## 3. Per-event-type table (4 registry trials)

| Type | N days | mean event-day excess | β vs non-event | t_HAC | p raw | p Šidák(4) |
|---|--:|--:|--:|--:|--:|--:|
| Pooled | 149 | +0.50 bp | −3.15 bp | −0.28 | 0.776 | 0.997 |
| FOMC | 38 | +20.11 bp | +16.46 bp | +0.85 | 0.395 | 0.866 |
| CPI | 56 | +10.18 bp | +6.53 bp | +0.34 | 0.730 | 0.995 |
| NFP | 56 | −21.08 bp | −24.74 bp | −1.38 | 0.166 | 0.517 |

Non-announcement-day mean: +3.65 bp (n=1,069). One dual-type day (CPI+FOMC) counted once
in pooled, once per type. The only positive trace is FOMC (+16–20 bp/day gross) —
underpowered (N=38, would need ≈3× the effect for t≥2.5), below the L12 event-count gate,
and consistent with the internal finding that pre-FOMC drift ≈ 0 in 2025/26. NFP days are
**negative** (hawkish-surprise regime 2022–24). The premium is not "decayed but positive";
on this sample it is absent.

## 4. Sub-period table (K3, blocks frozen)

| Block | Status | N event | β | t_HAC |
|---|---|--:|--:|--:|
| ≤2015 | EMPTY — calendar floor 2018-01-01 (declared at freeze) | — | — | — |
| 2016–2020 | EMPTY — US500 price hole 2018-01→2021-09 (see §6) | — | — | — |
| ≥2021 | evaluated (= full realized sample) | 149 | −3.15 bp | −0.28 |

K3's decay-detection design collapsed into a single block; the binding most-recent-block
test still fails decisively.

## 5. Strategy economics (unit notional, leverage-invariant)

- Exposure: 31.6 event-days/yr (w̄ = 12.2% of days), mean 1.05 nights/event (2 Good-Friday
  NFPs held Thu→Mon; listed in `events_mapped.csv`).
- Gross +0.49%/yr → spread (8 bps RT) −2.48%/yr, swap (−3.08 bp/night, L30-verified)
  −0.98%/yr → **net −2.97%/yr**, net Sharpe −0.40.
- Event-day win rate 51.7%; event-day annualized vol 21.3%.
- Dividend credits ignored (would add ≈ +0.2%/yr; identical for the K2 benchmark — no
  gate flips; documented conservatism).
- K2 benchmark (12.2%-scaled buy-and-hold net of swap): SR +0.056. Conditioning on
  announcement days is **worse than pro-rata beta** — there is no timing alpha to harvest.

## 6. Data integrity findings (side-deliverables)

1. **US500_M1.csv has a 3.7-year hole: 2018-01-01 → 2021-09-13** (0–23 stray bars/day vs
   ~695/day Dukascopy backfill before, ~1,200/day MT5 after). Root cause: the MT5 export's
   M1 depth starts 2021-09-14; stray pre-2021 bars made the splice treat 2018+ as
   "existing data", so Dukascopy filled only pre-2018. `MANIFEST.md`'s "US500: no
   existing-data outages" claim is wrong for this window. **Backfillable** from Dukascopy
   (source floor 2012-01-16) with the existing pipeline — would restore ~82 event days
   (28 FOMC + 45 NFP + CPI 2018–21) and enable the K3 2016–2020 block.
2. **Realized vs declared sample (deviation note):** contract declared calendar∩price =
   2018-01-03→2026-06-05; the realized intersection is 2021-09-15→2026-06-05 because of
   (1). Deterministic consequence of frozen rules + data state; no post-hoc choice.
3. **First-run contamination, caught and fixed outcome-blind:** the initial build let the
   seam row (2021-09-14, `nights` = 1,355) into the grid; the `mean_nights_event = 10.07`
   sanity diagnostic exposed it. Fix: validity rule `nights ≤ 7` (no legitimate US500
   close-to-close window exceeds ~5 nights). Both runs produced NO-GO on all gates; all
   reported numbers are from the corrected build (`max_nights_in_sample = 4`).
4. **Calendar vocabulary:** TradingView titles US CPI differently before ~Dec 2020 (only
   9 of ~44 hole-period CPI releases match the frozen filter). Within the realized sample
   coverage is complete: 56/56 CPI months, 56 NFP, 38 FOMC (8/yr).
5. **Exclusions (pre-registered rules):** 2 unscheduled FOMC (2020-03-03 15:00 UTC,
   2020-03-15 21:00 UTC — Covid emergency cuts; both inside the hole anyway); 2 NFP
   released while market closed (Good Friday 2023-04-07, 2026-04-03 → mapped to Monday
   close per frozen rule). Full manifest: `events_excluded.csv`, `events_mapped.csv`.

## 7. Registry & constitutional accounting

- **Trial registry: 97 → 101** (+4: pooled, FOMC, CPI, NFP — frozen in HYPOTHESIS §7;
  sub-periods and cost sensitivities are diagnostics of the same trials, not selections).
- **DSR (Bailey-LdP, daily units, T=1,218, N=101):** program convention (SE0=0.845)
  SR0_ann = 2.14 → DSR = 5.9e-09; within-study null SR0_ann = 1.15 → DSR = 2.5e-04.
- **Modifications consumed: 0/3.** Single pass, no iteration, study closed at first
  gate evaluation. L1/L26 respected by construction (calendar known in advance; release
  timestamps verified inside holding windows — see sanity gates in `build_meta.json`).
- **Container closure (L-candidate, unnumbered):** announcement-day conditioning on US500
  close-to-close, 2021–26, carries **no premium** — drift accrues off-event; event-night
  subsetting therefore cannot rescue the L36 overnight swap hurdle (the subset has *less*
  edge per night than unconditional overnight, not more). Complements (does not contradict)
  the B1 midweek-NQ overnight finding, which is a different container (all midweek nights,
  futures, swap-free).

## 8. Files

| File | Content |
|---|---|
| `HYPOTHESIS.md` | frozen contract (commit `88cc29e`) + outcome register |
| `build_dataset.py` / `run_study.py` | build + gate evaluation (deterministic, rerunnable) |
| `dataset_daily.csv` | 1,218-day grid: closes, returns, nights, rf, event flags |
| `events_mapped.csv` / `events_excluded.csv` | event↔day mapping + exclusion manifest |
| `build_meta.json` / `results.json` | sanity gates + full gate results |
