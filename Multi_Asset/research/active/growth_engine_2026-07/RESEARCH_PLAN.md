# RESEARCH PLAN — Aggressive growth engine (futures + forex), €12k IBKR

**Date:** 2026-07-16 · Frozen plan, to be launched via /goal. Successor to the Sharpe-max book (whose
audit showed high Sharpe is un-monetizable at retail borrow cost). New objective = **geometric growth**.

## 0. Objective & constraints (frozen)
- **Goal:** maximize compound growth of a €12k IBKR account. Aspiration: double / 6 months (~300%/yr);
  honest target: the maximum growth the real edge supports (likely 30–80%/yr = double in 1–2 yr).
- **Risk mandate:** NO max-drawdown constraint. The ONLY hard limit = **minimize probability of ruin**
  (account → near-zero). Deep drawdowns (50%+) are accepted; going to zero is not.
- **Universe:** futures (micros for €12k granularity) + forex (via CME FX futures or spot). NO crypto
  (revisit later; user's prior: no edge beyond beta — consistent with session findings).
- **Vehicle advantage (the crux):** futures embed leverage at ≈ risk-free cost → Kelly-leverage is
  actually monetizable here (unlike the ETF book, killed by ~6% margin cost). This is why futures fit.

## 1. Core thesis
The right engine for *growth + ruin-avoidance* is a **POSITIVE-SKEW directional edge run at fractional
Kelly on cheap futures leverage.** Positive skew (cut losers, let winners run) is ruin-PROTECTIVE — it is
why CTAs lever trend aggressively without blowing up. Negative-skew families (carry, short-vol,
mean-reversion) are ruin-PRONE at leverage → excluded as the core engine (allowed only as tiny satellites).
**Trend-following was rejected this session under a Sharpe/propfirm gate — the WRONG objective. Re-open it
under the growth gate below.**

## 2. Hypotheses (ranked by prior EV for THIS objective)
- **H1 — Diversified TSMOM / managed-futures core** (multi-lookback 1/3/6/12m, vol-scaled, long-short)
  on a broad micro-futures set (MES/MNQ/M2K/MYM, MCL/MGC/SIL/MHG, ZN/ZB, M6E/M6A/M6B FX). Positive skew +
  crisis-alpha. **The primary engine candidate.**
- **H2 — Breakout / channel momentum** (Donchian / range breakout, defined-risk stops) single- and
  multi-instrument. Positive skew, bounded per-trade loss.
- **H3 — Cross-asset momentum + "risk-off" overlay** (momentum + a trend-following short-leg that goes
  short in drawdowns = ruin hedge).
- **H4 — Forex trend** (G10 majors, TSMOM/breakout on CME FX futures — cheap leverage, no CFD swap).
- **H5 — Ensemble** (combine H1–H4 signals; ensembles reduce single-signal noise → higher growth-rate).

## 3. The GROWTH gate (replaces the Sharpe-max PERSONAL_PASS)
A candidate is promoted only if ALL hold:
1. **Positive geometric growth at HALF-Kelly, net of real futures cost** (commission + slippage; ~$2–5 RT
   micro). Growth, not Sharpe, is the objective function.
2. **Skew ≥ 0** on the trade/return distribution (ruin-protective). Negative-skew → rejected as core.
3. **Honest deflation** — DSR (Bailey-LdP) at honest N, walk-forward OOS ≥5 folds, two-sided (not pure
   long beta: must make money on BOTH long and short legs, else it is leveraged-long = crash-ruin).
4. **MC ruin probability chiffered** at full / half / quarter Kelly over 6mo & 1yr (block-bootstrap +
   trade-based generator; report P(account < 20% of start)). Promote the sizing that maximizes growth
   subject to **P(ruin 1yr) < 25%**.
5. **€12k-deployable** on micro contracts (granularity: 1 micro ≤ ~1 unit of the target vol).

## 4. Sizing framework (frozen)
- Estimate edge → **DEFLATE it** (assume in-sample SR overstates; use OOS/DSR-shrunk SR).
- Size at **half-Kelly of the DEFLATED edge** (never full — over-betting is the #1 ruin cause; estimate
  is uncertain).
- Report the full growth-vs-ruin frontier (quarter/half/full Kelly) so the user picks aggression seeing
  the ruin number explicitly.
- **Bond base retained**: month-end Treasury sleeve runs in parallel (uses capital ~3 days/mo, near-cash
  2%/yr, does not consume the risk budget) — a free additive base, NOT levered.

## 5. Anti-overfit discipline (same rigor as the audited session)
- Pre-register each H (signal, params, kill-rules) BEFORE results; freeze by commit.
- OOS split + DSR at honest N (the session's hard lesson: headline Sharpes inflate 2–3×).
- Roll-clean data for commodity futures; verify no look-ahead (signal lag explicit).
- Independent external-agent audit of the final engine before any deploy.

## 6. Data & vehicles
- Micro futures (CME): MES/MNQ/M2K/MYM (equity), MCL/MGC/SIL/MHG (commodity), M6E/M6A/M6B (FX), micro
  yield (rates). Prices: yfinance =F continuous + deep_history_utc (roll-clean cross-check).
- Forex: CME FX futures (cheap leverage) or deep_history_utc spot for signal research.

## 7. Success criterion (what "done" means)
NOT "Sharpe > X". Instead: **the sizing/strategy that maximizes honest half-Kelly geometric growth with
MC P(ruin 1yr) < 25%, deployable at €12k on micro futures**, with the growth-vs-ruin frontier reported so
the user sets aggression. Realistic expectation stated up front (30–80%/yr likely; 6-month doubling only
if a genuinely strong positive-skew edge survives deflation — flagged honestly, ruin quantified).

## 8. Deliverables
Pre-regs + RESULTS per H, the combined engine, the growth-vs-ruin frontier, the €12k execution plan
(micro-contract mapping + Kelly-fraction sizing), and an independent audit. All in
`Multi_Asset/research/active/growth_engine_2026-07/`.
