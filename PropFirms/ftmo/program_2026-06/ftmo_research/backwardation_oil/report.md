# Backwardation oil, long-only — VERDICT: **NO-GO (not even sleeve candidate)**

**Study:** `backwardation_oil` · **Run:** 2026-06-10 · **Pre-registration:** `HYPOTHESIS.md`, commit
`41f034f`, frozen BEFORE data contact · **Trials consumed:** 3 (IDs T109–T111 as frozen); cumulative
program N reconciled **112 → 115** (see Deviations §5) ·
**Engine:** `engine.py` (deterministic, seed 20260610) · **DSR (P, N=3):** 0.0007

## TL;DR

The long-only collectable side of oil CFD carry — the residual `commod_carry_makeorbreak.md` left open —
is now tested and dead. Long USOIL only when annualized WTI F1/F2 backwardation > 5% (weekly, T−1→T),
with the real FTMO swap credit modeled dynamically, earns **Sharpe −0.01 over 2005–2024** (HAC t −0.05).
The carry credit is real (+15%/yr in-market today, K5 audit clean) but the conditioned price beta cancels
it almost exactly: price leg **−1.03%/yr** vs swap leg **+0.96%/yr**. The pre-committed 2020 tail gate
PASSES — and that is the most informative result: the basis gate dodges **contango-led** crashes (flat
from Jan 2020) but rode every **backwardation-led** collapse (Lehman Oct 2008 −37%, Jul–Oct 2014 −24%,
Sep 2022 −12%). Backwardation is a demand-tightness signal that peaks near price tops; it cannot
distinguish which crash type comes next. All net positive P&L sits in 2021+ (the regime today's swap
snapshot reflects): **+0.33** for 2021–2024 vs **−0.36** for 2005–2020.

| gate | spec | result | pass |
|---|---|---|---|
| K1 binding tail (L31) | flat every day 2020-02-01→04-30 | 0/62 long days (last long: **2018-10-01**) | ✅ |
| K2 alpha-vs-beta | ΔSR vs always-long ≥ +0.20 | **+0.067** (−0.011 vs −0.078); regime-diff t = **0.49** | ❌ |
| K3 absolute | SR ≥ 0.5 standalone / ≥ 0.3 sleeve | **−0.011** | ❌ / ❌ |
| K4 regime decomposition (L31) | pre-2014 in-regime must pay; not 2021-23-only | pre-2014 in-regime **−0.19**; 2021+ carries all P&L | ❌ (flag) |
| K5 swap-sign audit (L30) | sign/magnitude/Friday-3x | model 4.10 vs specs 4.11 bps/night, credit ✓, 7 nights/wk ✓ | ✅ |

Frozen decision tree → **NO-GO, not even sleeve** (K3 < 0.3). Per HYPOTHESIS.md §7, no MC p(pass), no
correlation table (gates failed — no decoration of a corpse).

## What was tested (frozen rule)

Long USOIL iff `B_ann = (F1/F2 − 1) × 12 > 5%/yr`, evaluated at the last trading day of each week (T−1),
applied at the next trading day's close (T), held one week. Binary, long-only (L32 forbids the short
leg), zero modifications consumed. Net model: price return (capped ±20%, program convention) + dynamic
swap `(B_ann(t−1) − markup)/365 × nights` (Friday 3×) − 7 bps RT spread, zero commission.

## Calibration (K5-audited)

2026-06-09 curve: F1 (CLN26) 88.82 / F2 (CLQ26) 87.22 → **B_ann(now) = +22.0%/yr**. Measured FTMO long
swap +36.55 pts/night (digits 3, Friday 3×) at CL=F 88.89 → **+14.97%/yr credit** (the task's "+15–20%"
confirmed). Implied broker markup **7.05%/yr** — plausible financing + take; no flooring needed.
Historical long swap = B_ann(t) − 7.05%: credit in steep backwardation, −47%/yr drag in 2009-grade
contango (consistent with makeorbreak's measured short-leg asymmetry).

## Primary result — USOIL 2005-01-04 → 2024-04-12 (4,848 days)

| metric | strategy | always-long (same cost model) |
|---|---:|---:|
| net Sharpe | **−0.011** | −0.078 |
| ann. return | −0.17% | −3.24% (TIM-scaled −0.55%) |
| HAC lag-6 t | −0.05 | — |
| max DD (additive) | −70.8 pts | — |
| time in market | 17.1% | 100% |
| round trips | 27.5 (≤52/yr cap holds) | 1 |

Decomposition: price leg **−1.03%/yr**, swap leg **+0.96%/yr**, spread drag −0.10%/yr → net −0.17%/yr.
The collectable carry is collected — and fully spent buying conditioned oil beta that loses on average.

**Era P&L (additive return points):** pre-2014 **−0.193** · 2014–2020 **−0.169** · 2021–2023 **+0.232** ·
2024Q1 **+0.098**. In-regime spells: 28 total. Worst three: 2008-09-23→10-13 (**−0.370**),
2014-07-01→10-27 (**−0.242**), 2022-08-30→09-19 (**−0.119**). Best three: 2021-12-28→2022-08-22
(**+0.352**), 2007-08-28→12-10 (**+0.231**), 2024-02-21→04-12 (**+0.098**).

**The mechanism, stated precisely:** the 2020 crash was contango-led (B_ann: +4.5% on 2020-01-02 →
−0.2% by 01-16 → −13% by 03-09), so the point-in-time gate was flat well before the collapse — K1
genuinely passes, the gate gates. But 2008, 2014 and 2022 were **backwardation-led declines**: the curve
stayed backwardated while price collapsed, so the gate held its long. Carry-conditioning on oil is
protection against exactly one crash topology, and the 19-year net of the other topology is −0.36.

## Statistics

- **DSR (probabilistic Bailey-LdP, rf=0, PPY=252, std_sr 0.845):** N=3 → **0.0007**, N=5 → 4e−06,
  N=111 → ~0. (Bar > 0.5.)
- **Stationary bootstrap (21d blocks, 1000 draws) SR CI:** [−0.40, +0.35] — symmetric noise around zero.
- **Sensitivity (SR):** markup ×0.5 → +0.03, ×1.5 → −0.05, 2024-04 alt-calibration (markup floored at 0,
  i.e. full swap credit, no house take) → **+0.07**, spread ×0.5 / ×2 → −0.01 / −0.02. The result is
  structurally ~0 under every assumption — this is not a cost-knife-edge, no rescue exists (none was
  permitted anyway, L10).

## Secondary legs (registered, non-gate-deciding)

- **UKOIL (T110), 2007–2026:** SR −0.27 (bench −0.68, ΔSR +0.41; regime-diff t = +4.22 — the
  conditioning genuinely separates regimes on Brent but the level stays deeply negative). Caveats as
  pre-declared: spot−F1 basis with ×12 annualization overstates B (markup calibrates to 29%/yr — punitive
  drag), and the leg was long 10 days inside the K1 window (the coarse construction flips late). Reported
  for completeness; quality insufficient for any standalone claim beyond "does not help".
- **Sleeve 50/50 (T111), 2007–2024:** SR −0.18. Dead.

## Data provenance & deviations (all pre-declared in HYPOTHESIS.md §4 or documented here)

1. **Basis reconstruction (pre-declared):** `outputs/basis_oil.parquet` from the prior study is absent
   from disk (confirmed also by `CARRY_FEASIBILITY.md`). Rebuilt from **EIA official daily WTI contract-1/
   contract-2 settles** (RCLC1/RCLC2) — genuine point-in-time dynamic term structure, NOT a static
   snapshot (L26-compliant), strictly better provenance than an unverifiable parquet.
2. **EIA truncation (discovered at fetch):** EIA discontinued the futures series at **2024-04-05** →
   primary sample ends there (2024-04→2026-06 untestable on free point-in-time data). All gates remain
   evaluable; the "2024+" era is 2024Q1 only.
3. **Calibration date (forced adaptation):** markup calibrated on the **2026-06-09 live curve**
   (CLN26/CLQ26 via yfinance) to match the 2026 swap measurement date, instead of the frozen "last common
   sample date" (which EIA truncation pushed 26 months away from the swap quotes). The frozen-letter
   alternative (2024-04, markup floors at 0) is reported in sensitivities: SR +0.07 — verdict unchanged.
4. **Price source:** yfinance CL=F/BZ=F daily closes 2005/2007→2026 (single consistent source;
   deep_history Dukascopy starts 2013 only). Cross-validation vs Dukascopy daily closes: return corr
   **0.85 (USOIL)** / **0.89 (UKOIL)** — moderate, driven by the 23:50-UTC vs settle cut-time offset;
   level tracking consistent. Return cap ±20% per program convention (binds only around Apr 2020
   negative prices; strategy flat there, benchmark conservatively treated).
5. Trial-count note: the task said "registry 97 + variants"; canonical cumulative N was **108**
   (REGISTER.md 2026-06-09) → now **111**.

## Lesson candidate (for the L registry — L32 refinement, "L32b")

> **The collectable side of commodity-CFD carry is a credit, not an edge.** Long-only oil gated on real
> point-in-time backwardation (the only side retail CFD swaps let you collect, L32) nets ≈ 0 over 19y:
> the in-market swap credit (+0.96%/yr portfolio-level) is cancelled by the conditioned price beta
> (−1.03%/yr). Basis gating protects only against **contango-led** crashes (2020) and rides
> **backwardation-led** ones (2008, 2014, 2022) — backwardation peaks near price tops. All net positive
> P&L is the 2021+ regime (L31 confirmed in the long-only construction). Both sides of retail commodity
> CFD carry are now closed: short uncollectable (L32), long collectable-but-worthless (this study).

## Re-opening conditions

Only with (a) a genuine paid deferred-curve dataset extending past 2024-04 AND (b) a pre-registered
mechanism that separates backwardation-led from contango-led drawdowns ex-ante (e.g. basis × inventory
or basis × momentum interaction) — and that interaction is a NEW hypothesis with its own trial budget,
not a rescue of this one. The naked claim "long backwardated oil collects the swap" is falsified at the
net level and must not be re-proposed (registry: T109).

## Artifacts

`HYPOTHESIS.md` (frozen 41f034f) · `engine.py` · `fetch_data.py` / `fetch_curve_now.py` ·
`cache/{rclc1,rclc2,rbrte}.parquet`, `cache/curve_now.json` · `results.json` ·
`usoil_daily.csv`, `ukoil_daily.csv`, `k1_window_2020.csv`.
