# Strategy Research Log

## Portfolio Status
- Strategy A (TSMOM): LIVE on testnet
- Strategy B (Delta-neutral carry): LIVE on testnet
- Strategy C: RESEARCH ONGOING

---

## Strategies Currently Live

### Strategy A — Time-Series Momentum (TSMOM)

**Status**: LIVE — testnet  
**Files**: `tsmom_strategy.py`, `tsmom_backtest.py`, `tsmom_live.py`  
**Reference**: Moskowitz, Ooi & Pedersen (2012)

**Mechanism**: 28-day cumulative log return determines direction (long/short). Volatility-scaled to 15% annualized target. Rebalances only on direction change (~12–17 trades/year per asset).

**Signal**:
```
signal(T) = sign( sum(log_returns[T-28 : T-1]) )
vol_scalar(T) = clip( 0.15 / realized_vol[T-30:T-1], 0.1, 2.0 )
position(T) = signal(T) * vol_scalar(T)
```
Zero look-ahead: both signal and vol scalar use data through T-1 only.

**Assets**: BTC-USD, ETH-USD, SOL-USD (equal risk, 1/3 each)  
**Cost model**: 0.035% fee + 0.05% slippage per side (Hyperliquid)  
**Backtest Sharpe**: BTC 1.41, SOL 1.27 after costs (walk-forward validated)  
**Deployment**: Daily cron 00:05 UTC on Hetzner CX22, Hyperliquid testnet perps

---

### Strategy B — Delta-Neutral Funding Carry

**Status**: LIVE — testnet  
**Files**: `strategies/delta_neutral/live_trader.py`, `strategies/delta_neutral/backtest.py`

**Mechanism**: Simultaneously long spot on Binance testnet and short equal notional as perp on Hyperliquid. Net directional exposure = 0 by construction. Income comes entirely from HL funding payments received every 8h.

**Universe**: Monthly rebalance selects all viable assets where mean 8h funding > carry floor (0.34% weekly ÷ 90 bars). Current active assets: STX, WLD, HMSTR, TST, MEGA, BIO, TRUMP.

**Capital**: $50 per asset, max 5 assets, $250 total  
**Cost model**: 0.42% round trip (BN taker 0.075%×2 + HL taker 0.035%×2 + slippage 0.05%×4)

**Backtest (3m OOS, walk-forward 6m train / 1m test)**:
- Sharpe: 10.22 | MaxDD: -0.52%
- carry_frac: 1.026 (carry dominates; price effect negligible at 0.025)
- BTC-up Sharpe 13.03 / BTC-down Sharpe 7.33

**Risk controls**: One-legged position prevention — BN spot bought before HL short opened; if either leg fails the other is immediately unwound. Position reconciliation on every 8h cycle.

**Caveat**: 3-month OOS is short. Carry filter was corrected (removed incorrect `abs()`) after initial walk-forward. Strategy mechanics confirmed sound; longer OOS validation ongoing.

---

## Strategies Tested and Failed

### MLP on Daily OHLCV

**Status**: FAILED — DO NOT RE-TEST  
**Date tested**: Early project (see `a3d0d04`, `f46290f` in git log)  
**Economic mechanism hypothesis**: Deep learning on standard TA features (momentum, vol, MA, volume) would capture non-linear price patterns and generate reliable BUY/HOLD/SELL signals on daily crypto bars.  
**Signal**: PyTorch MLP classifier on rolling OHLCV-derived features → 3-class output (BUY / HOLD / SELL) with MC Dropout uncertainty  
**Assets / universe**: BTC-USD, SOL-USD (daily perpetuals on Hyperliquid)  
**Feasibility result**: Pre-correction Sharpe 3.56 (inflated by look-ahead bias)  
**Backtest result**: Corrected Sharpe 0.48; walk-forward mean Sharpe 0.40 across 8 BTC folds — not statistically distinguishable from zero (DSR < 0.95)  
**Cause of failure**: One-bar execution look-ahead — original backtester entered trades at `open[i]` using features computed from `close[i]`, which is future information at execution time. Diagnostic: 100% of BUY-signal bars had `Close > Open` — a statistical impossibility without leakage. After correcting to execute at `open[i+1]`, the edge vanished. Corrected walk-forward Sharpe 0.40 has no statistical significance.  
**Key lesson**: Always verify signal timing — signal at t-1, trade at t. No exceptions.

---

### Funding Rate Mean Reversion

**Status**: FAILED — DO NOT RE-TEST  
**Date tested**: See `215d233`, `e761936` in git log  
**Economic mechanism hypothesis**: Hyperliquid perpetual funding rates mean-revert predictably; an hourly z-score strategy should capture the reversion premium.  
**Signal**: Hourly z-score on Hyperliquid funding rates — long when funding rate z < -threshold, short when z > +threshold  
**Assets / universe**: BTC, ETH, SOL perps on Hyperliquid  
**Feasibility result**: BTC Sharpe -0.35, ETH -1.76, SOL +0.52  
**Backtest result**: N/A (failed feasibility except SOL; SOL result not robust)  
**Cause of failure**: Funding income (~$4/trade) covers only 17% of fees (~$22/trade). High signal turnover at hourly granularity makes fees prohibitive. The z-score fires too frequently relative to the carry income per signal event.  
**Key lesson**: Verify gross income vs fee ratio before any backtest on high-turnover strategies.

---

### Cross-Sectional Momentum L/S

**Status**: FAILED — DO NOT RE-TEST  
**Date tested**: See `c179c8d` in git log  
**Economic mechanism hypothesis**: Cross-sectional momentum (rank assets by past return, long winners, short losers) would work in crypto as it does in equities.  
**Signal**: Weekly cross-sectional return ranking; long top assets, short bottom assets  
**Assets / universe**: 20-asset large-cap crypto universe  
**Feasibility result**: Long leg +105%, short leg -107%, net -1%  
**Backtest result**: Net return near zero; long leg captures momentum but short leg destroys it  
**Cause of failure**: Crypto losers mean-revert systematically, destroying the short side. The short leg bets against assets that subsequently recover violently, producing consistent losses that offset long-side gains.  
**Key lesson**: No short side on crypto momentum. Losers mean-revert, winners trend.

---

### Crypto Pairs Trading (Cointegration)

**Status**: FAILED — DO NOT RE-TEST  
**Date tested**: See `9fc5c5a`, `491172c`, `84c7123` in git log (Strategy B, closed)  
**Economic mechanism hypothesis**: Cointegrated crypto pairs (BTC/ETH and other L1s) would produce a stationary spread with sufficient mean-reversion frequency to trade profitably.  
**Signal**: Johansen cointegration spread z-score; enter when |z| > threshold, exit at z=0  
**Assets / universe**: BTC/ETH and other L1 pairs on Hyperliquid  
**Feasibility result**: IC real (GO verdict at feasibility); walk-forward verdict: INSUFFICIENT_DATA across all three walk-forward attempts (12m, 36m, rolling 12m windows)  
**Backtest result**: Walk-forward INSUFFICIENT_DATA — could not complete a single full fold with adequate signal frequency  
**Cause of failure**: Trade frequency too low on the Hyperliquid universe. The cointegration spread moves slowly on the liquid large-cap pairs available; the strategy generates too few signals to achieve statistical significance in any realistic live trading period.  
**Key lesson**: IC alone is not enough. Signal frequency must support the cost model.

---

### Cross-Sectional Funding Carry (without hedge)

**Status**: FAILED — DO NOT RE-TEST  
**Date tested**: See `strat-C` entry `1fd650f` in git log; `strategies/funding_carry/`  
**Economic mechanism hypothesis**: Ranking assets by funding rate and going long high-carry assets would capture the funding premium as income.  
**Signal**: Rank assets by funding rate; long high-carry assets (no spot hedge)  
**Assets / universe**: 20-asset crypto universe  
**Feasibility result**: Carry IC 0.54 (strong signal); net walk-forward Sharpe -0.68 (7d rebalance); carry P&L +3.93, price P&L -0.64, fees destroy remainder  
**Backtest result**: Sharpe -0.68; carry_frac 35% (directional beta dominates carry at 65%)  
**Cause of failure**: Without a delta hedge, the long-only carry portfolio has full directional exposure to crypto. In bull markets the beta gains dominate; in bear markets the beta losses dwarf the carry income. The carry signal is real (IC 0.54) but the unhedged implementation is just leveraged directional beta — not an isolated carry premium.  
**Key lesson**: Carry signal requires delta-neutral execution to isolate the premium.

---

### Weekend Return Anomaly

**Status**: FAILED — DO NOT RE-TEST  
**Date tested**: See `93464b7` in git log (strat-D)  
**Economic mechanism hypothesis**: Crypto exhibits a weekend effect (predictable return pattern Friday close to Monday open) exploitable as a systematic signal.  
**Signal**: Long Friday close, exit Monday open on BTC and ETH  
**Assets / universe**: BTC-USD, ETH-USD  
**Feasibility result**: Sharpe 0.42; funding income +$8.7k but fees -$5.4k  
**Backtest result**: Sharpe 0.42 — below minimum threshold of 0.8  
**Cause of failure**: Edge is below the minimum Sharpe threshold (0.8) required for live deployment. The weekend effect is real but too small to survive realistic costs and execution risk. The anomaly has likely been partially arbitraged away.  
**Key lesson**: Seasonal anomalies in crypto have largely been arbitraged away.

---

### TSMOM × Funding Carry Signal Stack

**Status**: FAILED — DO NOT RE-TEST  
**Date tested**: See `06efa77` in git log; `strategies/signal_stack/`  
**Economic mechanism hypothesis**: Combining the cross-sectional TSMOM signal with funding carry would produce a diversified signal stack with higher Sharpe than either signal alone.  
**Signal**: Cross-sectional TSMOM combined with funding carry signal; weighted combination  
**Assets / universe**: Multi-asset crypto universe  
**Feasibility result**: Combined Sharpe -0.33 vs TSMOM standalone Sharpe -0.39; correlation between signals = -0.21  
**Backtest result**: Cross-sectional TSMOM Sharpe -0.385; signal combination added noise  
**Cause of failure**: Cross-sectional TSMOM doesn't generalize beyond BTC. The time-series TSMOM edge is asset-specific (BTC and SOL show it; the cross-sectional variant does not). Stacking an unvalidated signal onto a borderline signal degraded rather than improved performance.  
**Key lesson**: Validate each signal independently before stacking.

---

### Cross-Sectional Short-Term Reversal (STR)

**Status**: FAILED — DO NOT RE-TEST  
**Date tested**: 2026 (this session); `str_feasibility.py`  
**Economic mechanism hypothesis**: Weekly cross-sectional return reversal (losers bounce, winners give back) produces a tradeable long-only signal in large-cap crypto, analogous to Zaremba et al. (2021) findings in small-cap coins.  
**Signal**: `-1 × last week return`, rank-normalized cross-sectionally; long top-3 assets per week  
**Assets / universe**: 15 large-cap assets (BTC, ETH, SOL, BNB, AVAX, LINK, DOT, AAVE, LTC, ADA, ATOM, DOGE, XRP, TRX, NEAR)  
**Feasibility result**: Mean IC 0.019, t-stat 0.85, ICIR 0.06, hit rate 52.4%, long-only IC -0.041. FAIL.  
**Backtest result**: Not run (failed feasibility)  
**Cause of failure**: Large-cap crypto exhibits momentum, not reversal, at weekly frequency. The long-only IC of -0.041 confirms the top-ranked (most-reversed) assets actually underperform. Reversal exists only in small/illiquid coins where institutional arbitrage is absent (Zaremba et al., 2021).  
**Key lesson**: Reversal signal requires small/illiquid universe. Large-caps trend.

---

### Vol-Regime Mean Reversion

**Status**: FAILED — DO NOT RE-TEST  
**Date tested**: 2026 (this session); `vol_regime_mr_feasibility.py`, `vol_regime_mr_backtest.py`  
**Economic mechanism hypothesis**: BTC price mean-reverts within low-volatility regimes (RV < 40th percentile). Filtering to low-vol periods would isolate the regime where mean reversion operates and suppress noise.  
**Signal**: `-1 × 5-day price z-score` (z = (price − 20d mean) / 20d std), active only when 20d RV < expanding 40th percentile  
**Assets / universe**: BTC-USD  
**Feasibility result**: IC 0.344, t-stat 9.45, ICIR 0.73, hit rate 78.1%. FALSE POSITIVE — PASS verdict was a methodology failure.  
**Backtest result**: Sharpe -0.85, win rate 18.1%, cost drag 43.5%, max drawdown -66.1%. FAIL.  
**Cause of failure**: The feasibility IC measured intra-week rank correlation (signal on day T vs same-day return in a weekly window), not the Monday-open to Friday-close trade P&L the backtest used. The IC study showed a real intra-week pattern; the backtest measured a different, worse outcome. The win rate of 18.1% is the clearest symptom — the signal is right on rank but wrong on direction at the trade execution level.  
**Key lesson**: Always verify IC and backtest measure the **identical** signal→outcome pair. A feasibility PASS that uses different timing than the backtest is a methodology failure.

---

### Fear & Greed Contrarian

**Status**: FAILED — DO NOT RE-TEST  
**Date tested**: 2026 (this session); `fg_contrarian_feasibility.py`  
**Economic mechanism hypothesis**: Extreme fear (F&G < 20) marks oversold conditions ripe for recovery; extreme greed (F&G > 80) marks overextension due for reversal. Contrarian entries at both extremes would produce positive 5-day forward returns.  
**Signal**: Long when F&G index < 20, short when F&G index > 80; 5-day hold; 5-day minimum signal gap  
**Assets / universe**: BTC-USD, 2018-2025  
**Feasibility result**: IC -0.062, t-stat -0.65, hit rate 50.5%; fear-side mean return +1.2%, greed-side -2.5% (wrong direction for short). 107 total signals (15.6/year). FAIL.  
**Backtest result**: Not run (failed feasibility; negative IC)  
**Cause of failure**: Greed signals don't work — crypto greed periods continue trending (momentum dominates mean reversion). The IC is negative because the greed-side short is in the wrong direction. The fear side has marginal directional merit (+1.2%) but this is far below the 4.4% cost breakeven required at 5-day hold with 0.34% round-trip costs.  
**Key lesson**: Sentiment contrarian only works at extreme fear (not greed) in crypto. Even the fear-side returns are too small at daily granularity to clear 0.34% round trips.

---

### BTC-Neutral Residual Mean Reversion

**Status**: FAILED — DO NOT RE-TEST (accessible only at <0.1% fees)  
**Date tested**: 2026 (this session); `residual_mr_feasibility.py`, `residual_mr_backtest.py`  
**Economic mechanism hypothesis**: After stripping BTC beta via rolling OLS, the idiosyncratic residual of alt coins mean-reverts predictably. Trading the z-score of the residual (long when residual underperforms, short when it overperforms) isolates a pure idiosyncratic mean-reversion premium.  
**Signal**: Strip 180-day rolling BTC beta; trade z-score of residual return (30d window); enter when |z| > 1.5, long-only (z < -1.5 → long; short side not viable per prior lessons)  
**Assets / universe**: ETH-USD, BNB-USD (SOL dropped: >5% missing pre-2021); 2020-2025  
**Feasibility result**: ETH IC 0.217, t-stat 8.42, hit rate 67.1%. BNB IC 0.159, t-stat 6.29, hit rate 60.8%. Pooled t-stat 5.50, ICIR 0.30. Genuine strong signal. PASS.  
**Backtest result**: Sharpe -0.39, win rate 55.9% gross, avg hold 2.0 days, cost drag 15.7%. FAIL.  
**Cause of failure**: The actual mean reversion completes in ~2 days, not the 5-day IC measurement horizon. At 0.34% round trip, a 2-day hold requires ~4.4% return to break even; the signal produces ~0.85% mean return. The edge is genuine but the cost structure makes it inaccessible at Hyperliquid/Binance retail fees.  
**Key lesson**: The IC horizon and the execution horizon must match. This edge is accessible only to market makers or venues with fees < 0.1%.

---

## Research Conclusions

### What Works on This Setup
- Strategies with hold periods ≥ 7 days survive 0.34% round trips
- Structural premia (carry, trend) outperform statistical signals on a small liquid universe
- Long-only on large-caps only — short side consistently fails

### What Doesn't Work on This Setup
- Any reversal/mean-reversion strategy: reversion completes before costs are recovered
- Cross-sectional strategies: universe too small
- High-frequency signals: fee structure prohibitive
- Sentiment timing: insufficient signal magnitude

### Open Research Directions (Future)
- Residual MR viable with <0.1% fees (market maker tier or DEX)
- STR viable with 100+ coin universe including small-caps
- On-chain metrics (SOPR, active addresses) as Strategy C signal — requires Glassnode access
