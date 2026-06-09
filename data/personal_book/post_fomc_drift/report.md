# Post-FOMC Announcement Drift (Brooks–Katz–Lustig, NBER w25127) — falsification report

> **VERDICT: NO-GO at every horizon H ∈ {5, 10, 20}. Mechanism dead post-2015; sign-inverted post-2022.**
> Pre-registration: `HYPOTHESIS.md`, committed **before any outcome-data contact** (commit `2d13d5e`).
> No parameter, gate, or sample rule was modified after data contact. Session trials: **4**
> (3 holding horizons + 1 threshold), exactly as registered. Cumulative program count: **97 + 4 = 101**.
> Run date: 2026-06-10. Engine: `code/engine.py`; raw outputs in `results/`.

## TL;DR

The FOMC-day 2y-yield move (≥ 5 bps) does **not** predict continued drift in the same direction
in 10y Treasuries (IEF) on 2004–2026. Pooled net drift is statistically zero at all horizons
(t_HAC = +0.46 / +0.24 / −0.08 vs gate 2.5). The two-sided test (K2) and regime test (K3) jointly
reveal why naive versions of this strategy look alive in papers: **pre-2015 (the BKL in-sample era)
the drift was real and two-sided (+22 bps/event at H=5); 2015–2021 only the dovish-long leg paid
(the secular duration rally in costume); 2022+ the pattern inverts outright** (hawkish-short pays,
dovish-long loses ~70 bps/event at H=20). A signal whose sign flips by regime is the L33 trap —
not a tradable edge. DSR at N_trials=101 is ≤ 0.02 everywhere. Clean kill, archive.

## Cost assumption (stated per pre-registration §4)

**1.0 bp round-trip per event, futures tier** (deployment vehicle ZN; B1 sleeve cites ~0.3–1 bp RT;
CLAUDE.md "futures ~0.01% RT"). One RT per event including superseded/truncated positions. All
gates evaluated NET. Cost is immaterial to the verdict: **gross** pooled means are +6.8 / +4.5 /
−0.8 bps per event — the edge is absent gross, not cost-killed.

## Data provenance (deviations honestly logged)

| Input | Planned source | Used | Why / validation |
|---|---|---|---|
| DGS2, DGS10, DTB3 | FRED `fredgraph.csv` | **treasury.gov daily CMT / bill-rate CSVs** | FRED unreachable at run time (504s, then timeouts, 3 retry rounds — logged). treasury.gov is the *primary* source FRED republishes. Cross-check vs repo FRED parquet (`t10y2y/t10y3m/dgs3mo`, 4,099 common dates 2010–2026): **max abs diff 8.9e-16 — bit-identical.** |
| Target-change dates (cross-validation) | FRED DFEDTAR/DFEDTARU diffs | **federalreserve.gov `openmarket.htm`** | Same FRED outage; openmarket.htm is the primary record. Parsed 59 changes 2003–2025; per-year counts match the public record exactly. Dates are *effective* dates — absorbed by the pre-registered ±1 bd tolerance. |
| FOMC events 2018–2026 | prescribed 74,543-event calendar | as planned | 68 USD `Fed Interest Rate Decision` dates 2018-01-31 → 2026-04-29 (filter identical to `edge_fomc_cycle.py`). Includes both 2020 emergencies; correctly *lacks* the cancelled 2020-03-18 scheduled meeting. |
| FOMC events 2004–2017 | — (calendar starts 2018; K3 requires pre-2015) | **federalreserve.gov historical pages** (pre-registered supplement) | Statement press-release URL dates scraped from `fomchistoricalYYYY.htm` (three URL eras handled). 111/112 scheduled dates confirmed by scrape; the one gap (2007-06-28, page links minutes only) is confirmed by the minutes URL date embedding the meeting end-date. |
| Unscheduled decisions | FRED-diff mechanical rule | as planned (openmarket changes) | Added: **2008-01-22, 2008-10-08**. Correctly rejected (statements with no target change): 2007-06-18, 2007-08-10 (liquidity), 2007-08-17 (discount-rate-only), 2008-03-11 (TSLF), 2010-05-09 (swap lines). |

**Binding cross-validation: 58/58 target changes in-window matched a listed event (±1 bd).**
Event list: **182 events 2004-01-28 → 2026-04-29** (`data_cache/fomc_events.csv` — reusable
artifact: verified FOMC decision dates incl. emergency meetings, with per-row provenance).
Full log: `results/event_reconciliation.log`.

## Sample

- 182 events mapped; 0 dropped for missing DGS2; 0 dropped for missing panel data.
- **Traded (|d(2y)| ≥ 5 bps): 75** (hawkish 32 / dovish 43); flat: 107 (ZIRP-era meetings mostly).
- Traded |d2y|: median 8 bps, p75 12, max 28. Traded events/year ≈ 3.4.
- Instrument: IEF log adjusted-close returns (B1 source/convention), excess of DTB3/252.
- Data integrity: corr(logret_IEF, −Δ DGS10) = **0.962** ✓.
- Non-overlap held by construction: truncated windows 0 / 2 / 4 (H=5/10/20); 1 incomplete
  window dropped at H=20 (last event).

## Gates — per H (NET, bps per event)

| Gate (binding) | H=5 | H=10 | H=20 |
|---|---|---|---|
| K1 pooled mean (t_HAC, gate ≥ 2.5) | +5.8 (t=+0.46) **FAIL** | +3.5 (t=+0.24) **FAIL** | −1.8 (t=−0.08) **FAIL** |
| K2 hawkish-short leg (n=32/32/31) | +6.9 | −5.6 | −13.0 |
| K2 dovish-long leg (n=43/43/43) | +5.0 | +10.3 | +6.3 |
| K2 two-sided (L25) | PASS | **FAIL** | **FAIL** |
| K3 pre-2015 (n=34) | +21.7 | −1.5 | +7.8 |
| K3 2015–2021 (n=15) | +6.5 | +26.8 | +22.8 |
| K3 2022+ (n=26/26/25) | −15.5 | −3.3 | −29.6 |
| K3 regime stability (L31) | **FAIL** | **FAIL** | **FAIL** |
| K5 terciles T1/T2/T3 | +7/−2/+13 **FAIL** | −8/−24/+42 **FAIL** | −25/−4/+24 PASS |
| **All binding** | **FAIL** | **FAIL** | **FAIL** |
| K4 corr vs B1 month-end (flag > 0.4) | −0.027 ok | −0.014 ok | +0.024 ok |
| DSR @ N_trials=101 (deploy gate 0.95) | 0.023 | 0.011 | 0.005 |
| SR annualized | 0.11 | 0.05 | −0.02 |
| Hit rate / skew | 0.52 / −0.16 | 0.57 / −0.25 | 0.47 / +0.35 |

## The decisive table — regime × leg (mean NET bps/event)

| Regime | Leg | H=5 | H=10 | H=20 |
|---|---|---:|---:|---:|
| pre-2015 | hawkish-short | **+18.7** | −7.8 | −15.0 |
| pre-2015 | dovish-long | **+24.4** | +4.0 | +28.0 |
| 2015–2021 | hawkish-short | −18.3 | −52.1 | **−85.7** |
| 2015–2021 | dovish-long | +23.0 | +79.3 | **+95.2** |
| 2022+ | hawkish-short | +3.0 | +25.8 | **+38.9** |
| 2022+ | dovish-long | −27.1 | −21.4 | **−68.1** |

Three regimes, three different stories:

1. **pre-2015** (overlaps BKL's sample): genuine two-sided drift at H=5 — both legs positive,
   pooled +21.7 bps, t=1.38. Directionally consistent with the paper, already sub-significant
   on this proxy.
2. **2015–2021**: pure one-sidedness — dovish-long pays massively (+95 bps at H=20), hawkish-short
   bleeds (−86). That is the secular bond bull giving the dovish leg a free ride: **duration beta
   in costume**, exactly what K2 was registered to catch.
3. **2022+**: the sign flips — hawkish days are followed by *falling* yields' opposite (continuation
   pays on the short side) and dovish days mean-revert hard. Post-COVID, the announcement-day 2y
   move mean-reverts rather than drifts on the dovish side.

A conditional overlay ("trade the drift only in regime X" or "flip the sign post-2022") would be a
post-hoc sign-flip — the registered L33 trap — and is not pursued (modification budget intentionally
left at 0 consumed).

## Supplementary diagnostics (pre-registered, non-binding)

- **5-fold chronological consistency**: positive folds 2/5, 1/5, 2/5 (H=5/10/20). No horizon
  approaches the WF spirit of ≥3/5.
- **Calendar-only 2018+ subsample** (the literally prescribed source): mean NET −7.2 / −4.4 /
  −24.8 bps (t = −0.35 / −0.16 / −0.64). The pre-2018 extension did *not* manufacture the kill —
  restricted to the prescribed calendar alone the result is *worse*. NO-GO either way.
- **Tercile structure**: only the top-|surprise| tercile is ever positive at H≥10 (+42/+24 bps),
  driven by emergency-cut crisis rallies (2008, 2020) — dovish + flight-to-quality beta, not a
  monotone dose-response (middle tercile is negative at all H).
- K1 HAC(6) was belt-and-braces: windows are non-overlapping by construction (supersession rule).

## Honest caveats

1. **Surprise proxy**: FOMC-day d(2y) from daily CMT closes, not the 30-min Fed-Funds-futures
   surprise of the literature (no FF futures data on disk — pre-registered). Measurement noise
   attenuates t-stats toward zero (biases K1 toward NO-GO), but attenuation alone cannot produce
   the *opposite-signed* leg patterns across regimes in the decisive table. The taper-tantrum
   FOMC (2013-06-19, d2y = +4 bps) illustrates the proxy's bluntness: it sat below threshold.
2. **2007-06-28** kept from the prior with secondary confirmation (minutes URL date) — a
   no-change meeting, immaterial to traded set (|d2y| < 5).
3. IEF is an ETF total-return proxy for ZN futures P&L; the financing wedge over ≤20 bd windows
   is ≤ ~8 bps and symmetric across legs; conclusions are insensitive.

## Disposition

- **ARCHIVED — do not re-propose** without (a) true high-frequency monetary surprises
  (FF futures 30-min window, paid data), AND (b) an explanation for the 2022+ sign inversion.
  Even then, the post-publication decay pattern (BKL published 2018; effect present pre-2015,
  absent/inverted after) matches the L31 prior: published drift = arbitraged until proven
  otherwise OOS post-publication.
- **Lesson candidate** (for the L-register at next consolidation):
  `announcement-day-yield-direction-is-not-a-drift-signal-post-2015` — FOMC-day d(2y) direction
  stopped predicting Treasury continuation after 2015; 2015–2021 apparent drift = long-duration
  beta (one-sided); 2022+ inverts. Event-direction overlays on duration need two-sided + regime
  gates *jointly* (K2+K3); either alone would have passed a wrong version here (K2 passed at H=5,
  K3-2015–2021 passed at H≥10).
- **Reusable artifacts**: `data_cache/fomc_events.csv` (182 verified FOMC decisions 2004–2026 with
  provenance — first long-history FOMC event list in the repo; the 74,543-event calendar starts
  2018); `data_cache/{DGS2,DGS10,DTB3}.csv` (daily CMT/bills 2003–2026, bit-identical to FRED);
  `code/assemble_yields.py` (treasury.gov fallback for future FRED outages); openmarket.htm
  target-change parser.
- **Ledger**: program count 97 → **101** (this study: 4 trials, as registered). Global canonical
  CLAUDE.md ledger (+4) to be applied at the next consolidation pass — not edited here (outputs
  confined to this subdir per pre-registration §9).
- K4 footnote: corr to B1 month-end rally ≈ 0 at all H — it *would* have been a clean diversifier.
  The mechanism, not the portfolio fit, is what failed.
