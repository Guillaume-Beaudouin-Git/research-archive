"""
Part B (breakeven nights) + Part C (2026 compression), computed directly
from primary sources already loaded in this session:
  - swaps.py: real FTMO swap table, measured 2026-09-02 (given).
  - rates.py: FRED 3M interbank/policy rates, cache read directly (no
    network), used to build an INDEPENDENT (non-"ESTIMATION moyenne
    simple") theoretical differential for 2022-2024 vs 2026 YTD, by
    averaging actual monthly FRED observations in each window (not the
    hand-picked annual levels of dedale_broker_2026-08/RAPPORT_BROKER.md
    — this is a genuine cross-check, not a repeat of that report).

Vehicle costs (Part E): FTMO 2.48 bps RT (repo-canonical, dedale_broker
report), Eightcap Raw ~0.66-1.18 bps RT (ESTIMATION, dedale_broker
report §3.2 — plancher publié, PAS mesuré), IBKR ~0.4-0.5 bps RT + $2
min/order (L57: fixed-cost floor dominates on small notional).
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
from rates import load_rates_monthly, PAIR_CCY
from swaps import SWAP_TABLE

RES = Path(__file__).resolve().parents[1] / "results"
RES.mkdir(parents=True, exist_ok=True)


def period_avg_differential(pair: str, start: str, end: str) -> float:
    rates = load_rates_monthly()
    base, quote = PAIR_CCY[pair]
    diff = (rates[base] - rates[quote]).dropna()
    seg = diff[(diff.index >= start) & (diff.index <= end)]
    return float(seg.mean()) if len(seg) else np.nan


def bps_per_night(pp_per_year: float) -> float:
    return pp_per_year / 365.0 * 100.0


def main():
    rows = []
    for pair in PAIR_CCY:
        d_2022_24 = period_avg_differential(pair, "2022-01-01", "2024-12-31")
        d_2026 = period_avg_differential(pair, "2026-01-01", "2026-08-28")
        theo_bps_2022_24 = bps_per_night(d_2022_24)
        theo_bps_2026 = bps_per_night(d_2026)
        compression_pct = (
            (theo_bps_2026 - theo_bps_2022_24) / abs(theo_bps_2022_24) * 100
            if theo_bps_2022_24 not in (0, np.nan) and not np.isnan(theo_bps_2022_24)
            else np.nan
        )

        long_bps, short_bps, markup_bps, side = SWAP_TABLE[pair]
        actual_paying_bps = long_bps if side == "long" else (short_bps if side == "short" else max(long_bps, short_bps))
        capture_ratio = actual_paying_bps / theo_bps_2026 if theo_bps_2026 not in (0, np.nan) and not np.isnan(theo_bps_2026) else np.nan

        for vehicle, cost_bps in [("FTMO", 2.48), ("Eightcap_Raw_est", 0.90), ("IBKR_est", 0.45)]:
            if side is None or actual_paying_bps <= 0:
                breakeven_nights = np.inf
            else:
                breakeven_nights = cost_bps / actual_paying_bps
            rows.append(dict(
                pair=pair, vehicle=vehicle, cost_bps_rt=cost_bps,
                theo_diff_2022_24_bps_night=theo_bps_2022_24,
                theo_diff_2026_bps_night=theo_bps_2026,
                compression_pct=compression_pct,
                paying_side_2026=side,
                actual_swap_bps_night_2026_FTMO=actual_paying_bps,
                markup_rt_bps_night_FTMO=markup_bps,
                capture_ratio_actual_over_theoretical=capture_ratio,
                breakeven_nights_vs_cost=breakeven_nights,
            ))
    df = pd.DataFrame(rows)
    df.to_csv(RES / "part_bc_compression_breakeven.csv", index=False)
    print(df.to_string())
    print("Wrote", RES / "part_bc_compression_breakeven.csv")

    # markup-only breakeven: nights of the ACTUAL 2026 paying-side swap
    # needed just to cover the FTMO nightly markup itself (structural
    # drag independent of trading cost) -- only meaningful where a
    # paying side exists
    print("\n--- markup drag as pct of paying-side swap (FTMO) ---")
    for pair in PAIR_CCY:
        long_bps, short_bps, markup_bps, side = SWAP_TABLE[pair]
        if side is None:
            print(f"{pair}: no paying side (both long and short swap negative) -> markup is 100%+ of any position, structurally dead")
            continue
        paying = long_bps if side == "long" else short_bps
        # fair (no-markup) swap on the paying side would be paying - markup/2 approx;
        # report ratio of markup magnitude to paying-side swap directly
        ratio = abs(markup_bps) / paying if paying > 0 else np.inf
        print(f"{pair}: paying-side swap {paying:+.3f} bps/night, markup {markup_bps:+.3f} bps/night -> markup is {ratio*100:.0f}% of the collected swap")


if __name__ == "__main__":
    main()
