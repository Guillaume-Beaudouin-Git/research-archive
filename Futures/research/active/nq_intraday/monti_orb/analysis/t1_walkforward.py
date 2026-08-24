"""
T1 — Walk-forward 5 folds (baseline 1 NQ contract).

Expanding train/test: n_folds=5, approx 60/40 split per fold.
Reports Sharpe distribution, hit rate (folds with positive Sharpe), worst fold.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[6]))

from data.cache import load_nq_1min, get_cached_or_fetch_fred
from Futures.research.active.nq_intraday.monti_orb.signal import monti_orb_signal
from Futures.research.active.nq_intraday.monti_orb.backtest import (
    daily_returns, walk_forward, sharpe_hac,
)


def run(trades=None) -> dict:
    print("=" * 60)
    print("T1 — Walk-forward (5 folds, expanding, 1 contract fixed)")
    print("=" * 60)

    df = load_nq_1min()
    if trades is None:
        trades = monti_orb_signal(df)

    rf = get_cached_or_fetch_fred("DTB3", "2022-12-26", "2025-12-11")

    folds = walk_forward(
        trades, df,
        n_folds=5,
        sizing="fixed",
        n_contracts_fixed=1,
        rf_series=rf["dtb3"],
    )

    if not folds:
        print("[T1] No fold results — insufficient data")
        return {"test": "T1", "folds": [], "wf_pass_rate": 0.0}

    print(f"\n{'Fold':>4}  {'Start':>10}  {'End':>10}  {'N':>5}  {'WR':>6}  {'Sharpe':>8}  {'Net $':>8}")
    print("-" * 60)
    for f in folds:
        print(
            f"  {f['fold']:>2}  {f['test_start']:>10}  {f['test_end']:>10}  "
            f"{f['n_trades']:>5}  {f['win_rate']:.1%}  "
            f"{f['sharpe_hac']:>8.3f}  ${f['total_net_usd']:>8,.0f}"
        )

    sharpes = [f["sharpe_hac"] for f in folds if f["sharpe_hac"] is not None]
    n_pos   = sum(1 for s in sharpes if s > 0)
    wf_rate = n_pos / len(folds) if folds else 0.0

    print(f"\nFold Sharpes: {[round(s, 3) for s in sharpes]}")
    print(f"Positive folds: {n_pos}/{len(folds)} = {wf_rate:.1%}")
    print(f"Worst fold Sharpe: {min(sharpes):.3f}")
    print(f"Mean fold Sharpe: {np.mean(sharpes):.3f}")
    print(f"Std fold Sharpe:  {np.std(sharpes):.3f}")

    # WF gate: >50% folds positive = RESEARCH_PASS threshold
    if wf_rate >= 0.50:
        print("[T1] WF gate PASS (≥50% positive folds)")
    else:
        print("[T1] WF gate FAIL")

    result = {
        "test":         "T1",
        "folds":        folds,
        "wf_pass_rate": round(wf_rate, 4),
        "mean_sharpe":  round(float(np.mean(sharpes)), 4) if sharpes else None,
        "worst_sharpe": round(float(min(sharpes)), 4) if sharpes else None,
        "n_positive":   int(n_pos),
        "n_folds":      len(folds),
        "wf_gate_pass": wf_rate >= 0.50,
    }
    return result


if __name__ == "__main__":
    run()
