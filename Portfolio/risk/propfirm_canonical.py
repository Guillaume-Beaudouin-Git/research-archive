"""
propfirm_canonical.py — single source of truth for guardrail percentages.

PROPFIRM_CANONIQUE = FTMO (decision 2026-05-30):
  daily DD = 5% of starting balance (from EOD peak), max DD = 10% of starting balance.

Why FTMO is the canonical reference, not Tradeify or Propr:
  - Tradeify uses dollar trailing DD ($1,000 on $25K = 4%); covered by
    Portfolio.risk.trailing_dd_simulator.PropfirmConfig
  - Propr uses 3% daily / 6% total (Strategy A, frozen 2026-05-30; see
    Crypto/research/archived/_frozen/strategy_a_propr_2026-05-30/FREEZE.md)
  - HyroTrader / Breakout use 5% / 10% — coincidentally the same as FTMO

All strategies that do NOT have firm-specific guardrails should default to this
canonical. Strategies WITH firm-specific guardrails keep their own runtime
constants but should COMMENT them as "# legacy <firm>, non canonique".

Runtime consumers and their current guardrail source (verified 2026-05-30):
  - Strategy A (tsmom_v2_propfirm, FROZEN): execution/__init__.py:46-47
    → Propr 2.8/5.5; equity_monitor.py consumes these at runtime
  - Strategy A research scripts (sizing.py): config.py:55-56
    → HyroTrader 4.5/9; sizing.py consumes these for CHALLENGE_MODE budget
  - Strategy C (strategy_c_live): guardrails.py + config.py
    → Tradeify dollar-based ($1,000 trailing); see TRADEIFY_TRAILING_DD constants
  - Strategy D, future strategies: should import from this module by default.

References:
  CLAUDE.md L7 (propfirm match), L22 (MC eval mandatory)
  _audit/verification_2026-05-30.md V10 (constant inventory)
"""
from __future__ import annotations
from typing import Final

# ── PROPFIRM_CANONIQUE = FTMO ─────────────────────────────────────────────────
# These are the default % limits applied to any new strategy unless overridden.

FTMO_DAILY_DD_PCT: Final[float] = 0.05    # 5% from EOD peak balance
FTMO_MAX_DD_PCT:   Final[float] = 0.10    # 10% from starting balance
FTMO_PROFIT_TARGET_PCT: Final[float] = 0.10   # Phase 1 target (FTMO Challenge)
FTMO_MIN_TRADING_DAYS: Final[int] = 4         # Phase 1 minimum

# Re-export as the canonical names (use these in new code):
DAILY_DD_PCT_CANONICAL: Final[float] = FTMO_DAILY_DD_PCT
MAX_DD_PCT_CANONICAL:   Final[float] = FTMO_MAX_DD_PCT

# ── Legacy firm values (kept for backward compatibility, NOT canonical) ───────
# Do not introduce new code that depends on these names. Strategy-specific
# guardrails should live in the strategy's own config and reference these
# legacy values as fallbacks only.

# Propr (Strategy A, frozen) — 3% daily / 6% total. Buffered to 2.8/5.5.
LEGACY_PROPR_DAILY_DD_PCT: Final[float] = 0.028
LEGACY_PROPR_MAX_DD_PCT:   Final[float] = 0.055

# HyroTrader / Breakout (Strategy A challenge mode) — 5% daily / 10% total
# minus internal buffer → 4.5/9.
LEGACY_HYROTRADER_DAILY_DD_PCT: Final[float] = 0.045
LEGACY_HYROTRADER_MAX_DD_PCT:   Final[float] = 0.09
