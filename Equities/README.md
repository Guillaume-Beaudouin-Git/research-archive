# Equities — cross-sectional and pairs research, no live deployment

`live/` holds only a `.gitkeep` — there is no live equities strategy. Everything here is research.

## Structure

| Directory | Contents |
|---|---|
| `research/active/` | `sector_hothand_propfirm` — flagged in root `CLAUDE.md` as needing an audit before any further use: t_HAC 10.38 (red flag for an overfit or mismeasured statistic) and measured MaxDD -13.3%, which already breaches the FTMO 10% limit. Treat results in this folder as **unaudited** until that review happens |
| `research/passed/` | Empty (`.gitkeep` only) |
| `research/archived/` | `indices_swing`, `jt_momentum_cs`, `multi_asset_tsmom`, `pairs_cointegration`, `pairs_distance_gatev`, `sector_reversal_cs` |

## Why no live deployment

FTMO (the propfirm venue in force) is a CFD account; the persistent constraint on this asset class
is the same one documented for FX and commodities — retail CFD cost tiers (0.05-0.10% RT per
`CLAUDE.md` §Costs) are high enough to kill most of what has been tested here. Nothing in
`research/archived/` has cleared PROPFIRM_PASS.
