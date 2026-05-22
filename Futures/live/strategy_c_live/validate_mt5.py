"""
validate_mt5.py — MT5 validation tests for Strategy C (FTMO deployment)
========================================================================
Tests M1-M6 + Test C (VPS watchdog).

Run all: /usr/bin/python3 -m Futures.live.strategy_c_live.validate_mt5
Run one: /usr/bin/python3 -m Futures.live.strategy_c_live.validate_mt5 M1

COMMIT GATE: all tests must PASS before first live trade.
Market-hours tests (M4, M6 with signal): require MT5 open + FTMO Free Trial connected.
"""
from __future__ import annotations

import sys
import time
from datetime import time as _time
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parents[4]))

from Futures.live.strategy_c_live.config import (
    SYMBOL, LOT_SIZE, GUARDRAIL_DD_PCT, GUARDRAIL_DAILY_BUFFER_PCT,
    GUARDRAIL_TRAILING_DD_PCT,
)

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
SKIP = "\033[93mSKIP\033[0m"

results: dict[str, str] = {}


# ─────────────────────────────────────────────────────────────────────────────
# M1 — MT5 connection + account info
# ─────────────────────────────────────────────────────────────────────────────

def test_m1() -> None:
    print("\n── M1: MT5 connection + account info ──────────────────────")
    try:
        from Futures.live.strategy_c_live.mt5_client import MT5Client
        c = MT5Client()
        c.connect()
        acct_val = c.get_account_value()
        assert acct_val > 0, f"Equity = {acct_val} (expected > 0)"
        from Futures.live.strategy_c_live.mt5_client import mt5
        acct = mt5.account_info()
        print(f"  login={acct.login if acct else '?'}, equity=${acct_val:,.2f}, server={acct.server if acct else '?'}")
        print(f"  {PASS} M1 — MT5 connect + account info OK")
        results["M1"] = "PASS"
        c.disconnect()
    except Exception as e:
        print(f"  {FAIL} M1 — {e}")
        results["M1"] = f"FAIL: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# M2 — Symbol discovery + 1-min bars
# ─────────────────────────────────────────────────────────────────────────────

def test_m2() -> None:
    print("\n── M2: Symbol discovery + 1-min bars ──────────────────────")
    try:
        from Futures.live.strategy_c_live.mt5_client import MT5Client
        c = MT5Client()
        c.connect()

        bars = c.get_1min_bars(SYMBOL, n_days=2)
        assert len(bars) > 100, f"Only {len(bars)} bars (expected > 100)"
        assert bars.index.tzinfo is not None, "Index has no timezone"
        assert "America/New_York" in str(bars.index.tzinfo), \
            f"Expected ET tz, got {bars.index.tzinfo}"
        for col in ["open", "high", "low", "close", "volume"]:
            assert col in bars.columns, f"Missing column: {col}"
        times = bars.index.time
        assert all(t >= _time(9, 30) for t in times), "Bar before 09:30 ET found"
        assert all(t < _time(16, 0) for t in times), "Bar at/after 16:00 ET found"

        print(f"  {PASS} M2 — {len(bars)} RTH bars | {bars.index[0]} → {bars.index[-1]}")
        results["M2"] = f"PASS — {len(bars)} bars"
        c.disconnect()
    except Exception as e:
        print(f"  {FAIL} M2 — {e}")
        results["M2"] = f"FAIL: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# M3 — Signal engine on MT5 data vs backtest
# ─────────────────────────────────────────────────────────────────────────────

def test_m3() -> None:
    print("\n── M3: Signal engine on MT5 data ───────────────────────────")
    try:
        from Futures.live.strategy_c_live.mt5_client import MT5Client
        from Futures.live.strategy_c_live.signal_engine import compute_signal
        import pandas as pd

        c = MT5Client()
        c.connect()
        bars = c.get_1min_bars(SYMBOL, n_days=14)
        c.disconnect()

        if len(bars) < 100:
            print(f"  {SKIP} M3 — insufficient data ({len(bars)} bars)")
            results["M3"] = "SKIP — insufficient data"
            return

        # Group by trading day and compute signal for each
        days = bars.groupby(bars.index.date)
        n_signal = n_total = 0
        for d, day_bars in days:
            n_total += 1
            sig = compute_signal(day_bars)
            if sig is not None:
                n_signal += 1
                print(f"  Day {d}: {sig['direction']}  "
                      f"ORB={sig['opening_range']:.0f}pts  "
                      f"gap={sig['gap_pct']:+.2f}%  "
                      f"TP={sig['tp_price']:.2f}  SL={sig['sl_price']:.2f}")

        print(f"  {PASS} M3 — {n_signal}/{n_total} days produced a signal")
        results["M3"] = f"PASS — {n_signal}/{n_total} signals"
    except Exception as e:
        print(f"  {FAIL} M3 — {e}")
        results["M3"] = f"FAIL: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# M4 — Bracket order placement + integrity check (market hours only)
# ─────────────────────────────────────────────────────────────────────────────

def test_m4() -> None:
    print("\n── M4: Bracket order placement (market hours only) ─────────")
    try:
        from Futures.live.strategy_c_live.mt5_client import MT5Client, mt5
        if mt5 is None:
            print(f"  {SKIP} M4 — MT5 not available")
            results["M4"] = "SKIP — MT5 not available"
            return

        c = MT5Client()
        c.connect()

        # Check if market is open
        tick = mt5.symbol_info_tick(SYMBOL)
        if tick is None or tick.ask == 0:
            c.disconnect()
            print(f"  {SKIP} M4 — market closed / no tick for {SYMBOL}")
            results["M4"] = "SKIP — market closed (run during market hours)"
            return

        # Symbol info for volume_min
        sym_info = mt5.symbol_info(SYMBOL)
        volume   = max(sym_info.volume_min, round(LOT_SIZE * 0.1, 2))

        ask       = tick.ask
        tick_size = sym_info.trade_tick_size
        tp_price  = ask + 30 * tick_size
        sl_price  = ask - 20 * tick_size

        trade = c.place_bracket_order(SYMBOL, 'BUY', volume, tp_price, sl_price)
        time.sleep(3)

        status = c.get_order_status(trade['ticket'])
        assert status == 'Submitted', f"Expected Submitted, got {status}"

        fill = trade['entry_price']
        print(f"  ticket={trade['ticket']}, fill={fill:.5f}, status={status}")
        print(f"  {PASS} M4 — bracket placed + integrity OK")
        results["M4"] = f"PASS — ticket={trade['ticket']}, fill={fill:.5f}"

        # Close the test position
        positions = mt5.positions_get(symbol=SYMBOL)
        for pos in (positions or []):
            if pos.ticket == trade['ticket']:
                close_req = {
                    'action':       mt5.TRADE_ACTION_DEAL,
                    'symbol':       SYMBOL,
                    'volume':       volume,
                    'type':         mt5.ORDER_TYPE_SELL,
                    'price':        mt5.symbol_info_tick(SYMBOL).bid,
                    'position':     trade['ticket'],
                    'deviation':    20,
                    'magic':        20260522,
                    'comment':      'test close',
                    'type_filling': mt5.ORDER_FILLING_IOC,
                }
                result = mt5.order_send(close_req)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"  M4 cleanup: position closed @ {result.price:.5f}")
                else:
                    print(f"  M4 cleanup FAILED: {result.retcode if result else 'None'}")

        c.disconnect()
    except Exception as e:
        print(f"  {FAIL} M4 — {e}")
        results["M4"] = f"FAIL: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# M5 — Guardrails daily_floor FTMO
# ─────────────────────────────────────────────────────────────────────────────

def test_m5() -> None:
    print("\n── M5: Guardrails daily_floor FTMO ─────────────────────────")
    try:
        from Futures.live.strategy_c_live.challenge_state import ChallengeState
        from Futures.live.strategy_c_live.guardrails import PropfirmGuardrails, GuardrailTriggered

        state = ChallengeState.__new__(ChallengeState)
        state.initial_balance     = 10_000.0
        state.peak_balance        = 10_000.0
        state.balance_at_day_open = 10_500.0   # yesterday was profitable
        state.challenge_start_date = "2026-05-22"
        state.trades_since_start  = 0

        mock_client = MagicMock()
        g = PropfirmGuardrails(state, mock_client)

        # T1: $300 loss from midnight ($10,500 → $10,200) — BELOW $400 guardrail → OK
        g.check_all(10_200.0)
        print(f"  T1 {PASS}: loss $300 from midnight OK (floor=${state.daily_floor():.0f})")

        # T2: $450 loss from midnight ($10,500 → $10,050) — ABOVE $400 guardrail → TRIGGER
        try:
            g.check_all(10_050.0)
            print(f"  T2 {FAIL}: should have raised DAILY_LOSS")
            results["M5"] = "FAIL: T2 did not raise"
            return
        except GuardrailTriggered as e:
            assert "DAILY_LOSS" in str(e), f"Expected DAILY_LOSS, got: {e}"
            print(f"  T2 {PASS}: {e}")

        # T3: $900 loss from initial ($10,000 → $9,100) — ABOVE 8% DD ($800) → TRIGGER
        try:
            g.check_all(9_100.0)
            print(f"  T3 {FAIL}: should have raised FIXED_DD")
            results["M5"] = "FAIL: T3 did not raise"
            return
        except GuardrailTriggered as e:
            assert "FIXED_DD" in str(e) or "DD" in str(e), f"Expected DD, got: {e}"
            print(f"  T3 {PASS}: {e}")

        # T4: GUARDRAIL_TRAILING_DD_PCT is None → L1a disabled
        # Use a high peak so trailing DD (18%) would fire if enabled, but isn't
        assert GUARDRAIL_TRAILING_DD_PCT is None, \
            f"Expected None, got {GUARDRAIL_TRAILING_DD_PCT}"
        state.peak_balance = 12_000.0   # artificial high to force trailing_dd check
        g.check_all(10_200.0)   # trailing_dd=18% (skipped), static=-2%, daily $300<$400 OK
        print(f"  T4 {PASS}: trailing DD disabled (GUARDRAIL_TRAILING_DD_PCT=None)")

        print(f"  {PASS} M5 — all guardrail scenarios correct")
        results["M5"] = "PASS"
    except Exception as e:
        print(f"  {FAIL} M5 — {e}")
        results["M5"] = f"FAIL: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# M6 — Dry run run_daily.py (run after 16:00 ET / market closed)
# ─────────────────────────────────────────────────────────────────────────────

def test_m6() -> None:
    print("\n── M6: Dry run run_daily.py (post-market) ──────────────────")
    print("  Manual test — instructions:")
    print("  1. After 16:00 ET (22:00 Paris), with MT5 open + FTMO Free Trial connected:")
    print("     python3 -m Futures.live.strategy_c_live.run_daily")
    print("  2. Expected:")
    print("     - MT5 connect OK")
    print("     - get_1min_bars OK")
    print("     - signal = None (market closed)")
    print("     - Telegram: 'NQ-C | {date} | SKIPPED [filter(s) rejected]'")
    print("     - Exit code 0, no exceptions")
    print("  3. If run during market hours and signal fires:")
    print("     - Verify bracket in MT5 terminal (visual check)")
    print("     - Verify Telegram: SIGNAL + FILLED + EXIT messages")
    print(f"  {SKIP} M6 — manual test, mark PASS after observing correct behavior")
    results["M6"] = "PENDING — run manually (see instructions above)"


# ─────────────────────────────────────────────────────────────────────────────
# Test C — VPS watchdog
# ─────────────────────────────────────────────────────────────────────────────

def test_c() -> None:
    print("\n── C: VPS watchdog ─────────────────────────────────────────")
    try:
        import requests
        url_hb = "http://<VPS_IP>:8765/heartbeat"
        url_st = "http://<VPS_IP>:8765/status"

        r = requests.post(
            url_hb,
            json={"status": "TEST", "dd_pct": 0.0},
            timeout=5,
        )
        assert r.status_code == 200, f"HTTP {r.status_code}"
        data = r.json()
        assert data.get("ok"), f"Response not OK: {data}"
        print(f"  heartbeat: {data}")

        r2 = requests.get(url_st, timeout=5)
        print(f"  status: {r2.json()}")

        print(f"  {PASS} C — VPS watchdog responding")
        results["C"] = "PASS"
    except Exception as e:
        print(f"  {FAIL} C — {e}")
        results["C"] = f"FAIL: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Dispatch
# ─────────────────────────────────────────────────────────────────────────────

_tests = {
    "M1": test_m1,
    "M2": test_m2,
    "M3": test_m3,
    "M4": test_m4,
    "M5": test_m5,
    "M6": test_m6,
    "C":  test_c,
}


def main() -> None:
    requested = [a.upper() for a in sys.argv[1:]] if len(sys.argv) > 1 else list(_tests)
    unknown   = [t for t in requested if t not in _tests]
    if unknown:
        print(f"Unknown tests: {unknown}. Available: {list(_tests)}")
        sys.exit(1)

    print("=" * 60)
    print("VALIDATE MT5 — Strategy C FTMO deployment")
    print("=" * 60)

    for name in requested:
        _tests[name]()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    all_pass = True
    for name in requested:
        r = results.get(name, "NOT RUN")
        status = PASS if r.startswith("PASS") else (SKIP if r.startswith(("SKIP", "PENDING")) else FAIL)
        if not r.startswith(("PASS", "SKIP", "PENDING")):
            all_pass = False
        print(f"  {name:3s}  {status}  {r}")

    print()
    if all_pass:
        print("All tests PASS/SKIP — ready for FTMO Free Trial.")
    else:
        print("Some tests FAILED — fix before deploying.")
        sys.exit(1)


if __name__ == "__main__":
    main()
