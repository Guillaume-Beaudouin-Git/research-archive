"""Cost / swap / order-type model — catalogue (funnel) vs measured (repaired).

Defect 3 (costs), defect 5 (swaps), defect 6 (order type) live here.
The FX line is deliberately NOT repaired: the cache spread column is zero-inflated
on FX (EURUSD 33.2% of days at spread 0), so `FX_major = 1.5` is not demonstrated
too severe and could be optimistic (COST_AUDIT.md §2b, pre-registration §1.1).
"""
from __future__ import annotations

# --- Defect 3: round-trip cost, bps -----------------------------------------

COST_CATALOG = {          # top10_test/framework.py:29
    "FX_major": 1.5, "FX_cross": 4.0,
    "Index_CFD_major": 1.5, "Index_CFD_minor": 2.5,
    "Crypto_CFD": 12.0, "Metals_CFD_gold": 3.5, "Commodity_CFD": 8.0,
}

COST_MEASURED = {         # COST_AUDIT.md §3 (gold) and §5/§6 (indices)
    "FX_major": 1.5,      # UNCHANGED — see module docstring
    "FX_cross": 4.0,      # UNCHANGED — no measurement
    "Index_CFD_major": 0.9,
    "Index_CFD_minor": 0.9,
    "Crypto_CFD": 12.0,   # unused by the 142 specs
    "Metals_CFD_gold": 1.84,
    "Commodity_CFD": 8.0,  # UNCHANGED — USOIL/UKOIL never measured
}
COST_MEASURED_P95 = dict(COST_MEASURED, **{"Index_CFD_major": 2.3,
                                           "Index_CFD_minor": 2.3})

# --- Defect 5: overnight financing, bps per night, SIGNED --------------------

SWAP_CATALOG = {          # top10_test/framework.py:42, side-blind
    "FX_major": -1.1, "FX_cross": -1.3,
    "Index_CFD_major": -3.1, "Index_CFD_minor": -3.1,
    "Metals_CFD_gold": -2.9, "Commodity_CFD": -3.0, "Crypto_CFD": -3.5,
}

# spec_v22.yaml : cost_anchors.swap_bps_per_night_measured (FTMO specs 2026-06-10,
# reconstructed to the cent on 4/4 charges the night 10->11/06).
SWAP_MEASURED_BY_SYMBOL = {
    "US100": (-2.126, +0.092),      # (long, short)
    "GER40": (-1.564, -0.193),
    "XAUUSD": (-1.518, -0.336),
    "USDJPY": (+0.060, -1.267),
}
# US500 / US30 are not separately measured -> US100 anchor (same broker index family).
SWAP_MEASURED_PROXY = {"US500": "US100", "US30": "US100", "US2000": "US100"}

# --- Defect 6: cost by ORDER TYPE (measured 2026-08-13) ---------------------
# scheduled market/limit fill in a liquid session : ~0.0-0.1 bps beyond req_price (n=32)
# resting stop (ORB-style trigger)               : +2.169 bps                  (n=12)
SLIP_BY_ORDER_TYPE = {"scheduled_market": 0.0, "resting_stop": 2.169}


def rt_cost(asset_class: str, repaired: bool, order_type: str = "scheduled_market",
            typed_order: bool = False, p95: bool = False) -> float:
    table = (COST_MEASURED_P95 if (repaired and p95)
             else COST_MEASURED if repaired else COST_CATALOG)
    c = table[asset_class]
    if typed_order:
        c += 2.0 * SLIP_BY_ORDER_TYPE.get(order_type, 0.0)
    return c


def swap_night(asset_class: str, symbol: str, side: int, repaired: bool) -> float:
    """Signed bps per night for one leg held in direction `side`."""
    if not repaired:
        return SWAP_CATALOG.get(asset_class, -3.0)
    sym = SWAP_MEASURED_PROXY.get(symbol, symbol)
    if sym in SWAP_MEASURED_BY_SYMBOL:
        lo, sh = SWAP_MEASURED_BY_SYMBOL[sym]
        return lo if side > 0 else sh
    return SWAP_CATALOG.get(asset_class, -3.0)   # unmeasured -> unchanged
