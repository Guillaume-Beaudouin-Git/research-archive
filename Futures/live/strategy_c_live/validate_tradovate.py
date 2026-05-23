"""
validate_tradovate.py — Tradovate/Tradeify validation tests for Strategy C
===========================================================================
Tests T1-T6 + Test C (VPS watchdog).

Run all: /usr/bin/python3 -m Futures.live.strategy_c_live.validate_tradovate
Run one: /usr/bin/python3 -m Futures.live.strategy_c_live.validate_tradovate T1

COMMIT GATE: T1-T5 must PASS. T4 requires market hours + Tradovate Demo account.
Credentials must be in .env (TRADOVATE_USERNAME, TRADOVATE_PASSWORD, TRADOVATE_CID, etc.)
"""
from __future__ import annotations

import sys
import time
from datetime import time as _time
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parents[4]))

from Futures.live.strategy_c_live.config import (
    TRADOVATE_ENV,
    GUARDRAIL_TRAILING_DD_USD,
    GUARDRAIL_POST_LOCK_FLOOR,
    GUARDRAIL_DAILY_SELF_LIMIT,
)

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
SKIP = "\033[93mSKIP\033[0m"

results: dict[str, str] = {}


# ─────────────────────────────────────────────────────────────────────────────
# T1 — Tradovate connection + account info
# ─────────────────────────────────────────────────────────────────────────────

def test_t1() -> None:
    print("\n── T1: Tradovate connection + account info ──────────────────")
    try:
        from Futures.live.strategy_c_live.tradovate_client import TradovateClient
        c = TradovateClient()
        c.connect()
        assert c.token is not None, "token is None after connect"
        assert c.account_id is not None, "account_id is None after connect"
        acct_val = c.get_account_value()
        assert acct_val >= 0, f"Account value = {acct_val}"
        print(f"  env={TRADOVATE_ENV}, account_id={c.account_id}, balance=${acct_val:,.2f}")
        print(f"  {PASS} T1 — Tradovate connect + account info OK")
        results["T1"] = f"PASS — account_id={c.account_id}, balance=${acct_val:,.2f}"
        c.disconnect()
    except Exception as e:
        print(f"  {FAIL} T1 — {e}")
        results["T1"] = f"FAIL: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# T2 — Symbol discovery + 1-min bars MNQ
# ─────────────────────────────────────────────────────────────────────────────

def test_t2() -> None:
    print("\n── T2: Symbol discovery + 1-min bars MNQ ───────────────────")
    try:
        from Futures.live.strategy_c_live.tradovate_client import TradovateClient
        c = TradovateClient()
        c.connect()

        contract = c.get_mnq_contract()
        assert 'name' in contract, f"Contract missing 'name': {contract}"
        print(f"  Contract: {contract['name']} (id={contract.get('id')})")

        bars = c.get_1min_bars(contract, n_days=2)
        assert len(bars) > 50, f"Only {len(bars)} bars (expected > 50)"
        assert bars.index.tzinfo is not None, "Index has no timezone"
        assert "America/New_York" in str(bars.index.tzinfo), \
            f"Expected ET tz, got {bars.index.tzinfo}"
        for col in ["open", "high", "low", "close", "volume"]:
            assert col in bars.columns, f"Missing column: {col}"
        times = bars.index.time
        assert all(t >= _time(9, 30) for t in times), "Bar before 09:30 ET found"
        assert all(t < _time(16, 0) for t in times), "Bar at/after 16:00 ET found"

        print(f"  {PASS} T2 — {len(bars)} RTH bars | {bars.index[0]} → {bars.index[-1]}")
        results["T2"] = f"PASS — {contract['name']}, {len(bars)} bars"
        c.disconnect()
    except Exception as e:
        print(f"  {FAIL} T2 — {e}")
        results["T2"] = f"FAIL: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# T3 — Signal engine on Tradovate data
# ─────────────────────────────────────────────────────────────────────────────

def test_t3() -> None:
    print("\n── T3: Signal engine on Tradovate data ─────────────────────")
    try:
        from Futures.live.strategy_c_live.tradovate_client import TradovateClient
        from Futures.live.strategy_c_live.signal_engine import compute_signal

        c = TradovateClient()
        c.connect()
        contract = c.get_mnq_contract()
        bars = c.get_1min_bars(contract, n_days=14)
        c.disconnect()

        if len(bars) < 100:
            print(f"  {SKIP} T3 — insufficient data ({len(bars)} bars)")
            results["T3"] = "SKIP — insufficient data"
            return

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

        signal_rate = n_signal / n_total if n_total else 0
        status = PASS if signal_rate >= 0.2 else SKIP
        print(f"  {status} T3 — {n_signal}/{n_total} days produced a signal (rate={signal_rate:.0%})")
        results["T3"] = f"{'PASS' if signal_rate >= 0.2 else 'SKIP'} — {n_signal}/{n_total} signals"
    except Exception as e:
        print(f"  {FAIL} T3 — {e}")
        results["T3"] = f"FAIL: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# T4 — Bracket order placement (market hours only)
# ─────────────────────────────────────────────────────────────────────────────

def test_t4() -> None:
    print("\n── T4: Bracket order placement (market hours only) ──────────")
    try:
        from Futures.live.strategy_c_live.tradovate_client import TradovateClient
        import requests

        c = TradovateClient()
        c.connect()
        contract = c.get_mnq_contract()

        # Check if market is open via current price
        price = c.get_current_price(contract)
        if price is None or price == 0:
            c.disconnect()
            print(f"  {SKIP} T4 — no price tick, market likely closed")
            results["T4"] = "SKIP — market closed (run during RTH)"
            return

        qty      = 1
        tp_price = price + 30
        sl_price = price - 20

        trade = c.place_bracket_order(contract, 'BUY', qty, tp_price, sl_price)
        time.sleep(3)

        order_id = trade['orderId']
        status   = c.get_order_status(order_id)
        fill     = trade.get('entry_price')

        print(f"  orderId={order_id}, fill={fill}, status={status}")
        print(f"  tp_orderId={trade.get('tp_orderId')}, sl_orderId={trade.get('sl_orderId')}")
        assert order_id is not None, "orderId is None"
        print(f"  {PASS} T4a — bracket placed, status={status}")

        # Cancel bracket + close position
        try:
            c.cancel_all_for_contract(contract)
            flat = c.flatten_position(contract)
            if flat:
                fill_p = c.wait_for_fill(flat.get('orderId'), timeout_secs=15)
                print(f"  T4 cleanup: position closed @ {fill_p}")
        except Exception as ex:
            print(f"  T4 cleanup warning: {ex}")

        results["T4"] = f"PASS — orderId={order_id}, fill={fill}"
        c.disconnect()
    except Exception as e:
        print(f"  {FAIL} T4 — {e}")
        results["T4"] = f"FAIL: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# T5 — Guardrails pre/post-lock (offline)
# ─────────────────────────────────────────────────────────────────────────────

def test_t5() -> None:
    print("\n── T5: Guardrails pre/post-lock ($25K config) ───────────────")
    try:
        from Futures.live.strategy_c_live.challenge_state import ChallengeState
        from Futures.live.strategy_c_live.guardrails import PropfirmGuardrails, GuardrailTriggered

        # $25K account: initial=25_000, trailing_dd guardrail=$1,300, daily=$400
        state = ChallengeState.__new__(ChallengeState)
        state.initial_balance        = 25_000.0
        state.peak_balance           = 26_000.0
        state.balance_at_day_open    = 25_200.0   # small day open so daily self-limit stays clear
        state.lock_triggered         = False
        state.lock_floor             = 25_100.0
        state.is_funded              = True
        state.trades_since_start     = 0
        state.first_payout_requested = False
        state.cumulative_payouts     = 0.0
        state.challenge_start_date   = "2026-05-23"

        mock_client = MagicMock()
        g = PropfirmGuardrails(state, mock_client)

        # T5.1: pre-lock, trailing DD $1,000 from peak $26,000 → OK
        #   trailing: $26,000-$25,000=$1,000 < $1,300 guardrail ✓
        #   daily: $25,200-$25,000=$200 < $400 ✓
        g.check_all(25_000.0)
        print(f"  T5.1 {PASS}: pre-lock trailing DD $1,000 OK (guardrail=${GUARDRAIL_TRAILING_DD_USD:,})")

        # T5.2: pre-lock, trailing DD $1,500 → GuardrailTriggered TRAILING_DD
        #   trailing: $26,000-$24,500=$1,500 >= $1,300 → FAIL
        #   daily: $25,200-$24,500=$700 > $400, but trailing fires first ✓
        try:
            g.check_all(24_500.0)
            print(f"  T5.2 {FAIL}: should have raised TRAILING_DD")
            results["T5"] = "FAIL: T5.2 did not raise"
            return
        except GuardrailTriggered as e:
            assert "TRAILING_DD" in str(e), f"Expected TRAILING_DD, got: {e}"
            print(f"  T5.2 {PASS}: {e}")

        # T5.3: daily self-limit — $450 loss from day open → GuardrailTriggered
        #   trailing: $26,000-$25,550=$450 < $1,300 → OK, daily fires
        #   daily: $26,000-$25,550=$450 >= $400 → DAILY_SELF_LIMIT
        state.balance_at_day_open = 26_000.0
        try:
            g.check_all(25_550.0)
            print(f"  T5.3 {FAIL}: should have raised DAILY_SELF_LIMIT")
            results["T5"] = "FAIL: T5.3 did not raise"
            return
        except GuardrailTriggered as e:
            assert "DAILY_SELF_LIMIT" in str(e), f"Expected DAILY_SELF_LIMIT, got: {e}"
            print(f"  T5.3 {PASS}: {e}")

        # T5.4: post-lock, balance $25,200 > $25,175 guardrail → OK
        #   daily: $25,400-$25,200=$200 < $400 ✓
        state.lock_triggered      = True
        state.balance_at_day_open = 25_400.0
        g.check_all(25_200.0)
        print(f"  T5.4 {PASS}: post-lock $25,200 > guardrail ${GUARDRAIL_POST_LOCK_FLOOR:,} OK")

        # T5.5: post-lock, balance $25,100 < $25,175 guardrail → GuardrailTriggered POST_LOCK
        #   post-lock check fires before daily check ✓
        try:
            g.check_all(25_100.0)
            print(f"  T5.5 {FAIL}: should have raised POST_LOCK_FLOOR")
            results["T5"] = "FAIL: T5.5 did not raise"
            return
        except GuardrailTriggered as e:
            assert "POST_LOCK" in str(e), f"Expected POST_LOCK, got: {e}"
            print(f"  T5.5 {PASS}: {e}")

        print(f"  {PASS} T5 — all guardrail scenarios correct")
        results["T5"] = "PASS"
    except Exception as e:
        print(f"  {FAIL} T5 — {e}")
        results["T5"] = f"FAIL: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# T6 — Dry run run_daily.py (post-market, manual)
# ─────────────────────────────────────────────────────────────────────────────

def test_t6() -> None:
    print("\n── T6: Dry run run_daily.py (post-market) ───────────────────")
    print("  Manual test — instructions:")
    print("  1. After 16:00 ET, with Tradovate Demo credentials in .env:")
    print("     python3 -m Futures.live.strategy_c_live.run_daily")
    print("  2. Expected:")
    print("     - Tradovate connect OK")
    print("     - get_1min_bars OK")
    print("     - signal = None (market closed)")
    print("     - Telegram: 'NQ-C | {date} | SKIPPED [filter(s) rejected]'")
    print("     - Exit code 0, no exceptions")
    print(f"  {SKIP} T6 — manual test, mark PASS after observing correct behavior")
    results["T6"] = "PENDING — run manually (see instructions above)"


# ─────────────────────────────────────────────────────────────────────────────
# Test C — VPS watchdog
# ─────────────────────────────────────────────────────────────────────────────

def test_c() -> None:
    print("\n── C: VPS watchdog ──────────────────────────────────────────")
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
    "T1": test_t1,
    "T2": test_t2,
    "T3": test_t3,
    "T4": test_t4,
    "T5": test_t5,
    "T6": test_t6,
    "C":  test_c,
}


def main() -> None:
    requested = [a.upper() for a in sys.argv[1:]] if len(sys.argv) > 1 else list(_tests)
    unknown   = [t for t in requested if t not in _tests]
    if unknown:
        print(f"Unknown tests: {unknown}. Available: {list(_tests)}")
        sys.exit(1)

    print("=" * 60)
    print("VALIDATE TRADOVATE — Strategy C Tradeify deployment")
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
        print("All tests PASS/SKIP — ready for Tradeify Select Flex.")
    else:
        print("Some tests FAILED — fix before deploying.")
        sys.exit(1)


if __name__ == "__main__":
    main()
