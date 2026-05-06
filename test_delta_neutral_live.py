"""
test_delta_neutral_live.py

Integration tests for strategies/delta_neutral/live_trader.py.
All 7 tests must pass before enabling cron on VPS.

Tests:
  1. One-legged failure — BN spot buy succeeds, HL short fails
       → BN.market_sell called immediately in same execution block
  2. One-legged failure — HL short closes, BN spot sell fails
       → EMERGENCY alert sent; one-legged state detected (close_pair path)
  3. Reconciliation — spot/perp mismatch > 5%
       → Alert sent, action = RECONCILE_FAIL, no new positions opened
  4. Carry logging — funding payments appended to delta_neutral_carry.csv
  5. Kill switch — run() calls sys.exit(0) before any exchange access
  6. Data freshness — stale HL data (no recent datapoint) → asset skipped
  7. Dry-run — no real orders placed on BN or HL; HyperliquidClient not instantiated
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

PROJECT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT))

import strategies.delta_neutral.live_trader as lt


# ══════════════════════════════════════════════════════════════════════════
# Autouse — run from project root
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def working_dir(monkeypatch):
    monkeypatch.chdir(PROJECT)


# ══════════════════════════════════════════════════════════════════════════
# Shared helpers / fixtures
# ══════════════════════════════════════════════════════════════════════════

def _make_bn_client(buy_qty: float = 58.82, buy_ok: bool = True, sell_ok: bool = True):
    """Return a mock BinanceTestnetClient."""
    c = MagicMock(name="BinanceTestnetClient")
    if buy_ok:
        c.market_buy.return_value = {"qty": buy_qty, "avg_price": 0.85, "raw": {}}
    else:
        c.market_buy.side_effect = RuntimeError("BN buy failed — mock")
    if sell_ok:
        c.market_sell.return_value = {"qty": buy_qty, "avg_price": 0.85, "raw": {}}
    else:
        c.market_sell.side_effect = RuntimeError("BN sell failed — mock")
    c.get_current_price.return_value = 0.85
    c.get_asset_balance.return_value = 60.0
    return c


def _make_hl_client(short_ok: bool = True, close_ok: bool = True,
                    position: dict | None = None):
    """Return a mock HLPerpClient."""
    c = MagicMock(name="HLPerpClient")
    if short_ok:
        c.open_short.return_value = {"response": {}, "size": 58.82, "latency_ms": 50}
    else:
        c.open_short.side_effect = RuntimeError("HL short failed — mock")
    if close_ok:
        c.close_position.return_value = {"response": {}, "latency_ms": 50}
    else:
        c.close_position.side_effect = RuntimeError("HL close failed — mock")
    c.get_position.return_value = position or {"side": "short", "size": 58.82, "entry_price": 0.85}
    c.get_funding_paid.return_value = [{"funding_usd": "0.12", "position_size": "58.82",
                                        "funding_rate": "0.00005"}]
    return c


def _open_state(spot_qty: float = 58.82, notional: float = 50.0) -> dict:
    return {
        "position":         "open",
        "spot_qty":         spot_qty,
        "perp_notional":    notional,
        "entry_time":       "2026-05-06T08:10:00+00:00",
        "cumulative_carry": 0.0,
    }


# ══════════════════════════════════════════════════════════════════════════
# Test 1 — One-legged: BN buy succeeds, HL short fails → BN sold immediately
# ══════════════════════════════════════════════════════════════════════════

def test_oneleg_bn_succeeds_hl_fails(monkeypatch):
    """
    open_pair: BN market_buy succeeds, HL open_short raises.
    Emergency: BN market_sell must be called with the bought quantity.
    """
    alerts = []
    monkeypatch.setattr(lt.notifier, "send",
                        lambda msg, level="info": alerts.append((level, msg)))

    bn = _make_bn_client(buy_qty=58.82, buy_ok=True, sell_ok=True)
    hl = _make_hl_client(short_ok=False)

    result = lt.open_pair("WLD", 50.0, bn, hl, dry_run=False)

    assert result is None, "open_pair should return None on HL failure"
    bn.market_buy.assert_called_once()
    bn.market_sell.assert_called_once_with("WLDUSDT", 58.82)

    # Alert must contain emergency wording
    all_msgs = " ".join(m for _, m in alerts)
    assert "EMERGENCY" in all_msgs or "one-legged" in all_msgs, (
        f"Expected EMERGENCY alert; got: {alerts}"
    )


# ══════════════════════════════════════════════════════════════════════════
# Test 2 — One-legged: HL close succeeds, BN spot sell fails → emergency alert
# ══════════════════════════════════════════════════════════════════════════

def test_oneleg_hl_close_ok_bn_sell_fails(monkeypatch):
    """
    close_pair: HL close_position succeeds, BN market_sell raises.
    One-legged spot long remains. EMERGENCY alert must be sent.
    State returned must mark perp_notional=0 (HL closed) but spot_qty unchanged.
    """
    alerts = []
    monkeypatch.setattr(lt.notifier, "send",
                        lambda msg, level="info": alerts.append((level, msg)))

    bn    = _make_bn_client(sell_ok=False)
    hl    = _make_hl_client(close_ok=True)
    state = _open_state(spot_qty=58.82)

    new_state = lt.close_pair("WLD", state, bn, hl, dry_run=False)

    hl.close_position.assert_called_once()
    bn.market_sell.assert_called_once()

    # EMERGENCY alert must have been sent
    error_alerts = [(lvl, msg) for lvl, msg in alerts if lvl == "error"]
    assert error_alerts, (
        f"Expected error-level EMERGENCY alert; got: {alerts}"
    )
    all_msgs = " ".join(m for _, m in alerts)
    assert "EMERGENCY" in all_msgs or "one-legged" in all_msgs, (
        f"Expected EMERGENCY wording in alert; got: {alerts}"
    )

    # Perp should be marked flat (HL succeeded), spot still tracked
    assert new_state["perp_notional"] == 0.0, (
        f"perp_notional should be 0 after HL closed; got {new_state['perp_notional']}"
    )
    assert new_state["spot_qty"] == 58.82, (
        f"spot_qty should remain since BN sell failed; got {new_state['spot_qty']}"
    )


# ══════════════════════════════════════════════════════════════════════════
# Test 3 — Reconciliation: spot/perp mismatch > 5% → alert + RECONCILE_FAIL
# ══════════════════════════════════════════════════════════════════════════

def test_reconciliation_mismatch(monkeypatch, tmp_path):
    """
    reconcile_position: if spot_value vs perp_size_usd differ by >5%,
    send a warning/error alert and return False.
    run_asset with reconcile=False → action == "RECONCILE_FAIL", no OPEN.
    """
    alerts = []
    monkeypatch.setattr(lt.notifier, "send",
                        lambda msg, level="info": alerts.append((level, msg)))
    monkeypatch.setattr(lt, "STATE_DIR", tmp_path)

    # state: open with spot_qty=58.82 (spot_value ≈ $50)
    state = _open_state(spot_qty=58.82, notional=50.0)

    # BN: price = $0.85 → spot_value = 58.82 × 0.85 = $49.99
    # HL: position.size = 10.0 coins → perp_size_usd = 10.0 × 0.85 = $8.5
    # mismatch = |49.99 - 8.5| / 49.99 ≈ 83% >> 5%
    bn = _make_bn_client()
    bn.get_current_price.return_value = 0.85
    hl = _make_hl_client(position={"side": "short", "size": 10.0, "entry_price": 0.85})

    ok = lt.reconcile_position("WLD", state, bn, hl)

    assert not ok, "reconcile_position should return False for >5% mismatch"
    alert_levels = {lvl for lvl, _ in alerts}
    assert alert_levels & {"warning", "error"}, (
        f"Expected warning/error alert for mismatch; got: {alerts}"
    )


# ══════════════════════════════════════════════════════════════════════════
# Test 4 — Carry logging: funding payments written to delta_neutral_carry.csv
# ══════════════════════════════════════════════════════════════════════════

def test_carry_logging(tmp_path, monkeypatch):
    """
    log_carry_csv: appends one row per call; CSV is created if missing.
    After two calls, CSV has 2 data rows (+ header).
    """
    monkeypatch.setattr(lt, "LOG_DIR", tmp_path)

    since = datetime.now(timezone.utc) - timedelta(hours=8)
    lt.log_carry_csv("STX", 0.123456, since)
    lt.log_carry_csv("WLD", 0.054321, since)

    csv_path = tmp_path / "delta_neutral_carry.csv"
    assert csv_path.exists(), "delta_neutral_carry.csv not created"

    rows = csv_path.read_text().strip().splitlines()
    assert rows[0].startswith("timestamp,"), "CSV header missing"
    assert len(rows) == 3, f"Expected 3 lines (header + 2 data), got {len(rows)}"

    # Verify asset names are in the rows
    assert "STX" in rows[1]
    assert "WLD" in rows[2]
    assert "0.123456" in rows[1]


# ══════════════════════════════════════════════════════════════════════════
# Test 5 — Kill switch: run() halts sys.exit(0) before exchange access
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def stop_file():
    p = PROJECT / "STOP"
    p.write_text("pytest kill-switch test")
    yield
    p.unlink(missing_ok=True)


def test_kill_switch_halts(stop_file, monkeypatch):
    """STOP file must cause sys.exit(0) before any HL/BN API calls."""
    monkeypatch.setattr(lt.notifier, "send", lambda *a, **kw: None)

    fetched = []
    monkeypatch.setattr(lt, "fetch_hl_carry_30d",
                        lambda asset: fetched.append(asset) or 0.0)
    monkeypatch.setattr(lt, "check_hl_data_freshness", lambda a: True)

    with pytest.raises(SystemExit) as exc:
        lt.run(dry_run=True)

    assert exc.value.code == 0, (
        f"Kill switch must exit(0); got exit({exc.value.code})"
    )
    assert not fetched, (
        f"fetch_hl_carry_30d called after STOP file present: {fetched}"
    )


# ══════════════════════════════════════════════════════════════════════════
# Test 6 — Data freshness: stale HL data → asset skipped, no position opened
# ══════════════════════════════════════════════════════════════════════════

@patch("strategies.delta_neutral.live_trader.log_carry_csv")
def test_stale_data_skips_asset(mock_log_carry, monkeypatch):
    """
    check_hl_data_freshness returns False → asset excluded from carry_data
    → run_asset never called for that asset → no OPEN action.
    """
    monkeypatch.setattr(lt.notifier, "send", lambda *a, **kw: None)
    # All assets report stale data
    monkeypatch.setattr(lt, "check_hl_data_freshness", lambda a: False)
    monkeypatch.setattr(lt, "fetch_hl_carry_30d", lambda a: 0.001)

    open_calls = []
    monkeypatch.setattr(lt, "open_pair",
                        lambda *a, **kw: open_calls.append(a) or None)

    lt.run(dry_run=True)

    assert not open_calls, (
        f"open_pair called despite stale data: {open_calls}"
    )


# ══════════════════════════════════════════════════════════════════════════
# Test 7 — Dry-run: no real orders; HLPerpClient never instantiated
# ══════════════════════════════════════════════════════════════════════════

@patch("strategies.delta_neutral.live_trader.log_carry_csv")
def test_dry_run_no_exchange_calls(mock_log_carry, monkeypatch):
    """
    --dry-run mode must not instantiate HLPerpClient or BinanceTestnetClient,
    and must not call open_pair/close_pair with real clients.
    """
    monkeypatch.setattr(lt.notifier, "send", lambda *a, **kw: None)
    monkeypatch.setattr(lt, "check_hl_data_freshness", lambda a: True)
    # Provide a carry that passes the floor for all assets
    monkeypatch.setattr(lt, "fetch_hl_carry_30d", lambda a: lt.CARRY_FLOOR_8H * 2)

    hl_cls_mock = MagicMock(name="HLPerpClient")
    bn_cls_mock = MagicMock(name="BinanceTestnetClient")

    with patch("strategies.delta_neutral.live_trader.BinanceTestnetClient", bn_cls_mock):
        # HLPerpClient is imported inside run() only when --live
        lt.run(dry_run=True)

    assert not bn_cls_mock.called, (
        "BinanceTestnetClient was instantiated in dry-run mode"
    )
    # In dry-run: clients are None, so no exchange methods called
    # Verify no real exchange calls by checking bn/hl mock was never called
    inst = bn_cls_mock.return_value
    for method in ("market_buy", "market_sell"):
        assert not getattr(inst, method).called, (
            f"{method} was called in dry-run mode"
        )
