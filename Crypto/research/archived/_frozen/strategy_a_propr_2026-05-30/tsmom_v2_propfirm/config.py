"""
Configuration for TSMOM v2 — Prop-Firm Adapted Variant.

All strategy parameters live here. To switch between live and challenge
modes, set CHALLENGE_MODE = True before importing any other module.

Prop-firm target: Breakout (HyroTrader) rules assumed unless noted.
  - Max daily drawdown  : 5%   → we use 4.5% (safety buffer)
  - Max total drawdown  : 10%  → we use 9%   (safety buffer)
  - Profit target       : 10%  → relevant to CHALLENGE_MODE sizing
"""

from __future__ import annotations

from typing import Final

# ── Universe ───────────────────────────────────────────────────────────────────
# 14 assets: BTC/ETH/SOL core + top Hyperliquid perps ranked by open interest.
# ARB (Mar 2023) and OP (May 2022) have limited history — handled gracefully.
UNIVERSE: Final[list[str]] = [
    "BTC-USD",   # Bitcoin
    "ETH-USD",   # Ethereum
    "SOL-USD",   # Solana
    "AVAX-USD",  # Avalanche
    "LINK-USD",  # Chainlink
    "DOGE-USD",  # Dogecoin
    "ADA-USD",   # Cardano
    "DOT-USD",   # Polkadot
    "UNI-USD",   # Uniswap
    "LTC-USD",   # Litecoin
    "BCH-USD",   # Bitcoin Cash
    "MATIC-USD", # Polygon (POL)
    "OP-USD",    # Optimism  (listed 2022-05)
    "ARB-USD",   # Arbitrum  (listed 2023-03)
]

# ── Signal ─────────────────────────────────────────────────────────────────────
LOOKBACK_DAYS: Final[int] = 28        # 28-day return for momentum signal (unchanged from v1)
VOL_LOOKBACK_DAYS: Final[int] = 20    # rolling window for realized vol estimation
REBALANCE_WEEKDAY: Final[int] = 0     # 0 = Monday (pandas .dayofweek convention)

# ── Vol targeting ──────────────────────────────────────────────────────────────
# Toggle CHALLENGE_MODE to switch between modes; call get_vol_target() at runtime.
CHALLENGE_MODE: bool = False

VOL_TARGET_LIVE: Final[float] = 0.18       # 18% ann vol — optimized for Propr pass rate (challenge_optimizer.py, 2026-05)
VOL_TARGET_CHALLENGE: Final[float] = 0.35  # 35% ann vol — accelerated challenge mode

VOL_SCALAR_MIN: Final[float] = 0.1   # floor: 10% of nominal position
VOL_SCALAR_MAX: Final[float] = 2.0   # ceiling: 200% of nominal position

# ── Prop-firm guardrails ───────────────────────────────────────────────────────
# These are hard limits enforced before every order in live trading.
# Position size = min(vol_target_size, guardrail_allowed_size).
MAX_DAILY_DRAWDOWN: Final[float] = 0.045  # 4.5% intraday DD triggers full flatten
MAX_TOTAL_DRAWDOWN: Final[float] = 0.09   # 9% total DD from peak triggers full flatten
DAILY_PROFIT_CAP_PCT: Final[float] = 0.0  # no cap — log daily P&L only

# ── Stop-loss ──────────────────────────────────────────────────────────────────
# Placed on exchange immediately at order fill (required by HyroTrader).
# stop_price (long) = entry_price * (1 − STOP_LOSS_VOL_MULT × daily_vol)
STOP_LOSS_VOL_MULT: Final[float] = 2.0

# ── Execution costs (Hyperliquid defaults) ─────────────────────────────────────
FEE_RATE: Final[float] = 0.00035   # 0.035% taker fee (one-way)
SLIPPAGE: Final[float] = 0.0005    # 0.050% slippage estimate (one-way)
# Round-trip cost = 2 × (FEE_RATE + SLIPPAGE) = 0.17%

# ── Calendar ───────────────────────────────────────────────────────────────────
TRADING_DAYS_PER_YEAR: Final[int] = 365   # crypto is 24/7

# ── Challenge tracking (SQLite) ────────────────────────────────────────────────
DB_PATH: Final[str] = "challenge_state.db"

# ── Known minimum listing dates (hard filter to avoid pre-launch garbage data) ─
# yfinance occasionally returns erroneous historical data for newer tokens
# (e.g. ARB-USD returning 2019 data when Arbitrum launched March 2023).
# Data before these dates is discarded during the download step.
MIN_LISTING_DATES: Final[dict[str, str]] = {
    "SOL-USD":   "2020-04-10",
    "AVAX-USD":  "2020-07-13",
    "DOT-USD":   "2020-08-19",
    "UNI-USD":   "2020-09-17",
    "MATIC-USD": "2019-04-01",
    "OP-USD":    "2022-05-31",   # Optimism token listed May 2022
    "ARB-USD":   "2023-03-23",   # Arbitrum airdrop / listing
}

# ── Backtest parameters ────────────────────────────────────────────────────────
BACKTEST_START: Final[str] = "2019-01-01"
BACKTEST_END: Final[str] = "2024-12-31"
WALK_FORWARD_MIN_TRAIN_DAYS: Final[int] = 365  # 1-year warm-up before first OOS fold
WALK_FORWARD_FOLD_MONTHS: Final[int] = 6       # 6-month OOS evaluation windows


def get_vol_target() -> float:
    """Return the active annualized vol target based on CHALLENGE_MODE."""
    return VOL_TARGET_CHALLENGE if CHALLENGE_MODE else VOL_TARGET_LIVE
