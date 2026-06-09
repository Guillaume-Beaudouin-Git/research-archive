# HYPOTHESIS.md — Long-only oil backwardation carry-timing on FTMO (pre-registered)

**Study ID:** `backwardation_oil` · **Frozen:** 2026-06-10, BEFORE data contact · **Trials:** program N 108 → 111
**Verdict doc:** `report.md` (same dir) · **No parameter rescue permitted after this commit (L10).**

**Data-contact attestation at freeze time:** no market-data file has been opened or fetched for this study.
Inputs read so far: `ftmo_specs_full.csv` (contract metadata: digits/swaps/3x-day/commission — not a time
series), `code/ftmo_swaps.py` (sign/units conventions), prior reports (`commod_carry_makeorbreak.md`,
`research/commodity_carry_feasibility/*.md`), file listings (names only). No price, basis, or return series.

---

## 0. Provenance and label

- Task labels the thesis "L37 systematized". Per `CARRY_FEASIBILITY.md` §corrections, "L37" in
  `STRATEGY_RESEARCH_LOG.md` is actually a filter-sanity lesson; the substantive antecedents are
  **L31** (regime-bound carry → mandatory tail test) and **L32** (commodity CFD carry is
  one-sided-uncollectable: short-contango leg costs −46 to −64%/yr in swap). Label kept for traceability.
- Prior art: `commod_carry_makeorbreak.md` killed the **two-sided rotation** (dynamic Sharpe −1.15,
  t=−5.18). It explicitly left open: *"you can collect the long-backwardation side."* This study tests
  exactly that residual claim, once, pre-registered.
- Adversarial prior: `research/commodity_carry_feasibility/` (2026-06-08) closed the angle for **lack of
  on-disk term structure** and said re-opening requires a genuine historical term-structure dataset.
  A free one exists (EIA official daily WTI contract-1/2 settles) — see §4 deviation.

## 1. Hypothesis (falsifiable)

On FTMO, LONG USOIL/UKOIL **only when the front of the curve is in sufficient backwardation** is
carry-advantaged: the nightly long swap is then a credit (specs 2026: USOIL.cash swap_long **+36.55
pts/night**, UKOIL.cash **+27.62**, type=points, digits=3, Friday 3x, zero commission ⇒ ~+14–20%/yr at
plausible prices), and the backwardation gate should keep the book flat through contango/crash regimes
that kill always-long oil. This is **carry-conditioned beta timing, long-only by construction** (L32
forbids the short leg). It is NOT claimed as two-sided alpha.

## 2. Pre-registered rule (zero remaining degrees of freedom)

- **Instruments:** USOIL = **primary and gate-deciding**. UKOIL = secondary, reported, never gate-deciding
  (its basis construction is lower-quality, §4). Registered variants: (a) USOIL solo [primary],
  (b) UKOIL solo [secondary], (c) 50/50 fixed-weight sleeve [secondary; legs gated independently;
  no re-normalization when one leg is flat].
- **Signal:** annualized front basis `B_ann(t) = (F1_t / F2_t − 1) × 12` (adjacent monthly WTI contracts).
  UKOIL secondary leg: `B_ann(t) = (Spot_t / F1_t − 1) × 12` (dated-Brent vs ICE front; known scale bias
  toward 0 since the spot→F1 gap averages <1 month — conservative-leaning, frozen, documented).
- **Threshold:** θ = +5%/yr. Long iff `B_ann > 0.05`. Frozen here; never tuned.
- **Schedule:** weekly. Evaluation at the last trading day of week W (T−1, usually Friday, using that
  day's settle — publicly known before the next trading day). Position applies from the first trading
  day of week W+1 at its **close** (T) and is held to the next week's T. Signal at T−1, trade at T (L1).
- **Position:** binary {0, 1} per leg. No pyramiding, no vol targeting inside the gate backtest (binary
  single-asset exposure; FTMO sizing is the MC stage's job, only if gates pass).
- **Modifications budget:** 0 consumed, 0 permitted post-data.

## 3. Net P&L model (FTMO CFD)

`ret(t) = pos(t−1) · [ price_ret(t) + swap_yield(t) ] − half_spread · |pos(t) − pos(t−1)|`

- **price_ret:** close-to-close on the cash-CFD price series. Primary source
  `data/deep_history_utc/{USOIL,UKOIL}_M1.csv` resampled to daily closes (Dukascopy cash CFD, true-UTC,
  roll embedded in swap ⇒ spot-like path whose drift EXCLUDES collectable basis). Fallback (gaps or
  absence): `data/raw/yf_CL=F_1d_*.parquet` / `yf_BZ=F_1d_*.parquet` (front-month continuous with roll
  jumps included ⇒ same spot-like category). Either way the collectable basis enters ONLY via the swap
  term — no double counting.
- **swap_yield(t):** `(B_ann(t−1) − markup_ann) / 365 × nights(t)`, accrued only while in position.
  `nights(t)` = 3 if the previous trading day is a Friday, else 1 (specs `swap_3x_day=Friday`;
  7 accrual-nights/week ⇒ 364/yr).
- **markup_ann** (constant; the broker's financing+take, the only calibrated quantity):
  `markup_ann = B_ann(t0) − swap_long_ann(t0)` at t0 = last common sample date, where
  `swap_long_ann(t0) = swap_long_pts × 10^−digits × 364 / P(t0)` (per `ftmo_swaps.py` convention;
  USOIL: 36.55 pts, digits 3; UKOIL: 27.62 pts). If the calibration yields markup_ann < 0, floor at 0
  and FLAG: the model then favors the strategy, so only a NO-GO verdict is robust.
- **Spread:** frozen at **7 bps of notional per round trip** (3.5 bps per side; FTMO USOIL typical raw
  spread ≈ 2–6 bps RT — mildly conservative). Commission 0 per specs. Sensitivity ×0.5 / ×2 reported,
  non-gating (turnover is capped at ≤52 RT/yr by the weekly schedule).
- **Return convention:** CFD margin product ⇒ daily strategy returns are excess-return-like (financing
  lives inside markup_ann); rf=0, PPY=252 (consistent with the program's Ross-Hook precedent).

## 4. Pre-declared deviation — reconstruction of the dynamic basis

The task says *"reuse the dynamic basis series… (`outputs/basis_oil.parquet`)"*. **That artifact is absent
from disk** (verified by `find` 2026-06-10; independently documented in `CARRY_FEASIBILITY.md` §"Prior
primary artifacts are gone"). Frozen reconstruction policy, decided before fetching:

- **USOIL basis:** EIA official daily histories, Cushing WTI futures **contract 1** (`RCLC1`) and
  **contract 2** (`RCLC2`) settles, 1983→present. A genuine **point-in-time dynamic term structure** —
  the same object the prior study built against a real deferred contract, NOT a static swap snapshot,
  so the L26 static→dynamic requirement is satisfied by construction.
- **UKOIL basis:** no free historical Brent F2 exists. Secondary construction: EIA Europe Brent spot FOB
  (`RBRTE`) vs ICE front future (`yf_BZ=F`). Quality precondition: ≥15y overlap and no systematic
  staleness; else the UKOIL leg is DROPPED and documented. UKOIL is non-gate-deciding either way.
- If the EIA fetch fails entirely, the study **HALTS and reports the blocker** — no proxy substitution,
  per the feasibility report's "FAIL rather than fabricate a term structure".

## 5. Kill criteria (frozen; evaluated on the USOIL primary; any K1–K3 fail ⇒ NO-GO)

- **K1 — binding tail (L31, pre-committed):** with the pre-registered rule and point-in-time basis, the
  USOIL position must be **flat every day in [2020-02-01, 2020-04-30]**. Any long day in that window ⇒
  **NO-GO, no parameter rescue** (θ was pre-registered).
- **K2 — alpha-vs-beta (decisive):** `SR_net(strategy) − SR_net(always-long USOIL, same net-cost model
  incl. dynamic swap) ≥ +0.20` required. (Sharpe is invariant to constant exposure rescaling; the
  time-in-market-rescaled comparison is additionally reported for return/DD levels.) Supporting,
  non-gating: in-regime vs out-of-regime mean daily net return difference with HAC lag-6 t-stat.
- **K3 — absolute level:** net Sharpe < 0.5 ⇒ NO-GO standalone; < 0.3 ⇒ NO-GO even as sleeve candidate.
- **K4 — regime decomposition (L31):** net P&L by era {sample-start→2013, 2014→2020, 2021→2023,
  2024→2026}. If the 2021–2023 era contributes >80% of total net P&L, OR the pre-2014 in-regime spells
  sum to ≤0 net, the best possible outcome downgrades to **watchlist** (single-episode harvest, L27
  analogue) — not GO.
- **K5 — swap-sign audit (L30):** recompute today's long-swap bps/night from `ftmo_specs_full.csv` via
  the `ftmo_swaps.py` convention and verify the backtest's accrual at t0 matches in sign and magnitude
  (±10%), and that one full in-position week accrues exactly 7 nights. A discovered sign/units error is
  corrected and the study re-run ONCE, with the error documented (audit ≠ tuning).

## 6. Statistics (frozen conventions)

- Net Sharpe annualized √252 on daily returns; **HAC lag-6** t-stat on the mean daily net return.
- **DSR** = probabilistic Bailey–LdP (convention P, bar >0.5), PPY=252, rf=0, reported at:
  N_trials=3 (headline: 2 prior family trials [makeorbreak static, dynamic] + this pre-registered one),
  N_trials=5 (as if UKOIL and 50/50 were selection candidates), N_trials=111 (paranoid program floor,
  std_sr 0.845 per funnel convention).
- Stationary block bootstrap (Politis–Romano, mean block 21d, 1000 draws) for the SR confidence interval.

## 7. Only if ALL gates pass

MC p(pass) FTMO 2-step (canonical −5% daily / −10% static, +10% P1 / +5% P2) at 2–3 leverage levels with
bootstrap CI; worst single-day move at each leverage vs the 5% daily cap (the binding constraint);
correlation table vs the deployed TSMOM reference series and the commodity-seasonality sleeve
(anti-correlation requirement, L7). If any gate fails, none of this is run (no decoration of a corpse).

## 8. Registry

Program cumulative N: **108 → 111** (the task's "97" is the funnel-v2 figure, superseded by
edge_improvement→103 and paper_triage→108 per `research/positive_dsr_register/REGISTER.md` 2026-06-09).
Registered now, consumed regardless of outcome:

| trial | description |
|---|---|
| T109 | USOIL long-only B_ann>5% weekly, net FTMO swap model — **primary, gate-deciding** |
| T110 | UKOIL long-only (spot−F1 basis) — secondary |
| T111 | 50/50 USOIL+UKOIL sleeve — secondary |
