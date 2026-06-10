# Strategy B v2: Delta-Neutral Funding Arbitrage — Backtest Results

*Generated: 2026-05-06 00:58 UTC*

## Configuration

- Assets: TST, MEGA, WLD, STX, BIO, TRUMP, HMSTR
- Capital: $500.0
- Walk-forward: 6m train / 1m OOS
- Cost model: 0.42% round trip (BN+HL fees + slippage)
- Known omission: Binance spot borrow cost (using cash, not margin)

## Portfolio OOS Statistics

| Metric | Value |
|--------|-------|
| oos_bars | 270 |
| oos_months | 3.0 |
| total_carry_usd | 47.22 |
| total_price_usd | -1.17 |
| total_net_usd | 46.05 |
| sharpe | 10.218 |
| max_dd_pct | -0.52 |
| carry_frac | 1.026 |
| price_to_carry | 0.025 |
| win_rate | 0.644 |
| ann_return_pct | 37.35 |

## Per-Asset OOS Statistics

| asset   |   oos_months |   carry_pnl |   price_pnl |   net_pnl |   sharpe |   carry_frac |   price_to_carry |
|:--------|-------------:|------------:|------------:|----------:|---------:|-------------:|-----------------:|
| STX     |            3 |       23.05 |       -0.46 |     22.59 |    8.817 |        1.02  |            0.02  |
| WLD     |            3 |       20.84 |       -1.09 |     19.75 |    7.829 |        1.055 |            0.052 |
| TST     |            1 |        1.29 |        0.3  |      1.59 |    4.706 |        0.811 |            0.234 |
| HMSTR   |            2 |        2.04 |        0.07 |      2.11 |    1.282 |        0.968 |            0.033 |

## Basis Risk

| asset   |   mean_basis_usd |   std_basis_usd |   basis_std_pct | flagged   |
|:--------|-----------------:|----------------:|----------------:|:----------|
| TST     |           0      |          0.0002 |           0.558 | False     |
| BIO     |          -0.0001 |          0.0003 |           0.343 | False     |
| HMSTR   |          -0      |          0      |           0.214 | False     |
| STX     |           0.0004 |          0.0021 |           0.188 | False     |
| WLD     |           0.0004 |          0.0036 |           0.175 | False     |
| TRUMP   |          -0.0026 |          0.0144 |           0.165 | False     |

## Regime Analysis

| Regime | Sharpe |
|--------|--------|
| BTC up months | 13.03 |
| BTC down months | 7.327 |

## GO / NO-GO Verdict

```
GO
  GO: Sharpe 10.218 ≥ 1.0
  GO: MaxDD -0.5% ≤ 20%
  GO: carry_frac 1.026 ≥ 0.7
  GO: |price|/carry 0.025 < 0.5
  GO: BTC-up Sharpe 13.030 ≥ 0.5
```

## Notes

- TST carry is anomalously high (>5% 7d carry). Results with/without TST diverge significantly.
- MEGA has only ~6.5 months of history — barely qualifies for walk-forward.
- Basis risk: perp and spot prices may diverge during high-volatility periods.
- This is a testnet backtest. Live performance may differ due to:
  - Actual Binance spot fills (vs close price assumption)
  - Funding rate changes after position entry
  - Liquidation risk if basis widens significantly