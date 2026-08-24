"""
T3 — Cost gate (L11 binary TP/SL gate, L9 costs).

Pre-flight cost gate for binary TP/SL strategies:
  Gate condition: E[gross/trade] > 3 × cost/trade   (N-independent)

Where:
  cost/trade = COST_PER_CONTRACT + entry slippage already in pnl_pts
             = $14 RT (commission + exit slip)
  E[gross/trade] = avg_gross_usd per trade (before cost deduction)

Also computes:
  Annual turnover, cost drag annualized, gross/cost ratio.
  Reports if gate passes (ratio > 3.0).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[6]))

from data.cache import load_nq_1min, get_cached_or_fetch_fred
from Futures.research.active.nq_intraday.monti_orb.signal import monti_orb_signal
from Futures.research.active.nq_intraday.monti_orb.backtest import (
    POINT_VALUE, COST_PER_CONTRACT, daily_returns, sharpe_hac,
)

COST_ENTRY_SLIP_USD = 0.25 * POINT_VALUE  # already baked in pnl_pts
TOTAL_COST_PER_TRADE = COST_PER_CONTRACT   # $14 (entry slip already in pnl)


def run(trades=None) -> dict:
    print("=" * 60)
    print("T3 — Cost gate (binary TP/SL, L11b)")
    print("=" * 60)

    df = load_nq_1min()
    if trades is None:
        trades = monti_orb_signal(df)

    rf = get_cached_or_fetch_fred("DTB3", "2022-12-26", "2025-12-11")
    tl, dn = daily_returns(trades, sizing="fixed", n_contracts_fixed=1, rf_series=rf["dtb3"])

    if tl.empty:
        print("[T3] No trades — gate cannot be evaluated")
        return {"test": "T3", "gate_pass": False}

    n_trades = len(tl)
    n_years  = (tl.index.max() - tl.index.min()).days / 365.25
    trades_per_year = n_trades / n_years if n_years > 0 else np.nan

    # Gross per trade = pnl_pts × POINT_VALUE (before cost deduction)
    avg_gross_usd    = float(tl["gross_usd"].mean())
    avg_cost_per_trade = TOTAL_COST_PER_TRADE  # per contract, 1 contract

    ratio = avg_gross_usd / avg_cost_per_trade if avg_cost_per_trade > 0 else np.nan

    # Annual cost drag
    annual_cost_usd = trades_per_year * avg_cost_per_trade
    annual_cost_bps = (annual_cost_usd / 50_000.0) * 10_000  # basis points on $50K

    # Gross alpha rate
    annual_gross_usd = trades_per_year * avg_gross_usd

    print(f"\nN trades: {n_trades}  |  Period: {n_years:.2f} yr  |  {trades_per_year:.1f} trades/yr")
    print(f"\nCost model (per contract per trade):")
    print(f"  Entry slippage (in pnl_pts):  ${COST_ENTRY_SLIP_USD:.2f}  (0.25 pts, baked in)")
    print(f"  Commission RT:                $9.00")
    print(f"  Exit slip RT:                 $5.00  (0.25 pts)")
    print(f"  TOTAL per RT:                 ${TOTAL_COST_PER_TRADE + COST_ENTRY_SLIP_USD:.2f}")
    print(f"\nAvg gross USD/trade:   ${avg_gross_usd:>8.2f}")
    print(f"Avg cost USD/trade:    ${TOTAL_COST_PER_TRADE:>8.2f}  (excl. entry slip already in PnL)")
    print(f"Gross / cost ratio:    {ratio:.3f}  (gate: > 3.0)")
    print(f"\nAnnual cost drag:      ${annual_cost_usd:,.0f}  ({annual_cost_bps:.1f} bps on $50K)")
    print(f"Annual gross alpha:    ${annual_gross_usd:,.0f}")

    gate_pass = ratio >= 3.0
    if gate_pass:
        print("\n[T3] Cost gate PASS ✓  (ratio ≥ 3.0)")
    else:
        print(f"\n[T3] Cost gate FAIL ✗  (ratio {ratio:.2f} < 3.0)")
        print("     Edge insufficient vs transaction costs at this WR/PF")

    result = {
        "test":              "T3",
        "n_trades":          n_trades,
        "trades_per_year":   round(float(trades_per_year), 1),
        "avg_gross_usd":     round(float(avg_gross_usd), 2),
        "cost_per_trade":    TOTAL_COST_PER_TRADE,
        "gross_cost_ratio":  round(float(ratio), 3) if np.isfinite(ratio) else None,
        "annual_cost_usd":   round(float(annual_cost_usd), 0),
        "annual_cost_bps":   round(float(annual_cost_bps), 1),
        "gate_pass":         bool(gate_pass),
    }
    return result


if __name__ == "__main__":
    run()
