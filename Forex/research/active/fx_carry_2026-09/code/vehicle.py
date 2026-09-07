"""
Part E — vehicle comparison, costs as given/measured (no re-measurement
attempted here; sourced from dedale_broker_2026-08/RAPPORT_BROKER.md and
this session's mandate).

FTMO: 2.48 bps RT execution (repo-canonical retail CFD figure) + the
  real swap table in swaps.py (measured 2026-09-02).
Eightcap Raw: 0.66-1.18 bps RT per pair, ESTIMATION (plancher publié +
  commission, dedale_broker RAPPORT_BROKER.md §3.2) — NOT a measured
  average (myfxbook blocked 403; own EURUSD measurement was 0.75 bps,
  8-16x the plancher, so treat the JPY-cross estimates as a floor too).
  Swap table: NOT FOUND for Eightcap (dedale_broker §1 — SPA JS, no
  static/PDF table extractable by read-only fetch). Cannot run the
  same swap-conditional backtest for Eightcap without fabricating a
  number — flagged, not invented.
IBKR: ~0.4-0.5 bps RT (published ECN spread + commission, dedale_broker
  §5) + $2/order minimum commission (L57: fixed-cost floor dominates on
  small notional). IBKR does not charge a "swap" — it accrues/charges
  interest on the financed FX position at a market benchmark ± spread
  (published mechanism, not a broker-set point) — structurally
  different from a CFD swap (L28), and NOT modeled here as a bps/night
  table (would require IBKR's published tiered-interest schedule, out
  of scope for this session — flagged as future work, not invented).
"""
from __future__ import annotations

STANDARD_LOT_USD = 100_000  # notional of 1.0 lot, FX convention


def ibkr_min_commission_bps(notional_usd: float, min_usd: float = 2.0, rate_bps: float = 0.2) -> float:
    """IBKR charges max(min_usd, rate_bps * notional) per ORDER (one leg).
    Round-trip = 2 orders. Returns effective RT bps of notional."""
    per_leg_usd = max(min_usd, notional_usd * rate_bps * 1e-4)
    return 2 * per_leg_usd / notional_usd * 1e4  # bps


def print_table():
    print(f"{'notional_usd':>14} {'lot_equiv':>10} {'IBKR_RT_bps':>12}")
    for notional in [1_000, 5_000, 10_000, 25_000, 50_000, 100_000, 500_000]:
        bps = ibkr_min_commission_bps(notional)
        print(f"{notional:>14,.0f} {notional/STANDARD_LOT_USD:>10.3f} {bps:>12.3f}")


if __name__ == "__main__":
    print_table()
