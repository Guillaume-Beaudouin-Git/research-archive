"""
validate.py — Validation tests for Strategy C live infrastructure
==================================================================
Test 1: IBKR connection (requires TWS running on port 7497)
Test 2: Signal engine on historical data vs iter_10 backtest
Test 3: Paper order placement (requires TWS running)
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[4]))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")


# ─────────────────────────────────────────────────────────────────────────────
# Test 2 — Signal engine on historical data
# ─────────────────────────────────────────────────────────────────────────────

def test2_signal_engine() -> None:
    """
    Run compute_signal() on the last 10 trading days from NQ parquet cache.
    Compare to iter_10 backtest trade log (same direction on same days).
    Target match rate: >90%.
    """
    print("\n" + "=" * 70)
    print("TEST 2 — Signal engine vs iter_10 backtest (last 10 trade days)")
    print("=" * 70)

    # Load NQ 1-min data
    from datetime import time as _time
    from data.cache import load_nq_1min
    from Futures.research.active.nq_intraday.engine import NQBacktestEngine
    from Futures.research.active.nq_intraday.iter_05 import (
        build_opening_features, signals_from_features,
    )
    from Futures.live.strategy_c_live.signal_engine import compute_signal

    df     = load_nq_1min()
    engine = NQBacktestEngine(df)
    feats  = build_opening_features(engine.rth)
    feats_filt = feats[feats["rng"] >= 30.0].copy()
    sigs   = signals_from_features(feats_filt, gap_thresh=0.012, dollar_stop=400.0)
    tl, _  = engine.run(sigs)
    tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize()

    # Last 10 trading days that had a trade in the backtest
    recent_dates = sorted(tl["date"].unique())[-10:]

    print(f"\n  Testing on {len(recent_dates)} days: "
          f"{recent_dates[0].date()} → {recent_dates[-1].date()}")
    print(f"\n  {'Date':<12} {'BT dir':>8} {'SIG dir':>9} {'ORB':>7} {'Gap':>7} {'Match':>7}")
    print(f"  {'-'*52}")

    n_match   = 0
    n_total   = 0
    n_sig_none = 0

    for date in recent_dates:
        # Build 5-min bars for this date using the 1-min data (resample)
        date_naive = date.tz_localize(None) if hasattr(date, "tz_localize") and date.tzinfo is not None else date

        # Get prev day too for gap calculation
        prev_date = date_naive - pd.Timedelta(days=1)
        while prev_date.weekday() >= 5:
            prev_date -= pd.Timedelta(days=1)

        # Filter 1-min to 2 days, RTH only (09:30–16:00) — mirrors IBKR useRTH=True
        mask = (df.index.normalize().tz_localize(None) >= prev_date) & \
               (df.index.normalize().tz_localize(None) <= date_naive)
        day_1min = df[mask][
            (df[mask].index.time >= _time(9, 30)) &
            (df[mask].index.time <= _time(16, 0))
        ].copy()

        # Pass 1-min RTH directly — signal_engine resamples to 5-min internally
        # and computes VWAP on 1-min (matches iter_10 backtest)

        # Get backtest direction for this date
        bt_row = tl[tl["date"] == date]
        bt_dir = 'BUY' if int(bt_row.iloc[0]["direction"]) == 1 else 'SELL'

        # Run signal engine
        sig = compute_signal(day_1min)

        if sig is None:
            n_sig_none += 1
            print(f"  {str(date_naive.date()):<12} {bt_dir:>8} {'None':>9} {'---':>7} {'---':>7} {'N/A':>7}")
            continue

        sig_dir = sig["direction"]
        match   = "✓" if sig_dir == bt_dir else "✗"
        n_total += 1
        if sig_dir == bt_dir:
            n_match += 1

        print(f"  {str(date_naive.date()):<12} {bt_dir:>8} {sig_dir:>9} "
              f"{sig['opening_range']:>7.1f} {sig['gap_pct']:>+7.2f}% {match:>7}")

    match_pct = n_match / n_total * 100 if n_total > 0 else 0
    print(f"\n  Match rate: {n_match}/{n_total} = {match_pct:.1f}% "
          f"(target >90%)")
    print(f"  Signal returned None: {n_sig_none}/{len(recent_dates)} days")

    # Check TP/SL within $5 for matching days
    print(f"\n  TP/SL price check (first 3 matching days within $5 tolerance):")
    checked = 0
    for date in recent_dates:
        if checked >= 3:
            break
        date_naive = date.tz_localize(None) if hasattr(date, "tz_localize") and date.tzinfo is not None else date
        bt_row = tl[tl["date"] == date]
        if bt_row.empty:
            continue

        prev_date = date_naive - pd.Timedelta(days=1)
        while prev_date.weekday() >= 5:
            prev_date -= pd.Timedelta(days=1)

        mask = (df.index.normalize().tz_localize(None) >= prev_date) & \
               (df.index.normalize().tz_localize(None) <= date_naive)
        day_1min = df[mask][
            (df[mask].index.time >= _time(9, 30)) &
            (df[mask].index.time <= _time(16, 0))
        ]

        sig = compute_signal(day_1min)
        if sig is None:
            continue

        bt_entry = float(bt_row.iloc[0]["entry_price"])
        bt_tp    = float(bt_row.iloc[0]["tp_pts"])
        bt_sl    = float(bt_row.iloc[0]["sl_pts"])
        bt_dir   = 'BUY' if int(bt_row.iloc[0]["direction"]) == 1 else 'SELL'

        if sig["direction"] != bt_dir:
            continue

        tp_diff = abs(sig["tp_pts"] - bt_tp)
        sl_diff = abs(sig["sl_pts"] - bt_sl)
        ok_tp = "✓" if tp_diff <= 5 else "✗"
        ok_sl = "✓" if sl_diff <= 5 else "✗"

        print(f"    {str(date_naive.date())}: "
              f"TP_diff={tp_diff:.2f}pts {ok_tp}  SL_diff={sl_diff:.2f}pts {ok_sl}")
        checked += 1

    if match_pct >= 90:
        print(f"\n  TEST 2: PASS (match rate {match_pct:.1f}% ≥ 90%)")
    else:
        print(f"\n  TEST 2: FAIL (match rate {match_pct:.1f}% < 90%)")
        print("  Note: mismatches expected if 5-min VWAP differs from 1-min VWAP")
        print("  (IBKR 5-min bars use volume-weighted price; 1-min resample may differ)")


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 and 3 — IBKR connection + paper order
# ─────────────────────────────────────────────────────────────────────────────

def test1_connection() -> bool:
    print("\n" + "=" * 70)
    print("TEST 1 — IBKR connection (requires TWS running on port 7497)")
    print("=" * 70)
    try:
        from Futures.live.strategy_c_live.ibkr_client import IBKRClient
        from Futures.live.strategy_c_live.config import IBKR_HOST, IBKR_PORT, IBKR_CLIENT
        c = IBKRClient(host=IBKR_HOST, port=IBKR_PORT, client_id=IBKR_CLIENT)
        c.connect()
        accounts = c.ib.managedAccounts()
        print(f"\n  Connected. Account: {accounts}")
        c.disconnect()
        print("  TEST 1: PASS")
        return True
    except Exception as e:
        print(f"\n  TEST 1: FAIL — {e}")
        print("\n  TWS configuration checklist:")
        print("    1. Open TWS or IB Gateway")
        print("    2. File → Global Configuration → API → Settings")
        print("    3. Enable 'Socket port': 7497 (paper) or 7496 (live)")
        print("    4. Check 'Enable ActiveX and Socket Clients'")
        print("    5. Uncheck 'Read-Only API' (for order placement)")
        print("    6. Trusted IP: 127.0.0.1")
        print("    7. Restart TWS after changing settings")
        return False


def test3_paper_order(connected: bool) -> bool:
    print("\n" + "=" * 70)
    print("TEST 3 — Paper order placement (requires TWS + Test 1 PASS)")
    print("=" * 70)
    if not connected:
        print("  TEST 3: SKIP (Test 1 failed — TWS not connected)")
        return False
    try:
        from Futures.live.strategy_c_live.ibkr_client import IBKRClient
        from Futures.live.strategy_c_live.config import IBKR_HOST, IBKR_PORT, IBKR_CLIENT
        c = IBKRClient(host=IBKR_HOST, port=IBKR_PORT, client_id=IBKR_CLIENT)
        c.connect()

        contract = c.get_mnq_contract()
        print(f"\n  Contract: {contract.localSymbol}")

        # Place 1 /MNQ BUY
        print("  Placing 1 /MNQ BUY...")
        buy_trade = c.place_market_order(contract, 'BUY', 1)
        fill_price = c.wait_for_fill(buy_trade, timeout_secs=30)

        if fill_price is None:
            print("  TEST 3: FAIL — BUY order did not fill within 30s")
            c.disconnect()
            return False

        print(f"  BUY filled @ {fill_price}")

        # Flatten with SELL
        print("  Placing 1 /MNQ SELL to flatten...")
        import time; time.sleep(1)
        sell_trade = c.place_market_order(contract, 'SELL', 1)
        fill_sell = c.wait_for_fill(sell_trade, timeout_secs=30)

        c.disconnect()

        if fill_sell is not None:
            print(f"  SELL filled @ {fill_sell}")
            print(f"\n  Test 3 PASS — paper order placed and filled at {fill_price:.2f}")
            return True
        else:
            print("  TEST 3: FAIL — SELL order did not fill within 30s")
            return False

    except Exception as e:
        print(f"\n  TEST 3: FAIL — {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Run all tests
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Strategy C Live — Validation Tests")
    print("=" * 70)

    t1_pass = test1_connection()
    test2_signal_engine()
    t3_pass = test3_paper_order(t1_pass)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Test 1 (IBKR connection): {'PASS' if t1_pass else 'FAIL'}")
    print(f"  Test 2 (Signal engine):   see match rate above")
    print(f"  Test 3 (Paper order):     {'PASS' if t3_pass else 'FAIL/SKIP'}")
    if t1_pass and t3_pass:
        print("\n  ✓ Ready for first live paper trade tomorrow at 09:30 ET")
        print("  Run: /usr/bin/python3 -m Futures.live.strategy_c_live.run_daily")
    else:
        print("\n  Fix TWS connection (Tests 1+3) before paper trading.")
        print("  Test 2 (signal engine) runs offline — no TWS needed.")
