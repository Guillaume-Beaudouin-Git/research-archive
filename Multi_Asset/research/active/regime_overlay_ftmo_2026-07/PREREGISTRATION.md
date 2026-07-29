# PRE-REGISTRATION — Regime overlay on the deployed FTMO book

**Frozen: 2026-07-29 ~09:00 UTC, before any overlay number was computed.**
Author: research session `regime_overlay_ftmo_2026-07`. Nothing outside this folder is written.

---

## 1. The question

Public strategies claim a regime overlay reading (a) the **VIX term structure** and (b) **price vs its
200-day moving average**, cutting exposure to ~30% in stress, turns a −80% MaxDD into −33% while still
beating the index. Their book (70% GARCH vol-targeted multi-asset + 30% tech momentum) is **not our
object** and is not replicated: MaxDD −33% = 3.3× the FTMO static floor, β 0.47, and no FTMO vehicle.

**The only question tested here:** applied to the **book actually deployed on FTMO**, does a regime
overlay raise **p(pass)** and/or shorten **time-to-funded**?

Not tested, deliberately: ΔSharpe, ΔMaxDD in isolation, any claim about the public book.

## 2. Prior that conditions the test — L15

Project registry **L15**: *regime overlays on high-Sharpe (SR > 1.0) strategies give sub-threshold lift
(~1.7%/yr); only useful for strategies with MaxDD > 20%.* L15 does not close this branch, it conditions
it. So the **first computed quantity, before anything else**, is the deployed book's MaxDD.

**Gating rule (frozen):**
- If book MaxDD (at deployed sizing, unconstrained by the FTMO barriers) **< 20%** → L15 predicts
  failure; that is reported as the headline result and the overlay test is run anyway but read as a
  confirmation, not as a discovery.
- If MaxDD **> 20%** → L15's condition is met and the overlay test is the real decision.

Also distinguished from an adjacent, already-measured object: a **vol-scaling** overlay (reacting to the
book's own *realised* vol) was measured elsewhere as a **cost**, not an edge. This study tests a
**regime** overlay, i.e. cutting on an **exogenous** signal. Different object.

## 3. The book under test — exact reconstruction spec

The deployed book is **MONO** (memory `desk_audit_2026-07-24`): `w_xau = 0` for ~38-60 sessions and the
J1/USDJPY sleeve is off via its own suspension gate. What actually trades is the **overnight sleeve
US100 + GER40 on ON days (Monday, Tuesday)** — flat ~60% of calendar days.

Reconstruction (`build_book.py`), from the **audited cleanroom stack**, read-only:
- Engine: `data/ftmo_portfolio/audit_v2_independent/cleanroom/engine.py`, imported, **never modified**.
  Its accounting primitives (`_target_for_segment`, `_trade_to`, `_mtm`, `load_market`) are reused
  as-is: signed-$ notional, harmonic average entry, half-RT bps on |Δnotional|, nightly swaps from the
  measured `panel_swapL/S` panels × triple-day multiplier, 0.01-lot quantization, 60% margin cap.
- Market: `cache/sim_m5_repaired.parquet` (M5, 2013-09-25 → 2026-06-05, GER40 2018-2021 hole mask
  applied by the engine), swap panels, `outputs/phase0_rt_cost_bps.csv`.
- **Costs**: the engine's *measured* RT-bps panel + *measured asymmetric* FTMO swaps. The `spread`
  column of `data/deep_history_utc/` is **not used** anywhere (it is empty on a large share of bars and
  understates the real FTMO round-trip by ~2.4× when populated).
- Config: `on_w = 0.6`, `vm = 14`, `WT ≡ 0` (gold and J1 off = MONO), `orb_risk = 0` (ORB is
  challenge-OFF and is a day-counter, not a P&L driver), `margin_cap = 0.60`,
  `mrate = MRATE_SWING` (live Swing margin rates), `quantize = True`.
- **Constant-risk series**: equity is renormalised to 10,000 at each day's close (positions scaled
  proportionally, average entry unchanged). Consequence: `taper = glide = pace = 1` identically, so the
  series is the book's return stream **at constant deployed gross leverage**, which is exactly what
  `Portfolio/admission/barrier.py` expects ("book daily returns at the sizing actually deployed") and
  what a bootstrap requires (stationary, no compounding artefact).
- No FTMO barrier is applied inside the reconstruction; the barriers are applied afterwards by
  `barrier.py`, which is the tool under-test-independent.

**Sanity checks required before use** (fail ⇒ stop and report): non-zero on ~40% of days; ON days ⊂
{Mon, Tue}; realised daily vol and Sharpe of the same order as the audited `phase1c_sleeves.parquet`
`overnight` column after leverage adjustment.

## 4. Regime signals — exactly 3 variants, no sweep

Frozen thresholds, all standard/canonical, **no grid, no tuning**. Any threshold search after seeing
results invalidates the study.

| id | signal (all measured at close of the previous engine day) | stress condition |
|---|---|---|
| **O1** | VIX term structure `^VIX / ^VIX3M` (yfinance, free) | ratio **> 1.00** (backwardation) |
| **O2** | US100 close vs its **200-day** moving average | close **< MA200** |
| **O3** | O1 **OR** O2 | either fires |

Exposure map, frozen: `e_t = 0.30` when the regime is in stress, `e_t = 1.00` otherwise. (Reading of
"reduce exposure to 30% in stress". No intermediate levels, no smoothing, no hysteresis.)

The overlay is applied as a **per-day multiplier on `vm`** inside the engine's own sizing function, i.e.
it scales the notional target of every risk-posting segment — the exact live semantics of "trade
smaller today". It is applied on the **historical timeline**, before any resampling.

### 4.1 No look-ahead — explicit contract

The FTMO ON sleeve posts risk at **17:35 CET** (GER40) and **22:05 CET** (US100). 22:05 CET = 16:05 ET,
which is **before** the 16:15 ET VIX print of the same date. Therefore same-date VIX is unusable.

Frozen rule: **every regime input is reindexed onto the engine calendar and then shifted by one full
engine day** (`.reindex(dates, method="ffill").shift(1)`), so day *T*'s exposure can only depend on
information stamped strictly **before** day *T*. This is asserted in code (`assert_no_lookahead`) by
checking that the exposure series is unchanged when the future of the input is truncated. MA200 uses
daily closes from `data/deep_history_utc/US100_M1.csv` (true-UTC M1 → daily close), cross-checked
against `cache/panel_px.parquet` (corr ≥ 0.999 required).

## 5. The two mandatory comparisons

An overlay compared to *nothing* is not evidence. Both controls are frozen here:

1. **PLACEBO — random overlay, same duty cycle and same clustering.** 200 random **circular rotations**
   of the realised exposure series. A rotation preserves *exactly* the fraction of reduced days and the
   run-length structure of the overlay, and destroys only its **alignment** with returns. The overlay
   must beat the placebo **p95**, not the placebo mean.
2. **UNIFORM DE-LEVER — same volatility, no regime information.** A constant `c` applied every day,
   calibrated so the de-levered series has the **same realised daily volatility** as the overlaid
   series (primary), with the mean-exposure-matched constant reported as a secondary control. An
   overlay that does not beat this is a sizing parameter in disguise, obtainable for free by lowering
   `vm`.

## 6. Decision metric and evaluation protocol

Decision metric is **Δp(pass) on the FTMO 2-phase challenge** and **Δ time-to-funded (median, p90)**.
**Sharpe is not a decision metric here.**

- Barriers: `Portfolio/admission/barrier.py` `BarrierConfig` defaults = the live contract — +10% P1 /
  +5% P2, **−5% daily**, **−10% static floor** (FTMO DD is static, memory `ftmo_dd_model_static_2026-07`),
  min 4 trading days per phase, no time limit.
- Paths: stationary block bootstrap (Politis-Romano, `marginal.stationary_bootstrap_indices`),
  mean block 10 days. **Never iid** — the book's returns cluster (2 ON days a week).
- **Paired**: every variant is evaluated on the **same** bootstrap index draws (same seed, equal-length
  series), so Δp is free of Monte-Carlo noise across variants. Per-path outcomes are retained so the
  CI on Δp is a **paired** bootstrap over paths, not two independent binomials.
- N paths = 20,000 baseline/variant; 200 placebo rotations × 4,000 paths.
- **Death decomposition mandatory**: p(fail daily barrier) vs p(fail static floor). A regime overlay's
  theoretical mechanism is cutting the extreme *days*, so the gain must show up mainly on the **daily**
  barrier. A gain arriving anywhere else is treated as suspicious and reported as such.

## 7. Verdict rule — frozen before results

- **PASS** — requires *all* of: (a) Δp(pass) > 0 with a paired 95% CI excluding 0; (b) overlay p(pass)
  **above the placebo p95**; (c) overlay p(pass) **above the vol-matched uniform de-lever**; (d) the
  gain is concentrated on the daily-barrier death channel.
- **UNDERPOWERED** — Δp(pass) point estimate positive but CI straddles 0, or the placebo band is too
  wide to separate it.
- **REJECTED** — Δp(pass) ≤ 0, or the overlay does not beat placebo p95, or it does not beat the
  vol-matched de-lever (⇒ it is a de-lever in disguise).

Multiple testing: 3 overlay variants → the best-of-3 is read against the placebo distribution, which is
itself the multiplicity control (the placebo band is the null of "any exposure schedule with this duty
cycle"). No DSR is quoted because the decision metric is a probability, not a Sharpe.

## 8. What would make me stop early

- Book MaxDD < 20% → L15 condition unmet → report it first as the headline (still run the test).
- Reconstruction sanity checks fail → stop, report the reconstruction problem, no verdict.
- VIX3M coverage shorter than the book history → truncate the sample and say so.
