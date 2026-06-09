# PRE-REGISTERED HYPOTHESIS — US500 Macro Announcement Premium (Savor-Wilson 2013)

**Study ID:** `announcement_premium` · **Frozen:** 2026-06-10 · **Program:** FTMO challenge book
**Attestation:** committed BEFORE any US500 price file was opened. Pre-commit recon was limited to:
directory listings, `data/deep_history_utc/MANIFEST.md` (provenance), calendar metadata
(event-title vocabulary, UTC-hour histograms, row counts — no returns), FTMO cost specs,
`data/ftmo_research/code/ftmo_swaps.py`, and the funnel DSR/noise-floor conventions.
Any post-hoc modification of this contract after price data is read = study invalidation;
each additional variant tested counts as a new registry trial.

## 1. Hypothesis

Savor & Wilson (2013, JFQA): aggregate equity earns an abnormal excess return on days of
scheduled macroeconomic announcements (compensation for macro-news risk). H1: US500
close-to-close excess return on scheduled FOMC-decision, US CPI and NFP days exceeds the
non-announcement-day mean, is economically large enough to clear real FTMO CFD costs, and
is stable in the most recent sub-period.

Prior internal evidence (declared bias): pre-FOMC drift found ≈0 in 2025/26 internally;
the published premium is ~10 bp/event-day (1958–2009), which at N≈265 event days and
σ_d≈1.2% gives t≈1.5 < 2.5. **Expected outcome: NO-GO. The honest negative is the deliverable.**

## 2. Strategy specification (exact, frozen)

- Long US500, fixed unit notional, entered at close(T−1), exited at close(T), where T is an
  announcement day. Flat on all other days. No stops, no vol overlay, no sizing rule.
  (Daily vol targeting is intentionally NOT applied at this premium-measurement stage; a
  vol-sized variant would consume one of the 3 modification slots. Modifications used: 0/3.)
- Long-only by construction (premium hypothesis, not a directional signal). L25 two-sided
  testing does not apply; the alpha-vs-beta gate K2 replaces it (adapted per task spec).
- L1/L26: the event calendar is known in advance (release schedule published months ahead)
  → signal at T−1 is structurally guaranteed; no look-ahead is possible. Release-timestamp
  vs holding-window verification is still performed (§4 mapping rule + audit table).

## 3. Data (frozen sources, read-only)

| Input | Path | Notes |
|---|---|---|
| US500 M1, TRUE UTC | `data/deep_history_utc/US500_M1.csv` | 2012-01-16→2026-06-05, validated (MANIFEST: 0 OHLC violations, monotonic, splice-audited) |
| Economic calendar | `data/deep_history_utc/calendar/economic_calendar_2018_2026_full.csv` | 74,543 events, 2018-01-01→2026-06-07, UTC timestamps, TradingView-sourced |
| Risk-free | `data/raw/fred_DTB3_37358bdf84.parquet` | DTB3 2000→2026-05-27; ffill to sample end (≤9 days), documented |
| Swap | `research/ftmo_survivors_book/swap_sensitivity/swap_sensitivity.py` PERLEG | US500 long = **−3.08 bps/night** (real FTMO US100.cash specs, price-independent USD-index financing; L30 sign-verified: long PAYS) |
| Spread/slippage | task spec | **8 bps RT base**, sensitivity 6 and 10 bps RT (K4 re-stated at each; no selection) |

**Sample = calendar ∩ price = 2018-01-03 → 2026-06-05** (≈8.4y, ≈2,100 trading days,
expected ≈260–270 event days ≈ 31/yr). The ≤2015 K3 block is EMPTY by construction
(calendar floor 2018-01-01); declared here, not discovered.

**Dividends:** US500 CFD long receives dividend credits (~1.5–1.8%/yr on held notional);
ignored. Effect: strategy and the K2 benchmark have identical exposure-days, so K2 is
unaffected; K1 difference unaffected (uniform drip); K4 net is slightly UNDERSTATED
(conservative, ≈+0.6 bp/event-day if included). Documented, not modeled.

## 4. Event extraction (frozen rules)

From calendar rows with `country == "US"`:

- **FOMC** = `event == "Fed Interest Rate Decision"` AND UTC hour ∈ {17,18,19,20}
  (scheduled 14:00 ET). Rows outside that band are UNSCHEDULED (2020 emergency cuts) →
  excluded, listed in an exclusion manifest. "FOMC Minutes", projections, press-conference
  rows are NOT decisions → excluded.
- **CPI** = `event ∈ {"CPI", "CPI s.a", "CPI s.a Final"}` (TradingView headline US CPI;
  indicator families "Consumer Price Index CPI" / "CPI seasonally adjusted"; 08:30 ET).
  Excludes PPI, PCE, real-earnings and any other inflation rows.
- **NFP** = `event == "Non Farm Payrolls"` (headline only; excludes "Nonfarm Payrolls
  Private" (same timestamp — day-dedupe equivalent), "Nonfarm Productivity QoQ" (different
  release), "Non Farm Payrolls Annual Revision").

**Day-mapping rule (frozen):** event with UTC timestamp `ts` is assigned to announcement
day **T = first trading day whose 16:00 ET close timestamp ≥ ts**. Entry at the
immediately preceding trading-day close. This places every release strictly inside the
holding window (close T−1, close T]; a release after close T is impossible by
construction (it maps to T+1). CPI/NFP 08:30 ET and FOMC 14:00 ET land on their own
calendar day; a release while the market is closed (holiday NFP, e.g. Good Friday) maps
to the next trading close — faithful generalization, counted and listed.
**Dedupe:** one event-day per (T, type); pooled event set = union of days (a day with two
types counts once in pooled, once per type in type tables).

## 5. Price-derived definitions (frozen before reading prices)

- **Trading day / close:** NY-calendar date with ≥100 M1 bars with bar-open time in
  [09:30, 16:00) America/New_York; **close = close of the last such bar** (≈16:00 ET cash
  close; early closes yield the 13:00 ET close and are kept if ≥100 bars). M1 timestamps
  are bar-open, TRUE UTC (MANIFEST gates 1–2).
- **Return:** r_T = close_T / close_{T−1} − 1 on consecutive kept trading days (Monday
  return spans the weekend; `nights_T` = calendar-day gap T−1→T).
- **Excess return (K1, underlying premium):** r_T − rf_T, rf_T = DTB3_{T−1}/100 ×
  nights_T/360 (L8 convention).
- **Strategy net daily (event days):** r_T − 0.0008 (8 bps RT) − 0.000308 × nights_T.
  CFD P&L is excess-by-construction (financing embedded in swap); no double rf subtraction.
  Swap charged per calendar night (Fri→Mon = 3 nights ≡ broker triple-swap convention).
- **Sanity gates before stats** (abort + document if violated): event days/yr ∈ [25, 40];
  trading days/yr ∈ [240, 260]; CPI+NFP UTC release hours ∈ {12,13}, FOMC ∈ {17,18,19,20};
  no event mapped to a non-trading day; grid strictly monotonic.

## 6. Kill criteria (pre-registered; ANY one ⇒ NO-GO, document and stop)

- **K1 — Significance:** OLS r_excess = α + β·1[event] on the full daily grid, HAC
  Newey-West lag-6. Kill if t(β) < 2.5.
- **K2 — Alpha-vs-beta (adapted L25):** strategy net Sharpe (√252, full grid, zeros on
  flat days) must EXCEED the net Sharpe of buy-and-hold US500 scaled to identical average
  exposure w̄ = N_event/N_grid (benchmark net daily = w̄·(r_T − 0.000308·nights_T); entry
  cost amortized ≈0). Kill if SR_net(strategy) ≤ SR_net(benchmark). Net Sharpe is
  leverage-invariant (costs ∝ notional) → no leverage parameter.
- **K3 — Sub-period stability (L31):** blocks by event date: ≤2015 (EMPTY, declared),
  2016–2020 (effective 2018–2020), ≥2021. Kill if, in the ≥2021 block, sign(β) flips vs
  full-sample β or t_HAC(β) < 1.0.
- **K4 — Net vs costs (L11-adapted, = gross > 3× cost):** kill if annualized strategy net
  return (252 × mean net daily) < 2 × annualized cost drag (252 × mean daily spread+swap
  cost). Evaluated at 8 bps RT; re-stated at 6 and 10 bps (sensitivity, not selection).
- **K5 — Event-count concentration (L12):** kill if BOTH (a) removing the
  largest-contribution event type drives the remaining pooled event-day β ≤ 0, AND
  (b) that dominant type has < 40 event days.

Additionally (constitutional, L20): GO requires program-convention DSR > 0.95 (§7).
A pass on K1–K5 with DSR ≤ 0.95 is reported as NO-GO (noise-floor).

## 7. Statistics conventions (frozen)

- HAC lag-6 everywhere (L8). Per-type regressions: D_type vs non-event baseline,
  excluding other types' event days from the sample.
- **AMTP (within-study):** Šidák m=4 family {pooled, FOMC, CPI, NFP}; adjusted p reported
  next to raw.
- **Trial registry:** base **97** (canonical per `research/PROGRAM_DECISION_MEMO.md`)
  + **4 trials here** (pooled, FOMC, CPI, NFP) → **N = 101**. Sub-period blocks and cost
  sensitivities are diagnostics of the same trials (no selection), not new trials. Any
  unplanned variant explored later increments N and is logged in report.md.
- **DSR (Bailey–López de Prado), reported both ways, daily units, T = grid days:**
  PSR form: DSR = Φ( (SR̂_d − SR0_d)·√(T−1) / √(1 − γ₃·SR̂_d + ((γ₄−1)/4)·SR̂_d²) ),
  SR0_d = σ_trials,d · [ (1−γ_E)·Φ⁻¹(1−1/N) + γ_E·Φ⁻¹(1−1/(N·e)) ], γ_E = 0.5772, N = 101.
  (a) **Program convention (primary, gate):** σ_trials annualized = 0.845 (funnel
  pre-registered SE0) → σ_trials,d = 0.845/√252.
  (b) **Within-study null (secondary):** σ_trials,d = √((1 + SR̂_d²/2)/T).
  SR̂_d on strategy net daily series (full grid, zeros included), γ₃/γ₄ from same series.

## 8. Deliverables

- `report.md`: GO/NO-GO verdict, per-gate K1–K5 results, sub-period table, per-event-type
  table, exclusion manifest summary, DSR (both conventions), registry update 97→101,
  cost sensitivities.
- `results.json`, dataset + events manifest CSVs, build/study scripts (English,
  production-quality, vectorized) — all artifacts ONLY in this directory.
- **Conditional (only if K1–K5 all pass AND DSR > 0.95):** Monte-Carlo p(pass) on FTMO
  10k 2-step (+10%/+5% targets, −5% daily, −10% total, no time limit) with CI, at 2–3
  leverage levels, reusing the first-passage engine
  (`research/ftmo_candidate_funnel/funnel_lib.py::combined_pass_prob_empirical`).
  If any gate fails, MC is NOT run (no posthoc exploration).

## 9. Outcome register (to fill AFTER results — empty at freeze)

| Gate | Result | Value |
|---|---|---|
| K1 | — | — |
| K2 | — | — |
| K3 | — | — |
| K4 | — | — |
| K5 | — | — |
| DSR | — | — |
| Verdict | — | — |
