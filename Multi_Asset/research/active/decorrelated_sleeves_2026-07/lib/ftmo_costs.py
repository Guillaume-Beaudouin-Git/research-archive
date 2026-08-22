"""FTMO real-cost model — decorrelated-sleeves study (2026-07).

Anchors are the MEASURED FTMO-Demo Standard specs read 2026-06-10 (source:
`data/ftmo_portfolio/v22/spec_v22.yaml::measured_specs`, validated 4/4 to the cent on the
10->11/06 triple night). Instruments not in the measured set (US500, US30, EURUSD, GBPUSD,
AUDUSD, NZDUSD, XAGUSD, crosses) use DOCUMENTED anchors extrapolated from the measured cluster
and the stat-arb deep-dive structural finding ("a market-neutral CFD pair pays ~2x broker
markup ~1.5 bps/night, benchmark cancels between legs"). Every anchor is explicit and stressable.

Cost components (all in bps of traded notional):
  1. round-trip transaction cost = quoted spread crossing + ACTIVE-FILL slippage (not passive).
     The brief mandates the aggressive-fill cost, so we pay the full spread + a slippage uplift.
  2. overnight/weekend SWAP, asymmetric by instrument & side, x3 on the triple-rollover weekday.

Excess-return note: for margined CFDs the broker charges financing on the *notional* via the swap,
which already embeds the benchmark rate. Subtracting a separate risk-free rate would double-count.
The swap IS the excess-return / carry adjustment here (documented, deliberate).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

# ---------------------------------------------------------------- asset classes
CLASS = {
    "US100": "INDEX", "US500": "INDEX", "US30": "INDEX", "GER40": "INDEX",
    "XAUUSD": "METAL", "XAGUSD": "METAL",
    "EURUSD": "FX", "GBPUSD": "FX", "AUDUSD": "FX", "NZDUSD": "FX",
    "USDJPY": "FX", "USDCHF": "FX", "USDCAD": "FX", "EURJPY": "FX",
    "AUDJPY": "FX", "EURGBP": "FX",
}

# ---------------------------------------------------------------- 1) transaction cost
# Round-trip (enter+exit) bps/leg = spread crossing + active-fill slippage.
# Base spread anchors match the deep-dive MT5 spread column (FX 0.9-1.2, indices 1.5, gold 2.0 RT).
SPREAD_RT_BPS = {"FX": 1.0, "INDEX": 1.5, "METAL": 2.0}
# Active-fill slippage uplift (market order crossing, not passive limit). Stressable.
SLIP_RT_BPS = {"FX": 0.4, "INDEX": 0.4, "METAL": 0.5}
# Commission RT bps (measured): FX ~0.5 (USDJPY), metals 0.14 (XAU), indices 0.
COMM_RT_BPS = {"FX": 0.5, "INDEX": 0.0, "METAL": 0.14}


def rt_cost_bps(sym: str, slip_mult: float = 1.0) -> float:
    """All-in round-trip cost (one full open+close) for one leg, bps of notional."""
    c = CLASS[sym]
    return SPREAD_RT_BPS[c] + slip_mult * SLIP_RT_BPS[c] + COMM_RT_BPS[c]


# ---------------------------------------------------------------- 2) swaps (bps/night, signed)
# MEASURED (FTMO Standard 2026-06-10). Negative = you PAY.
_SWAP_MEASURED = {
    "XAUUSD": {"long": -1.518, "short": -0.336},
    "USDJPY": {"long": +0.060, "short": -1.267},
    "US100":  {"long": -2.126, "short": +0.092},
    "GER40":  {"long": -1.564, "short": -0.193},
}
# DOCUMENTED anchors (extrapolated). Indices: markup-dominated, cluster on US100/GER40 measured.
# FX majors: modelled as rate-independent broker markup only (benchmark ~cancels in a USD-bloc
# pair); the era-dependent carry is second-order for pairs that already fail OOS cointegration.
_SWAP_ANCHOR = {
    "US500":  {"long": -1.80, "short": -0.05},
    "US30":   {"long": -1.70, "short": -0.10},
    "XAGUSD": {"long": -1.50, "short": -0.35},
    "EURUSD": {"long": -0.60, "short": -0.30}, "GBPUSD": {"long": -0.55, "short": -0.30},
    "AUDUSD": {"long": -0.45, "short": -0.30}, "NZDUSD": {"long": -0.45, "short": -0.30},
    "USDCHF": {"long": -0.40, "short": -0.35}, "USDCAD": {"long": -0.40, "short": -0.35},
    "EURJPY": {"long": -0.50, "short": -0.45}, "AUDJPY": {"long": -0.50, "short": -0.45},
    "EURGBP": {"long": -0.40, "short": -0.35},
}
SWAP_BPS = {**_SWAP_ANCHOR, **_SWAP_MEASURED}
MEASURED_SET = set(_SWAP_MEASURED)

# Triple-rollover weekday (python weekday: Mon=0..Sun=6). Indices Fri(4), metals/FX Wed(2).
TRIPLE_DOW = {s: (4 if CLASS[s] == "INDEX" else 2) for s in CLASS}


def swap_bps_night(sym: str, side: str) -> float:
    """Signed swap bps/night for a single held leg (before triple multiplier)."""
    return SWAP_BPS[sym][side]


def swap_series(sym: str, side: str, index: pd.DatetimeIndex, swap_mult: float = 1.0) -> pd.Series:
    """Per-date signed swap bps charged for holding `side` overnight into each date.
    Applies x3 on the instrument's triple-rollover weekday. `swap_mult` = stress multiplier."""
    base = swap_bps_night(sym, side) * swap_mult
    dow = index.weekday
    mult = np.where(dow == TRIPLE_DOW[sym], 3.0, 1.0)
    # weekend: Fri->Mon carries the Wed/Fri triple already; nights held handled by caller.
    return pd.Series(base * mult, index=index)


def pair_financing_bps_night(sym_long: str, sym_short: str, spread_dir: int,
                             swap_mult: float = 1.0) -> float:
    """Signed swap bps/night for a market-neutral pair spread.
    spread_dir=+1 => long sym_long / short sym_short ; -1 => the reverse."""
    if spread_dir >= 0:
        return (swap_bps_night(sym_long, "long") + swap_bps_night(sym_short, "short")) * swap_mult
    return (swap_bps_night(sym_long, "short") + swap_bps_night(sym_short, "long")) * swap_mult


if __name__ == "__main__":
    print("RT cost (bps/leg):", {c: round(rt_cost_bps(s), 2)
                                  for c, s in [("FX", "EURUSD"), ("INDEX", "US100"), ("METAL", "XAUUSD")]})
    for a, b in [("US100", "US500"), ("US500", "US30"), ("EURUSD", "GBPUSD"), ("XAUUSD", "XAGUSD")]:
        print(f"pair {a}/{b}: long-spread fin {pair_financing_bps_night(a,b,+1):+.3f} | "
              f"short-spread fin {pair_financing_bps_night(a,b,-1):+.3f} bps/night")
