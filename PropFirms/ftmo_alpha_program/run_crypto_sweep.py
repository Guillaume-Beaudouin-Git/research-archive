"""
run_crypto_sweep.py — systematic cross-sectional crypto screen (minimal gate)
==============================================================================
Tests the cross-sectional families from the strategy list on the 174-token 8h panel,
dollar-neutral long-short, net of crypto cost, IS vs untouched hold-out 2025-2026.
Minimal gate only: causal + net cost + net-positive OOS. No barrier, no DSR hard-fail.
Outputs results/crypto_sweep.csv (master table, appended per family).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from strategy.crypto_xs import (load_panel, xs_backtest,                # noqa: E402
                                sig_momentum, sig_reversal, sig_carry, sig_funding_mom)

RES = HERE / "results"


def main() -> int:
    print("=" * 90)
    print("CRYPTO SWEEP — cross-sectional batch (minimal gate: causal, net cost, OOS-positive)")
    print("=" * 90)
    C, F = load_panel(min_bars=300)
    print(f"universe: {C.shape[1]} tokens, {C.index.min().date()} → {C.index.max().date()}, "
          f"hold-out from 2025-01-01\n")

    rows = []
    def run(name, family, signal, rebal, q=0.2, fund=False):
        r = xs_backtest(C, F, signal, rebal_bars=rebal, q=q, include_funding=fund)
        passed = r.metrics_oos["sharpe"] > 0 and r.metrics_is["sharpe"] > 0
        rows.append({"strategy": name, "family": family,
                     "IS_sharpe": round(r.metrics_is["sharpe"], 2),
                     "OOS_sharpe": round(r.metrics_oos["sharpe"], 2),
                     "OOS_annret%": round(r.metrics_oos["ann_ret"] * 100, 1),
                     "turnover/yr": round(r.turnover_yr, 1),
                     "min_gate": "PASS" if passed else "fail"})
        return r

    # ── (1) cross-sectional momentum — multiple lookbacks (bars: 3=1d, 9=3d, 21=7d, 63=21d) ──
    for k, lbl in [(3, "1d"), (9, "3d"), (21, "7d"), (63, "21d")]:
        run(f"CS-momentum {lbl}", "1 directional/XS", sig_momentum(C, k), rebal=3)
    # ── (1) short-term reversal (fast) ──
    for k, lbl in [(1, "8h"), (3, "1d")]:
        run(f"CS-reversal {lbl}", "1 directional/XS", sig_reversal(C, k), rebal=max(1, k))
    # ── (2) funding carry (long low / short high funding, incl funding accrual) ──
    for reb, lbl in [(1, "8h"), (3, "1d")]:
        run(f"Funding-carry {lbl}", "2 carry", sig_carry(F), rebal=reb, fund=True)
    # ── (2) funding momentum ──
    for k, lbl in [(3, "1d"), (9, "3d")]:
        run(f"Funding-mom {lbl}", "2 carry", sig_funding_mom(F, k), rebal=3, fund=True)

    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    RES.mkdir(exist_ok=True)
    df.to_csv(RES / "crypto_sweep.csv", index=False)
    npass = (df["min_gate"] == "PASS").sum()
    print(f"\n{npass}/{len(df)} configs pass the minimal gate (net-positive IS AND hold-out).")
    best = df.loc[df["OOS_sharpe"].idxmax()]
    print(f"Best hold-out: {best['strategy']} — OOS Sharpe {best['OOS_sharpe']}, "
          f"ann {best['OOS_annret%']}%/yr net, turnover {best['turnover/yr']}/yr.")
    print(f"\n  → results/crypto_sweep.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
