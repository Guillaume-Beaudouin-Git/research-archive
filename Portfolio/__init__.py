# Portfolio — multi-strategy risk and sizing framework
#
# Structure:
#   state/portfolio_state.py  — PortfolioState: positions, returns, allocation
#   risk/correlation.py       — rolling correlation, divergence alerts
#   risk/sizing.py            — ERC and inverse-vol weighting
#
# Strategies tracked:
#   A — TSMOM crypto (live, Propr testnet)
#   B — Delta-neutral carry (live, Propr testnet)
#   C — NQ opening momentum (paper trading, 0.25 contracts)
