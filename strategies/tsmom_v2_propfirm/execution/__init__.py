"""
TSMOM v2 execution layer — Propr API.

Confirmed from Step 0 API discovery (2026-05-11):
  Asset naming : bare symbols  ("BTC", "ETH", "SOL", ...)
  Order POST   : {"asset", "side", "quantity", "type"}
  Cancel       : DELETE /accounts/{id}/orders/{orderId}
  Equity       : GET /challenge-attempts/{id} → account.marginBalance / highWaterMark
"""

from __future__ import annotations

from pathlib import Path

# ── Asset map: yfinance ticker → Propr/Hyperliquid symbol ──────────────────
ASSET_MAP: dict[str, str] = {
    "BTC-USD":   "BTC",
    "ETH-USD":   "ETH",
    "SOL-USD":   "SOL",
    "AVAX-USD":  "AVAX",
    "LINK-USD":  "LINK",
    "DOGE-USD":  "DOGE",
    "ADA-USD":   "ADA",
    "DOT-USD":   "DOT",
    "UNI-USD":   "UNI",
    "LTC-USD":   "LTC",
    "BCH-USD":   "BCH",
    "MATIC-USD": "MATIC",   # NOTE: may need "POL" if Hyperliquid renamed it
    "OP-USD":    "OP",
    "ARB-USD":   "ARB",
}

REVERSE_ASSET_MAP: dict[str, str] = {v: k for k, v in ASSET_MAP.items()}

# ── API constants ───────────────────────────────────────────────────────────
BASE_URL = "https://api.propr.xyz/v1"

# ── DB paths (absolute, relative to project root) ──────────────────────────
_EXEC_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _EXEC_DIR.parent.parent.parent   # Algo_claude/

STATE_DB_PATH = str(_PROJECT_ROOT / "challenge_state.db")
ORDERS_DB_PATH = str(_PROJECT_ROOT / "orders_log.db")

# ── Guardrail limits ────────────────────────────────────────────────────────
# legacy Propr, non canonique (Propr 3%/6% minus 0.2/0.5 internal buffer).
# Canonical reference: Portfolio/risk/propfirm_canonical.py (FTMO 5/10).
# RUNTIME-ACTIVE: equity_monitor.py imports these at order-time. This is the
# guardrail that gates live trades on Strategy A's Propr account. The values in
# strategies/tsmom_v2_propfirm/config.py (4.5/9, HyroTrader) are NOT consumed
# in this path — only by sizing.py CHALLENGE_MODE budget calculation.
# Strategy A is FROZEN as of 2026-05-30 (Crypto/research/archived/_frozen/
# strategy_a_propr_2026-05-30/FREEZE.md); these values stay for the cron weekly
# Propr rebalance still installed on VPS, which is breached and inactive.
MAX_DAILY_DD: float = 0.028   # 2.8% — legacy Propr
MAX_TOTAL_DD: float = 0.055   # 5.5% — legacy Propr
