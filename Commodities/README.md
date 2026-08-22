# Commodities — cross-sectional basis/TSMOM, carry closed

## Structure

| Directory | Contents |
|---|---|
| `research/active/xs_basis_tsmom/` | Cross-sectional basis + time-series momentum, the one open line in this asset class. Per root `CLAUDE.md`, phase A is incomplete and n ≤ 279 — treat any headline number here as provisional until phase A closes |
| `research/archived/commodity_tsmom/` | Time-series momentum on commodities, closed (`feasibility.py`, `commodity_tsmom_summary.md`) |
| `research/passed/` | Empty (`__init__.py` only) |

## Commodity carry is closed (L32b)

Commodity carry on CFD is a closed family: the collectable side of the carry trade is a credit, not
an edge — long-only oil gated on backwardation nets to approximately zero over 19 years
(+0.96%/yr of swap collected, cancelled by -1.03%/yr of price beta), and the short-contango leg pays
-46+ bps/month of swap. Both sides of commodity CFD carry are closed; do not re-propose a carry
variant without a genuinely new angle (see the reopening policy in root `README.md`). Term-structure
data itself (EIA) remains free and reusable for other hypotheses.
