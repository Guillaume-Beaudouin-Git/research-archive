# Stat-arb on FTMO — consolidated verdict (6 ideas, clean slate)
*2026-06-03. Pre-registered per `RESEARCH_PROTOCOL_statarb.md`; no p-hacking; every verdict on validated data. This is a clean, falsified negative result — a CV asset, not a failure.*

## One-line verdict
**Compliant stat-arb does not yield an FTMO-deployable edge.** Across 6 pre-registered ideas spanning FX, indices, commodities, crypto and equities, none passes the FTMO 2-step barrier. The one idea with a genuine risk-adjusted edge (gold/silver rotation) is incompatible with the −10% floor. This extends the program's canonical finding — *"no accessible retail alpha; only long-equity beta survives"* — into the stat-arb domain, now on clean data.

## The 6 ideas
| # | Idea (compliant, single-leg) | Result | Why it fails on FTMO |
|---|---|---|---|
| 1A | AUD/NZD cross reversion | ❌ kill | cross-level β=1 barely reverts (Hurst 0.47); no significant edge on clean data |
| 1B | EUR/GBP cross reversion | ❌ kill | clean 27y (ECB): t=0.58, 14/27 yrs +, p(funded) 20–34%. (3.5y "promise" was overfit; yfinance synthetic was an artifact) |
| 2B | NQ intraday OU reversion | ❌ kill | no gross edge (t=−1.1) + 37 trades/day → cost-killed (L33) |
| 5B | US x-sectional reversion | ❌ kill | neutral form (losers−winners) = hedging-rule violation; compliant long-only alpha cost-killed by ~10 bps → only beta survives |
| 4A | ETH/BTC ratio (ETH directional) | ❌ kill | RV-timing underperforms passive ETH (Sh 0.35 vs 0.57); fails barrier (p(funded) 16–23%) |
| 3A | Gold/Silver rotation | ❌ kill *(for FTMO)* | **real edge over buy-&-hold (Sh 0.77, t 2.16, cost+delay robust) BUT −50% maxDD ≫ −10% floor → p(funded) 24–27%, bust 73%** |

## The two structural reasons (the actual finding)
1. **The FTMO hedging rule strips the edge.** Stat-arb's edge lives in the *market-neutral spread* (cointegration residual with β≠1; losers−winners). FTMO forbids "opposing positions on correlated instruments," forcing a **single-leg** expression that discards the hedge ratio. What's left is either (a) a near-random single series (cross levels: 1A/1B), or (b) directional beta with an RV overlay (3A/4A/5B).
2. **What remains then dies on cost or on the barrier.** Single-leg signals are either **cost-killed by turnover** (2B intraday, 5B long-only) or, when a genuine edge exists (3A), they require **volatility incompatible with the −10% static floor** — the metal's daily swings breach the floor before the +10% target, at any leverage.

**3A is the instructive exception:** a real, cost-robust, delay-robust risk-adjusted edge (gold/silver rotation, net Sharpe ~0.77) — that is simply in the **wrong container**. It would be a legitimate medium-Sharpe swing strategy in a *normal* trading account; the FTMO barrier (not the signal) is what kills it. Portable finding if a non-barrier account is ever in scope.

## Methodology wins banked (CV-grade)
- **The anti-artifact check earned its keep:** it caught a **false positive** (synthetic EURGBP "18/18, t=3.9" — yfinance ratio desync, return-corr 0.018 vs real) AND a **false negative** (AUDNZD "kill" on the same bad data). Both prior verdicts were data artifacts; clean data reversed them.
- **Data-source lesson (now in the protocol):** yfinance daily FX — ratio *and* direct ticker — is corrupted for daily-return work (return-corr ≈ 0 vs real). Clean FX = **ECB reference rates** (return-corr 0.99) or real broker M1. Single-leg-directional designs (3A/4A) are robust to the ratio artifact because the traded P&L is a real single series.
- **Pre-registration + the L33 cost-first gate** prevented every false rescue; kills were fast and honest.

## Decision
- **Compliant stat-arb branch: CLOSED on FTMO.** 6/6 ideas fail the barrier; the mechanism is structural (hedging rule + cost + the −10% floor), not a tuning shortfall.
- The only thing that has ever survived the FTMO barrier in this program is **long-equity beta with a trend gate + small size + no time limit** (the overnight harvester) — and even that is idealized-cost-fragile (swap; see `_RECONCILIATION_overnight.md`).
- **3A (gold/silver) is logged as a real edge for a non-barrier account**, should that ever become the goal.

*Reproduce: `statarb_audnzd/` — `audnzd_engine.py`, `crossrev_eurgbp.py`, `deep_validate_eurgbp.py`, `nq_ou_engine.py`, `xsec_engine.py`, `ratio_single_leg.py`; pre-regs `IDEA_1A/1B/2B/5B/3A_4A*.md`.*
