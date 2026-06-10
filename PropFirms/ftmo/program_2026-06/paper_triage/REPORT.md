# Paper-corpus triage + orthogonal backtest — REPORT

**Date:** 2026-06-08 · **Task:** triage the accumulated paper/idea corpus by **structural orthogonality**
to the proven-exhausted box, then **backtest only** structurally-orthogonal survivors **whose data exists,
one at a time**, at honest cumulative N. The danger is **not** missing an edge — it is **manufacturing a
false positive by inflating N**. Most papers re-enter an already-closed box → **rejected at triage**.

**Scope discipline:** READ-ONLY on source data, `_automation/`, and prior deliverables; all new artifacts
written only under `research/paper_triage/` (`build_daily_commod.py`, `commodity_tsmom_backtest.py`,
`commodity_tsmom_results.json`, `cache/`). Reused **verbatim**: `funnel_lib` → `CFDCostModel`
(`cfd_costs.py`), `combined_pass_prob_empirical` (`ftmo_first_passage.py`), `deflated_sharpe_ratio`
(`dsr.py`); frozen pre-registered noise floor `SE0=0.845` (`gate0_noise_floor.json`).

---

## 0. Headline

**No orthogonal idea beat the ceiling.** The commodity frontier the goal points to splits in two, and both
halves are now closed:

1. **Commodity *carry/basis* (the signal the goal calls "L37")** was **already closed by a prior same-day
   session** (`commodity_carry_feasibility` memory + `data/ftmo_research/commod_carry_makeorbreak.md`):
   dynamic point-in-time basis Sharpe **−1.15** (t=−5.18, inverts every sub-period), 2020-contango tail
   (**L31**), and **one-sided-uncollectable** on retail CFD — short-oil-in-contango swap **−64%/yr** (**L32**).
   That prior work also flags the goal's **"L37" as a mislabel** (L37 in project memory is a filter-sanity
   lesson, *not* carry). I do **not** re-test the carry signal — it is bucket A (closed).
2. **Commodity *trend* (TSMOM) as a standalone FTMO book** — the residual that prior work measured only as
   "≈0.12 Sharpe" — had **not** been run as a full causal backtest. I ran it (the one new test here). It is
   **sub-threshold and independently REPRODUCES the prior numbers** (TSMOM ≈0.12–0.14; the L32 one-sided-carry
   killer; oil-concentration). It confirms the ceiling; it does not break it.

L37/the swap snapshot *is* real and now quantified (FTMO long swap: USOIL **+14%/yr**, UKOIL **+9%/yr** at
recent prices — long energy is genuinely *paid* to hold) — but it is a **directional long-oil tailwind, not a
systematic two-sided edge**, and it does not manufacture a survivor:

| Commodity TSMOM (6 FTMO-executable, real cost+swap, OOS untouched) | full Sharpe [90% CI] | OOS Sharpe [90% CI] | DSR@N=108 | WF | p(pass) FTMO / FundedNext |
|---|--:|--:|--:|--:|--:|
| **Symmetric L/S** (standard TSMOM) | **−1.07** [−1.66, −0.53] | −0.56 [−1.84, 0.81] | 0.00 | 1/6 | 0.089 / 0.109 |
| **Long-only** (the L37-favorable config) | **+0.14** [−0.44, 0.71] | +0.96 [−0.47, 2.36] | 0.02 | 4/6 | **0.323 / 0.355** |

Both fail every gate: full-history Sharpe ≤ 0.14, DSR ≈ 0 (need > 0.5), OOS Sharpe far below the frozen
noise floor (**2.17** to beat at N≈110), and p(pass) parks at the **same ~0.33 wall** the whole program
keeps hitting. The mechanism **reproduces L32**: the carry helps the **long leg only** — **shorting**
backwardated commodities is brutally expensive (USOIL short ≈ **−65%/yr**), which destroys symmetric L/S.
Net of the still-heavy CFD spread, the underlying commodity-trend signal is too thin for either barrier.
**The ceiling is confirmed, not broken.**

---

## 1. Existing-triage ingest (extend, don't redo)

The routines and prior sessions had already done most of STEP 1–2. What I ingested and what changed:

**A. `_automation/synthesis/` + `_state.json` (the routine triage).** W22 was a **data drought** (0 new
arxiv papers, alpha_hunt 0 retained). The five tracked themes are all **DECLINING** → bucket-A by the
saturated-theme rule. Open hypotheses **H001** (funding-OU speed → Strategy-B carry) and **H002** (vol-ratio
scalar → Strategy-A v4) are *existing-strategy overlays*, not orthogonal new sources. The 3 deep-dived arxiv
papers are all pre-tagged and re-confirmed here: **2605.04004** MNQ falsification → REFERENCE_ONLY (confirms
the box); **2605.05089** DeFi collateral → TEST_LATER (Strategy-B mainnet ~2026-07-17); **2605.27848**
HMM+RL regime → REFERENCE_ONLY (bucket-A regime overlay, L15).

**B. Prior `research/paper_triage/PAPER_TRIAGE.md` (structural, 0 backtests).** Ranked bucket B
**B1 (FINRA→NQ overnight) ≫ B2 (options-implied) > B3 (earnings) ≈ B4 (central-bank text)**. I adopt its A/C
buckets wholesale. **Two gaps I close:** (i) it predates the commodity facts, so its bucket B contained **no
commodity idea at all** — I add the commodity-*trend* standalone book as the new top survivor (the
commodity-*carry* variant being separately pre-closed, §1.D); (ii) it ran no backtests.

**C. Prior sessions already RESOLVED two of its top-4 — I do not re-test them:**
- **B1 (FINRA short-volume → NQ overnight): FAIL at the IC gate** (`research/b1_feasibility/`). The
  swap-free-axis thesis held, but the *signal* is absent: clean QQQ short-ratio IC is null (|HAC t|≤1.4);
  the only near-miss (NDX-aggregate) is survivorship-optimistic and still |t|=2.37 < 2.5. Closed cheaply,
  correctly — no full backtest justified.
- **Non-symmetric container pivot (FTMO-Swing / FundedNext): NO-GO** (`research/container_eval/`). A
  container change *alone* lifts the existing swap-net book from p(pass) 0.329 → **0.371** (FundedNext 8%
  target) — a real +4 pts, but ~13 pts short of 0.50. The wall is the **~0.30 swap-gated Sharpe**, not the
  barrier.

**D. The commodity-CARRY angle was already closed (prior same-day session) — I do not re-test it.**
`commodity_carry_feasibility` memory + `data/ftmo_research/commod_carry_makeorbreak.md`: the static
swap-snapshot carry (Sharpe +0.46) is hindsight; the **dynamic point-in-time basis is Sharpe −1.15**
(t=−5.18, inverts every sub-period — oil was contango 57% of 2006–2026, e.g. 2009 −40%, 2020 −61%). Two
structural kills: **L31** (2020 negative-price/contango tail) and **L32** (one-sided-uncollectable — the
real per-leg CFD swap charges **−64%/yr** to short oil in contango; 77% oil-concentrated). That work also
notes the goal's **"L37" is a mislabel** (L37 = a filter-sanity lesson; the carry lessons are L31/L32) and
that *no futures term structure is on disk* (single-price CFDs), so the basis is unmeasurable here without
paid deferred-contract curves. **Commodity carry/basis → bucket A (closed).**

**E. What legitimately remained: commodity TREND as a standalone book.** The prior work measured commodity
**TSMOM only as a ≈0.12 residual** inside the carry deep-dive — it never ran it as a full causal FTMO book
with WF/DSR/p(pass)±CI and swap/spread/universe robustness. The 6 commodities are **both on disk and
FTMO-executable**, and `PROGRAM_DECISION_MEMO §2` lists "energy/silver … excluded, not tested". That
standalone trend-book test is the **one new backtest** here (§3) — and it independently reproduces the prior
≈0.12 and the L32 carry asymmetry.

---

## 2. Full corpus classified A / B / C

### Bucket A — IN THE CLOSED BOX → REJECT (one-line structural reason)

| Cluster | Why it's in the box (prior result) |
|---|---|
| MNQ/NQ intraday signal variants (2605.04004; triage "C1" trailing-SL iter_11) | free-price NQ intraday, symmetric barrier; iter_10 already invalidated (`strategy_c_iter10_validation`) |
| Regime overlays (HMM+RL 2605.27848; quantinsti HMM; k-means/PCA; "surfing equity curve"; triage "C2" HMM on D3+D5) | a regime *filter* on a free-price edge stays in the box; L15 caps lift to ~+1.7%/yr; `orb_regime_2026-06` (no forward predictor passes \|t\|>1.5) |
| Strategy-A-v4 mods (tweedie, EGARCH, vol-ratio H002, "rethinking trend", "why momentum struggling") | vol/regime overlays on free-price crypto TSMOM; A is FROZEN; 3-mod-budget items, not box-escapes |
| Daily momentum / GTAA / TAA / dual-momentum / Donchian / 60-40 | free-price daily momentum/allocation on liquid ETFs; commodity-TSMOM-ETF archived (AMTP p=0.808); gold-BTC dual-mom fails L11 pre-flight |
| Pairs / stat-arb ("cointegrated pairs", "the metamorphosis") | price cointegration; pairs archived (0/19, Gatev SR −0.44) |
| FX price/regime ("ai forex llm regime", "eur hedge", "currency you didn't choose") | FX price/regime, USD-base; FX archived n=181 (FX-1→4, Strategy E, L23) |
| **VRP / options-pricing / vol-surface / skew** ("vrp intraday clustering", PIDE option pricing, IV solvers) | **VRP family ARCHIVED (L13)**: BTC VRP gross 4.4% < cost 8.9%; SPX VRP IC negative. `data/vrp/`, `data/skew_research/` already explored. Better pricing math ≠ economics. |
| Insider / prediction-markets / EM-equity / attention-sentiment | archived/closed angles; L17 (FGVD), L18 (Wikipedia) — Da-et-al attention taxonomy exhausted |
| "Index of commodity futures since 1871" / "commodity portfolio for 2026" | reference dataset / generic commodity momentum — **subsumed by the bucket-B trend backtest below** (tested, sub-threshold) |
| **Commodity carry / basis** ("backwardated pay +long carry") | **resolved NO-GO** (`commod_carry_makeorbreak.md`): dynamic basis Sharpe −1.15; L31 tail + **L32 one-sided-uncollectable**; no term structure on disk. The goal's "L37" mislabels this. |
| **B1 FINRA→NQ overnight** *(was bucket B)* | **resolved FAIL** at IC gate (`b1_feasibility`); clean signal null |

### Bucket B — STRUCTURALLY ORTHOGONAL → testable (each rests on ≥1 uncovered thing)

Ranked by **orthogonality × retail-feasibility × cost-to-test**, with the **one decisive feasibility
question** (usually: data on disk?).

| Rank | Idea | Wall(s) broken | Decisive question | Data on disk? | Status |
|---|---|---|---|---|---|
| **1** | **Commodity TSMOM (trend) standalone FTMO book** (new universe) | new universe (FTMO-16 never traded commodities ex-gold); prior work only measured it as a ≈0.12 residual | does the standalone trend book clear once costed end-to-end as an FTMO book? | **YES** — 6 commods on disk + FTMO swaps measured | **TESTED → §3 (sub-threshold; reproduces ≈0.12 + L32; confirms ceiling)**. *(Carry/basis variant = bucket A, pre-closed L31/L32.)* |
| 2 | B1 FINRA short-vol → NQ overnight | new data + overnight axis + swap-free futures | does the FINRA→NQ IC survive at N≥50/yr? | fetchable | **RESOLVED: FAIL** (prior session) |
| 3 | B2 options-implied (put-call disparity / skew) as *directional* signal | options-implied data source | does PCR/skew predict **direction**, standalone (not a regime overlay)? | partial (VIX term, CBOE PCR) | **RECLASSIFIED → A** (VRP/skew archived L13; PCR-directional = index signal under symmetric barrier ⇒ re-enters box). *Narrow PCR-directional IC gate remains a cheap future option, but not orthogonal enough to test now.* |
| 4 | B3 event-microstructure (earnings-day direction) | new return source (scheduled-event) + alt-data | low-infra retail reduction exists? | **NO** (equities intraday at scale) | untested — data-blocked |
| 5 | B4 central-bank / 10-K text sentiment | alt-data *content* (vs archived *attention* L17/L18) | off-the-shelf hawkishness index usable? | **NO** | untested — data-blocked |

### Bucket C — METHOD / TOOLING (audit toolkit, not strategy pipeline)

Post-selection Sharpe de-biasing (2606.01650 → hardens DSR/L20); non-linear cost model (→ `sizing_analysis`);
retrospective/Brownian-bridge path gen (→ `trailing_dd_simulator`); spot-perp basis rebalancing (2605.05089
→ Strategy-B mainnet prep); effective-N / backtests-lie / conformal / heavy-tails / Bayesian-allocation
(combination tooling, already covered by DSR/HAC/first-passage). **H001** (funding-OU → Strategy-B sizing)
is a Strategy-B operational improvement, not a new return source.

---

## 3. Backtest #1 — Commodity TSMOM on the new FTMO-executable universe, with L37 carry

**Pre-registration / spec (one idea).** Universe = the **6 commodities that are both on disk AND
FTMO-executable** (ftmo_specs has only 21 tickers): `USOIL, UKOIL, XAGUSD, COCOA, COFFEE, SOYBEAN`
(NGAS/COPPER/SUGAR/COTTON/OJUICE/DIESEL are **not FTMO instruments** → non-deployable, excluded; gold is
already in the FTMO-16). Signal = causal blended TSMOM (sign of trailing {60,120,250}-day return, gated at
|·|≥0.34, **shift(1)**), vol-targeted per leg, equal-weight book. Two directional modes: **symmetric L/S**
(standard) and **long-only** (the L37-favorable config). **Real costs:** ECN spread × markup 3.0 × **+50%
stress** (uncalibrated-spread caveat) + 1 bp slippage; **signed per-night FTMO swap** (the L37 carry),
×1.45 weekend multiplier. OOS = 2025-01-01.. untouched. Window 2017-12 → 2026-06 (≈8.5y, all 6 present).

**The carry, quantified (annualized long-side, recent prices):** USOIL **+14%/yr**, UKOIL **+9.4%/yr**,
COFFEE +2.5% — vs XAGUSD **−29%/yr**, COCOA **−15%**, SOYBEAN **−9%**. Shorts: USOIL **−65%/yr**, UKOIL
−44%, COFFEE −15%. **L37 confirmed for energy longs; shorting backwardated energy is the new killer.**

### 3.1 Results

**Cumulative N = 108** (103 prior + 5 honestly-distinct signal configs: sym-blend, long-blend, sym-L60,
sym-L120, sym-L250). Counting the 2 sub-universe books (energy-2, energy-silver-3) → ≤110; **immaterial**
(DSR benchmark E[max] moves 2.12→2.13, DSR stays ≈0). Swap/spread sweeps are cost-sensitivity on fixed
signals, not selections. DSR call mirrors the program verbatim: `n_trials=N, periods_per_year=252,
std_sr_trials=0.845`; survivor at DSR > 0.5. Noise floor to beat (OOS Sharpe): **2.14 @N100, 2.17 @N110**.

**Signal configs (EW-6, swap=base measured, spread ×1.5):**

| config | full Sharpe [CI90] | IS | OOS [CI90] | WF (pos/6) | DSR_oos | DSR_full | exkurt |
|---|--:|--:|--:|--:|--:|--:|--:|
| sym_blend | −1.07 [−1.66,−0.53] | −1.18 | −0.56 [−1.84, 0.81] | 1/6 | 0.00 | 0.00 | 6.2 |
| **long_blend** | **+0.14 [−0.44, 0.71]** | −0.04 | **+0.96 [−0.47, 2.36]** | 4/6 | 0.02 | 0.00 | 8.3 |
| sym_L60 | −1.73 | −1.88 | −0.98 | 0/6 | 0.00 | 0.00 | 2.5 |
| sym_L120 | −1.42 | −1.35 | −1.77 | 1/6 | 0.00 | 0.00 | 2.9 |
| sym_L250 | −1.16 | −1.27 | −0.63 | 1/6 | 0.00 | 0.00 | 1.9 |

**Headline p(pass) ± CI (first-passage MC, scaled to 1%/day).** A commodity TSMOM book *holds overnight and
weekends* → FTMO-**Standard** is illegal for it; the "FTMO 10/5" column **is the FTMO-Swing geometry** (legal
overnight, identical 10/5 barrier — per `container_eval`), shown alongside FundedNext Stellar 8/5:
- Symmetric: FTMO-Swing 10/5 = **0.089** [0.084, 0.094]; FundedNext 8/5 = 0.109 [0.103, 0.114].
- Long-only: FTMO-Swing = **0.323** [0.313, 0.334]; FundedNext = **0.355** [0.345, 0.366]. *(same ~0.33 wall)*

**Per-year Sharpe (long-only headline):** 2017 +4.2, 2018 +0.4, 2019 −2.5, 2020 −1.1, 2021 +0.1, 2022 +0.4,
2023 −0.7, 2024 +1.4, 2025 +0.5, 2026 +1.7 → **5 of 10 years negative, no persistence**; the positive
full-sample tilt rides 2017/2024/2026, not a stable edge.

### 3.2 Robustness (does the verdict hinge on an assumption? No.)

- **Swap** (EW-6, sym | long): swap-*free* −0.27 | **+0.37**; base −1.07 | +0.14; contango-stress −1.36 |
  −0.21; double −1.86 | −0.09. **Even with zero swap, the long book is only +0.37 full** — the optimistic
  current-snapshot carry is *not* what's missing; the trend signal is.
- **Spread** (×1.0/1.5/2.0, sym | long): −0.87/−1.07/−1.27 | +0.27/+0.14/+0.01. Sub-threshold even at the
  *least* punitive cost (markup 3.0, no stress).
- **Universe** (long-only): energy-2 full +0.10 / OOS +1.09 / WF 3/6 / DSR 0.03 / pFTMO 0.21;
  energy-silver-3 full **−0.48** / OOS +1.67 / DSR 0.15 / pFTMO 0.12. The OOS-positive-but-full-negative
  pattern = edge concentrated in the recent window only → **fails the "hold on full history" requirement.**
- **Per-leg standalone (full Sharpe):** USOIL −0.83, UKOIL −0.75, XAGUSD −0.45, COCOA −0.91, COFFEE −0.09,
  SOYBEAN −0.24. **No single leg has a robust net-of-cost trend edge.**

### 3.3 Verdict — Backtest #1

**SUB-THRESHOLD / REJECTED — confirms the ceiling and independently reproduces the prior commod-carry
NO-GO.** The symmetric strategy is *killed* (full −1.07, p 0.089) by the **L32 mechanism**: shorting
backwardated commodities pays a punitive swap (this is the same one-sided-uncollectable finding the prior
session documented, here reproduced from the trend side). The long-only config is the *only* positive
variant, but its edge is indistinguishable from noise (full Sharpe **0.14 ≈ the prior work's ≈0.12 TSMOM
residual**, CI spans 0; DSR ≈ 0; OOS Sharpe ≪ noise floor 2.17; full history fails) and its p(pass) lands at
**0.32–0.36 — the identical ~0.33 wall**. **The positive long-energy swap is a directional tailwind, not a
two-sided edge; it does not lift commodity trend over the bar.**

---

## 4. Why no 2nd backtest was run (report-then-decide, ruthless on bucket A)

Protocol = test survivors **one at a time, in rank order, whose data exists**, stopping to report each. After
#1: rank-2 (**B1**) and the container pivot are **already resolved** (FAIL / NO-GO). Rank-3 (**B2
options-implied**) has partial data on disk **but reclassifies to A**: the VRP/skew sub-angle is archived
(L13) and a put-call-ratio *directional* signal on an index under the *symmetric barrier* re-enters the
closed box. Advancing it to a backtest would **inflate N for a likely-bucket-A idea** — exactly the false
positive this task exists to prevent. Ranks 4–5 (B3 earnings, B4 central-bank text) are **data-blocked**.
**No remaining survivor has both orthogonality and on-disk data → backtesting stops here, correctly.**

---

## 5. Overall statement

**Did any orthogonal idea beat the ceiling? No — it confirmed the ceiling, and the "new" commodity frontier
turned out to be already mapped.** The commodity-*carry* signal was pre-closed (L31/L32, prior session); the
commodity-*trend* book — the only piece that hadn't been run end-to-end — was tested here and lands
sub-threshold (best honest config: full Sharpe 0.14 ≈ the prior ≈0.12 residual, DSR ≈ 0, p(pass) ~0.33),
**independently reproducing** the prior result from a fuller angle. This *triangulates* both
`PROGRAM_DECISION_MEMO` and `commod_carry_makeorbreak.md`: the wall is **distribution-shape-vs-barrier + thin
post-cost Sharpe + one-sided-uncollectable carry (L32)**, and it holds on a new universe whose long-energy
swap *inverts* the prior #1 killer only on the long side. The ceiling is universe-and-barrier-robust, not a
quirk of the FTMO-16.

**Lesson — CONFIRMS L31 + L32 (not a new lesson); corrects a task mislabel:** *The goal framed "commodity +
L37 positive carry" as an untested orthogonal escape. It is not untested: commodity carry/basis is a
documented NO-GO (dynamic basis Sharpe −1.15; L31 2020-tail; L32 one-sided-uncollectable — short-oil-contango
swap −64%/yr), and "L37" in project memory is a filter-sanity lesson, not carry. This run adds the missing
piece — a full causal standalone backtest of commodity TSMOM as an FTMO book — and independently reproduces
both the ≈0.12 trend residual and the L32 carry asymmetry (symmetric L/S destroyed by the −65%/yr short-energy
swap; long-only sub-threshold at p(pass)~0.33). Net: commodity trend does not escape the symmetric-barrier
ceiling. Residual caveat: the FTMO swap is a 2026 snapshot, but the verdict is swap-robust (sub-threshold even
swap-free), so a historical swap series would not change it. Do NOT re-propose commodity carry/trend as
orthogonal without PAID deferred-futures curves.*

### Rejected for RE-ENTERING the closed box
NQ/MNQ intraday variants & trailing-SL iter_11 · HMM/RL & all regime overlays (D3+D5, Strategy-A v4) ·
GTAA/dual-momentum/Donchian/60-40 · cointegrated pairs · FX price/regime signals · **VRP / option-pricing /
vol-surface / skew (L13)** · attention-sentiment (L17/L18) · **B1 FINRA→NQ (resolved FAIL)** ·
PCR-directional-on-index-under-symmetric-barrier (B2) · **commodity carry/basis (resolved NO-GO, L31/L32 —
the goal's "L37 untested orthogonal" premise; the *trend* book was the only genuinely-unrun piece and it too
is sub-threshold)**.

### Untested for lack of data / infra (not claimed dead — flagged)
- **B3 earnings-day direction** — needs equities intraday at scale + earnings calendar (not on disk).
- **B4 central-bank / 10-K text content** — needs an off-the-shelf hawkishness index or an NLP pipeline.
- **Historical commodity roll/backwardation series** — would let the L37 carry be time-varying rather than a
  2026 snapshot (result is swap-robust, so low priority).
- **Order-flow / tick / book microstructure** — not on free feeds; not retail-FTMO-executable.
- **Paid alt-data** (Glassnode stablecoin; point-in-time index constituents for a survivorship-clean B1) —
  cost-gated, deferred.

---

*Causal throughout (signal ≤ t-1); real costs incl. signed per-night swap; OOS 2025-01.. untouched;
walk-forward 6 folds; daily Sharpe + block-bootstrap 90% CI; DSR at true cumulative N with the frozen
SE0=0.845; p(pass)±CI under FTMO (10/5) and FundedNext (8/5). Infra reused verbatim. Commodity spreads
ECN-uncalibrated → headline at +50% stress. Nothing fabricated — every data gap (FTMO swap snapshot,
non-FTMO commodities, B2/B3/B4 data) is reported, not guessed. Artifacts: `build_daily_commod.py`,
`commodity_tsmom_backtest.py`, `commodity_tsmom_results.json`, `cache/`.*
