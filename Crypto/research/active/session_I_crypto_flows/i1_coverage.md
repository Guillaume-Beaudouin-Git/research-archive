# I-1 stage (a) — event DB coverage report

- DefiLlama protocols listed: **331**, emissions JSONs fetched: **331**
- Cliff events (same-day merged, ex-noncirculating): **22424**; ≤ 2026-05-25: **19012**
- ≥ 1.0% of circ proxy: **2901**; with a Binance UM perp ever listed: **1782**
- Passing ex-ante floor (age≥60d, 30d med vol ≥ $20M at T-10): **578** events, **73** symbols, 2020-09-16 → 2026-05-24
- Insider/privateSale-flagged events: **453** vs other: 125

## Circulating-proxy validation vs CoinGecko (mcap/price)

| token | date | ours | coingecko | rel_err |
|---|---|---|---|---|
| arbitrum | 2025-09-10 | 4.412e+09 | 5.300e+09 | -16.8% |
| arbitrum | 2025-12-10 | 4.737e+09 | 5.627e+09 | -15.8% |
| arbitrum | 2026-03-11 | 5.062e+09 | 5.939e+09 | -14.8% |
| aptos | 2025-09-10 | 3.953e+08 | 6.895e+08 | -42.7% |
| aptos | 2025-12-10 | 4.262e+08 | 7.378e+08 | -42.2% |
| aptos | 2026-03-11 | 4.572e+08 | 7.813e+08 | -41.5% |
| celestia | 2025-09-10 | 8.992e+08 | 7.749e+08 | +16.0% |
| celestia | 2025-12-10 | 9.773e+08 | 8.523e+08 | +14.7% |
| celestia | 2026-03-11 | 1.016e+09 | 8.901e+08 | +14.1% |

Coverage bias (from phase0_audit): DefiLlama list skews to post-2022 survivors; early-cycle dead tokens absent at the SOURCE; Binance-perp requirement is the binding selection and Vision retains delisted symbols, so exchange-side survivorship is handled; calendar-side survivorship remains and is reported, not hidden.
