# Double 7 book-fit gate — decorrelation vs Strategy A — VERDICT

**Date:** 2026-06-14  · **Pre-registration:** `REGISTER.md` (frozen before test) · **Code:** `analysis.py` · **Data:** `results.json`, `aligned_weekly_WSUN.csv`, `strategy_a_prices.parquet`

## TL;DR — **GO (diversifying brick), borderline on the upper CI**

Double 7 (vol-target 12% + time-stop 10j, FROZEN) **passes the pre-registered decorrelation
gate** vs Strategy A on every anchor, and shows **no statistically significant tail co-crash**.
The decorrelation is **regime-dependent** (it weakens in broad macro risk-off), so the verdict
carries a documented caveat, not a clean all-clear.

| Pre-registered gate | Result | Pass? |
|---|---|---|
| Weekly W-SUN \|ρ_pearson\| < 0.30 | **0.197** | ✅ |
| Weekly W-SUN \|ρ_spearman\| < 0.30 | **0.137** | ✅ |
| Tail co-crash not significant & negative | hypergeom p=0.119, tail-ρ = −0.215 | ✅ |
| (robustness) W-FRI weekly Pearson | 0.161 | ✅ |
| (robustness) Daily Pearson / Spearman | 0.150 / 0.150 | ✅ |
| (honesty) Weekly bootstrap 95% CI | [+0.047, **+0.341**] | ⚠ pierces 0.30 |
| (honesty) Daily bootstrap 95% CI (N=1591) | [+0.102, +0.200] | ✅ tight, sub-gate |

**N = 331 weeks** (2020-02-02 → 2026-05-31), common window of A and D7.

---

## 1. Variant verification (no unverified curve)
Regenerated the frozen combo from the engine — `portfolio([SPY,QQQ,GLD], sig_double7(7,7,200),
frac_voltarget(0.12), time_stop=10, slip=5bps)` — and cross-checked vs the canonical
`eq_imp_combo_final.csv`: **max relative |Δequity| = 1.3e-15** (machine precision). The CSV
*is* exactly the vol-12%+ts-10 variant. Regenerated metrics reproduce the rapport §8.2 combo:
**CAGR 3.55%, Sharpe 0.66, MaxDD −9.7%, n_trades 652.** My cash-aware reimplementation with
rf=0 reproduces the engine to 1.5e-10 (validates the cash machinery).

## 2. Cash-adjustment (deliverable #5) — idle cash credited at DTB3
Calendar-day accrual on the un-invested cash of each sleeve (incl. the vol-target un-invested
fraction). The combo runs ~80% in cash on average (vol-targeting at 12% keeps positions small).

| Window | CAGR rf=0 (report basis) | CAGR cash@DTB3 | Uplift | avg DTB3 |
|---|---|---|---|---|
| **Full 2005–2026** | +3.55% | **+4.90%** | **+1.35 pts** | 1.71% |
| 2022–2026 (current rates) | — | — | **+3.26 pts** | 3.99% |
| 2009–2021 (ZIRP) | — | — | +0.37 pts | 0.48% |

- The rapport's "~2 pts" (Annex B) was a recent-era estimate for the *base* strategy; the
  **vol-12% combo holds more cash**, so the 2022–2026 uplift is **+3.26 pts**, larger than ~2.
- **It is benchmark yield, not alpha.** Sharpe on an excess-return basis is essentially
  unchanged: **0.66 (rf=0) → 0.59 (excess)**; the rf=0-accounting "0.90" overstates because it
  credits the cash yield without benchmarking it. Bottom line: cash crediting raises *absolute*
  CAGR materially in the current rate regime but does **not** improve risk-adjusted return.

## 3. Correlation gate (decisive)
All point estimates are well under 0.30 and raw ≈ excess (rf choice immaterial):

- **Primary (W-SUN, excess):** Pearson **+0.197**, Spearman **+0.137** (raw Pearson +0.193).
- Robustness (W-FRI, excess): Pearson +0.161, Spearman +0.120.
- Daily (common trading days, N=1591): Pearson +0.150, Spearman +0.150.

Economic read: two **long-biased risk-asset** books (A = crypto momentum BTC/ETH/SOL; D7 =
equity/gold mean-reversion SPY/QQQ/GLD) correlating at only **~0.15–0.20** is a *good*
diversification result — the GLD sleeve and the momentum-vs-mean-reversion timing contrast do
real work. This is far below the ρ≈0.8 equity-beta floor that kills long-only crypto sleeves (L11).

## 4. Regime dependence (the caveat that makes it "borderline")
The full-sample 0.197 is **not stable** — it is inflated by two synchronized-macro episodes:

| Year | weekly ρ | | Year | weekly ρ |
|---|---|---|---|---|
| 2020 (COVID) | **+0.462** | | 2023 | −0.110 |
| 2021 | +0.283 | | 2024 | +0.017 |
| 2022 | +0.053 | | 2025 | +0.264 |
| | | | 2026 (ytd) | +0.077 |

- Rolling-52w ρ: **max +0.417** (window ending 2021-01-24 = COVID crash+recovery), min −0.191
  (2023), **last ≈ +0.26 and rising** (2025–26 macro re-coupling).
- **Interpretation:** decorrelation is real in idiosyncratic crypto cycles (2022–24 ≈ 0) but
  **weakens exactly in broad risk-off / liquidity regimes** (COVID, 2025), when both long-biased
  books fall together. The diversification is genuine on average but partially *pro-cyclical* —
  weakest when you most want it. This, plus only 331 weekly obs, is why the weekly bootstrap
  upper CI reaches **+0.341**. The much tighter daily CI [0.10, 0.20] argues the true structural
  co-movement is ~0.15.

## 5. Tail-coincidence ("do both draw down the same weeks?")
- Bottom-decile weeks: A=34, D7=34; **overlap k=6** vs expected 3.5 → **hypergeom P(X≥6)=0.119**
  (NOT significant at 5%).
- Mean D7 return in A's worst-decile weeks = **−0.32%** (vs +0.05% overall): D7 is *mildly*
  negative when A craters — **not a hedge, but not a co-crash amplifier**.
- **Pearson on the union of bottom-decile weeks = −0.215** (tail co-movement is slightly
  *negative*). The 6 overlapping bad weeks are not a tight linear co-crash.
- Verdict on tails: no significant joint crash; the crash-correlation kill condition is not met.

## 6. Verdict & how it feeds the book
**GO** vs the pre-registered gate: Double 7 (vol-12%+ts-10) is a **genuine diversifier** relative
to Strategy A (ρ≈0.15–0.20, sub-0.30 on every anchor, no significant tail co-crash). Annotate
**borderline** for the regime-dependence (rolling-ρ rises to +0.3–0.46 in risk-off; weekly CI
upper +0.341).

**Separate, higher bar — do not conflate:** the personal-book D-gate is Sharpe(book+D) > **2.54**
(book A+B SR 2.31 × 1.10). Double 7's standalone Sharpe is **0.66 (0.59 excess)**. Even at ρ=0.15
the optimal two-asset combination of a 2.31-SR book with a 0.66-SR sleeve tops out at
SR ≈ **2.33** — *below* 2.54. So Double 7 **clears the decorrelation brick-gate but cannot, alone,
clear the book Sharpe gate.** Its plausible role is **drawdown/tail smoothing** or as one
component of a larger multi-brick "D" sleeve — not a Sharpe enhancer. Recommend: keep as a
candidate brick; do **not** deploy solo into the personal book on Sharpe grounds.

## 7. Reproducibility
`python3 data/double7_connors/bookfit/analysis.py` (network once for yfinance; cached). Inputs:
ETF panels `data/panels/{equity,macro_etf}_panel.csv`; A prices yfinance BTC/ETH/SOL (cached);
rf `data/raw/fred_DTB3_37358bdf84.parquet`. Strategy A return logic inlined verbatim from
`Portfolio/validation/strategies/tsmom_signal.py`. Seed 42, 10k bootstrap draws.
