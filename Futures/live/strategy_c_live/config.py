"""
config.py — Strategy C Live Configuration
==========================================
iter_10: VWAP + A$400 dollar stop + B1.2% gap filter + M1(rng≥30pt)

Broker: Tradeify Select Flex $50K via Tradovate REST API.
  - Real CME MNQ, headless Linux/VPS compatible
  - EOD trailing DD $2,000 (locks to $50,100 floor after first payout)
  - No daily loss limit, no consistency rule (funded)
  - Python automation allowed (FTA §6.6), 90/10 profit split

Staged sizing (Sharpe-regime conservative, from propfirm_compat_v2 Tradeify section):
  Phase 1 — Eval  (3 MNQ): up to +$3,000 eval target
  Phase 2 — Pré-lock (4 MNQ): funded, until lock trigger (EOD ≥ $52,100 + first payout)
  Phase 3 — Post-lock (5 MNQ): floor locked at $50,100, ad infinitum

Lock trigger: EOD balance ≥ $52,100 AND first payout requested → floor locked at $50,100.

VPS execution (headless, no MT5 terminal needed):
  Cron VPS (heure été UTC+2: 09:25 ET = 13:25 UTC):
    25 13 * * 1-5  cd /home/algo/projects/Algo_claude && \\
      /home/algo/venv/bin/python -m Futures.live.strategy_c_live.run_daily \\
      >> ~/logs/strategy_c.log 2>&1
  (Hiver UTC+1: 09:25 ET = 14:25 UTC → 25 14 * * 1-5)

Legacy brokers (MT5/IBKR) kept in comments for reference.
"""
import logging
import os
from datetime import time as _time
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# ── Broker selector ───────────────────────────────────────────────────────────
BROKER = 'tradovate'   # 'tradovate' | 'mt5' (legacy) | 'ibkr' (legacy)

# ── Tradovate / Tradeify credentials — NEVER hardcode here ───────────────────
TRADOVATE_ENV         = os.getenv('TRADOVATE_ENV', 'demo')   # 'demo' | 'live'
TRADOVATE_USERNAME    = os.getenv('TRADOVATE_USERNAME', '')
TRADOVATE_PASSWORD    = os.getenv('TRADOVATE_PASSWORD', '')
TRADOVATE_CID         = os.getenv('TRADOVATE_CID', '0')
TRADOVATE_SECRET      = os.getenv('TRADOVATE_SECRET', '')
TRADOVATE_APP_ID      = os.getenv('TRADOVATE_APP_ID', 'StratC')
TRADOVATE_APP_VERSION = os.getenv('TRADOVATE_APP_VERSION', '1.0')
TRADOVATE_DEVICE_ID   = os.getenv('TRADOVATE_DEVICE_ID', '')

# ── Contract ──────────────────────────────────────────────────────────────────
SYMBOL        = 'MNQ'   # Micro E-mini Nasdaq — front month resolved at runtime
CONTRACT_SIZE = 2.0     # $2 per point per MNQ contract

# ── Staged sizing ─────────────────────────────────────────────────────────────
PHASE_CONTRACTS = {
    'eval':      3,
    'pre_lock':  4,
    'post_lock': 5,
}
N_CONTRACTS_DEFAULT = 3   # Phase 1 eval — updated by challenge_state.get_n_contracts()

# Legacy alias used by monitor_loop._build_exit
N_CONTRACTS = N_CONTRACTS_DEFAULT

# ── Signal parameters ─────────────────────────────────────────────────────────
ORB_OPEN       = _time(9, 30)
ORB_CLOSE      = _time(9, 45)
ENTRY_TIME     = _time(9, 46)
TIME_STOP      = _time(12, 30)
TZ_ET          = ZoneInfo('America/New_York')

TP_RATIO       = 1.5
SL_RATIO       = 0.5
SL_CAP_USD     = 400    # $400/NQ-contract cap (backtest reference)
SL_CAP_PTS     = 20.0

GAP_FILTER     = 0.012
RANGE_MIN_PTS  = 30

# ── MNQ contract specs ────────────────────────────────────────────────────────
MNQ_POINT_VALUE = 2.0
MNQ_TICK_SIZE   = 0.25
MNQ_COST_RT     = 2.15   # $2.15 round-trip per MNQ (Tradovate NinjaTrader fees)

# ── Broker-agnostic P&L params ────────────────────────────────────────────────
POINT_VALUE         = MNQ_POINT_VALUE   # $2/pt/contract
TRADE_COST_PER_UNIT = MNQ_COST_RT       # per contract round-trip

# ── Guardrails — Tradeify Select Flex $50K ────────────────────────────────────
# Tradeify limits:
#   EOD trailing DD from peak: $2,000  (pre-lock)
#   Post-lock floor:           $50,100 (permanent, after first payout + EOD ≥ $52,100)
#   Daily loss limit:          None    (Tradeify has no DLL)
#
# Our guardrails fire BEFORE Tradeify limits:
TRADEIFY_INITIAL_BALANCE  = 50_000
TRADEIFY_TRAILING_DD_USD  = 2_000     # Tradeify hard limit (pre-lock)
TRADEIFY_LOCK_BALANCE     = 52_100    # EOD balance that triggers lock
TRADEIFY_LOCKED_FLOOR     = 50_100    # permanent floor post-lock
TRADEIFY_PROFIT_TARGET    = 3_000     # eval target (6% of $50K)

GUARDRAIL_TRAILING_DD_USD  = 1_750    # halt at $1,750 from peak (buffer $250 before $2,000)
GUARDRAIL_POST_LOCK_FLOOR  = 50_175   # halt $75 above Tradeify locked floor
GUARDRAIL_DAILY_BUFFER_PCT = None     # no Tradeify DLL — disabled
GUARDRAIL_DAILY_SELF_LIMIT = 800      # self-imposed: 2 SL hits ($400 each at 5 MNQ)

# Legacy aliases (used by validate_mt5.py offline tests — keep for compatibility)
GUARDRAIL_DD_PCT          = 0.08      # FTMO legacy (unused for Tradeify)
GUARDRAIL_TRAILING_DD_PCT = None      # FTMO legacy (unused for Tradeify)
GUARDRAIL_FIXED_DD_PCT    = GUARDRAIL_DD_PCT
GUARDRAIL_DAILY_PCT       = GUARDRAIL_DAILY_BUFFER_PCT

# ── Monitor loop ──────────────────────────────────────────────────────────────
MONITOR_INTERVAL_SECS = 30
RECONNECT_RETRIES     = 3
RECONNECT_WAIT_SECS   = 15

# ── Paths ─────────────────────────────────────────────────────────────────────
CHALLENGE_STATE_PATH = Path(__file__).parent / "challenge_state.json"
HALT_SENTINEL_PATH   = Path(__file__).parent / "HALTED"

# ── VPS watchdog ──────────────────────────────────────────────────────────────
VPS_WATCHDOG_URL   = "http://<VPS_IP>:8765/heartbeat"
HEARTBEAT_INTERVAL = 30

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL = logging.INFO

# ── Legacy broker params (reference only) ────────────────────────────────────
# MT5 / FTMO legacy (BROKER=mt5):
#   SYMBOL='US100', LOT_SIZE=1.0, CONTRACT_SIZE=10.0, MT5_SERVER/LOGIN/PASSWORD from .env
# IBKR legacy (BROKER=ibkr):
#   IBKR_HOST='127.0.0.1', IBKR_PORT=7497, IBKR_CLIENT=1
#   CONTRACT='MNQ', EXCHANGE='CME', CURRENCY='USD'
#   N_CONTRACTS=20 (paper only)
#   MNQ_COST_RT=2.15

# Legacy names needed by ibkr_client and mt5_client if imported directly
LOT_SIZE    = 1.0       # MT5 legacy
IBKR_HOST   = '127.0.0.1'
IBKR_PORT   = 7497
IBKR_CLIENT = 1
