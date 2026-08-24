# PREREG — Non-crypto multi-asset daily trend sleeve on FUTURES

**Status: LOCKED 2026-06-14, before any signal/return/metric computation.**
Any change to the kill criteria, gates, universe, cost model, or hypotheses below AFTER
data contact invalidates the pre-registration and must be logged as such in REPORT.md.
This file is git-committed as the lock. Separate program from FTMO — does NOT touch the
FTMO `REGISTER.md` (single-writer convention). Trials are logged in `trials_log.csv` here.

---

## 0. Objective (narrow, falsifiable)

Does a **non-crypto** multi-asset **daily trend** sleeve on **futures** add a *decorrelated*
return stream to the existing personal book (Strategy A crypto-TSMOM + Strategy B
delta-neutral carry), with a net Sharpe that survives **DSR + walk-forward + honest futures
costs**, AND a **positive marginal contribution** to A+B (not merely standalone-positive)?

This is the futures re-test of a corner killed on FTMO (Session F) where the killer was the
overnight CFD swap hurdle (L36). **Futures carry no nightly swap** — cost of carry is embedded
in the term structure and rolls through a back-adjusted continuous series — so the futures
version is a legitimately open question.

**Prior (NOT a target to reproduce):** an independent Ed-Seykota-style replication
(`data/seykota_trend/`, verified V1–V7) produced full-system Sharpe 0.94 / long-only 1.19 over
2014–2026 on a 6-asset CFD/spot universe. **Critically, ~55% of that Sharpe is BTC+ETH**
(attribution: BTC 44%, ETH 11%); the non-crypto remainder is USOIL 26% / US100 8% / XAU 6% /
US500 5%. The prior used CFD costs (2–10 bp/side) and did NOT compute marginal contribution to
A+B. This study redoes the corner: non-crypto, futures, futures-correct costs, marginal lens.

**Primary deliverable metric = MARGINAL Sharpe to A+B at matched vol.** Standalone Sharpe is a
necessary screen, not the verdict.

---

## 1. Kill criteria (locked, forward-looking — sunk cost is not a justification)

- **K1 (DSR).** DSR ≤ 0 after deflating by the **full trial count** (every backtested config in
  `trials_log.csv` counts) → **KILL**.
- **K2 (directional symmetry, L25).** A directional asymmetry that does NOT hold **per-subperiod
  AND per-asset** → **KILL the symmetric system**; only a regime-conditioned / long-biased
  variant may survive. Validation: split-by-direction, per asset, per subperiod; placebo
  RE-DERIVES breakout features on **block-shuffled returns**, never permutes the PnL column.
- **K3 (incumbent-marginal).** If adding the sleeve to A+B does **not raise** portfolio Sharpe at
  matched portfolio vol → **NO SLOT** (clean kill, logged as a deliverable).
- **K4 (walk-forward).** OOS Sharpe collapses (< 0.5) **or** sign-flips in ≥ 2 of ≥ 5 folds →
  **KILL**.

## 2. Gates (pre-declared thresholds)

- **RESEARCH_PASS:** net Sharpe > 0.7, MaxDD > −25%, WF > 50% folds positive, alpha t > 1.5,
  DSR > 0.
- **Book-slot (the real bar):** marginal Sharpe uplift to A+B **> 0** at matched vol, AND
  sleeve-to-A correlation **< 0.4** (monthly).
- **Context only (not a gate here):** the project's formal new-strategy D-gate is
  Sharpe(book+D) > 1.10 × 2.31 = **2.54**. Reported for context; the brief's bar for THIS sleeve
  is Book-slot (marginal uplift > 0), which is softer and correct for a diversifier.

**GO** ⇔ RESEARCH_PASS **and** Book-slot **and** not killed by K1–K4.
A clean **NO-GO** with documented rationale **is** a valid deliverable.

---

## 3. Constitution (binding — enforced in code, not just prose)

- **L1** signal at T−1, execute at T: signal on close of bar J → fill at **open of J+1**. No exceptions.
- **L2** walk-forward ≥ 5 folds (expanding-window / CPCV-style); AMTP/DSR for multiple testing.
- **L5** FUTURES, not ETFs: continuous **back-adjusted** contracts; the roll is IN the series.
- **L8** canonical: **excess** returns vs DTB3, HAC Newey-West **lag-6**, daily vol-target
  (63d std × √252) for any IC / alpha-t computation.
- **L19** any "improvement" is ablated AND compared to a baseline **rescaled to the same
  realized/operational vol**. De-levering trivially cuts DD — that is not an edge.
- **L25** two-sided validation by split-by-direction, per asset, per subperiod (see K2).
- **L26** delay-1 is the decisive arbiter (DSR is blind to fill artifacts). Stops intrabar; gaps
  fill at the **open** (worse than the stop), never at the stop level.

---

## 4. Universe (locked)

- **CORE (non-crypto, 7):** NQ, ES, GC, CL, 6E, 6A, 6B.
  - Sizing/granularity modeled in **micros** (MNQ, MES, MGC, MCL, M6E, M6A, M6B) for a ~$100k
    book, matching Strategy C / MNQ.
  - MES/MNQ are highly correlated (equity-index cluster) → handled via **cluster risk budget**,
    not naive equal weight.
- **EXTENSION (Phase 4 breadth only, L19-disciplined add-on):** RTY (Russell), SI (silver), ZN
  (10Y). Tested ONLY as a constant-risk-budget add-on with **no new optimized parameter**.
- **CRYPTO:** excluded from CORE (Strategy A already owns crypto-long momentum; corr ≥ 0.8 is
  unavoidable → L4 redundancy). Crypto enters ONLY as a **SHORT-ONLY ablation** for bear-market
  convexity (2018/2022), explicitly to avoid double-counting A's long-crypto exposure.

## 5. Data (locked)

- **Price path source:** yfinance continuous `=F` (ES=F, GC=F, CL=F, 6E=F, 6A=F, 6B=F; ext
  RTY=F/SI=F/ZN=F), daily OHLC. For a slow daily trend system the `=F` price path ≈ the actual
  micro future. **NQ** is additionally built from the **local Databento CME batch**
  (`data/GLBX-…NQ.FUT`) as a gold-standard, self-back-adjusted reference; **NQ=F is
  cross-validated against it** (corr, ATR, Sharpe) to validate the `=F` sourcing for the others.
- **Back-adjustment:** **proportional (ratio)** so % moves and ATR levels are preserved across
  rolls. For yfinance `=F`, apply the `AdjClose/Close` ratio to O/H/L (or, if Yahoo does not
  adjust, build proportional back-adjustment from detected roll gaps). For Databento NQ, build
  proportional back-adjustment from the individual contracts + roll dates. **Additive vs
  proportional is flagged as a robustness check** (Phase 3).
- **Period:** primary backtest **2014-01-01 → 2026-06-12** (matches the prior's extended window;
  2013 data reserved for EMA100 warmup). RTY extension starts 2017-07.
- **RF:** FRED DTB3 (local: `data/raw/fred_DTB3_*.parquet`) for excess returns.
- **SPX:** `^GSPC` for monthly correlation / crisis-alpha checks.

## 6. Cost model (futures-correct — this is what makes the question open)

- **NO overnight CFD swap.** Carry is in the term structure / roll. Do NOT bolt on a swap.
- **Per-side friction:** commission + exchange + slippage ≈ **0.5–1.0 bp** baseline, set
  **per-instrument** from each micro's tick value / typical notional (≈ $0.5–1.5 round-turn comm +
  1 tick slippage/side). Slippage is in the BASE cost.
- **Roll cost:** cross the bid-ask **once per roll per contract held** (index/FX quarterly ≈ 4/yr;
  GC ≈ 6/yr; CL monthly ≈ 12/yr). Charged explicitly on roll days for held positions.
- **Stress:** ×2 and ×3 on all frictions (the prior showed cost-immunity at ~28d hold — verify).

## 7. System — pre-registered PRIMARY config (the video's params, NOT in-sample-optimized)

| Param | Value | Param | Value |
|---|---|---|---|
| EMA trend filter | 100 d | Risk per unit | 1% of equity |
| Breakout window | 20 d (close-based) | Max add-ons | 3 (≤4 units) |
| ATR | 14 d (Wilder) | Pyramid step | 0.5 × ATR |
| Trailing stop | 3 × ATR chandelier, ratcheting | Gross cap (cash variant) | 100% |
| Execution | open J+1, stops intrabar | Initial equity | $100,000 |

Two-sided, trend-filtered, non-crypto core. **Cash variant (gross ≤ 100%) is the realistic
deployment**; literal-leverage variant reported as a theoretical upper bound only.

## 8. Trial-counting protocol (for honest DSR — locked)

- Every distinct **signal/system config that produces a Sharpe** is appended to `trials_log.csv`
  and **counts toward DSR N_trials**. Cost-stress multipliers on a fixed config are NOT new
  trials (same signal); ablations and grid points ARE.
- **Pre-declared planned grid (bounds the count a priori):** parameter grid EMA{50,100,150,200} ×
  breakout{10,20,40,55} (≤16) + stop{2,3,4}×ATR × pyramid_step{0.5,1.0} (≤6) + ablations
  {no-EMA, no-pyramid, long-only, stop-4×} (≤4) + H1 short variants (≤3) + H2 vol-target (≤2) +
  H3 breadth/ensemble (≤2) + Phase-1/2 baselines (≤2). **Planned ceiling ≈ 37 trials.** The actual
  count from `trials_log.csv` is used; if it exceeds the ceiling, the excess is disclosed.
- **Reported headline = the PRE-REGISTERED primary config** (Section 7), deflated by the full
  trial count (conservative). The in-sample-best config is reported SEPARATELY and flagged as
  selection-biased.

## 9. Phase-1 gating rule (locked, to prevent goalpost-moving)

Phase 1 screens whether a trend signal exists on this futures universe before any full backtest.

- **Primary statistic:** pooled time-series-momentum IC — regress next-day excess return on the
  lagged standardized trend signal across the non-crypto universe; HAC lag-6 t-stat.
- **Secondary:** breakout-conditional forward-payoff (mean forward R after a 20d-breakout entry,
  vs block-shuffled placebo).
- **Decision:**
  - primary |t| **> 2.5** → **PASS** (proceed).
  - **1.65 ≤ |t| ≤ 2.5** → **MARGINAL** — proceed to full backtest but DSR/WF are decisive, and
    the marginal status is reported. (Rationale: a breakout/trailing-stop system's edge is
    *convexity*/payoff asymmetry, which a linear daily IC understates; the secondary test guards
    against full-backtesting a truly dead signal.)
  - primary |t| **< 1.65 AND** secondary payoff indistinguishable from placebo → **STOP, log.**

## 10. Hypotheses (Phase 4 — each tested under L19: ablate AND compare to baseline rescaled to
the same realized vol)

- **H1 — conditional / long-biased shorts.** Short only assets without positive structural carry
  (energy, crypto) OR stricter short filter (EMA200↓ AND 12m momentum < 0) OR half risk on shorts.
  Must clear K2 (hold per-asset AND per-subperiod).
- **H2 — portfolio vol-target (~15% ann.).** EWMA covariance of current positions, per-cluster
  risk budgets (indices / metals / energy / FX), proportional DD de-lever — vs the binary
  100%-cap baseline **rescaled to the same realized vol**.
- **H3 — breadth.** Extension universe + parameter ensemble {20,40,55}d × {2,3}×ATR at constant
  risk budget. Must add Sharpe with **NO new optimized parameter**.

## 11. Reproduction / engine

Reuse the verified `data/seykota_trend/engine.py` (V1–V7 pass: accounting identity, no
look-ahead, fill integrity, −1R bounded). Port into `strategies/trend_futures/engine.py` with:
futures per-instrument bp costs, explicit roll-day cost, no swap, an integer-micro sizing mode.
Re-run the V1–V7 verification on the futures port before trusting any number.

---

*Locked pre-registration. Past performance, simulated a fortiori, does not guarantee future
results. Not investment advice.*
