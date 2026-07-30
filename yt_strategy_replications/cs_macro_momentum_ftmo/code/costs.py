"""Cost model — PREREGISTRATION section 4.

Three components, all in bps of *held notional per leg*:

1. **spread** — measured per M1 bar in ``deep_history_utc`` (MT5 ``spread``
   column, in points), aggregated to a daily median and p95 by
   ``build_panel.py``. Crossing costs half the quoted spread per unit of
   notional traded, so a round trip pays one full spread.
2. **commission** — from the frozen yaml ``measured_specs`` where the symbol is
   covered; extrapolated by asset class otherwise (see COMM_RT_BPS).
3. **swap** — charged on held notional, per leg, both directions, x3 on the
   symbol's rollover day.

DOCUMENTED DEVIATION (see RESULTS.md). PREREGISTRATION section 4 anchors the swap on
``measured_specs`` of the frozen yaml v2.2.2. That block physically covers only
**four** symbols (XAUUSD, USDJPY, US100, GER40) — the four legs of the live EA —
whereas the frozen universe has 17. A measured anchor for the other 13 does not
exist in this repository and cannot be created without a live broker read.

Rather than assume a number, the four anchors are *decomposed* into the two
economic pieces a CFD swap is made of, and the decomposition is extrapolated:

    swap_long  = fair_financing - markup
    swap_short = -fair_financing - markup

    fair_financing = (swap_long - swap_short) / 2       [pure carry]
    markup         = -(swap_long + swap_short) / 2      [pure dealer spread]

The anchors give, in bps/night:

    | leg     | fair    | markup |
    | XAUUSD  | -0.591  | 0.927  |
    | USDJPY  | +0.664  | 0.604  |
    | US100   | -1.109  | 1.017  |
    | GER40   | -0.686  | 0.879  |

``fair`` is then *rebuilt from observable 3-month rates* (data/panels/fx_rates_3m.csv):
long an index CFD pays the quote-currency rate, long an FX pair earns the base rate
and pays the quote rate. Reconstructed at the anchor date this gives US100 -0.989 vs
-1.109 measured, USDJPY +0.641 vs +0.664 measured — i.e. the rate-based
reconstruction reproduces the measured carry to within 10% on the two independent
legs where it can be checked. Gold reconstructs at -0.989 vs -0.591 measured, i.e.
the model is 1.7x *more expensive* than the broker on metals: conservative, kept.

``markup`` is time-constant by class (an anchor read on 2026-06-10 applied over
2013-2026). This is the weakest assumption in the study and is stress-tested
explicitly (swap x0 / x1 / x1.5) rather than defended.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")

# point = 10 ** -digits (inferred from price granularity, cross-checked against
# measured_specs digits for XAUUSD=2, USDJPY=3, US100=2, GER40=2).
DIGITS = {
    "EURUSD": 5, "GBPUSD": 5, "USDJPY": 3, "AUDUSD": 5, "USDCAD": 5,
    "USDCHF": 5, "NZDUSD": 5,
    "US30": 2, "US100": 2, "US500": 2, "GER40": 2,
    "XAUUSD": 2, "XAGUSD": 3, "COPPER": 4,
    "UKOIL": 3, "USOIL": 3, "NGAS": 4,
}

CLASS = {
    "EURUSD": "fx", "GBPUSD": "fx", "USDJPY": "fx", "AUDUSD": "fx",
    "USDCAD": "fx", "USDCHF": "fx", "NZDUSD": "fx",
    "US30": "index", "US100": "index", "US500": "index", "GER40": "index",
    "XAUUSD": "metal", "XAGUSD": "metal", "COPPER": "metal",
    "UKOIL": "commodity", "USOIL": "commodity", "NGAS": "commodity",
}

# FX pair -> (base ccy, quote ccy); index/metal/commodity -> financing currency.
FX_LEGS = {
    "EURUSD": ("EUR", "USD"), "GBPUSD": ("GBP", "USD"), "USDJPY": ("USD", "JPY"),
    "AUDUSD": ("AUD", "USD"), "USDCAD": ("USD", "CAD"), "USDCHF": ("USD", "CHF"),
    "NZDUSD": ("NZD", "USD"),
}
FIN_CCY = {"US30": "USD", "US100": "USD", "US500": "USD", "GER40": "EUR",
           "XAUUSD": "USD", "XAGUSD": "USD", "COPPER": "USD",
           "UKOIL": "USD", "USOIL": "USD", "NGAS": "USD"}

# Dealer markup per night per leg, bps of notional. Calibrated on the four
# measured anchors (see module docstring); commodities inherit the metals tier.
MARKUP_BPS = {"fx": 0.604, "index": 0.948, "metal": 0.927, "commodity": 0.927}

# Round-trip commission, bps. Measured for the four anchored legs; extrapolated
# by class elsewhere (FX from USDJPY $2.5/side/lot, metals from XAUUSD 7e-6/side).
COMM_RT_BPS = {"fx": 0.50, "index": 0.0, "metal": 0.14, "commodity": 0.14}

# x3 rollover weekday (Python dow). measured_specs: XAUUSD/USDJPY = 2 (Wednesday),
# US100/GER40 = 4 (Friday). cost_anchors.triple_days states the rule as
# {indices: Friday, metals+FX: Wednesday}; commodities follow the metals tier.
TRIPLE_DOW = {"fx": 2, "metal": 2, "commodity": 2, "index": 4}

DAYS_PER_YEAR = 365.0


def load_rates() -> pd.DataFrame:
    """Monthly 3-month rates in %, forward-filled to daily."""
    r = pd.read_csv(REPO / "data/panels/fx_rates_3m.csv", parse_dates=["Date"])
    r = r.set_index("Date").sort_index().ffill()
    idx = pd.date_range(r.index.min(), "2026-12-31", freq="D")
    return r.reindex(idx).ffill()


def swap_bps_frame(symbols: list[str], dates: pd.DatetimeIndex,
                   side: str) -> pd.DataFrame:
    """bps/night charged on held notional, per symbol and date, for ``side``.

    Positive = credit, negative = cost. Triple-rollover multiplier included.
    """
    rates = load_rates().reindex(dates).ffill()
    per_day = 100.0 / DAYS_PER_YEAR  # % p.a. -> bps per night
    out = {}
    for sym in symbols:
        cls = CLASS[sym]
        if cls == "fx":
            base, quote = FX_LEGS[sym]
            fair = (rates[base] - rates[quote]) * per_day
        else:
            fair = -rates[FIN_CCY[sym]] * per_day
        mk = MARKUP_BPS[cls]
        leg = fair - mk if side == "long" else -fair - mk
        mult = np.where(dates.dayofweek == TRIPLE_DOW[cls], 3.0, 1.0)
        out[sym] = leg.to_numpy() * mult
    return pd.DataFrame(out, index=dates)


# Ratio (live measured RT anchor) / (panel measured RT) on the four anchored legs,
# computed by qc.py on 2020+: XAUUSD 2.45, USDJPY 1.97, US100 2.28, GER40 2.77.
# The deep-history spread column is systematically ~2.4x cheaper than what the live
# FTMO account actually pays (L33: the instrument's real cost structure decides).
ANCHOR_UPLIFT = {"fx": 1.97, "index": 2.50, "metal": 2.45, "commodity": 2.45}


def spread_bps(panel: pd.DataFrame, field: str = "spread_med",
               repair_zeros: bool = True, uplift: bool = False) -> pd.DataFrame:
    """Quoted spread in bps of price: points * 10**-digits / price * 1e4.

    ``repair_zeros``: the FX segment of ``deep_history_utc`` has an unpopulated
    spread column over large parts of 2021-2023 (EURUSD 70-79% of bars, USDJPY
    57-74%, GBPUSD 29% in 2022); indices and metals are clean. A zero there is a
    missing measurement, not a free trade, so it is replaced by the symbol's median
    over the sessions where the column *is* populated.

    ``uplift``: rescale to the live FTMO round-trip anchors (see ANCHOR_UPLIFT).
    """
    px = panel.xs("close", level=1, axis=1)
    sp = panel.xs(field, level=1, axis=1)
    pt = pd.Series({s: 10.0 ** -DIGITS[s] for s in px.columns})
    out = (sp * pt / px * 1e4).clip(lower=0.0)
    if repair_zeros:
        pos = out.where(out > 0)
        out = out.mask(out <= 0, pos.median(), axis=1)
    if uplift:
        out = out.mul(pd.Series({s: ANCHOR_UPLIFT[CLASS[s]] for s in out.columns}), axis=1)
    return out


def commission_rt_bps(symbols: list[str]) -> pd.Series:
    return pd.Series({s: COMM_RT_BPS[CLASS[s]] for s in symbols})
