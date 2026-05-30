"""
TSMOM v2 — Prop-Firm Adapted Time-Series Momentum.

Changes from v1:
  • Universe expanded to 14 assets (BTC/ETH/SOL + 11 Hyperliquid perps)
  • Weekly rebalancing (Monday UTC 00:00) instead of monthly
  • Long-only (no shorting — v1 validated short crypto TSMOM doesn't work)
  • CHALLENGE_MODE flag to switch vol target (15% live / 35% challenge)
  • Prop-firm guardrails: 4.5% daily DD, 9% total DD, auto-flatten kill switch
  • Mandatory stop-loss placed at exchange: entry × (1 − 2 × daily_vol)
  • SQLite tracking: trading_days_counter, challenge_pnl_tracker
"""

from strategies.tsmom_v2_propfirm.config import (
    UNIVERSE,
    CHALLENGE_MODE,
    get_vol_target,
    MAX_DAILY_DRAWDOWN,
    MAX_TOTAL_DRAWDOWN,
)
from strategies.tsmom_v2_propfirm.signal import compute_signal
from strategies.tsmom_v2_propfirm.sizing import (
    compute_vol_scalars,
    compute_positions,
    apply_guardrails,
    compute_stop_price,
)

__all__ = [
    "UNIVERSE",
    "CHALLENGE_MODE",
    "get_vol_target",
    "MAX_DAILY_DRAWDOWN",
    "MAX_TOTAL_DRAWDOWN",
    "compute_signal",
    "compute_vol_scalars",
    "compute_positions",
    "apply_guardrails",
    "compute_stop_price",
]
