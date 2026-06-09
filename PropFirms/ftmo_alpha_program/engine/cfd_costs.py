"""
cfd_costs.py — CFD dealer-spread + swap cost model (FTMO MT5 microstructure)
=============================================================================

Phase 0b of the roadmap. The white paper's central operating-environment finding
(§5.1) is that FTMO trades CFDs via MT5, not futures, so "the signal may transfer;
the cost model does not." Every backtest must be re-costed against CFD microstructure
(dealer spread + overnight swap), not exchange ticks + commission (L9).

This model is calibrated directly to the *realised* MT5 `spread` column in
data/panels/m5_indices/<SYMBOL>_M1.csv (spread quoted in MT5 points; point size =
10^-decimals of the price). Round-trip cost when entering and exiting at market is
~one full spread (half-spread crossing each side), plus optional commission and a
slippage/markup stress to respect retail-vs-feed skepticism (L19, L23b).

Intraday-flat strategies (the target profile, §5.1.2) pay *zero* swap — a structural
reason the barrier-optimal design and the cost-optimal design coincide.

Reconciliation against white-paper Table 3 is in `reconcile_table3()`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]          # .../Algo_claude
PANEL = REPO / "data" / "panels" / "m5_indices"

# Price decimals → point size = 10^-decimals (verified from the data).
DECIMALS = {"EURUSD": 5, "GBPUSD": 5, "USDJPY": 3,
            "US100": 2, "US500": 2, "US30": 2, "GER40": 2,
            "XAUUSD": 2, "US2000": 2, "BTCUSD": 2, "ETHUSD": 2}
# Pip size (FX convention); for indices/metals we report in "index points" / "$".
PIP_SIZE = {"EURUSD": 1e-4, "GBPUSD": 1e-4, "USDJPY": 1e-2}


def point_size(symbol: str) -> float:
    return 10.0 ** (-DECIMALS[symbol])


@dataclass
class CFDCostModel:
    """
    Round-trip cost in *return units* (fraction of notional) for a CFD trade.

      rt_cost_return = (effective_spread_price + slippage_price + commission_price) / price

    where effective_spread_price = spread_points * point_size * markup.

    Parameters
    ----------
    symbol            : instrument key (EURUSD, US100, ...).
    markup            : multiply the feed spread to approximate the FTMO dealer
                        markup over a raw feed (retail-vs-feed; L23b). 1.0 = use feed.
    slippage_points   : fixed adverse slippage per round trip, in MT5 points (L19).
    commission_rt     : round-trip commission in *price units* (0 for spread-only CFDs).
    swap_points_per_night : overnight financing in points (>0 = adverse). Intraday-flat → 0.
    """
    symbol: str
    markup: float = 1.0
    slippage_points: float = 0.0
    commission_rt: float = 0.0
    swap_points_per_night: float = 0.0

    @property
    def point(self) -> float:
        return point_size(self.symbol)

    def rt_cost_return(self, spread_points, price, nights_held: float = 0.0):
        """Round-trip cost as a fraction of notional. Accepts scalars or arrays."""
        spread_points = np.asarray(spread_points, dtype=float)
        price = np.asarray(price, dtype=float)
        eff_spread = spread_points * self.point * self.markup
        slip = self.slippage_points * self.point
        swap = nights_held * self.swap_points_per_night * self.point
        return (eff_spread + slip + self.commission_rt + swap) / price

    def rt_cost_price(self, spread_points, nights_held: float = 0.0):
        spread_points = np.asarray(spread_points, dtype=float)
        return (spread_points * self.point * self.markup
                + self.slippage_points * self.point
                + self.commission_rt
                + nights_held * self.swap_points_per_night * self.point)


def load_spread_series(symbol: str, tail_rows: int | None = 400_000) -> pd.DataFrame:
    """Load (timestamp, close, spread) for an MT5 panel symbol; recent regime by default."""
    p = PANEL / f"{symbol}_M1.csv"
    if tail_rows:
        n = sum(1 for _ in open(p)) - 1
        df = pd.read_csv(p, skiprows=range(1, max(1, n - tail_rows)))
    else:
        df = pd.read_csv(p)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S",
                                         errors="coerce")
    return df[["timestamp_utc", "close", "spread"]].dropna()


def reconcile_table3(symbols=("EURUSD", "US500", "US100", "XAUUSD", "GER40", "US30")) -> dict:
    """
    Reproduce white-paper Table 3 indicative RT costs from the realised feed and
    show them in the paper's native units (pips / index points / $).
    """
    rows = {}
    for s in symbols:
        df = load_spread_series(s)
        sp = df["spread"][df["spread"] > 0]
        med_pts = float(sp.median())
        price = float(df["close"].median())
        pt = point_size(s)
        rt_price = med_pts * pt                       # round-trip cost in price units
        if s in PIP_SIZE:
            native = rt_price / PIP_SIZE[s]
            unit = "pip"
        elif s == "XAUUSD":
            native = rt_price
            unit = "$"
        else:
            native = rt_price                         # index points (point=0.01)
            unit = "idx_pts"
        rows[s] = {
            "median_spread_points": med_pts,
            "p95_spread_points": float(sp.quantile(0.95)),
            "median_price": price,
            "rt_cost_price": rt_price,
            "rt_cost_native": round(native, 4),
            "rt_cost_unit": unit,
            "rt_cost_bps_notional": round(rt_price / price * 1e4, 3),
        }
    return rows


if __name__ == "__main__":
    import json
    rec = reconcile_table3()
    print(f"{'Symbol':8s} {'med pts':>8s} {'p95 pts':>8s} {'RT cost':>14s} {'bps notional':>13s}")
    for s, r in rec.items():
        print(f"{s:8s} {r['median_spread_points']:>8.0f} {r['p95_spread_points']:>8.0f} "
              f"{r['rt_cost_native']:>9.3f} {r['rt_cost_unit']:<5s} "
              f"{r['rt_cost_bps_notional']:>12.3f}")
    print(json.dumps(rec, indent=2))
