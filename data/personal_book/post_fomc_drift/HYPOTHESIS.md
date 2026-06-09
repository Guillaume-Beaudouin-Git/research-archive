# PRE-REGISTRATION — Post-FOMC Announcement Drift in Treasuries (falsification study)

> **Status: FROZEN.** Committed BEFORE any contact with outcome data (yields, bond returns).
> Any modification of signal, parameters, gates, or sample rules after first data contact
> **invalidates the study** (house prespec convention, cf. commit c735681).
> Date frozen: 2026-06-10. Author: Claude Code session (effort max), supervised G. Beaudouin.

## 1. Hypothesis

**Brooks–Katz–Lustig (NBER w25127): post-FOMC announcement drift in U.S. bond markets.**
Treasury yields underreact to FOMC-day monetary surprises: yields continue to drift in the
DIRECTION of the announcement-day surprise for days-to-weeks. Tradable implication: after a
hawkish surprise (yields up on FOMC day) short duration; after a dovish surprise, long duration.

This is a **falsification study** for the personal book (NOT FTMO — bonds are Gate-0 excluded,
cf. `data/personal_book/sleeves/b1_month_end_bond_rally.md`).

## 2. Signal — frozen parameters

- **Surprise proxy**: `d2y_bps = (DGS2[E_yld] − DGS2[prev]) × 100`, where `E_yld` = first DGS2
  observation date ≥ FOMC announcement calendar date (handles the Sunday 2020-03-15 emergency),
  `prev` = immediately preceding DGS2 observation. FRED DGS2 (2y CMT, ~3:30pm ET quote; FOMC
  statements 14:00–14:15 ET are inside the observation day). We do NOT have Fed Funds futures;
  d(2y) is the pre-registered proxy, accepted as noisier (attenuation biases toward NO-GO).
- **Threshold**: `x = 5 bps`, frozen. Trade iff `|d2y_bps| ≥ 5` (the spec "flat if |surprise| < x"
  resolves the boundary: |surprise| = exactly 5 bps TRADES). Float tolerance: `|d2y_bps| ≥ 5 − 1e-9`.
- **Side**: `d2y_bps ≥ +5` → SHORT duration (side = −1); `d2y_bps ≤ −5` → LONG duration (side = +1).
- **Instrument**: **IEF** (7–10y Treasury ETF) from `data/panels/macro_etf_panel.csv` — the same
  data source and convention as validated sleeve B1 (month-end bond rally). Task specifies 10y
  duration; IEF is the 10y vehicle of the B1 universe (deployment vehicle: ZN futures). Returns:
  `np.log(close).diff()` on panel (adjusted) closes — identical to B1 code (`skew_phase2_B1.py`).
- **Entry**: close of `T+1` = first panel trading day strictly AFTER `E_px` (`E_px` = first panel
  trading day ≥ announcement date).
- **Exit**: close of `min(entry + H business days on panel index, entry day of the NEXT FOMC event)`.
  The information-supersession rule (every position dies no later than the next FOMC entry day)
  mechanically guarantees **non-overlapping event windows** (K1 requirement; truncation count reported).
- **Holding grid**: `H ∈ {5, 10, 20}` panel business days, frozen.
- **Per-event return**: `r_event = side × Σ_{t ∈ (entry, exit]} (logret_IEF,t − rf_t)` with
  `rf_t = DTB3_t / 100 / 252` (excess returns, house hard rule #1; futures P&L proxy — long futures
  ≈ r − rf, short ≈ −(r − rf)).
- **Events with incomplete windows** (exit beyond available panel data): dropped, count logged.
- **Missing DGS2** on either side of the surprise window: event dropped, count logged.
- **Sizing**: unit notional per event. No daily vol-targeting at study stage (event-driven sleeve;
  same posture as B1 "vol-targeting: à fixer au déploiement"). Deployment sizing out of scope.

## 3. Event list — sources (pre-registered, incl. known calendar limitation)

- **2018-01-01 → 2026-06-07**: USD `Fed Interest Rate Decision` rows of the prescribed 74,543-event
  calendar `data/deep_history_utc/calendar/economic_calendar_2018_2026_full.csv` (filter identical
  to `PropFirms/ftmo_paper_edges/code/edge_fomc_cycle.py::fomc_dates`). 68 rows found at recon
  (count only — no outcome data touched).
- **KNOWN LIMITATION, resolved pre-data**: the prescribed calendar starts 2018-01-01, but gate K3
  REQUIRES a pre-2015 regime bucket. Supplement, frozen procedure:
  **2004-01-01 → 2017-12-31** FOMC announcement dates from federalreserve.gov historical-materials
  pages (`fomchistoricalYYYY.htm`, statement press-release URLs `monetaryYYYYMMDDa.htm` /
  `/boarddocs/press/monetary/YYYY/YYYYMMDD/`). Years yielding ≠ 8 scheduled candidates are
  reconciled against the public scheduled-meeting record and logged. Sample start 2004 = IEF panel start.
- **Unscheduled decisions** (all years): any DFEDTAR/DFEDTARU (FRED) target-change date NOT within
  ±1 business day of a listed event is ADDED as an event (mechanical rule — catches 2008-01-22,
  2008-10-08, 2020-03-03, 2020-03-15 if absent). Non-rate FOMC statements (e.g., TSLF 2008-03-11)
  never enter: not scheduled-meeting statements, no target change.
- **Cross-validation (binding)**: every DFEDTAR/DFEDTARU change date must match a listed event
  (±1 bd). Mismatch → resolve to the Fed primary source, log in report.
- **Dedup**: events deduplicated on `E_px`.
- Yield/RF series: FRED `fredgraph.csv` for DGS2, DGS10 (diagnostic only), DTB3 — cached in
  `data_cache/`, read-only thereafter.

## 4. Costs

**Futures-tier: 1.0 bp round-trip per event**, subtracted from each event's gross return
(`net = gross − 0.0001`). Basis: deployment vehicle ZN futures, spread ≈ 0.3–1 bp RT
(B1 sleeve, L9/CLAUDE.md "futures ~0.01% RT"). No CFD swap pollution (futures carry nets in price).
Each event = exactly one RT (truncated/superseded positions included). All gates evaluated NET.

## 5. Pre-registered kill criteria (binding)

Each H is evaluated independently against K1/K2/K3/K5; K4 is a flag.

- **K1 — Pooled drift t-stat**: OLS of per-event NET returns on a constant,
  `cov_type='HAC', maxlags=6` (house rule; windows are non-overlapping by construction §2,
  so HAC is belt-and-braces, L12b/L26 concern). **t < 2.5 → NO-GO.**
- **K2 — TWO-SIDED (L25)**: mean NET return > 0 on BOTH legs independently — hawkish events
  (short bonds) AND dovish events (long bonds). Per-leg t reported. **Either leg ≤ 0 → FAIL**
  (one-sided = duration beta in costume).
- **K3 — Regime stability (L31)**: buckets by announcement date — **pre-2015 / 2015-2021 / 2022+**.
  Pooled NET mean must be > 0 in EVERY bucket containing ≥ 10 traded events (buckets with < 10
  traded events: reported, non-binding, flagged). The 2010-2021 secular duration rally gives the
  dovish leg a free ride — K2 + K3 jointly are the real test.
- **K4 — Diversification flag (non-killing)**: Pearson correlation of the daily strategy return
  series (0 on flat days) vs the B1 month-end bond rally daily series (long TLT, last 3 trading
  days of month, log returns — exact replication of `skew_phase2_B1.py`), common index 2004-2026.
  **corr > 0.4 → flag "not a diversifier, marginal value only"** (report, no kill).
- **K5 — Surprise-size monotonicity**: traded events split into terciles of `|d2y_bps|` (qcut).
  PASS requires `mean_net(T1) ≤ mean_net(T2) ≤ mean_net(T3)` AND `mean_net(T3) > mean_net(T1)`.
  Not increasing → mechanism story fails → **NO-GO.**

## 6. Trials accounting & DSR

- Session trials: **4** (3 holding horizons H + 1 threshold x). No other variant will be touched;
  if any is, it increments the count (L10 budget: max 3 modifications, 0 consumed, none planned).
- Cumulative program count: **97 (prior, per task) + 4 = 101.**
- **DSR (Bailey–LdP)** computed per H on per-event NET returns (T = N_traded events, native event
  frequency, skew/kurtosis-adjusted; canonical weights `(1−γ)·Z(1−1/N) + γ·Z(1−1/(N·e))`,
  γ = 0.5772 on the LARGER quantile — note: corrects the swapped weights in
  `edge_fomc_cycle.py::dsr`). **N_trials = 101.** Reported for every H.
- **Deployment qualifier** (house L20 discipline, distinct from mechanism verdict):
  deployable only if DSR > 0.95 at N_trials = 101. A "mechanism GO / not deployable (DSR)" split
  verdict is possible and will be stated as such.

## 7. Verdict rule (frozen)

- **NO-GO** if, for ALL H ∈ {5,10,20}: any of K1, K2, K3, K5 fails.
- **GO (mechanism)** if ≥ 1 H passes K1, K2, K3, K5 simultaneously. K4 flag attached.
- **GO (deployable)** additionally requires DSR > 0.95 at that H. If multiple H pass, the one with
  highest DSR is named — no re-testing.

## 8. Supplementary diagnostics (pre-registered, NON-binding, reported)

1. 5-fold chronological consistency: traded events split into 5 equal chronological folds per H;
   fold means + count of positive folds (house WF hard-rule analogue for event studies).
2. IEF-vs-DGS10 sanity: corr(logret_IEF, −ΔDGS10) on full sample (data-integrity check, expect ≫ 0.8).
3. Calendar-only consistency line: pooled NET mean + t on the 2018+ subsample (the literally
   prescribed source), per H.
4. Per-event table with emergency-meeting flag (gap < 20 bd to previous event), truncation flag.
5. Distribution stats per H: hit rate, skew, p5/p95 of net event returns.

## 9. Deliverables

- `data/personal_book/post_fomc_drift/` ONLY (code in `code/`, cached inputs in `data_cache/`,
  tables in `results/`, `report.md` at root of subdir). English code. No file outside the subdir
  is touched (except this pre-registration commit itself).
- `report.md`: go/no-go, per-gate, per-leg, per-regime tables, correlation to month-end rally,
  DSR at N_trials = 101, cost assumption stated, event-source reconciliation log.
