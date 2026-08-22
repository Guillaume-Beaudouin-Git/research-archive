# PRE-REGISTRATION — Piste A: Statistical arbitrage / pairs (cointegration) on FTMO

**Frozen:** 2026-07-08 13:52 UTC · **Author:** solo algo researcher · **Status:** design frozen BEFORE any result.
**Isolation:** additive folder, zero git-HEAD ops, live book untouched, nothing deployed.
**Reconciliation policy (per user mandate "fresh per brief"):** this study is run as an independent
from-scratch replication. The in-repo precedent (`PropFirms/ftmo/program_2026-06/ftmo_research/
statarb_deepdive_ftmo.md`, `STATARB_VERDICT.md`) is **NOT consulted during execution**; results are
compared to it only in the final synthesis. This makes the study author≠auditor by construction.

---

## 0. Prior (declared, not peeked)
- §4 FTMO-compatible profile (`ftmo_profile_study/`) ranks **carry / relative-value LAST (reject)**:
  always-on presence + negative tail. Pairs are relative-value → a priori a poor §4 shape fit on the
  *presence* and *intraday-excursion* axes, though a **good** fit on the *tail-decorrelation* axis
  (long A / short B cancels market beta). We test anyway — §4 shape is necessary, not sufficient, and
  the point of a fresh pass is to let the data speak.
- Known classic failure modes of retail pairs: (i) in-sample cointegration selection that breaks OOS;
  (ii) multi-week half-life → forced multi-day holds → financing; (iii) 2-leg cost; (iv) the spread
  inheriting a **relative drift** (market-neutral-by-construction ≠ two-sided-in-spread). We measure
  each explicitly rather than assume.

## 1. Hypothesis
**H_A:** ≥1 pair in the liquid FTMO CFD universe has a spread that simultaneously is
(i) cointegrated **and OOS-stable**, (ii) has a **tradeable half-life**, (iii) mean-reverts with a
**two-sided** edge (long-spread AND short-spread both net-positive) surviving **real 2-leg cost +
overnight swap**, and (iv) survives **multiple-testing deflation (DSR)**.
**H0 (null):** no such pair — the family reduces to relative drift (beta trap) and/or is cost/financing-dead.

## 2. Universe (frozen — 12 candidate pairs)
Daily UTC closes, `data/deep_history_utc/`, log prices, common-overlap sample per pair.
- **Index pairs (6):** US100/US500, US100/US30, US500/US30, US100/GER40, US500/GER40, US30/GER40
- **FX bloc pairs (5):** EURUSD/GBPUSD, AUDUSD/NZDUSD, EURUSD/USDCHF, USDCAD/USDCHF, AUDUSD/EURUSD
- **Metal pair (1):** XAUUSD/XAGUSD (gold/silver — the one pair with a genuine structural/monetary link)

## 3. Cointegration protocol
- **Engle-Granger:** OLS hedge ratio β (log P_a on log P_b + const), ADF on residual. p<0.05 = cointegrated.
- **Johansen:** `coint_johansen(det_order=0, k_ar_diff=1)`; trace & max-eig vs 95% critical values.
- **OOS stability (the decisive coint gate):** β fit on **first 50%**, spread built on **second 50%**
  with that fixed β, ADF on the OOS spread. p_oos<0.05 required. Also report per-year coint fraction.
- **OU half-life** of the full-sample spread (AR(1) of Δspread on lagged spread). Buckets:
  ≤10d "fast", 10–30d "slow", >30d "too slow for an intermittent hard-stopped sleeve".

## 4. Signal & execution (frozen)
- **Spread:** `s_t = logP_a,t − β_roll·logP_b,t`, β_roll = rolling OLS over trailing **252 trading days** (causal).
- **z-score:** rolling mean/std over trailing **60 days** (causal). No look-ahead anywhere.
- **Entry** |z|>z_in ; **exit** |z|<z_out ; **hard stop** |z|>z_stop=4.0 (divergence = coint break → cut, realise loss).
- **Timing:** signal on close of T−1, **execute at close of T (1-bar delay)**. Non-overlapping trades.
- **Grid (pre-registered search space, for DSR N):** z_in∈{1.5,2.0,2.5,3.0} × z_out∈{0.0,0.5} = 8 configs
  × 12 pairs = **96 trials** tracked for DSR.
- **Cost (NET, mandatory):** per round trip = 2 legs × `rt_cost_bps` (active-fill: spread + slippage +
  commission; FX 1.9 / index 1.9 / metal 2.64 bps/leg RT) **+ financing** = per-leg swap (measured FTMO
  anchors, §`lib/ftmo_costs.py`) × nights held, x3 on triple-rollover weekday. Stress: swap ×1.5, slip ×1.5.
- **Vol targeting:** spread P&L scaled to 10% annual (63d rolling σ) for Sharpe comparability.

## 5. Two-sided requirement (decisive falsifier — L25/L27)
Long-spread and short-spread P&L reported **separately**. A pair qualifies as two-sided only if
**both legs net ≥ 0 with short-leg HAC t > −1**. A one-sided spread = relative drift = beta trap → REJECT,
regardless of pooled Sharpe.

## 6. Success / fail thresholds (frozen)
| Gate | RESEARCH_PASS | PROPFIRM_PASS |
|---|---|---|
| Net Sharpe (after cost+swap) | > 0.7 | > 1.0 |
| HAC t (lag-6) | > 2.5 | > 2.5 |
| Walk-forward folds positive (≥5) | > 50% | > 60% |
| Max drawdown | < −25% | < −10% (FTMO floor) |
| OOS cointegration | required | required |
| Two-sided (both legs net≥0) | required | required |
| DSR (Bailey-LdP, N=96) | > 0.5 | > 0.95 |

## 7. Pre-declared falsification triggers (any ⇒ Piste A FALSIFIED, with the named mechanism)
- **F1:** 0/12 pairs OOS-cointegrated → "no stable structural anchor".
- **F2:** all OOS-stable pairs have half-life > 30d → "half-life wall → financing-forced".
- **F3:** for every OOS-stable pair, cost+financing ≥ gross reversion → "financing/cost dead".
- **F4:** no pair is two-sided → "relative-drift beta trap in market-neutral costume".
- **F5:** best DSR < 0.5 across the 96-trial space → "multiple-testing artefact".

## 8. Candidate criterion (what would make this a CANDIDATE-TO-REVALIDATE, not falsified)
A pair passing all §6 RESEARCH_PASS gates AND two-sided AND OOS-coint AND DSR>0.5. For any such
candidate we then report the §4 profile: ρ vs market beta, skew, bounded excursion, behaviour under the
hard stop, net cost — and specify exactly what to re-run on the audited FTMO engine
(`data/ftmo_portfolio/audit_v2_independent/`) before any deployment consideration.

**Modifications budget:** 3 (repo rule). The §4 grid above is the frozen search space, not modifications.
