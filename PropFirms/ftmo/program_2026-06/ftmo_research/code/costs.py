"""
costs.py — Realistic FTMO transaction-cost model (in pips, round-trip).

Calibration
-----------
EURUSD broker spread distribution (from the MT5 export's realtime `spread`
column, ~2.37M one-minute observations):
    median  = 0.2 pip  (liquid hours, raw-spread account)
    p90     ~ 5.0 pip  (rollover / thin-liquidity spikes)
    hour 00 ~ 2.2 pip  (daily rollover)

Round-trip cost = spread + commission + slippage:
    spread     : 0.2-1.0 pip (we use a conservative liquid-hour blend)
    commission : FTMO ~ $3 / lot / side -> $6 RT per std lot = 0.6 pip
    slippage   : ~0.2 pip RT (stops/market orders)

We therefore use conservative *round-trip* costs:
    EURUSD = 1.0 pip      GBPUSD = 1.5 pip
and stress-test everything at 2x.
"""
from __future__ import annotations

PIP = 1e4  # for 5-digit majors (EURUSD, GBPUSD): 1 pip = 1e-4 price units

ROUND_TRIP_PIPS = {"EURUSD": 1.0, "GBPUSD": 1.5}


def round_trip_cost(symbol: str, stress: float = 1.0) -> float:
    """Round-trip cost in pips. `stress`=2.0 doubles costs for robustness tests."""
    return ROUND_TRIP_PIPS[symbol] * stress
