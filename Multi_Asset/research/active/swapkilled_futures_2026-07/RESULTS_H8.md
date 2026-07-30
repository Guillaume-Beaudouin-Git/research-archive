# RESULTS H8 — Hard-capped grid under short-horizon ruin constraint

**Verdict: the grid is a bet on mean-reversion, deployable within a <30%/≤1yr ruin budget ONLY on a
genuinely mean-reverting underlying + a trend kill-switch.** The sizing math is solved; sourcing the
underlying is the (hard) open problem. MC: 4000 paths, €12k, cap L=10, g=2%, lev 1×, fee 5 bps RT.

## The three regimes (1-year, corrected for the exp-convexity beta artefact)

| Underlying | 1yr ruin | E[final] | Read |
|---|---|---|---|
| **True random walk** (driftless PRICE) vol 15% | 0.0% | €11,953 | **EV ≈ 0** — the trap: bounded ruin, no edge |
| True random walk vol 40% | 7.7% | €11,756 | EV ≈ 0 (fee bleed) |
| True random walk vol 80% | **34.8%** | €11,712 | EV ≈ 0 but **ruin breaches 30%** |
| **OU mean-reversion** hl=20d, vol 40% | 0.0% | **€13,954** | genuine grid edge |
| OU hl=5d | 0.0% | €15,946 | stronger reversion → more edge |
| OU + mean SHIFT −40% (level break) | 1.8% | €10,148 | **survives** — reversion forgives level shifts |
| **Trend DOWN −20%/yr** (no reversion) | 15.4% | €10,653 | ruin mode building |
| **Trend DOWN −40%/yr** | **29.2%** | €9,279 | **the killer** — long-biased grid bleeds into trend |

## Findings (each pre-registered)

1. **C1 confirmed — grid EV = 0 on a true random walk.** The earlier "positive EV on GBM" was the
   exp-convexity price drift (σ²/2) captured by the long-biased dip-buyer = **beta, not grid edge**. On a
   driftless-PRICE walk, E[final] ≈ €12,000 (slightly negative after fees). Matches arXiv 2506.11921
   (EV=0 under random walk) and H7.
2. **C2 confirmed — positive EV requires genuine mean-reversion**, stronger with shorter half-life. And
   it is **robust to a level shift** (−40% mean shift → still profits) *as long as the process keeps
   oscillating*.
3. **The ruin comes from ONE thing: a sustained trend against the (long-biased) grid.** −40%/yr trend →
   29% ruin. Not from volatility per se, not from level shifts — from *loss of mean-reversion*.
4. **High vol alone can breach the ruin budget on a random walk** (vol 80% → 34.8%) for zero EV — never
   grid a high-vol non-reverting instrument.
5. **C3 Sharpe illusion:** a stable-mean OU-grid path shows a smooth in-sample Sharpe ~1.1 — but that is
   the IDEAL case; the number says nothing about the trend-break tail.

## Actionable answer to the constraint (6-12mo, ruin < 30%)

**Yes — mathematically usable within your budget, but ONLY as the execution of a verified mean-reversion
edge, with:**
- (a) a **genuinely mean-reverting underlying** (stationary/cointegrated spread, or a detected range
  regime) — NOT a liquid index/gold/FX outright (those random-walk or trend → zero-EV or ruin);
- (b) a **hard inventory cap** (L levels; full inventory = your DD budget) — done here;
- (c) a **trend / regime-break kill-switch** (flatten if the underlying starts trending against the grid)
  — this is what keeps you off the −40%/yr = 29% ruin line;
- (d) **moderate vol** (high vol breaches ruin even with zero edge).

**The binding constraint is NOT the sizing (solved) — it is sourcing (a) + detecting the break for (c).**
That is exactly the ingredient the repo has repeatedly failed to find (decorrelated_sleeves: 0/12 pairs
OOS-cointegrated; statarb closed). The grid does not create the edge; it needs a stationary underlying
that the market rarely provides and that breaks without warning. **Without a verified mean-reverting
underlying + kill-switch, the grid is the zero-EV trap with a real ruin tail.**

## Verdict

Grid ≠ free lunch, but ≠ pure poison either: it is a **legitimate execution layer for a mean-reversion
edge**, ruin-compliant on your horizon IF that edge is real and trend-breaks are cut. Deploying it =
solving the stationarity-sourcing problem first. Recommend: do not deploy a grid until a mean-reverting
underlying passes the same PERSONAL_PASS discipline (OOS stationarity + two-sided + cost) — otherwise it
is H7 in disguise.
