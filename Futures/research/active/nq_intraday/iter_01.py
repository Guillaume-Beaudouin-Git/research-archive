"""
iter_01.py — Opening Range Momentum (baseline)
================================================
HYPOTHESIS: Direction of first 15 min of RTH (09:30–09:45) predicts
next 60-90 min. Institutional order flow at the open is directional.

Variants:
  1a: TP=1.5R, SL=0.5R  (asymmetric, let winners run)
  1b: TP=1.0R, SL=0.5R  (tighter TP)
  1c: TP=2.0R, SL=1.0R  (wider 2:1 RR)

Entry  : 09:46 bar open (first bar after 09:45 signal)
Time stop: 12:30 ET
Max 1 trade per day
R = |close_09:45 - open_09:30|  (opening range)
n_tests: 85 → 88
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd
import numpy as np

# project imports
sys.path.insert(0, str(Path(__file__).parents[4]))
from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import (
    NQBacktestEngine, append_result, load_results, print_comparison_table, RESULTS_PATH
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

N_TESTS_START = 85

VARIANTS = {
    "1a": {"tp_mult": 1.5, "sl_mult": 0.5},
    "1b": {"tp_mult": 1.0, "sl_mult": 0.5},
    "1c": {"tp_mult": 2.0, "sl_mult": 1.0},
}


# ---------------------------------------------------------------------------
# Signal generation
# ---------------------------------------------------------------------------

def build_signals(df_1min: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    Generate opening momentum signals.
    Returns DataFrame indexed by signal timestamp (09:45 bar close),
    with columns: direction, tp_points, sl_points, exit_time.
    """
    tp_mult = params["tp_mult"]
    sl_mult = params["sl_mult"]

    import datetime
    t_0930 = datetime.time(9, 30)
    t_0945 = datetime.time(9, 45)
    t_1230 = datetime.time(12, 30)

    records = []
    dates = df_1min.index.normalize().unique()

    for date in dates:
        day = df_1min[df_1min.index.normalize() == date]
        # Opening window: 09:30-09:45 (inclusive)
        opening = day[
            (day.index.time >= t_0930) &
            (day.index.time <= t_0945)
        ]
        if len(opening) < 2:
            continue

        open_price  = float(opening.iloc[0]["open"])
        close_price = float(opening.iloc[-1]["close"])
        rng         = abs(close_price - open_price)

        if rng < 1.0:         # min 1-pt opening range to avoid flat opens
            continue

        direction = 1 if close_price > open_price else -1

        # Signal fires at 09:45 bar close
        sig_ts = opening.index[-1]

        # Exit time: 12:30 on the same day
        exit_time = pd.Timestamp(
            date.year, date.month, date.day,
            t_1230.hour, t_1230.minute, 0,
            tzinfo=sig_ts.tzinfo
        )

        records.append({
            "signal_ts": sig_ts,
            "direction": direction,
            "tp_points": rng * tp_mult,
            "sl_points": rng * sl_mult,
            "exit_time": exit_time,
        })

    if not records:
        return pd.DataFrame()
    sigs = pd.DataFrame(records).set_index("signal_ts")
    return sigs


# ---------------------------------------------------------------------------
# Walk-forward wrapper
# ---------------------------------------------------------------------------

def signal_fn(df_window: pd.DataFrame, params: dict) -> pd.DataFrame:
    return build_signals(df_window, params)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=== Iter 01 — Opening Range Momentum ===")

    df = load_nq_1min()
    engine = NQBacktestEngine(df)

    best_sharpe = -np.inf
    best_variant = None
    n_test = N_TESTS_START

    for var_id, params in VARIANTS.items():
        n_test += 1
        log.info(f"--- Variant {var_id}: TP={params['tp_mult']}R  SL={params['sl_mult']}R ---")

        signals = build_signals(engine.rth, params)
        log.info(f"  Signals generated: {len(signals)}")

        trade_log, met = engine.run(signals)
        boot = engine.bootstrap_ev(trade_log)
        wf   = engine.walk_forward(signal_fn, params, train_months=12, test_months=6)

        # Verdict
        sh  = met.get("sharpe_daily_hac") or 0
        pf  = met.get("profit_factor")    or 0
        if sh >= 1.0 and pf >= 1.20:
            verdict = "STRONG"
        elif sh >= 0.5 and pf >= 1.10:
            verdict = "IMPROVE"
        elif sh >= 0.0 and pf >= 0.95:
            verdict = "WEAK"
        else:
            verdict = "SKIP"

        result = {
            "iteration":        f"iter_{var_id}",
            "n_tests":          n_test,
            "description":      f"Opening momentum TP={params['tp_mult']}R SL={params['sl_mult']}R",
            **met,
            **boot,
            "wf_pct_positive":  wf.get("wf_pct_positive"),
            "wf_n_windows":     wf.get("n_windows"),
            "verdict":          verdict,
        }
        append_result(result)

        print(f"\n  [iter_{var_id}] TP={params['tp_mult']}R SL={params['sl_mult']}R")
        print(f"    Trades:  {met.get('n_trades',0)}  |  WR: {met.get('win_rate',0)*100:.1f}%")
        print(f"    AvgTrd:  ${met.get('avg_trade_usd',0):.1f}  |  PF: {met.get('profit_factor') or 0:.3f}")
        print(f"    Sharpe:  {sh:.3f}  |  MaxDD: {met.get('max_dd_pct',0)*100:.1f}%")
        print(f"    WF%pos:  {wf.get('wf_pct_positive','?')}%  ({wf.get('n_windows',0)} windows)")
        print(f"    P(EV≤0): {boot.get('p_ev_zero','?')}  |  95%CI: [{boot.get('ci_low','?')}, {boot.get('ci_high','?')}]")
        print(f"    Verdict: {verdict}")

        if sh > best_sharpe:
            best_sharpe  = sh
            best_variant = var_id

    print(f"\n--- Iter 01 best variant: iter_{best_variant} (Sharpe={best_sharpe:.3f}) ---")

    # Stopping rule check
    results = load_results()
    iter_results = [r for r in results if r.get("iteration","").startswith("iter_1")]
    best_pf = max((r.get("profit_factor") or 0) for r in iter_results) if iter_results else 0
    if best_sharpe < 0 and best_pf < 0.95:
        print("\nSTOPPING RULE: Sharpe < 0 AND PF < 0.95 across all iter_01 variants.")
        print("Opening momentum has no signal on NQ in this sample. Proceeding to iter_03 (breakout).")
    else:
        print("\nProceed to iter_02 (VWAP filter on best variant).")

    print_comparison_table(results)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("iter_01 failed")
        sys.exit(1)
