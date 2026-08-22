# ITERATION 2 — literature-grounded new angles (pre-registered before results)

**Frozen:** 2026-07-08 · **Goal (user):** for each piste, find a literature-grounded variant reaching
**net Sharpe > 0.5** that is **FTMO-challenge-suitable** — respects **10% total DD** and **5% daily DD**
(and clears the +10% target in the 91-day window). "Not production-ready" ≠ failure → iterate.
**Honesty rule:** same bar as iteration 1 — net of real FTMO cost+swap, DSR on the trial space, explicit
challenge-DD simulation. Report negatives as clearly as positives. Directional (non-decorrelated) variants
are allowed for the CHALLENGE but flagged as such (they are timed beta, not funded-phase §4 sleeves).

## Literature reviewed (sources in `synthesis/SOURCES.md`)
- **Avellaneda & Lee (2010)** — statistical arbitrage via **PCA / ETF factor-residual s-score** (market-
  neutral on the idiosyncratic residual, not pairwise cointegration). Net Sharpe 1.44 (PCA)/1.51 (ETF)
  1997–2007, decaying to ~0.9 by 2007. → Piste A angle: residual-of-index-vs-basket, not a fragile pair.
- **Connors & Alvarez, "Short-Term Trading Strategies That Work"** — **RSI(2) < 10 above the 200-day SMA**,
  long-only, exit > 5-day SMA. Documented Sharpe ~1.0–1.18 but **MaxDD 37–57%** on cash index. → Piste C
  angle: the DD must be cut to <10% with vol-targeting + hard stop + a multi-index portfolio.
- **Lou, Polk & Skouras (2019), "A Tug of War"** — nearly all equity-index gains are **overnight**;
  intraday is flat/negative. → explains why Piste-C's *short* leg failed (fighting overnight drift) and
  motivates an **overnight-drift / intraday-reversion** split.
- **Gold/silver ratio + Kalman/ML regime filter** (2015–2025 studies) — dynamic hedge + regime gate
  **reduces drawdown** vs static z-score. → Piste A angle: DD-control the repo's 3A (Sharpe 0.77, −50% DD).
- **Bollinger squeeze + low-ADX** range fade — real but "win 55–65%, R:R the lever"; edge is amplitude vs
  cost. → Piste B angle: **amplitude filter** (fade only when band width ≫ spread) + causal vol-persistence.

## Pre-registered hypotheses & success criteria

### C-iter (priority 1 — most likely to clear the bar)
**H:** Connors RSI(2)<10 **above SMA200**, long-only, exit >SMA5, on a **4-index portfolio**
(US100/US500/US30/GER40), **vol-targeted to 12%** + **hard stop 1.5×ATR**, nets Sharpe>0.5 with
MaxDD<10% and daily DD<5% after cost+swap.
- Grid (DSR N): entry RSI2∈{5,10}, cumulative-RSI2(2)<{35,50}, exit{SMA5, RSI2>70, 5-day time}, stop{1.5,2.5×ATR} → tracked.
- Falsify if: net Sharpe<0.5 OR MaxDD≥10% OR daily-DD≥5% after cost, on the portfolio.
- **Decorrelation caveat:** long-only = timed index beta (ρ high). Fine for the CHALLENGE; flag for funded.

### A-iter (priority 2)
**H1 (gold/silver DD-control):** XAU/XAG ratio z-score, enter ±2 / exit 0, **hard stop z>3.0** (cut the
divergence that caused −50%) + **vol-target 10%**; nets Sharpe>0.5 with MaxDD<10%.
**H2 (Avellaneda-Lee residual):** s-score of one index's residual vs an OLS/PCA factor of the other three
(rolling, causal); market-neutral; enter s<−1.25 / s>+1.25, exit |s|<0.5. Two-sided.
- Falsify if: net Sharpe<0.5 OR (H1) MaxDD≥10% OR (H2) not OOS-stable / short leg fails.

### B-iter (priority 3 — hardest)
**H:** Bollinger-fade in low-ADX, but **only when band width ≥ k× round-trip cost** (amplitude filter,
attacks the cost gate) AND a **causal vol-persistence** flag (prior-day realized vol in bottom tercile);
nets Sharpe>0.5, gross/cost≥3, two-sided.
- Falsify if: causal gross ≤0 OR gross/cost<3 OR one-sided OR net Sharpe<0.5.

## Deliverables
`iteration_2/{piste_C,piste_A,piste_B}/` engines + RESULTS; `iteration_2/CHALLENGE_SIM.md` (FTMO 2-step
Monte-Carlo/historical for any Sharpe>0.5 candidate); `iteration_2/ITERATION_REPORT.md` (verdicts, DD,
decorrelation status, next steps).
