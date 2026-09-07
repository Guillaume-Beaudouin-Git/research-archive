"""
Real FTMO swap table, measured 2026-09-02 (given by mandate, MT5 points
converted to bps/night; point = 0.001 on JPY crosses, 0.00001 otherwise).

⚠ Calibration caveat (checked 2026-09-02, this session): the only swap
data available on the VPS (`data/ftmo_portfolio/swaps_billed_live.csv`,
read-only) covers US100.cash / GER40.cash — index CFDs. The live funded
book has NEVER held an FX leg, so there is NO real billed-swap series to
calibrate the point->bps conversion against for any of these 9 pairs.
The absolute scale below is taken at face value from the mandate; it is
cross-checked instead against FRED theoretical differentials (structural
consistency, see code/compression.py) — that check is independent of the
point/bps conversion and confirms sign + order of magnitude (structural
facts, not the calibration).
"""
from __future__ import annotations

# bps per night, FTMO, measured 2026-09-02
SWAP_TABLE = {
    #            long_bps   short_bps   markup_rt_bps  paying_side
    "AUDJPY": (0.393, -1.428, -1.035, "long"),
    "GBPJPY": (0.291, -1.356, -1.066, "long"),
    "USDJPY": (0.156, -1.266, -1.111, "long"),
    "USDCHF": (0.219, -1.610, -1.391, "long"),
    "USDCAD": (0.050, -0.788, -0.738, "long"),
    "EURUSD": (-0.741, 0.030, -0.711, "short"),
    "AUDUSD": (-0.489, -0.888, -1.377, None),
    "GBPUSD": (-0.341, -0.436, -0.777, None),
    "NZDUSD": (-0.613, -0.128, -0.742, None),
}


def swap_bps_per_night(pair: str, position: int) -> float:
    """position: +1 long, -1 short. Returns bps of notional per night (can be negative)."""
    long_bps, short_bps, _, _ = SWAP_TABLE[pair]
    return long_bps if position > 0 else short_bps


def markup_rt_bps(pair: str) -> float:
    return SWAP_TABLE[pair][2]


def paying_side(pair: str) -> str | None:
    return SWAP_TABLE[pair][3]
