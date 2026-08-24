# PRE-REGISTRATION — Regime-concentration diagnostic of the FTMO book's losses

**Frozen:** 2026-06-20, BEFORE any concentration result computed (git history attests).
**Branch:** `claude/regime-diagnostic` (worktree `Algo_claude_regime_diag`).
**Nature:** DIAGNOSTIC only. Decides whether a future macro-overlay study has a target.
No strategy is built, no overlay is constructed, no deployment. Live book / EA untouched.

---

## 0. The question, made falsifiable

Do the book's **losses** concentrate in identifiable, **causally-observable** macro
regimes, or are they spread uniformly across regimes? An overlay can only ever exploit a
concentration that is visible at **T-1** (yesterday's close). Therefore the decisive
quantity is the **causal (lagged) regime**, not the contemporaneous one.

Pre-committed trap to avoid: losses may concentrate in a regime *contemporaneously*
(VIX spikes the same day the book bleeds) yet be invisible at T-1 → an overlay cannot act
on it. We report both alignments; **only the T-1 result drives the verdict.**

---

## 1. Substrate (audited engine, real dated)

- Engine: clean-room `engine.py` (imported read-only by absolute path from main dir
  `…/data/ftmo_portfolio/audit_v2_independent/cleanroom`). Same engine validated in the
  asia / soybean / funded-sizing / overnight-basket / vm-sweep studies.
- Sample: `load_market()` → n≈3295 trading days, 2013-10-01 → 2026-06-05 (CET/EET dates).
- Book = 4 sleeves: **gold** (XAUUSD carry-adj blended-sign TSMOM), **J1** (USDJPY 12-1
  long-only), **overnight** (GER40 held Mon/Tue + US100 intraday), **ORB** (synthetic e7).
- Two date-stamped event sources (the only date-preserving way; the forward block-bootstrap
  MC `ftmo_sim._boot` resamples indices and is **date-less by construction → cannot answer a
  regime question**, so it is deliberately NOT used):
  1. **CHALLENGE busts** — `run_funnel(CFG_V2, vm=14)` over dense cohort starts (step=2 bd)
     across the full sample; `diag` records every bust with `date`, `kind∈{bust,breaker}`,
     and cause `bust_daily` (−5% daily) vs `bust_floor` (−10% static floor).
  2. **FUNDED daily series** — instrumented `run_funded(FUNDED_CFG, vm=1)`, reset-on-bust,
     full-sample horizon; logs per day: date, daily P&L fraction, intraday-min fraction (vs
     midnight balance), per-sleeve P&L contribution, daily-pierce flag, bust flag. Yields the
     book's realized daily return series + drawdown episodes, all real-dated. Engine primitives
     (`_target_for_segment`, `_trade_to`, `_flat`, `_mtm`, swaps) are reused verbatim.

**Scale-invariance note (pre-committed):** the regime *profile of the left tail* is invariant
to the sizing multiplier vm (vm scales all days equally, preserving ordering). Hence the same
daily series characterises both books; the two books differ only in **which horizon of the
left tail binds** — acute single-day (challenge) vs cumulative drawdown (funded).

---

## 2. Regime panel — exactly 4 pre-registered axes, all causal

All macro levels are **lagged 1 trading day** (value as of prior close) and forward-filled to
book dates ⇒ strictly T-1 / overlay-relevant. Bucketing uses full-sample breakpoints
(descriptive; the permutation null permutes labels so the bucketing is not a confound).

| Axis | Signal | Source (main dir, read-only) | Buckets |
|---|---|---|---|
| **A1 Vol** | VIX level | `data/panels/vix.csv` `^VIX` (2007–26) | terciles low/mid/high (+ quintiles for top-Q metric) |
| **A2 Dollar** | DXY 3m momentum = DTWEXBGS/DTWEXBGS.shift(63)−1 | `data/raw/fred_BAMLH0A0_DGS3MO_DTWEXBGS_d06fce80fc.parquet` `dtwexbgs` | terciles USD-down/flat/up |
| **A3 Credit** | HY OAS level | same parquet `bamlh0a0hym2` (2007–26) | terciles tight/mid/wide |
| **A4 Announce** | within ±1 trading day of **FOMC** (full sample) | `data/personal_book/post_fomc_drift/data_cache/fomc_events.csv` (2004–26) | binary |

Secondary / reduced-power (explicitly flagged, NOT in primary family):
- A4b NFP, CPI (`data/panels/economic_calendar.csv`, **2020+ only**), BoJ
  (`Forex/data/news_events_2020_2025.csv`, **2020–2025 only**, skip `#` header rows) ±1 bd.
- A1' VVIX, A3' 21d OAS change, contemporaneous (T) versions of A1–A3.
- **Q3 Day-of-week** (Mon–Fri, 5 buckets) — separate structural family.

Coverage caveat (pre-stated): VIX / DXY / HY OAS / FOMC cover the full 2013–2026 sample;
NFP/CPI/BoJ cover only 2020+ → their tests are reduced-power and secondary.

---

## 3. Loss-event definitions

**Q1 CHALLENGE (acute horizon):**
- *Primary event* = distinct calendar days on which ≥1 funnel cohort busts (full-sample dense
  sweep). Reported also cohort×retry-weighted. Cause-split bust_daily vs bust_floor.
- *Power-confirmation* = worst 1% / 5% of single-day book returns (vm-invariant left tail).

**Q2 FUNDED (cumulative horizon):**
- *Primary event* = funded-book **deep-drawdown days** = days with running drawdown ≥ p90 of
  the realized drawdown-depth distribution; PLUS daily −5% pierce days (rare at vm=1).
- *Power-confirmation* = worst 5% of rolling-5d and rolling-10d cumulative book returns.

---

## 4. Concentration test (pre-specified)

For each (event-set × axis): H0 = "loss events are distributed across regime buckets
identically to all trading days" (loss ⟂ regime).

- **Statistic:** χ² of independence on the (loss-day vs non-loss-day) × (regime bucket) table
  (2×3 for A1–A3, 2×2 for A4).
- **Primary p-value:** **random circular-shift permutation null** (B=5000): randomly rotate
  the regime-label series relative to the fixed (autocorrelated) event series, recompute χ²,
  p = P(χ²_perm ≥ χ²_obs). This preserves the serial structure of BOTH series and breaks only
  their cross-alignment — the autocorrelation-robust null. Naive χ² p reported alongside but
  does NOT govern. (Secondary robustness: stationary block bootstrap L=21.)
- **Magnitude (for overlay sizing):**
  - `lift_worst` = P(event | worst bucket) / base-rate.
  - `topQ_share` = fraction of events in the highest-risk **quintile** vs 20% baseline.
  - `tailmass_share` = fraction of total left-tail loss mass in the worst bucket vs its
    day-share (exposure).
  - rough avoided-loss = (event-share removed) at cost of (day-share exposure) if the worst
    bucket were sat out.

---

## 5. Multiple-testing control (pre-specified family)

- **PRIMARY family = 4 axes × {Q1 challenge, Q2 funded} = 8 tests**, all at T-1, circular-shift
  p. **Holm–Bonferroni** FWER control at α=0.05 (valid under arbitrary dependence; the two
  event sets overlap, so Holm is conservative-correct). BH-FDR q also reported.
- Everything else (contemporaneous T, quintile/rolling variants, NFP/CPI/BoJ 2020+, Q3 DoW,
  mechanism cross-tabs) is **SECONDARY/exploratory**, corrected within its own family (BH-FDR),
  and **no headline claim may rest on it**.

---

## 6. Pre-committed verdict rubric

Stated separately for CHALLENGE and FUNDED:

- **CONCENTRATED — overlay has a target** iff ≥1 PRIMARY axis survives **Holm at 0.05** with
  **lift_worst ≥ 1.5×** at **T-1**, AND the same axis is directionally consistent in the
  power-confirmation tail (and, where applicable, across challenge & funded). Then report the
  rough avoided-loss vs exposure cost — the thing a future overlay study would target.
- **DISPERSED — overlay has no target** iff no primary axis survives Holm at T-1, **or** the
  apparent concentration exists only contemporaneously and vanishes at T-1 (the trap). Then:
  state plainly that a macro overlay has nothing to aim at — do not spend trials on it.
- The contemporaneous-only outcome is reported explicitly as "looks concentrated, unexploitable".

## 7. Mechanism checks (descriptive, pre-listed)

- Co-loss decomposition: for worst book days, count negative sleeves + contribution Herfindahl
  → single-sleeve vs multi-sleeve (risk-off) days; cross-tab vs A1/A3.
- Per-sleeve Q3: J1 tail on BoJ days; gold+overnight tail on FOMC days; conditional CVaR vs
  unconditional.

## 8. Honesty guards

T-1 governs (not T) · circular-shift p governs (not naive χ²) · Holm over the pre-registered 8 ·
two book series (governor ON vs constant-sizing) cross-check the funded tail · sample caveats
(NFP/CPI/BoJ 2020+, GER40 2018–21 hole masked by engine) · CET/EET-vs-UTC absorbed by the
±1-day announcement window · this diagnostic mints **0 strategy trials** (no IC test, no
backtest of a rule) — it consumes the registry like session_H (a STOP/decision, +0).
