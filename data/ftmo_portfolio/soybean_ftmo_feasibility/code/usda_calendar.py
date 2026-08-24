"""Scheduled USDA report calendar for the SOYBEAN reopen skip variant (Q3).

The soybean window is 01:00->07:00 UTC. A USDA report released 12:00 ET on calendar
date R lands at ~16:00 UTC (EDT) / 17:00 UTC (EST) on UTC-date R -> the soybean window
NEVER holds through the release (window is the overnight, 20:00-03:00 ET). So:
  - UTC-date R     = the PRE-release morning (anticipation; before the noon report).
  - UTC-date R+1   = the POST-release morning (digests the report) <- expected tail.
`is_skip_morning(D)` flags D in {R, R+1} for any scheduled report R (brackets the event).
Dates are KNOWN IN ADVANCE (USDA publishes the schedule a year out) -> no look-ahead.

Sources / confidence:
  - WASDE 2025 & 2026: CONFIRMED from USDA published schedule (web, 2026-06).
  - WASDE 2017-2024 + big NASS reports: best-estimate on the regular schedule (WASDE ~9-12th,
    weekday, 12:00 ET; Prospective Plantings & Mar Grain Stocks last bd of March; Acreage &
    Jun Grain Stocks last bd of June; Sep Grain Stocks ~last bd Sep). ±1-2 day uncertainty.
  - VALIDATED downstream by elevated realised range on tagged R/R+1 mornings (Q3); the
    empirical worst-days cross-check (calendar-free) is the robust primary attribution.
"""
from __future__ import annotations
import datetime as _dt
import numpy as np
import pandas as pd

# --- WASDE monthly release dates (12:00 ET). (year, month, day) ---
_WASDE = {
    2017: [(1,12),(2,9),(3,9),(4,11),(5,10),(6,9),(7,12),(8,10),(9,12),(10,12),(11,9),(12,12)],
    2018: [(1,12),(2,8),(3,8),(4,10),(5,10),(6,12),(7,12),(8,10),(9,12),(10,11),(11,8),(12,11)],
    # Jan 2019 WASDE delayed to Feb 8 (Dec-2018/Jan-2019 federal gov shutdown) -> no Jan release.
    2019: [(2,8),(3,8),(4,9),(5,10),(6,11),(7,11),(8,12),(9,12),(10,10),(11,8),(12,10)],
    2020: [(1,10),(2,11),(3,10),(4,9),(5,12),(6,11),(7,10),(8,12),(9,11),(10,9),(11,10),(12,10)],
    2021: [(1,12),(2,9),(3,9),(4,9),(5,12),(6,10),(7,12),(8,12),(9,10),(10,12),(11,9),(12,9)],
    2022: [(1,12),(2,9),(3,9),(4,8),(5,12),(6,10),(7,12),(8,12),(9,12),(10,12),(11,9),(12,9)],
    2023: [(1,12),(2,8),(3,8),(4,11),(5,12),(6,9),(7,12),(8,11),(9,12),(10,12),(11,9),(12,8)],
    2024: [(1,12),(2,8),(3,8),(4,11),(5,10),(6,12),(7,12),(8,12),(9,12),(10,11),(11,8),(12,10)],
    2025: [(1,12),(2,11),(3,11),(4,10),(5,12),(6,12),(7,11),(8,12),(9,12),(10,9),(11,10),(12,9)],
    2026: [(1,12),(2,10),(3,10),(4,9),(5,12),(6,11),(7,10),(8,12),(9,11),(10,9),(11,10),(12,10)],
}

# --- big NASS reports (12:00 ET): Prospective Plantings + Mar Grain Stocks (last bd Mar);
#     Acreage + Jun Grain Stocks (last bd Jun); Sep Grain Stocks (last bd Sep). The Mar/Jun
#     acreage surprises are historically the largest single-day soybean movers. ---
_BIG = {
    2017: [(3,31),(6,30),(9,29)], 2018: [(3,29),(6,29),(9,28)],
    2019: [(3,29),(6,28),(9,30)], 2020: [(3,31),(6,30),(9,30)],
    2021: [(3,31),(6,30),(9,30)], 2022: [(3,31),(6,30),(9,30)],
    2023: [(3,31),(6,30),(9,29)], 2024: [(3,28),(6,28),(9,30)],
    2025: [(3,31),(6,30),(9,30)], 2026: [(3,31),(6,30),(9,30)],
}


def _all_report_dates() -> set[_dt.date]:
    out = set()
    for y, lst in _WASDE.items():
        for m, d in lst:
            out.add(_dt.date(y, m, d))
    for y, lst in _BIG.items():
        for m, d in lst:
            out.add(_dt.date(y, m, d))
    return out


REPORT_DATES = _all_report_dates()
# day-after set (R+1), for the post-release digestion morning
_AFTER = {r + _dt.timedelta(days=1) for r in REPORT_DATES}


def is_report_day(index: pd.DatetimeIndex) -> np.ndarray:
    d = pd.DatetimeIndex(index).normalize().date
    return np.array([x in REPORT_DATES for x in d])


def is_skip_morning(index: pd.DatetimeIndex) -> np.ndarray:
    """True if the UTC date is a scheduled report date R OR the day-after R+1."""
    d = pd.DatetimeIndex(index).normalize().date
    return np.array([(x in REPORT_DATES) or (x in _AFTER) for x in d])


def report_dates_in(lo, hi) -> list[_dt.date]:
    lo, hi = pd.Timestamp(lo).date(), pd.Timestamp(hi).date()
    return sorted(r for r in REPORT_DATES if lo <= r <= hi)


if __name__ == "__main__":
    rd = sorted(REPORT_DATES)
    print(f"total scheduled USDA report dates 2017-2026: {len(rd)} "
          f"(WASDE {sum(len(v) for v in _WASDE.values())} + big {sum(len(v) for v in _BIG.values())})")
    print(f"range {rd[0]} -> {rd[-1]}")
