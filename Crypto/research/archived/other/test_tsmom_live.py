"""
test_tsmom_live.py

Integration tests for tsmom_live.py.
No ML model required — TSMOM is a rules-based strategy.

Tests:
  1. Kill switch → sys.exit(0) before any data fetch
  2. Stale data (3d old) → sys.exit(1) + warning/error alert
  3. Dry-run: state files unchanged after run
  4. Dry-run: HyperliquidClient never instantiated
  5. Telegram summary alert contains all 3 asset names
  6. decide_action: same direction → HOLD
  7. decide_action: direction changes → OPEN / FLIP / CLOSE
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

PROJECT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT))

import tsmom_live


# ══════════════════════════════════════════════════════════════════════════
# Autouse: always run from project root
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def working_dir(monkeypatch):
    monkeypatch.chdir(PROJECT)


# ══════════════════════════════════════════════════════════════════════════
# OHLCV helpers
# ══════════════════════════════════════════════════════════════════════════

def _make_ohlcv(periods: int = 200, trend: float = 0.001,
                last_offset_days: int = 1) -> pd.DataFrame:
    """
    Synthetic OHLCV DataFrame.

    trend > 0  → positive 28d log return → signal = +1 (long)
    trend < 0  → negative 28d log return → signal = -1 (short)
    last_offset_days=1  → last bar = yesterday (fresh)
    last_offset_days=3  → last bar = 3 days ago (stale)
    """
    last = datetime.now(timezone.utc).date() - timedelta(days=last_offset_days)
    idx  = pd.date_range(end=str(last), periods=periods, freq="D", tz="UTC")
    rng  = np.random.default_rng(42)
    log_r  = np.full(periods, trend) + rng.normal(0, 0.005, size=periods)
    closes = 60_000.0 * np.exp(np.cumsum(log_r))
    noise  = rng.uniform(0.99, 1.01, size=periods)
    return pd.DataFrame({
        "Open":   closes * noise,
        "High":   closes * rng.uniform(1.001, 1.010, size=periods),
        "Low":    closes * rng.uniform(0.990, 0.999, size=periods),
        "Close":  closes,
        "Volume": rng.uniform(1e8, 2e8, size=periods),
    }, index=idx)


FRESH_UP_DF = _make_ohlcv(trend=+0.003)   # strong uptrend  → signal = +1
FRESH_DN_DF = _make_ohlcv(trend=-0.003)   # strong downtrend → signal = -1
STALE_DF    = _make_ohlcv(last_offset_days=3)  # 3-day lag → freshness fail


# ══════════════════════════════════════════════════════════════════════════
# Test 1 — Kill switch halts before any data fetch
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def stop_file():
    p = PROJECT / "STOP"
    p.write_text("pytest kill-switch test")
    yield
    p.unlink(missing_ok=True)


def test_kill_switch_halts(stop_file, monkeypatch):
    """STOP file must cause sys.exit(0) before fetch_ohlcv is reached."""
    monkeypatch.setattr(tsmom_live.notifier, "send", lambda *a, **kw: None)
    fetched = []
    monkeypatch.setattr(
        tsmom_live, "fetch_ohlcv",
        lambda sym: fetched.append(sym) or FRESH_UP_DF,
    )

    with pytest.raises(SystemExit) as exc:
        tsmom_live.run(dry_run=True)

    assert exc.value.code == 0, (
        f"kill switch must exit(0); got exit({exc.value.code})"
    )
    assert not fetched, (
        f"fetch_ohlcv was called after STOP file was present: {fetched}"
    )


# ══════════════════════════════════════════════════════════════════════════
# Test 2 — Stale data → exit(1) + warning/error alert
# ══════════════════════════════════════════════════════════════════════════

def test_stale_data_exits(monkeypatch):
    """Data 3 days old must trigger sys.exit(1) and a warning/error alert."""
    monkeypatch.setattr(tsmom_live, "fetch_ohlcv", lambda sym: STALE_DF)
    alerts: list[tuple[str, str]] = []
    monkeypatch.setattr(
        tsmom_live.notifier, "send",
        lambda msg, level="info": alerts.append((level, msg)),
    )

    with pytest.raises(SystemExit) as exc:
        tsmom_live.run(dry_run=True)

    assert exc.value.code == 1, (
        f"stale data must exit(1); got exit({exc.value.code})"
    )
    levels = {lvl for lvl, _ in alerts}
    assert levels & {"warning", "error"}, (
        f"expected warning/error alert for stale data; got: {alerts}"
    )


# ══════════════════════════════════════════════════════════════════════════
# Test 3 — Dry-run: state files unchanged
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def flat_states():
    """Write flat state for all 3 assets; clean up after test."""
    paths = [tsmom_live._state_path(sym) for sym in tsmom_live.ASSETS]
    for p in paths:
        p.write_text(json.dumps(
            {"position": "flat", "entry_price": 0.0, "entry_time": None}
        ))
    yield
    for p in paths:
        p.unlink(missing_ok=True)


@patch("tsmom_live.log_trade_csv")
def test_dry_run_state_unchanged(mock_log_csv, flat_states, monkeypatch):
    """Dry-run must never open, flip, or close a position."""
    monkeypatch.setattr(tsmom_live, "fetch_ohlcv", lambda sym: FRESH_UP_DF)
    monkeypatch.setattr(tsmom_live.notifier, "send", lambda *a, **kw: None)

    tsmom_live.run(dry_run=True)

    assert mock_log_csv.called, "log_trade_csv was not called — logging is broken"
    for sym in tsmom_live.ASSETS:
        state = json.loads(tsmom_live._state_path(sym).read_text())
        assert state["position"] == "flat", (
            f"[{sym}] dry-run must not open a position; got {state['position']!r}"
        )


# ══════════════════════════════════════════════════════════════════════════
# Test 4 — Dry-run: HyperliquidClient never instantiated
# ══════════════════════════════════════════════════════════════════════════

@patch("tsmom_live.log_trade_csv")
def test_no_exchange_calls_in_dry_run(mock_log_csv, monkeypatch):
    """
    In dry-run without private_key, the exchange client must never be
    instantiated and no order methods may be called.
    """
    import hyperliquid_client as hc_mod

    mock_cls = MagicMock(name="HyperliquidClient")
    monkeypatch.setattr(hc_mod, "HyperliquidClient", mock_cls)
    monkeypatch.setattr(tsmom_live, "fetch_ohlcv", lambda sym: FRESH_UP_DF)
    monkeypatch.setattr(tsmom_live.notifier, "send", lambda *a, **kw: None)

    tsmom_live.run(dry_run=True, private_key=None)

    assert not mock_cls.called, (
        "HyperliquidClient was instantiated during dry-run"
    )
    inst = mock_cls.return_value
    for method in ("open_long", "open_short", "close_position"):
        assert not getattr(inst, method).called, (
            f"{method} was called in dry-run mode"
        )


# ══════════════════════════════════════════════════════════════════════════
# Test 5 — Telegram alert covers all 3 assets
# ══════════════════════════════════════════════════════════════════════════

@patch("tsmom_live.log_trade_csv")
def test_telegram_alert_covers_all_assets(mock_log_csv, monkeypatch):
    """The summary Telegram message must reference BTC-USD, ETH-USD, SOL-USD."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "999:FAKETOKEN")
    monkeypatch.setenv("TELEGRAM_CHAT_ID",   "-9999999")
    monkeypatch.setattr(tsmom_live, "fetch_ohlcv", lambda sym: FRESH_UP_DF)

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None

    with patch("notifier.requests.post", return_value=mock_resp) as mock_post:
        tsmom_live.run(dry_run=True)

    assert mock_post.called, "requests.post was never called"

    # The last call should be the summary alert
    last_text = mock_post.call_args_list[-1][1]["json"]["text"]
    for sym in ["BTC-USD", "ETH-USD", "SOL-USD"]:
        assert sym in last_text, (
            f"{sym} not in summary alert. Alert text: {last_text!r}"
        )


# ══════════════════════════════════════════════════════════════════════════
# Test 6 — decide_action: same direction → HOLD
# ══════════════════════════════════════════════════════════════════════════

def test_decide_action_hold():
    """If signal matches current position, no trade should occur."""
    assert tsmom_live.decide_action("long",  +1) == "HOLD"
    assert tsmom_live.decide_action("short", -1) == "HOLD"
    assert tsmom_live.decide_action("flat",   0) == "HOLD"


# ══════════════════════════════════════════════════════════════════════════
# Test 7 — decide_action: direction changes → correct action
# ══════════════════════════════════════════════════════════════════════════

def test_decide_action_direction_changes():
    """All direction-change scenarios return the correct action string."""
    assert tsmom_live.decide_action("flat",  +1) == "OPEN_LONG"
    assert tsmom_live.decide_action("flat",  -1) == "OPEN_SHORT"
    assert tsmom_live.decide_action("long",  -1) == "FLIP_TO_SHORT"
    assert tsmom_live.decide_action("short", +1) == "FLIP_TO_LONG"
    assert tsmom_live.decide_action("long",   0) == "CLOSE"
    assert tsmom_live.decide_action("short",  0) == "CLOSE"
