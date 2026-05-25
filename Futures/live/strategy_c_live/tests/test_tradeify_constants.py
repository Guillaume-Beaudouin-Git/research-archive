"""
Verify Tradeify-specific constants in config.py match PropFirms/tradeify/rules.md.

If this test fails, EITHER:
  - rules.md was updated → update config.py to match, update last_sync comment
  - config.py was changed accidentally → revert to match rules.md
  - Tradeify changed rules → update both + new last_verified date in rules.md

Source of truth: PropFirms/tradeify/rules.md (last_verified: 2026-05-25)
"""
from Futures.live.strategy_c_live import config


# ── Eval phase ────────────────────────────────────────────────────────────────

def test_starting_balance():
    assert config.TRADEIFY_INITIAL_BALANCE == 25_000


def test_eval_trailing_dd():
    assert config.TRADEIFY_TRAILING_DD_USD == 1_000


def test_profit_target():
    assert config.TRADEIFY_PROFIT_TARGET == 1_500


def test_consistency_ratio():
    assert config.CONSISTENCY_RATIO_EVAL == 0.40


def test_min_trading_days():
    assert config.MIN_TRADING_DAYS_EVAL == 3


# ── Funded phase — lock mechanics ─────────────────────────────────────────────

def test_funded_trailing_dd():
    assert config.TRADEIFY_TRAILING_DD_FUNDED == 1_500


def test_lock_trigger_excess():
    assert config.LOCK_TRIGGER_EXCESS == 100


def test_lock_balance_derivation():
    """$25,000 + $1,500 funded_DD + $100 = $26,600."""
    expected = (
        config.TRADEIFY_INITIAL_BALANCE
        + config.TRADEIFY_TRAILING_DD_FUNDED
        + config.LOCK_TRIGGER_EXCESS
    )
    assert config.TRADEIFY_LOCK_BALANCE == expected == 26_600


def test_locked_floor_offset():
    assert config.LOCKED_FLOOR_OFFSET == 100


def test_locked_floor_derivation():
    """$25,000 + $100 = $25,100."""
    expected = config.TRADEIFY_INITIAL_BALANCE + config.LOCKED_FLOOR_OFFSET
    assert config.TRADEIFY_LOCKED_FLOOR == expected == 25_100


# ── Payout rules ──────────────────────────────────────────────────────────────

def test_payout_threshold_days():
    assert config.PAYOUT_THRESHOLD_DAYS == 5


def test_win_day_min_pnl():
    assert config.WIN_DAY_MIN_PNL == 100.0


def test_max_payout():
    assert config.MAX_PAYOUT == 1_250.0


def test_payout_pct_of_profit():
    assert config.PAYOUT_PCT_OF_PROFIT == 0.50


# ── Internal guardrails ───────────────────────────────────────────────────────

def test_guardrail_under_eval_dd():
    """Internal guardrail must fire before the $1,000 hard limit."""
    assert config.GUARDRAIL_TRAILING_DD_USD < config.TRADEIFY_TRAILING_DD_USD


def test_guardrail_post_lock_above_floor():
    """Internal post-lock guardrail must be strictly above Tradeify's locked floor."""
    assert config.GUARDRAIL_POST_LOCK_FLOOR > config.TRADEIFY_LOCKED_FLOOR


# ── Cross-check simulator defaults match config ───────────────────────────────

def test_simulator_defaults_match_config():
    """PropfirmConfig defaults in trailing_dd_simulator must agree with config.py."""
    from Portfolio.risk.trailing_dd_simulator import PropfirmConfig
    cfg = PropfirmConfig()
    assert cfg.capital            == config.TRADEIFY_INITIAL_BALANCE
    assert cfg.profit_target      == config.TRADEIFY_PROFIT_TARGET
    assert cfg.trailing_dd_eval   == config.TRADEIFY_TRAILING_DD_USD
    assert cfg.trailing_dd_funded == config.TRADEIFY_TRAILING_DD_FUNDED
    assert cfg.lock_trigger_excess == config.LOCK_TRIGGER_EXCESS
    assert cfg.locked_floor_offset == config.LOCKED_FLOOR_OFFSET
    assert cfg.consistency_cap_pct == config.CONSISTENCY_RATIO_EVAL
    assert cfg.payout_threshold_days == config.PAYOUT_THRESHOLD_DAYS
    assert cfg.win_day_min_pnl    == config.WIN_DAY_MIN_PNL
    assert cfg.max_payout         == config.MAX_PAYOUT
    assert cfg.payout_pct_of_profit == config.PAYOUT_PCT_OF_PROFIT
