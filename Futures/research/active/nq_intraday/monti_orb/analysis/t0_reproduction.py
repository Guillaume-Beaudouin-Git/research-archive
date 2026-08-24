"""
T0 — Reproduction baseline Monti.

Fixed 1 NQ contract, no extra filters, full dataset 2022-12-26 to 2025-12-11.
Reference: Monti video (2021-today): 846 trades, WR 58%, PF 1.33.
Dataset covers ~3 years vs Monti's ~4-5 years → expect ~508-635 trades (prorated).
Tolerance: ≤15% deviation on trade count and WR before declaring an implementation bug.

Outputs: prints metrics + writes t0_result to caller's result dict.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[6]))

from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.monti_orb.signal import monti_orb_signal
from Futures.research.active.nq_intraday.monti_orb.backtest import (
    daily_returns, compute_metrics,
)


def run() -> dict:
    print("=" * 60)
    print("T0 — Baseline reproduction (1 NQ contract, no filter)")
    print("=" * 60)

    df = load_nq_1min()
    trades = monti_orb_signal(df)

    n_signal_days = int((trades["exit_reason"] != "no_signal")
                        .sum() - (trades["exit_reason"] == "insufficient_orb").sum())
    n_actual = int((~trades["exit_reason"].isin(["no_signal", "insufficient_orb"])).sum())
    print(f"Total days in dataset: {len(trades)}")
    print(f"Trades fired: {n_actual}")

    from data.cache import get_cached_or_fetch_fred
    rf = get_cached_or_fetch_fred("DTB3", "2022-12-26", "2025-12-11")

    tl, dn = daily_returns(trades, sizing="fixed", n_contracts_fixed=1, rf_series=rf["dtb3"])
    m = compute_metrics(tl, dn)

    # Exit distribution
    exit_counts = trades["exit_reason"].value_counts().to_dict()

    print(f"\nTrades: {m.get('n_trades', 0)}")
    print(f"Win rate: {m.get('win_rate', 0):.1%}  (Monti ref: 58%)")
    print(f"Profit factor: {m.get('profit_factor', 0):.3f}  (Monti ref: 1.33)")
    print(f"Total net USD: ${m.get('total_net_usd', 0):,.0f}")
    print(f"Sharpe HAC: {m.get('sharpe_hac', None)}")
    print(f"Max DD: {m.get('max_dd_pct', 0):.1%}")
    print(f"Exit breakdown: {exit_counts}")

    # Deviation check
    n_ref_prorated = 846 * (3.0 / 4.5)  # ~564 for 3 years
    wr_ref = 0.58
    n_dev = abs(m.get("n_trades", 0) - n_ref_prorated) / n_ref_prorated
    wr_dev = abs(m.get("win_rate", 0) - wr_ref)

    bug_flag = False
    if n_dev > 0.15:
        print(f"\n*** WARNING: trade count deviation {n_dev:.1%} > 15% threshold ***")
        bug_flag = True
    if wr_dev > 0.08:
        print(f"*** WARNING: WR deviation {wr_dev:.2%} — check implementation ***")
        bug_flag = True

    if not bug_flag:
        print("\n[T0] Reproduction within tolerance ✓")
    else:
        print("\n[T0] REPRODUCTION DIVERGENCE — debug before proceeding")

    result = {
        "test": "T0",
        "n_trades": m.get("n_trades"),
        "n_ref_prorated": round(n_ref_prorated, 0),
        "win_rate": m.get("win_rate"),
        "profit_factor": m.get("profit_factor"),
        "sharpe_hac": m.get("sharpe_hac"),
        "max_dd_pct": m.get("max_dd_pct"),
        "total_net_usd": m.get("total_net_usd"),
        "exit_counts": exit_counts,
        "reproduction_ok": not bug_flag,
    }
    return result


if __name__ == "__main__":
    run()
