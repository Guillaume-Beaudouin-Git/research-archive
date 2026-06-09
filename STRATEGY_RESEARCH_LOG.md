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

### Overnight Indices Drift — Midweek-Only (FTMO / Personal Book)

**Status**: CONFIRMED-CLOSED for FTMO sprint ; conditional candidate for FTMO unlimited-time only ; NO-GO personal book.
**Date reconciled**: 2026-06-03 ; see `data/overnight_research/overnight_verification_2026-06.md`
**Specs reconciled**: dossier `data/ftmo_universe/OVERNIGHT_VERIFICATION_REPORT.md` + cross-doc `PropFirms/ftmo_alpha_program/README.md` (Family-5 NO-GO verdict, indépendant)
**Economic mechanism hypothesis**: equity-index overnight risk premium (Cooper-Cliff-Gulen 2008, Lou-Polk-Skouras 2019 "Tug of War"). Midweek concentration (Tue+Wed open-day = Mon-night + Tue-night holds) consistent with cross-market academic data.
**Signal**: long NQ at RTH close of day t−1, exit at RTH open of day t, held only when weekday(open) ∈ {Tue, Wed}. Two-sided NOT considered (long-only equity premium, structural).
**Assets / universe**: NQ databento M1 2010-2026 (canonical) ; reproduced QQQ / ^NDX / SPY / ^GSPC via yfinance daily (G0 independent test).
**Feasibility result**:
- G0 (yfinance independent): QQQ ALL overnight = +4.69 bps, t_HAC6 = 4.20 ; midweek Wed +9.03 (t=3.57). Replicated on SPY/^GSPC/^NDX too.
- G1 (NQ databento independent reconstruction): ALL overnight = +4.895 bps, t_HAC6 = 4.45 (vs dossier 4.90/4.04, exact match Tue +7.44, Wed +8.69).
- G2 (swap unit cross-validated): US100.cash swap_long = −3.08 bps/nuit (1x), point_size=0.01 forcé par digits=2 ; cross-checked EURUSD (−1.11), XAUUSD (−2.93) → industry-consistent.
- G2 net midweek invariant aux 2 conventions 3x : Tue +4.36 / Wed +5.61 bps/nuit. Toutes-nuits net ≈ +0.57 bps (marginal).
- G3 (gap tail) : worst night midweek −6.26%, p1 −1.96%. Levier soutenable FTMO (sans MaxDD>10%) ≈ 0.5×.
- G4 (3 conteneurs) : (a) sprint FTMO 2-step <2mo p(pass)<0.1% à L≤1× → NON-véhicule ; (b) unlimited-time L=0.75× p(funded)=82.4% bust 5.8% median 36 mois ; (c) personal book SR_net=0.68 invariant au levier, MaxDD historique −8.2% à L=0.5×.
- G5 (réconciliation) : β=+0.33 corr=+0.57 vs NQ buy-hold → beta-proxy (L25 trigger) ; OOS≥2019=+6.66 vs IN<2019=+3.52, Welch t=0.85 → OOS hold ; mais **2023-2024 net négatif (−3.9 / −3.4 bps/an mid)** = soft regime drift.
**Backtest result**: SR_net=0.68 (sous RESEARCH_PASS 0.7), AnnRet 2.49%/an à L=0.5×, MaxDD historique −8.21%, worst-month −2.26%. Comparé à A (SR 1.33), B (proxy 2.0), C (1.52→0.51) : clairement inférieur.
**Cause of failure**:
1. **Sprint FTMO** : variance par nuit (std 73 bps) × 2 nuits/sem × 42 jours ≠ atteinte de +10% sans breach DLL 5%. p(pass)<2mo virtuellement nul à leviers safe.
2. **Personal book** : SR 0.68 < gate 0.7 ; β 0.33 corr 0.57 vs NQ → ~1/3 beta long-equity déguisé, alpha brut +1.07 bps/nuit (faible) ; dilution Sharpe portefeuille A+B (currently 2.24, D-gate >2.46).
3. **Unlimited-time FTMO** : faisable à L=0.75× mais **median 3 ans grind** + tail-risk crash-from-highs (worst-night −6.26% sur 16 ans, un −10% sortie de distribution casse L=0.5×) + 2023-2024 régime négatif.
4. **L25 confirmed beta-proxy** : edge fondamentalement equity-risk-premium, non-alpha indépendant. Cohérent indépendamment avec `PropFirms/ftmo_alpha_program/` Family-5 verdict NO-GO net.
**Key lesson (banked as L36)**:
- **L36 — Overnight equity premium = beta-proxy, not alpha** : Cooper-Cliff-Gulen 2008 effect is REAL (G0+G1 confirme +4.9 bps t=4.04 sur NQ 2010-2026) mais corr +0.57 et β +0.33 avec NQ full-day buy-hold sur le sous-ensemble midweek → c'est essentiellement de l'exposition beta long-equity reconditionnée. SR_net 0.68 est cohérent avec un "harvester" de prime de risque, pas un alpha. Pour un book qui héberge déjà du risk-equity (Strategy C NQ ORB, même family), l'ajouter c'est dupliquer la même exposition au pire moment (gap-down systémique). N'admettre ce type de signal qu'avec un β-hedge explicite (short SPY/NQ overnight balanced) ou comme paire long-short midweek vs autres jours.
**Re-opening conditions** (low probability):
1. Vérification mainnet du swap réel sur compte FTMO (capture MT5 specifications) confirmant point_size=0.01 et swap_3x_day Friday — déjà vérifié via `ftmo_specs_full.csv`, donc OK.
2. β-hedge midweek (long NQ overnight + short équipondéré 1/3 NQ daily = neutralise β=0.33) → recalcule SR du résidu → si > 1.0, ré-examiner comme alpha sleeve indépendant.
3. Régime 2023-2024 réversé sur 18+ mois (overnight midweek redevient consistently positif) AVEC β/corr stable.

---

### NQ ORB (V2+E7) — FTMO/Propfirm Path (Strategy C family)

**Status**: CONFIRMED-CLOSED — DO NOT RE-OPEN absent hard new evidence  
**Date reconciled**: 2026-06-03; see `data/ftmo_research/ORB_reconciliation_2026-06.md`  
**Specs reconciled**: V2+E7 two-sided (doc4 `STRATEGY_DOSSIER_ORB.md`) + long-only filtré (doc3 `FTMO_Research_Report.pdf`) + decision report (`ORB_1step_improvement.md`) + MFFU audit (`ORB_feasibility_audit_2026-06.md`)  
**Economic mechanism hypothesis**: Intraday opening-range breakout on NQ captures momentum/continuation from auction-imbalance, exit-engineered (E7 trail-to-BE) to shape the return distribution favorably under FTMO symmetric barrier.  
**Signal**: V2 dust filter (OR ≥ 10 bps), entry on first 1-min break of OR_high/low after 09:30-10:00 ET, stop at opposite OR side (= 1R), E7 trail-to-BE after +1R, exit at RTH close. Cost 2 bps RT abstract.  
**Assets / universe**: NQ futures (Databento 1-min, 2010-2026, 3992-4012 trades depending on ledger)  
**Feasibility result (canonical ledger `nq_v2_trades.parquet`, pre-computed cost grid)**:
- Baseline @ 1 bps: mean_R = +0.027 | @ 2 bps: +0.004 | @ 3 bps: -0.018 | @ 4 bps: -0.040
- E7 lift = +0.015 R/trade vs baseline (doc4 canonical), so E7 @ 2 bps = +0.020 / E7 @ 3 bps = -0.003 / E7 @ 6 bps = -0.070
- Sign-flip @ ~2.7 bps RT cost
- DSR ≈ 0.70 (< 1.0 fail), doc4 §3.5 admits
- p(funded) FTMO 2-step full sample = 33% (1% risk), bust 60%
- Cherry-pick admis : "50.9% (2022-25), 93% (2026)" sub-windows  
**Backtest result**: Full 16-year contiguous 2-step FTMO p(funded) = 32-34% flat across sizings; 60-67% bust rate. doc3 long-only filtré = 30% full / 44% recent regime. ORB_1step_improvement projection 48-52% killed at Gate 0 (no licorne firme géométrique en 1-step futures direct 2026-06, cf. ORB_feasibility_audit Gate 0) + Gate 1 (mean_R -0.024 @ 3 bps MFFU NQ direct).  
**Cause of failure**: 
1. **Cost-bound**: drift bascule sous zéro entre 2 et 3 bps RT cost. Real propfirm cost (MFFU NQ direct = $4.68 RT comm = 0.94 bps + slippage 09:30 ~2 bps = 3 bps; FTMO US100 CFD = 6-10 bps) → E7 NÉGATIF en réel.
2. **Container-bound**: la "licorne" 1-step (static DD + cible≤DD + no daily + no consistency + futures direct) n'existe pas dans l'univers vérifié 2026-06 (Topstep/Apex/MFFU = trailing; Phidias/Traders Launch/Atlas = static mais ratio cible/DD défavorable 1.5-3×).
3. **DP-ceiling**: doc3 prouve que DP-optimal sizing est le ceiling, pas un heuristic. 33% full sample est mathematical bound, pas tunable par money management.
4. **Placebo finding**: ~80% du p(pass) sur container floor-taper + unlimited time vient de la math no-bust, pas du signal. Strategy C signal contribute ~0-15 pts marginal (doc4 §3.5 admis).
5. **Regime-bound**: full-sample edge ≈ 0 (doc3 fig p.6: "SR 0.11, t=0.4 — positive only in 2021-2024"). 2022+ regime cherry-pick.
6. **L10 violated 2.7×**: 8 mods empilées (V2+E7+filtre tendance+gap filter+DP+book+floor_taper+K5) vs max 3.  
**Key lesson (banked as L34/L35)**: 
- **L34**: Audit prop-firm honesty checklist = (a) 1 ledger canonique avec grille coûts pré-calculée, (b) cost model honnête au coût réel propfirm (futures direct ~3 bps, CFD ~6-10 bps), (c) spec gelée (E7 vs baseline explicit), (d) full-sample regime (pas de cherry-pick). Quand les 4 sont satisfaits, le "sign-flip" disparaît : différentes hypothèses, mêmes données.
- **L35**: DP-optimal sizing = mathematical ceiling, pas heuristic. Pour ORB single-attempt FTMO 2-step <2mo : ceiling = 33% full sample. Money management n'est PAS le lever — l'edge est, et il est cost-bound.
- **Container-math dominance**: ~80% du p(pass) sous floor-taper + unlimited time = math no-bust, pas signal. Pour les strategies à edge per-trade ~0 : l'engineering de barrière décide. Et la barrière favorable n'existe pas en propfirm 2026.  
**Re-opening conditions (theoretical, near-zero probability in next 12 months)**:
1. Firme 1-step futures direct + static DD + ratio cible≤DD + no daily + no consistency apparaît (n'existe pas 2026-06)
2. Cost all-in propfirm ≤ 2 bps RT confirmé sur 60+ trades demo
3. Edge démontré sur post-2026 out-of-sample (pas le 2022-2024 in-sample post-hoc)
4. DSR > 1.0 sur mod-count L10-compliant (currently 0.70 with 8 mods)

---

### Trend book J1+G1 (USDJPY carry-aligned TSMOM + Gold TSMOM)

**Status**: NOT-AN-ARTIFACT, DILUTIF-A-A+B, KEEP-AS-CV-ITEM
**Date reconciled**: 2026-06-03; see `data/trend_research/trend_verification_2026-06.md`
**Specs reconciled**: `data/ftmo_research/RAPPORT_replication_trend.md` (script `code/trend_replication.py`)
**Economic mechanism hypothesis**: classique TSMOM Moskowitz 12-1 sur USDJPY filtré carry-aligned (J1) + TSMOM 12-1 sur Gold (G1), vol-targeté 10%/yr, equal-risk book. Suggestion implicite du rapport : edge "carry-aligned trend" orthogonal au beta carry-trade JPY.
**Signal**: J1 = `sign(P_USDJPY[t-22]/P_USDJPY[t-252]-1) × {1 if sign(carry_US-JP)==sign(mom) else 0}`. G1 = `sign(P_GC[t-22]/P_GC[t-252]-1)`. Vol-target 10%, cap leverage 3×. Costs : 0.6 bp J1, 1.5 bp G1. Swap modélisé : J1 +carry/100/252, G1 -US_rate×0.9/100/252 sur long.
**Assets / universe**: USDJPY (JPY=X Yahoo, 2000-2026), Gold (GC=F Yahoo). Carry proxy : ^IRX - taux directeur JP (0/0.25/0.5 BoJ 2024+).
**Feasibility result (twin littéral du script)**: SR J1 +0.578 | SR G1 +0.664 | corr J-G +0.018 | SR book +0.698 (CI95 J1 [+0.18, +0.96] ; G1 [+0.25, +1.06]).
**Backtest result (vérification falsifiante 6 gates indépendants)**:
- G0 PASS (twin reproduit littéralement) + G0bis ALERTE : réplication INDÉP (log-ret, lag carry t-1) → J1 0.45 / G1 0.48 / book 0.47 → **edge fragile ±0.15 SR aux conventions d'impl**
- G1 KILL : filtre carry-aligned cosmétique à **99.9%** (carry<0 sur 8/6857 jours) ; J1 ≡ TSMOM long-only (SR identique à 0.003 près) ; OLS J1 ~ buy & hold USDJPY vol-tgt + swap → **β=0.51, α=+2.11%/yr (t=1.98 naïve), R²=0.51** ⇒ J1 = ~70% beta carry-trade + ~30% timing TSMOM
- G2 FLAG : swap modélisé apporte +0.175 SR à J1 (30% du SR) ; sensibilité ±50% donne book SR ∈ [0.49, 0.80] ; **swap jamais mesuré broker**
- G3 conditionnel : daily skew -0.36 stable (rolling <0 82% du temps), CVaR1 daily -3.37% sur vol 10%, worst day -6.26% (2005-12-14) ; **mais skew MENSUEL POSITIF +0.31** ; top-10 worst days **0/10 dans 2008/2020/2022** (mythe "carry-crash structurel" contredit) ; kill switch -3% daily ajoute +0.10 SR (partie des pertes mesurable intraday, ≠ tout gap-overnight)
- G4 PASS : délai+1 dégrade SR J1/G1/book de -0.12/-0.19/-0.22 → pas de leak résiduel
- G5 DILUTIF : corr book vs Strategy A proxy ≈ 0 (daily +0.004, monthly -0.027) ; **MAIS** SR_port(A+B+book) = 2.31 vs SR(A+B) = 2.36 → gain **-1 à -2%** ; gate D requis 2.59 → **NOT QUALIFIED comme strategy D**
**Cause of "failure to qualify"** :
1. **Filtre carry cosmétique** (G1) → le SR vient du timing TSMOM long-only, pas d'un carry-edge orthogonal. Le rapport overpitch.
2. **Edge fragile à l'implémentation** (G0bis) : simple vs log returns + lag carry t-1 vs t-2 → -0.15 SR ; un investor sceptique recalculerait différemment.
3. **SR 0.58-0.70 trop faible vs A (SR 1.33) et B (SR 2.0)** : même décorrélé, ajouter un sleeve à SR 0.7 dilue un portefeuille à SR 2.4 quand les vols cibles sont égales.
4. **Swap non mesuré** (G2) : 30% du SR de J1 vient d'une modélisation ^IRX/BoJ. Sur broker réel, swap typiquement shaved 25-50% → -0.05-0.10 SR sur J1.
5. **Skew daily -0.36** (G3) : *spécifique* barrière FTMO ; sur personal book mensuel +0.31 = sain. Mais empêche le sleeve d'être utile sur prop firm.
**Key lesson (banked as L37/L38/L39 candidates)**:
- **L37** — *Filter sanity check* : pour tout sleeve avec filtre conditionnel (carry-aligned, regime-conditional, etc.), compter la fraction du temps où `sign(filtre) != signal_natif`. Si < 5%, le filtre est cosmétique ; appeler le sleeve par son nom réel (ici : TSMOM long-only USDJPY, pas "carry-aligned trend").
- **L38** — *Beta-orthogonal test* : tout sleeve "structural premium" doit être régressé sur un buy & hold vol-targeté de l'asset primaire. Reporter (β, α HAC, R²). Si R² > 30%, **pas un edge orthogonal** — c'est du timing sur beta, le présenter comme tel.
- **L39** — *Daily vs monthly skew dissociation* : sur trend/carry, daily skew peut être négatif et monthly skew positif simultanément. Daily skew importe sur barrière daily FTMO 5%, monthly skew importe sur personal book + monthly DD rules. Toujours reporter les deux.
**Methodological wins (banked, real CV item)**:
- Réplication propre d'un classique (TSMOM Moskowitz 12-1, formulation littérature non tunée, 6 gates falsifiants indépendants)
- 2 bugs attrapés dans le rapport source : (a) look-ahead trailing-stop SR 2.05→0.32 ; (b) blowup numérique CTA (vol→0, MaxDD -2048%)
- Décomposition honnête : filter cosmétique démasqué, swap modélisé non mesuré quantifié à 30% du SR, dilution portefeuille calculée
- 0 jour live, pas de pivot opportuniste
**Re-opening / re-deployment conditions**:
1. Pour deployment personal book add-on : SR > 1.0 net après mesure swap démo 60+ jours (improbable, gap actuel 0.30 SR)
2. Pour deployment sleeve secours (A gelé + B retardé) : vol cible 5%, worst month attendu ~-3% ; OK à activer si A reste breached et B mainnet > 2026-09
3. Pour entrer comme strategy D propfirm : aucun chemin (NQ/ORB ne match pas FTMO ; book trend macro ne match pas non plus — symmetric barrier daily + skew daily -0.36 incompatibles)

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
