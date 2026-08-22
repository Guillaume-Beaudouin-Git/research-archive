# PRE-REGISTRATION — Double 7 book-fit gate (decorrelation vs Strategy A)

**Date:** 2026-06-14 (written BEFORE computing any correlation statistic)
**Author:** Claude Code session (priority-1 book-fit gate)
**Decision owner:** personal book (A + B). Question: is Double 7 a *diversifying* brick,
or does it add equity-beta / crash-correlation already present via Strategy A?

This file is frozen before data contact for the test statistic. The candidate variant is
itself frozen by the external rapport+audit (PBO = 69% → **never tune** 7/7/200, σ=12%,
time-stop=10). No parameter of either leg may be adjusted after seeing ρ.

---

## H0 (null we hope to retain)

> Double 7 (ETF, **vol-target 12% + time-stop 10j** variant) returns are **decorrelated**
> from Strategy A (TSMOM v3, weekly long-only crypto BTC/ETH/SOL) returns.

A "retained H0" (low correlation) supports promotion as a diversifying brick.

## Frozen specifications

**Leg 1 — Double 7 candidate (FROZEN, no tuning):**
- Variant = `combo_voltarget12_ts10_full` = canonical file
  `data/double7_connors/eq_imp_combo_final.csv`.
- Construction: `portfolio(etf=[SPY,QQQ,GLD], signal=sig_double7(7,7,200),
  frac=frac_voltarget(0.12), time_stop=10, slip=5bps)`, 3 equal sleeves,
  window 2005-09-01 → 2026-05-27. Source engine: `data/double7_connors/improvements.py`.
- **Verification step (pre-test):** regenerate this equity from the engine and confirm
  max |Δequity| vs `eq_imp_combo_final.csv` is ≈ 0 (tolerance < 0.01% of equity). If it
  fails, STOP and reconcile — do not proceed on an unverified curve.

**Leg 2 — Strategy A (FROZEN, production spec):**
- `compute_tsmom_returns(BTC/ETH/SOL)` per
  `Portfolio/validation/strategies/tsmom_signal.py` (inlined verbatim for reproducibility).
- Spec: `signal = tanh(cumret_28 / (vol_28·√28)).clip(lower=0)` (long-only), vol-target 0.18
  (crypto √365 annualization), Monday rebalance `.where(dayofweek==0).ffill()`, `position.shift(1)`
  (signal T-1, trade T), cost 0.17% RT on Monday turnover. Output = **daily** net MTM returns.
- Prices: yfinance auto-adjusted daily, 2020-01-01 → 2026-05-28 (SOL ≥ 2020-04-10), matching
  `proof_of_work_strategy_a.py`. Cached to `bookfit/strategy_a_prices.parquet`.

## Returns convention
- **Excess returns vs DTB3** (CLAUDE.md hard rule). DTB3 from
  `data/raw/fred_DTB3_37358bdf84.parquet` (2000→2026-05-26), ffilled to calendar days.
  Weekly excess = weekly compounded raw − weekly compounded rf over that week's calendar days.
- Raw-return correlation reported alongside as a check (expected ≈ identical at this frequency).

## Alignment (Step 3)
- A is **weekly** (Monday rebalance, held Mon→Sun); Double 7 is **daily**.
- **Primary anchor: W-SUN (Mon→Sun calendar weeks)** — aligns A's Monday-rebalanced holding
  week exactly and buckets D7's Mon–Fri trading days into the same calendar week. Compound
  daily returns within each week. Restrict to the common weekly index; report **N_weeks**.
- Robustness anchors: **W-FRI** (equity-standard) and **daily** (max power; note A's daily
  obs are autocorrelated within a week by construction).

## GATE (book promotion) — decision rule fixed now
- **PASS / GO** ⟺ on the common weekly (W-SUN, excess) window:
  `|ρ_pearson| < 0.30` **AND** `|ρ_spearman| < 0.30`,
  **AND** tail-coincidence check shows no excess co-crashing (see below).
- **KILL / NO-GO** ⟺ `|ρ| ≥ 0.30` on the primary weekly window → it imports
  equity-beta / crash-correlation rather than diversification → reject as a brick.
- Bootstrap CI and robustness anchors are **reported for honesty** but the binary gate is the
  point-estimate rule above. If point estimate < 0.30 but the 97.5% bootstrap upper bound
  pierces 0.30, the verdict is annotated "GO (borderline — wide CI)".

## Statistics (Step 4)
1. Pearson ρ and Spearman ρ — weekly (primary) + daily (robustness).
2. Rolling 52-week Pearson ρ (regime stability of the correlation).
3. **Tail-coincidence:** bottom-decile weeks of A and of D7; (a) overlap count vs
   hypergeometric expectation + p-value; (b) mean D7 weekly return during A's worst-decile
   weeks (and symmetric); (c) Pearson ρ on the union of both bottom-decile weeks.
4. **Block-bootstrap CI on ρ** — circular blocks, L=20 (daily, per the rapport's
   `metrics.block_bootstrap` convention / Politis-Romano); weekly bootstrap with L=8 weeks as
   robustness. 10,000 resamples, 2.5/97.5 percentiles.

## Cash-adjustment deliverable (Step 5)
- Re-run the Double 7 combo crediting **idle cash at DTB3** (calendar-day accrual on the
  un-invested cash component of each sleeve, including the vol-target un-invested fraction).
- Report corrected **CAGR** and **Sharpe** vs the report's rf=0 baseline, plus the
  excess-return Sharpe (house standard). Expected uplift ≈ +2 CAGR pts (report Annex B).

## Constraints
- No in-sample tuning of either leg (both frozen). HAC where relevant. Honest negative is a
  deliverable. Verdict is whatever the frozen procedure returns.
