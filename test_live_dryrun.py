"""
test_live_dryrun.py

End-to-end dry-run integration tests for live_trader.py.

These are integration tests — they exercise the real live_trader code paths
with real torch / pandas / scikit-learn.  No module-level stubs are used.

Guard rails tested (one test each):
    1. Kill switch       — STOP file → sys.exit(0) before load_model
    2. Data freshness    — stale yfinance data → sys.exit(1) + alert
    3. Model freshness   — expired trained_until → sys.exit(1) + alert
    4. Telegram alert    — requests.post called with correct payload
    5. State roundtrip   — dry-run must not mutate position in state.json
    6. No real orders    — HyperliquidClient never instantiated in dry-run
    7. fills.csv guard   — fills.csv not created / appended in dry-run

yfinance network calls are replaced in tests 4-7 by _fresh_df(), which
returns a synthetic 200-bar OHLCV series with yesterday as the last bar.
This isolates the tests from yfinance freshness / midnight-UTC edge cases.

Telegram HTTP calls are intercepted (requests.post patched) so no real
messages are sent.  No exchange orders are placed (dry_run=True throughout).

Prerequisites:
    model_store/BTC_USD_model.pt must exist.
    If missing: python train_and_save.py --symbol BTC-USD
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# ── Project paths ─────────────────────────────────────────────────────────
PROJECT     = Path(__file__).parent.resolve()
MODEL_STORE = PROJECT / "model_store"
META_PATH   = MODEL_STORE / "BTC_USD_meta.json"
STATE_PATH  = PROJECT / "state_BTC_USD.json"
STOP_PATH   = PROJECT / "STOP"
FILLS_CSV   = PROJECT / "logs" / "fills.csv"

SYMBOL  = "BTC-USD"
CAPITAL = 1_000.0

sys.path.insert(0, str(PROJECT))
import live_trader  # real import — requires torch, yfinance, etc.


# ══════════════════════════════════════════════════════════════════════════
# Autouse fixtures — applied to every test automatically
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def working_dir(monkeypatch):
    """
    All relative paths inside live_trader (model_store/, state_*.json,
    logs/, STOP) must resolve from the project directory, not from wherever
    pytest was invoked.
    """
    monkeypatch.chdir(PROJECT)


@pytest.fixture(autouse=True)
def require_model():
    """Skip every test if the trained model is absent from disk."""
    if not (MODEL_STORE / "BTC_USD_model.pt").exists():
        pytest.skip(
            "model_store/BTC_USD_model.pt not found — "
            "run: python train_and_save.py --symbol BTC-USD"
        )


# ══════════════════════════════════════════════════════════════════════════
# OHLCV helpers
# ══════════════════════════════════════════════════════════════════════════

def _stale_df() -> pd.DataFrame:
    """
    OHLCV DataFrame whose last bar is 3 calendar days old.
    Used by test_data_freshness_stale to simulate yfinance serving stale data.
    """
    end = datetime.now(timezone.utc).date() - timedelta(days=3)
    idx = pd.date_range(end=str(end), periods=200, freq="D", tz="UTC")
    return pd.DataFrame(
        {"Open": 100.0, "High": 105.0, "Low": 95.0,
         "Close": 102.0, "Volume": 1_000_000.0},
        index=idx,
    )


def _fresh_df() -> pd.DataFrame:
    """
    Synthetic 200-bar OHLCV DataFrame with yesterday as the last bar.

    Prices use a seeded linear trend so features (EMA, RSI, Bollinger,
    z-score) are well-defined and non-NaN.  Volume has mild variation.
    Used by tests 4-7 to decouple from real yfinance network calls and
    midnight-UTC freshness edge cases.
    """
    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
    idx = pd.date_range(end=str(yesterday), periods=200, freq="D", tz="UTC")

    rng    = np.random.default_rng(42)
    base   = 60_000.0
    # Small random daily returns so indicators have meaningful variation
    log_r  = rng.normal(0.001, 0.02, size=200)
    closes = base * np.exp(np.cumsum(log_r))

    noise = rng.uniform(0.98, 1.00, size=200)
    return pd.DataFrame({
        "Open":   closes * noise,
        "High":   closes * rng.uniform(1.001, 1.010, size=200),
        "Low":    closes * rng.uniform(0.990, 0.999, size=200),
        "Close":  closes,
        "Volume": rng.uniform(0.8e9, 1.2e9, size=200),
    }, index=idx)


# ══════════════════════════════════════════════════════════════════════════
# Test 1 — kill switch halts before load_model
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def stop_file():
    STOP_PATH.write_text("pytest kill-switch test")
    yield
    STOP_PATH.unlink(missing_ok=True)


def test_kill_switch_halts(stop_file, monkeypatch):
    """
    With a STOP file present, run() must call sys.exit(0) before reaching
    load_model().  We sentinel load_model so any bypass is unmistakable.
    """
    reached_load = []
    monkeypatch.setattr(
        live_trader, "load_model",
        lambda *a, **kw: reached_load.append(True),
    )
    monkeypatch.setattr(live_trader.notifier, "send", lambda *a, **kw: None)

    with pytest.raises(SystemExit) as exc:
        live_trader.run(SYMBOL, CAPITAL, dry_run=True)

    assert exc.value.code == 0, (
        f"kill switch must exit(0) (intentional halt); got exit({exc.value.code})"
    )
    assert not reached_load, (
        "load_model was called after a STOP file was present — "
        "check_kill_switch() must be the very first action in run()"
    )


# ══════════════════════════════════════════════════════════════════════════
# Test 2 — stale data → exit(1) + warning/error alert
# ══════════════════════════════════════════════════════════════════════════

def test_data_freshness_stale(monkeypatch):
    """
    Monkey-patching get_latest_bars to return data 3 days old must trigger
    check_data_freshness to exit(1) and emit at least one warning/error alert.
    """
    monkeypatch.setattr(live_trader, "get_latest_bars", lambda sym: _stale_df())

    alerts: list[tuple[str, str]] = []
    monkeypatch.setattr(
        live_trader.notifier, "send",
        lambda msg, level="info": alerts.append((level, msg)),
    )

    with pytest.raises(SystemExit) as exc:
        live_trader.run(SYMBOL, CAPITAL, dry_run=True)

    assert exc.value.code == 1, (
        f"stale data must exit(1); got exit({exc.value.code})"
    )
    levels = {lvl for lvl, _ in alerts}
    assert levels & {"warning", "error"}, (
        f"expected at least one warning or error alert for stale data; "
        f"got alerts: {alerts}"
    )


# ══════════════════════════════════════════════════════════════════════════
# Test 3 — expired model (trained_until 100 days ago) → exit(1)
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def stale_meta():
    """
    Overwrite BTC_USD_meta.json with trained_until = 100 days ago,
    then restore the original content unconditionally on teardown.
    """
    original = META_PATH.read_text()
    meta = json.loads(original)
    old_date = (
        datetime.now(timezone.utc).date() - timedelta(days=100)
    ).strftime("%Y-%m-%d")
    meta["trained_until"] = old_date
    META_PATH.write_text(json.dumps(meta, indent=2))
    yield old_date
    META_PATH.write_text(original)   # always restore — even if test fails


def test_model_freshness_expired(stale_meta, monkeypatch):
    """
    A model trained 100 days ago exceeds the default 45-day limit.
    check_model_freshness must exit(1) and send a level='error' alert
    containing the word 'EXPIRED'.
    """
    alerts: list[tuple[str, str]] = []
    monkeypatch.setattr(
        live_trader.notifier, "send",
        lambda msg, level="info": alerts.append((level, msg)),
    )

    with pytest.raises(SystemExit) as exc:
        live_trader.run(SYMBOL, CAPITAL, dry_run=True, max_model_age_days=45)

    assert exc.value.code == 1, (
        f"expired model must exit(1); got exit({exc.value.code})"
    )
    error_msgs = [msg for lvl, msg in alerts if lvl == "error"]
    assert error_msgs, f"expected at least one error-level alert; got: {alerts}"
    assert any("EXPIRED" in m for m in error_msgs), (
        f"alert must contain 'EXPIRED'; got error alerts: {error_msgs}"
    )


# ══════════════════════════════════════════════════════════════════════════
# Test 4 — Telegram heartbeat reaches requests.post
# ══════════════════════════════════════════════════════════════════════════

def test_telegram_alert_sent(monkeypatch):
    """
    A successful dry-run always fires a heartbeat via notifier.send().
    With fake credentials set in os.environ, send() must proceed to
    requests.post.  We intercept that call and verify the payload structure.

    get_latest_bars is replaced with _fresh_df() so the test is isolated
    from yfinance network calls and midnight-UTC freshness edge cases.
    """
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "999:FAKETOKEN")
    monkeypatch.setenv("TELEGRAM_CHAT_ID",   "-9999999")
    monkeypatch.setattr(live_trader, "get_latest_bars", lambda sym: _fresh_df())

    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None

    with patch("notifier.requests.post", return_value=mock_resp) as mock_post:
        live_trader.run(SYMBOL, CAPITAL, dry_run=True)

    assert mock_post.called, (
        "requests.post was never called — "
        "heartbeat did not reach the Telegram API"
    )

    first_url  = mock_post.call_args_list[0][0][0]
    first_body = mock_post.call_args_list[0][1].get("json", {})

    assert "999:FAKETOKEN" in first_url, (
        f"URL must contain our fake bot token; got: {first_url}"
    )
    assert first_body.get("chat_id") == "-9999999", (
        f"chat_id mismatch; got: {first_body}"
    )
    assert "text" in first_body, (
        f"Telegram payload missing 'text' key; got: {first_body}"
    )
    # The heartbeat is always the last send() call on a successful run
    last_body = mock_post.call_args_list[-1][1].get("json", {})
    assert "Heartbeat" in last_body.get("text", ""), (
        f"last alert should be the heartbeat; got: {last_body.get('text')!r}"
    )


# ══════════════════════════════════════════════════════════════════════════
# Test 5 — state.json roundtrip: position unchanged after dry-run
# ══════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def known_state():
    """
    Write a deterministic flat state before the test.
    Restore (or delete) whatever was there on teardown.
    """
    original_text = STATE_PATH.read_text() if STATE_PATH.exists() else None

    initial = {"position": "flat", "entry_price": 0.0, "entry_time": None}
    STATE_PATH.write_text(json.dumps(initial))
    yield initial

    if original_text is not None:
        STATE_PATH.write_text(original_text)
    elif STATE_PATH.exists():
        STATE_PATH.unlink()


def test_state_roundtrip(known_state, monkeypatch):
    """
    Even if the ML signal says BUY, a dry-run must not open a position.
    The `if dry_run:` guard skips all order execution and state mutation;
    save_state() writes back the unchanged loaded dict.
    """
    monkeypatch.setattr(live_trader, "get_latest_bars", lambda sym: _fresh_df())
    monkeypatch.setattr(live_trader.notifier, "send", lambda *a, **kw: None)

    live_trader.run(SYMBOL, CAPITAL, dry_run=True)

    after = json.loads(STATE_PATH.read_text())
    assert after["position"] == "flat", (
        f"dry-run must not open a position; "
        f"got position={after['position']!r}"
    )
    assert after["entry_price"] == 0.0, (
        f"entry_price must remain 0.0 after dry-run; "
        f"got {after['entry_price']}"
    )


# ══════════════════════════════════════════════════════════════════════════
# Test 6 — HyperliquidClient never instantiated in dry-run
# ══════════════════════════════════════════════════════════════════════════

def test_no_real_orders_placed(monkeypatch):
    """
    Replace HyperliquidClient in the hyperliquid_client module with a Mock.
    In dry-run without a private key:
      - reconcile block is skipped (no key)
      - order block is skipped  (`if dry_run:`)
      - funding block is skipped (`if not dry_run and private_key:`)
    So the mock must never be instantiated.  This acts as a regression
    guard: if the dry-run guard is accidentally removed, the Mock records
    the call and the assertion fails loudly.
    """
    import hyperliquid_client as hc_mod

    mock_cls = MagicMock(name="HyperliquidClient")
    monkeypatch.setattr(hc_mod, "HyperliquidClient", mock_cls)
    monkeypatch.setattr(live_trader, "get_latest_bars", lambda sym: _fresh_df())
    monkeypatch.setattr(live_trader.notifier, "send", lambda *a, **kw: None)

    live_trader.run(SYMBOL, CAPITAL, dry_run=True, private_key=None)

    assert not mock_cls.called, (
        "HyperliquidClient was instantiated during dry-run — "
        "order guard or funding guard is broken"
    )
    inst = mock_cls.return_value
    assert not inst.open_long.called, (
        "open_long was called in dry-run mode"
    )
    assert not inst.open_short.called, (
        "open_short was called in dry-run mode"
    )
    assert not inst.close_position.called, (
        "close_position was called in dry-run mode"
    )


# ══════════════════════════════════════════════════════════════════════════
# Test 7 — fills.csv not created or appended in dry-run
# ══════════════════════════════════════════════════════════════════════════

def test_fills_csv_not_written_in_dry_run(monkeypatch):
    """
    _log_fill() (and therefore fills.csv) is only reached through
    open_long / open_short / close_position — none of which run in dry-run.
    Record the file size (or absence) before and after; assert no change.
    """
    monkeypatch.setattr(live_trader, "get_latest_bars", lambda sym: _fresh_df())
    monkeypatch.setattr(live_trader.notifier, "send", lambda *a, **kw: None)

    size_before = FILLS_CSV.stat().st_size if FILLS_CSV.exists() else None

    live_trader.run(SYMBOL, CAPITAL, dry_run=True, private_key=None)

    size_after = FILLS_CSV.stat().st_size if FILLS_CSV.exists() else None

    assert size_after == size_before, (
        f"fills.csv was modified during dry-run. "
        f"Size before: {size_before} bytes → after: {size_after} bytes. "
        f"_log_fill() must not be reachable in dry-run mode."
    )
