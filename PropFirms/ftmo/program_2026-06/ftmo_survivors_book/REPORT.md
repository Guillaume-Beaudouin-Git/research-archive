# FTMO 10k 2-Step — "Survivors Book" honest baseline

**Goal:** the TRUE p(pass) with confidence intervals at 6mo AND 12mo, built only from independently
validated inputs, after two prior portfolio reports collapsed under audit (stacked optimism). A
reproducible 0.45 would be a success; an unreproducible 0.55 is the failure we are escaping.
**Engine:** reuses the audit's monotone absorbing-barrier first-passage MC
(`research/ftmo_portfolio_audit/code/firstpassage.py`, read-only) — never the discredited author engine.
**Date:** 2026-06-08 · code `code/*.py` · data `results/*` · figure `figures/survivors_ppass.png`.

---

## 0. Verdict (plain)

**No horizon clears 0.50 out-of-sample. The free-price-data survivors edge is too thin to financiably
clear the bar.**

| | p(pass) | 90% CI (outer bootstrap) | vs 0.50 |
|---|--:|--:|---|
| **OOS (2025-26) ≤ 6 mo** | **0.24** | [0.06, 0.53] | **below** (central 0.24; CI top just grazes 0.53) |
| **OOS (2025-26) ≤ 12 mo** | **0.34** | [0.08, 0.69] | **below** (central 0.34; CI too wide to *support* clearing) |
| IS (2008-24) ≤ 6 mo | 0.21 | [0.16, 0.26] | below |
| IS (2008-24) ≤ 12 mo | 0.31 | [0.24, 0.39] | below |

Headline book = **2 sleeves** (Ross Hook + swap-net TSMOM), leverage **L=2.0 fixed ex-ante on IS**.
p(pass) is monotone in horizon (OOS 3/6/9/12mo = 0.09 / 0.21 / 0.27 / 0.29 — sanity ✓).

**The single dominant driver:** real CFD overnight **swap** consumes most of TSMOM's edge — its
deployable (swap-net) Sharpe is **~0.05 full-sample / 0.92 OOS**, not the swap-free **0.85** the input
file carries. Using the swap-free 0.85 would re-introduce exactly the optimism we are escaping; even so,
the swap-free book tops out at **0.49 (12mo OOS)** and is *not deployable*. Sleeve C (US30 MR), the only
mean-reversion / genuinely-different return source, **failed its inclusion bar** (OOS Sharpe +0.04, 90%
CI [−1.35, +1.31]), so the book is two trend-correlated momentum legs.

---

## 1. Inputs — provenance re-confirmed (Task 1)

| series | source | period | ann Sharpe | note |
|---|---|---|--:|---|
| **Ross Hook deployable** | `s076_replication/results/mtm_deployable.csv` (`ret`) | 2007-2026 | **0.44** | net of spread+slip+commission; EET server-day; excess kurt **45** |
| **TSMOM deployed (swap-free)** | `data/ftmo_research/tsmom/chosen_returns.csv` | 2000-2026 | **0.85** | regen matches **corr +1.000** (validated); **swap-FREE → not deployable** |

**Decorrelation reproduced exactly:** Pearson **+0.262** (all overlap) / **+0.299** (both-active), matching
A.1 — which confirms the date alignment (a 1-day misalignment would collapse it). Both are momentum-family.

**Critical cost correction (Task: real swap).** The TSMOM dossier itself states `chosen_returns.csv` is
swap-FREE and the canonical is **CLOSED** pending demo swap measurement. I regenerated TSMOM net of
**directional per-night swap on held notional** (measured proxy: non-crypto long −3.08 bps/night, short
≈ free, weekend ×3 ≈ ×1.45/trading-day; crypto = the unmeasured leg, swept):

| TSMOM variant | Sharpe (2007+) | Sharpe OOS 25-26 |
|---|--:|--:|
| swap-FREE (input file) — *not deployable* | 0.91 | 1.47 |
| swap-net, **no-crypto** (headline; no unmeasured-rate dependence) | **0.05** | 0.92 |
| swap-net, full basket, crypto-swap = 0 (optimistic) | 0.32 | 0.85 |
| swap-net, full basket, crypto-swap = 12 ("the wall") | 0.01 | 0.53 |

Net of measured swap, TSMOM is **negative in 5 of the last 8 years** (2019,2021,2022,2023,2024) — its
edge is concentrated in strong-trend years (2020, 2025-26). The long-run trend edge is real but small
once financing is paid.

---

## 2. Sleeve C re-verification (Task 2) — EXCLUDED

Clean-room US30 60-min MR, US cash 13-20 UTC (the audit confirmed this window is genuinely true-UTC
aligned), intraday-flat, 2% daily-stop, causal, real spread×2:

- IS (≤2024) ann Sharpe **−0.20**, 90% CI [−0.63, +0.23]
- OOS (2025-26) ann Sharpe **+0.04**, 90% CI **[−1.35, +1.31]**

Inclusion bar (OOS Sharpe 90% CI lower > 0): **FAILS.** Sleeve C is excluded. **Tradeoff flagged:** it was
the only mean-reversion candidate, so the book is now two momentum-family legs whose correlation rises in
trend — it has no genuinely-orthogonal third return source. (Forcing C in *lowers* the book: IS combined
Sharpe 0.27→0.01, OOS 12mo p(pass) 0.34→0.30.)

---

## 3. Final book (Task 3) & p(pass) (Task 5)

- **Composition:** RH (deployable, 0.44) + TSMOM (swap-net no-crypto). Each **causally vol-targeted** to
  1%/day (63-day trailing, cap 4×); **equal-weight** baseline (risk-parity ≈ identical: sleeves already
  equal-vol; OOS ann Sharpe 0.26 either way).
- **Leverage:** **L=2.0, fixed ex-ante on IS** (argmax IS p(pass≤12mo)); applied unchanged to OOS. The
  sweep (figure left) shows the honest book sits at ~0.25-0.29 across L∈[1.5,3.5] — **flat and below 0.50
  at every L**, so no leverage rescues it; the OOS-best L is never used for the headline.
- **Combined:** ann Sharpe IS **0.27** / OOS **0.26**; daily Sharpe OOS 0.017; excess kurtosis **13.9**.

**p(pass) table — `results/ppass_table.csv`, `figures/survivors_ppass.png`:** see §0. Every cell carries a
90% CI from **outer block-resampling of the data series** (not just inner MC SD). OOS CIs are wide
(12mo [0.08, 0.69]) — the honest consequence of a ~350-day OOS window, exactly as anticipated.

Ceiling check (sensitivities, OOS 12mo): swap-FREE TSMOM 0.49 [0.20, 0.82]; crypto-swap-0 0.45 [0.17,
0.72]. Even the most optimistic, non-deployable assumption does not put the central estimate above 0.50.

---

## 4. Tail / conditional correlation (Task 4)

| regime | n | corr(RH, TSMOM) |
|---|--:|--:|
| unconditional | full | **+0.203** |
| strong-trend days (top-25% \|20d US500\|) | 1216 | +0.217 |
| vol-shock days (top-10% \|US500 daily\|) | 488 | +0.161 |
| **worst-decile portfolio days** | 488 | **−0.249** |

The feared momentum co-move (A.1's +0.65 on the proxy universe) **does not materialize** on the deployable
series — trend-day corr is only +0.22, and on the book's *worst* days corr goes **negative** (the sleeves
do not co-crash). **Co-breach** (≥2 sleeves below own 5th pct same day): empirical **0.0072** vs
independence 0.0025 (×2.9) — elevated in *relative* terms but low in absolute frequency (0.7% of days).
Decorrelation is intact; it is not what fails — the thin post-swap Sharpe is.

---

## 5. DSR at honest N (Task 6)

Combined book (swap-net, daily Sharpe 0.017):

| N (trials) | 1 | 20 | 100 | 500 |
|---|--:|--:|--:|--:|
| DSR | 1.00 | 0.27 | **0.11** | 0.04 |

**Honest N ≫ 100:** RH was selected from a **109-strategy** library; TSMOM from a multi-asset program;
this exercise adds the leverage sweep (5) × weightings (2) × Sleeve-C variants × swap scenarios (4) ×
the 2-vs-3-sleeve choice. At any honest N (≥100), **DSR ≈ 0.04-0.11 → fails deflation**: the post-swap
combined Sharpe is too low to survive multiple-testing correction.

---

## 6. Honest limitations (what could not be checked / residual uncertainty)

1. **TSMOM swap rate is a measured *proxy*.** Non-crypto legs use the one measured leg (US100.cash,
   −3.08 bps/night long); gold/silver/oil CFD financing differs in detail. **Crypto swap is unmeasured**
   (swept 0/12); the headline avoids it by using the no-crypto basket. Demo measurement is still the one
   decisive open number (per the TSMOM dossier's CLOSED status).
2. **RH swap is an uncosted residual.** The deployable RH series (0.44) is net of spread+slippage+
   commission but **not overnight swap**; RH holds positions multiple days, so its true deployable Sharpe
   is somewhat below 0.44. Not separately costable from the combined MTM series here — flagged, not fixed.
3. **Short OOS (~350 trading days, 2025-26)** → wide OOS CIs by construction; the 12mo OOS CI [0.08, 0.69]
   cannot statistically *exclude* 0.50, but the point estimate (0.34) does not support clearing it.
4. **Design-stage MC on bootstrap history, NOT realised performance.** Paper-trading the real (swap-
   bearing, partly intraday) execution stack for ≥1 month remains required before any funding.
5. **Vol-targeting drag.** Re-vol-targeting the already-vol-targeted TSMOM trims its OOS Sharpe
   (0.94→0.49); a single constant scaling would be modestly kinder. I kept the causal trailing vol-target
   as instructed and note the cost.
6. **Sleeve C tested only at its documented 13-20 UTC config.** A wider config search (the audit found an
   8-21 window scored better OOS) was deliberately **not** pursued — that is the config-shopping that sank
   the prior report; re-opening it would require a pre-registered OOS test.
7. **Both surviving sleeves are momentum-family.** With Sleeve C excluded there is no mean-reversion
   diversifier; a sustained-chop regime bleeds both (visible: TSMOM-net negative 2021-2024, RH negative
   2025-26). This is the structural ceiling, consistent with the audit's conclusion that the FTMO-
   executable free-data universe yields too few genuinely-orthogonal edges.

---

## 7. Recommendation

**Do not fund this book.** The honest, reproducible result is p(pass) ≈ **0.24 (6mo) / 0.34 (12mo) OOS**,
below the 0.50 bar at both horizons, driven by real CFD swap consuming TSMOM's edge and by the absence of
a surviving mean-reversion diversifier. This is the correct outcome of the protocol — a reproducible
sub-0.50 number, not an engineered 0.55. The only paths to a financiable book are (a) **measure the real
crypto/equity CFD swap on demo** (it gates TSMOM between ~0 and a modestly-positive deployable Sharpe),
and (b) **source a genuinely-orthogonal, low-swap edge** (intraday-flat, so no overnight financing) to
replace the failed Sleeve C — the same structural lever the audit identified. Absent both, the free-
price-data edge is too thin.

*Design-stage Monte-Carlo on historical bootstrap; not realised performance. CIs on every p(pass); leverage
fixed ex-ante on IS; real costs incl. swap; reused the audited monotone engine; nothing fabricated.*
