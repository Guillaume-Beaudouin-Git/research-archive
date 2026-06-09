# FTMO 10k 2-Step — Decorrelated Multi-Sleeve Portfolio
### Institutional research report — p(pass) maximization under a symmetric drawdown barrier

**Author:** quant research (solo) · **Date:** 2026-06-08 · **Status:** ⛔ **RETRACTED 2026-06-08** — headline did not survive independent clean-room audit. See `RECONCILIATION.md`.

---

## 0a. ⛔ RETRACTION NOTICE (2026-06-08)

**The headline p(pass ≤ 3mo) ≈ 0.55 below is WRONG and is retracted.** An independent clean-room audit (`research/ftmo_portfolio_audit/`) regenerated every sleeve from scratch on **timezone-verified** data and could not reproduce it. I re-verified the root causes myself and concur:

| | Claimed (this report) | Honest re-baseline (monotone engine, CIs) |
|---|--:|--:|
| Combined Sharpe | 1.39 | **+0.32 full / −0.32 OOS** |
| Sleeve A (RSI2 MR) | +0.97 | **−0.04** (open-to-open + entry-booking artifact; clean MTM ≈ 0) |
| Sleeve B (BTC) | +0.51 | **−0.92 OOS** (EET-mislabeled window; OOS-negative) |
| Sleeve C (US30) | +1.00 | **+0.19** (my "13-20 UTC" was really 10-17 UTC; true-UTC ≈ 0.1-0.2) |
| **p(pass ≤ 3mo)** | **0.55** | **0.43 full [0.32, 0.55] / 0.35 OOS [0.25, 0.53]** |
| DSR (N=100 / 500) | 0.86 | **0.13 / 0.07 (edge indistinguishable from zero)** |

**No version clears 0.50 with its confidence interval. The objective is not met.** Root causes: (1) `panels/m5_indices` is **EET mislabeled as UTC** — Sleeves B & C traded different (more favorable) windows than documented; (2) Sleeve A's open-to-open + entry-day-booking convention manufactured an edge that vanishes under a standard close-to-close MTM; (3) no committed runner ever reproducibly generated the numbers; (4) inflated Sharpe × optimistic per-phase MC × favorable leverage × no CIs, stacked. The **decorrelation thesis survives** (|ρ|<0.06) but the sleeves are individually ≈-zero/OOS-negative. Full reconciliation: `RECONCILIATION.md`. **Everything below §0a is retained only as a record of the retracted claim.**

---

## 0. Executive summary  *(RETRACTED — see §0a)*

We engineered a **3-sleeve decorrelated portfolio** whose daily-return distribution is shaped to clear the FTMO 10k 2-step evaluation **within 3 months**. After an exhaustive systematic search (≈ a dozen strategy families, the overwhelming majority rejected) and a full adversarial audit (look-ahead, slippage, fees, IS→OOS, walk-forward, DSR, feasibility), the honest, fully-audited result is:

| Metric (3-sleeve portfolio) | Value |
|---|---|
| **p(pass) ≤ 3 months — out-of-sample (2025-2026)** | **0.55** |
| p(pass) ≤ 3 months — full sample (2022-2026, incl. 2022 bear stress) | 0.49 |
| p(pass) ≤ 6 months — full sample | ~0.60 |
| Combined daily Sharpe (annualized) | 1.39 |
| Excess kurtosis (daily) | 6.3 |
| Positive every calendar year 2022-2026 | ✅ |
| Deflated Sharpe Ratio (N=100 trials) | 0.86 |
| Walk-forward folds positive (≥5) | 4-5 / 5 |

**Honest headline:** the > 0.50 objective is **achieved on the genuine out-of-sample window (0.55)**; on the full sample including the 2022 bear/high-vol stress it sits at the 0.50 threshold (0.49). Forward expectation ≈ 0.50-0.55, with a "2022 repeats" scenario as the documented downside (~0.40).

This is **not** a high-margin result — it is a *threshold* result delivered honestly. Two apparent improvements (a per-trade stop, a daily winsorize) were caught as artifacts and rejected during audit.

---

## 1. Objective & theoretical framing

**Target:** FTMO 10k **2-step Standard** — Phase 1 +10% / Phase 2 +5% profit targets; **−5% daily loss** floor (resets each session); **−10% static max drawdown** (from initial balance); min 4 trading days/phase; FTMO imposes **no time limit** — the "< 3 months" (≈ 63 trading days) is a self-imposed aggressive constraint.

An FTMO challenge is a **first-passage problem**, not a profitability problem. For an arithmetic-Brownian-motion approximation, the single-phase pass probability against a symmetric barrier is the logistic

```
P(pass one phase) = 1 / (1 + e^(−2 · S_d · n)),   S_d = µ/σ (daily Sharpe),  n = B/σ (vol-units to barrier)
```

Two consequences govern everything:
1. **p(pass) is scale-invariant in account size** and (we verified) **also invariant to horizon for a single lumpy sleeve** — extending the deadline does not help a strategy whose barrier race is already decided early.
2. The levers are **daily Sharpe** and **per-day volatility / kurtosis**. Fat left tails (a trend day that ruins a mean-reversion book) make realised crossing probability strictly worse than logistic ⇒ the **kurtosis gate is first-order**.

The winning profile (CLAUDE.md L24): high daily Sharpe, win-rate, low kurtosis, high frequency — *not* lumpy momentum. The path to > 0.50 in 3 months is therefore a **portfolio of decorrelated weak-to-moderate edges** (√N Sharpe boost + kurtosis averaging), never a single strategy.

---

## 2. Methodology & gates (pre-registered)

- **Causality:** signal at T-1, execute at T. No bar-t close used in features. Verified by an explicit +1-bar delay stress test on every intraday sleeve.
- **Costs first:** real MT5 spread per bar × conservative retail markup (×2-3), commissions per FTMO specs (FX 2.5 USD/lot; **crypto 0.0325%/side = 6.5 bps RT, live since 28-Jul-2025**), swap on held positions, ≥1-tick slippage on intraday entries.
- **First-passage engine:** block-bootstrap (Politis-Romano) absorbing-barrier Monte-Carlo with the −5% daily floor + −10% static DD + min-days, validated against the closed form to max error 0.0038. `engine/ftmo_first_passage.py`.
- **Validation:** strict IS (≤ 2024) / untouched hold-out (2025-2026); walk-forward ≥ 5 folds; DSR (Bailey-López de Prado) deflated for trial count; multi-seed MC stability.
- **Portfolio rule:** sleeves combined only if pairwise corr < 0.3 (OOS); causal trailing-vol targeting (no full-sample scaling — see Audit A1).

---

## 3. The systematic search — what was rejected (the 90% negative)

A genuine institutional search is mostly negatives. Families tested and **rejected**, with the killing mechanism:

| Family | Verdict & mechanism |
|---|---|
| Intraday FX mean-reversion (11 pairs) | **All OOS-negative.** FX majors are intraday-efficient; IS-positive pairs (AUDUSD, USDCAD) all collapse 2025-26 |
| Index-pair stat-arb | Cost-killed at the 2-leg gate (gross/cost ≈ 0.6 vs 3× required) |
| XAUUSD range-fade | Edge failure — gross Sharpe negative at zero cost |
| Equity overnight premium | Real gross OOS edge (1.78) but net-of-swap ≈ 0 (carry-fundamental, not venue-fixable) |
| Commodity TSMOM / reversion (daily) | Both negative 2021-26 (2022 spike+reversal whipsaws both directions) |
| Commodity intraday momentum | Cost-killed (wide CFD spreads vs intraday range) |
| Daily trend (FX/indices/gold) | No gross edge in a range-bound regime |
| Turn-of-month seasonality | Decorrelated but net-negative (arbitraged away) |
| Crypto daily TSMOM / cross-sectional | Gross edge real but swap/spread-killed; CS not FTMO-executable (170-token universe) |
| Event-driven — pre-FOMC drift | Real but **decayed OOS** (2022 +79bp → 2026 −35bp); 8 events/yr too sparse |
| Event-driven — post-news reversion | **Null** (corr(spike, subsequent move) ≈ 0 — markets efficient around scheduled releases) |
| FX carry (G10) | Archive-confirmed dead post-GFC (IC −0.028 on 2013-23) |

**Conclusion:** the FTMO-executable, free-data, price universe yields exactly **three** robust edges. Genuinely-orthogonal 4th edges (carry, vol-risk-premium) require instruments FTMO does not offer (perps, options) — a structural ceiling, not a search failure.

---

## 4. The validated portfolio — three decorrelated sleeves

Pairwise correlations (OOS): all **|ρ| < 0.15**. Three distinct return sources.

### Sleeve A — FX/Index daily mean-reversion (Connors RSI2), inverse-vol weighted
- **Universe (11):** EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCHF, USDJPY, US500, US100, US30, GER40, XAUUSD.
- **Signal (causal):** RSI(2) on daily close, shifted 1. Enter at next open when RSI2 < 10 (long) / > 90 (short); exit at open on revert-to-50 or 8-day max hold.
- **Sizing (the key improvement — see §6):** per-instrument **inverse-volatility risk-parity** (90-day trailing) instead of equal-weight.
- **Costs:** real spread + FX commission + swap on held days.
- **Metrics:** daily Sharpe ≈ **0.97**, excess kurtosis ≈ **14**, positive every year.

### Sleeve B — BTCUSD intraday momentum (banded breakout)
- **Bars:** 120-min, liquid window 00-21 UTC, **intraday-flat** (no overnight swap).
- **Signal (causal):** z-score of log price vs 16-bar mean; banded hysteresis (enter |z|>2, exit |z|<0.5), momentum direction. Hard 2% intraday daily-stop.
- **Costs (realistic FTMO crypto):** spread ×2 (~6-7 bps) **+ 0.065% RT commission** (post-July-2025). Net OOS Sharpe ≈ **0.51** (survives the new commission with a modest haircut).
- **Role:** regime hedge — the only momentum sleeve; profits when the reversion sleeves struggle (e.g., trending 2024).

### Sleeve C — US30 intraday mean-reversion (banded fade)
- **Bars:** 60-min, US cash session 13-20 UTC, intraday-flat, 2% daily-stop.
- **Signal (causal):** same banded z-reversion engine as B (un-inverted = fade).
- **Robustness:** **positive every calendar year 2022-2026** (IS +0.76 / OOS +1.00); survives **4× spread markup** (IS +0.58 / OOS +0.86). US equity indices exhibit genuine intraday reversion that FX majors do not.

### Portfolio construction
Each sleeve causally vol-targeted (63-day trailing, cap 4×) to ≈ 1%/day, **equal-weighted**, portfolio leverage L ≈ 2.5-3 (the p(pass)-optimal static leverage).

---

## 5. Results

| Horizon | p(pass) full (2022-26) | p(pass) hold-out (2025-26) |
|---|--:|--:|
| ≤ 3 months | 0.485 | **0.549** |
| ≤ 6 months | 0.580 | ~0.55 |
| ≤ 9 months | 0.531 | 0.531 |

**Per-year combined Sharpe (equal-weight, inverse-vol MR):** 2022 +0.17 · 2023 +1.90 · 2024 +1.89 · 2025 +1.26 · 2026 +2.40. The diversification works — in every year where one sleeve decheats (BTC 2022/2025, MR 2026), the other two compensate.

**Walk-forward (5 folds, leverage fixed ex-ante):** 0.24 (2022) · 0.62 · 0.56 · 0.48 · 0.59 — positive and mostly > 0.50 in 4 of 5 folds; the lone weak fold is the 2022 bear/high-vol stress.

---

## 6. Improvement phase — 10 ideas, 1 robust win, 2 artifacts caught

| # | Idea | Verdict |
|---|---|---|
| **2** | **Per-instrument inverse-vol sizing (MR)** | ✅ **The win.** MR Sharpe 0.83→0.97, kurt 26→14; combo hold-out 0.467→**0.549**. Principled (risk parity, zero tuning); multi-seed stable; walk-forward 4/5. |
| 1 | Per-trade daily stop | ❌ **Artifact.** Apparent gain (Sharpe 0.97→1.59) was the *optimistic stop-fill* assumption; with realistic fill at the breaching close it is neutral-to-negative (0.97→0.91). Consistent with "stops hurt mean-reversion." |
| 3 | Daily winsorize (tail-cap) | ❌ **L25 artifact** (cap-and-continue inflates a series mean without a real exit). |
| 4 | Cross-sectional concentration | ❌ Reduces breadth → kurtosis explodes (15→93). |
| 5 | Index risk-parity (US30+US500) | ~ Helps 6-month Sharpe, hurts 3-month (US500 fat tails raise kurt). |
| 6 | Crypto momentum basket | ❌ Simple basket inferior to the validated engine-BTC. |
| 7 | Intraday session conditioning | ❌ Baseline window (13-20 UTC) already optimal; narrowing destroys the edge. |
| 8 | Barrier-aware dynamic sizing | ❌ De-risking when ahead forfeits drift → lowers p(pass). |
| 9 | ERC portfolio weights | ❌ No improvement over equal-weight (sleeves already ≈ equal-vol, low-corr). |
| 10 | Smooth regime tilt | ❌ Worse (tilt amplifies the wrong sleeve in transitions). |

The two artifacts (a cap-and-continue and an optimistic stop fill) are textbook traps; catching them is the point of the protocol, not a footnote.

---

## 7. Full adversarial audit

| Audit | Finding |
|---|---|
| **A1 — Look-ahead** | Found one **self-inflicted** look-ahead: the portfolio was scaled by *full-sample* std. Corrected to causal trailing-vol → headline fell 0.50 → 0.485/0.549. Sleeve signals themselves verified causal. |
| **A2 — Slippage / timing** | Survives slippage (FX/index/crypto). Both intraday sleeves are **timing-sensitive** (a +1-bar execution delay weakens them) → fast (next-bar) automated execution required. Daily MR is timing-robust. |
| **A3 — Fees / data** | FX/index spreads realistic; commissions modeled. BTC re-costed at realistic FTMO crypto rate (spread + new 0.065% RT commission) — survives with a modest Sharpe haircut. |
| **A4 — IS→OOS + walk-forward** | Leverage fixed on IS (2022-24) → OOS p(pass) 0.48 (no leverage overfit). Walk-forward positive every fold. |
| **A5 — DSR** | Deflated Sharpe 0.94 (N=20) → 0.86 (N=100). Survives multiple-testing deflation; 2 of 3 sleeves originate from an *independent* prior program. |
| **A6 — Feasibility** | Crypto 1:3 leverage cap satisfied (BTC notional ≈ 25-33% of account at 1%/day vol); margin OK on 10k; 3 multi-session sleeves are automatable. |
| **A7 — Improvement audit** | Inverse-vol confirmed robust (multi-seed + WF). Stop and winsorize rejected as artifacts (above). |

---

## 8. Honest caveats & limitations

1. **Threshold, not comfortable.** 0.55 OOS / 0.49 full — at the objective on out-of-sample, just below on the full sample. Not a 0.65 result.
2. **2022 stress.** A bear/high-vol regime drags the portfolio (walk-forward fold ≈ 0.24). Forward downside scenario ≈ 0.40 if 2022 repeats.
3. **Reversion-regime concentration.** 2 of 3 sleeves are mean-reversion; 2022-2026 was reversion-favorable. BTC momentum is only a *partial* regime hedge.
4. **Intraday execution sensitivity.** Sleeves B & C lose materially under execution lag — requires reliable next-bar automated execution and tight infra.
5. **Crypto cost & rules.** Crypto spreads/commission are the largest cost uncertainty; the post-July-2025 commission is modeled but must be re-confirmed live, along with FTMO's crypto daily-floor treatment.
6. **Design-stage MC.** All p(pass) are Monte-Carlo design estimates on historical bootstrap, **not realised performance.** All spreads/swaps/commissions must be reconciled against the live FTMO portal before funding.

---

## 9. Reproducibility

- Engine & sleeves: `PropFirms/ftmo_alpha_program/` (first-passage engine, CFD cost model, banded intraday MR/momentum).
- Data: deep-history M5 UTC (Dukascopy+MT5 splice) for FX/indices/gold/BTC; FTMO instrument specs; economic calendar (audit of event-driven angles).
- Sleeve daily-return series and the portfolio combination are cached and regenerable end-to-end.

---

## 10. Conclusion & recommendation

Starting from a prior program in which **every** single-strategy family was NO-GO, we built a **decorrelated 3-sleeve portfolio that passes the FTMO 10k 2-step with p ≈ 0.55 on out-of-sample data within 3 months** — via genuine diversification (√N) and one principled, audited improvement (inverse-vol risk parity). The result is honest and threshold-level: robust on recent OOS, at the 0.50 line on the full sample, with the 2022 regime as the documented stress.

**Recommended next steps for team review:**
1. **Live reconciliation** of spreads/swaps/crypto-commission on the FTMO portal; re-run p(pass) with portal costs.
2. **Paper-trade** the 3 sleeves with the real (timing-sensitive) execution stack for ≥ 1 month before funding.
3. **Decision:** the cleanest path to *comfortable* > 0.50 is to relax the deadline to ~5-6 months (no FTMO time limit) — p(pass) rises to ~0.60 — or to source a genuinely orthogonal edge from **new data** (order-flow, alt-data), the only remaining lever for a 4th sleeve.

*This document reports design-stage Monte-Carlo estimates, not investment advice or realised returns. All parameters are indicative and require live reconciliation before any capital is deployed.*
