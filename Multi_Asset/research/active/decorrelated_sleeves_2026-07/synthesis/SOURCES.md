# SOURCES — literature & references (iteration 2)

## Stat-arb / factor residual (Piste A)
- Avellaneda, M. & Lee, J.-H. (2010). *Statistical Arbitrage in the US Equities Market.* Quantitative
  Finance 10(7). PCA / ETF factor-residual s-score; net Sharpe 1.44 (PCA) / 1.51 (ETF) 1997–2007.
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1153505 ·
  https://traders.studentorg.berkeley.edu/papers/Statistical%20arbitrage%20in%20the%20US%20equities%20market.pdf
- Hudson & Thames, *arbitragelab* — PCA approach / s-score docs.
  https://hudson-and-thames-arbitragelab.readthedocs-hosted.com/en/latest/other_approaches/pca_approach.html
- Gold/silver pair (Kalman + ML regime filter, 2015–2025) — DD reduction vs static z-score.
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5710242 ·
  https://www.quantifiedstrategies.com/gold-silver-chart-ratio-strategy/

## Mean reversion / trend gate (Piste C)
- Connors, L. & Alvarez, C. (2008). *Short-Term Trading Strategies That Work.* RSI(2)<10 above the
  200-day SMA, exit >5-day SMA, long-only.
  https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/rsi-2 ·
  https://www.quantifiedstrategies.com/rsi-2-strategy/
- Quantitativo — cumulative-RSI mean reversion (Sharpe 1.18 vs 1.05; DD still 37%).
  https://www.quantitativo.com/p/squeezing-more-profits-with-cumulative ·
  https://www.quantitativo.com/p/trading-the-mean-reversion-curve
- Lou, D., Polk, C. & Skouras, S. (2019). *A Tug of War: Overnight versus Intraday Expected Returns.*
  JFE. Nearly all equity-index gains are overnight; intraday flat/negative (explains the short-leg failure).
  https://personal.lse.ac.uk/polk/research/TugOfWar.pdf

## Range / volatility regime (Piste B)
- Bollinger squeeze + low-ADX range identification (band contraction = low vol = range).
  https://www.luxalgo.com/blog/band-indicators-volatility-in-trading-explained/
- Robot Wealth — mean reversion & cointegration (return-corr not price-corr; OOS discipline).
  https://robotwealth.com/exploring-mean-reversion-and-cointegration-part-2/

## FTMO rules (challenge design)
- FTMO Trading Objectives — +10% / +5% targets, 5% daily / 10% max loss (equity-based, incl. floating P/L & swaps).
  https://ftmo.com/en/trading-objectives/
- FTMO — no time limit since 2024 (take as long as you want).
  https://ftmo.com/en/blog/trade-without-any-time-limit-and-take-as-long-as-you-want-to-pass/
- FTMO Forbidden Trading Practices — opposing positions on correlated instruments permitted *within a single
  account*; cross-account hedging banned. https://ftmo.com/en/forbidden-trading-practices/
