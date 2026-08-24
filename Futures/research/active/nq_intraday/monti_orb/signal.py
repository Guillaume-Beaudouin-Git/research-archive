"""
signal.py — Monti ORB (Fabio-improved) signal generator for NQ 1-min data.

ORB window:   09:30–10:00 ET (30-min range, inclusive of 09:30, exclusive of 10:00)
Entry:        close of first 5-min bar in [10:00, 15:00) where close > orb_high → long
Slippage:     entry_fill = bar_close + SLIPPAGE_ENTRY_PTS (breakout premium)
SL:           orb_low
TP:           entry_fill + (entry_fill – orb_low) = 1R
Time stop:    exit at close of last 1-min bar before 15:00 ET
Max trades:   1 per day, long-only
No look-ahead: signal fires at 5-min bar close; exit simulated on subsequent 1-min bars.

Performance: fully vectorized — ORB and 5-min bar computation uses pandas resample
directly on the full dataset. Exit simulation loops only over actual trades (~500 total).
"""
from __future__ import annotations

import datetime
from typing import Optional

import numpy as np
import pandas as pd

SLIPPAGE_ENTRY_PTS: float = 0.25  # breakout slippage added to entry (conservative)

_ORB_START  = datetime.time(9, 30)
_ORB_END    = datetime.time(10, 0)   # exclusive
_SCAN_START = datetime.time(10, 0)
_TIME_STOP  = datetime.time(15, 0)   # exclusive upper bound for exit simulation


def monti_orb_signal(df_1min: pd.DataFrame) -> pd.DataFrame:
    """
    Compute daily ORB Monti trade outcomes on NQ 1-min data.

    Parameters
    ----------
    df_1min : tz-aware (US/Eastern) DatetimeIndex DataFrame
              required columns: open, high, low, close

    Returns
    -------
    DataFrame indexed by date (datetime64) with columns:
        orb_high, orb_low, orb_range_pts,
        entry_5m_label, entry_close_px, entry_fill_px,
        sl_px, tp_px, risk_pts,
        exit_time, exit_px, exit_reason,
        pnl_pts          (gross, before commissions/exit-slippage)

    exit_reason values:
        'tp'               — take-profit hit
        'sl'               — stop-loss hit
        'time'             — time stop (15:00 ET)
        'no_signal'        — no 5-min bar closed above ORB high
        'insufficient_orb' — fewer than 5 ORB bars on that day
    """
    # ── Step 1: ORB per day — vectorized ─────────────────────────────────────
    orb_1m = df_1min[
        (df_1min.index.time >= _ORB_START) &
        (df_1min.index.time < _ORB_END)
    ]
    orb_daily = orb_1m.resample("1B").agg(
        orb_high=("high", "max"),
        orb_low=("low",  "min"),
        orb_count=("close", "count"),
    ).dropna(subset=["orb_high"])
    # Require ≥5 ORB bars (30-min window minus data gaps)
    orb_daily = orb_daily[orb_daily["orb_count"] >= 5].copy()
    orb_daily.index = orb_daily.index.normalize()

    # ── Step 2: 5-min bars from [10:00, 15:00) — vectorized ──────────────────
    scan_1m = df_1min[
        (df_1min.index.time >= _SCAN_START) &
        (df_1min.index.time < _TIME_STOP)
    ]
    bars_5m = (
        scan_1m
        .resample("5min", label="left", closed="left")
        .agg(
            high=("high",  "max"),
            low=("low",   "min"),
            close=("close", "last"),
        )
        .dropna(subset=["close"])
    )
    bars_5m = bars_5m.copy()
    bars_5m["date"] = bars_5m.index.normalize()

    # Join ORB data
    bars_5m = bars_5m.join(
        orb_daily[["orb_high", "orb_low"]],
        on="date",
        how="inner",
    )

    # ── Step 3: Find first trigger bar per day ────────────────────────────────
    trigger_mask = bars_5m["close"] > bars_5m["orb_high"]
    triggered    = bars_5m[trigger_mask].copy()

    # First trigger per day
    # Sort by index (ascending time) and keep first occurrence per date
    triggered = triggered.sort_index()
    first_trigger = triggered.groupby("date").first()  # indexed by date

    # ── Step 4: Exit simulation — loops only over ~500 trades ─────────────────
    # Pre-build per-day fast lookup: date → slice of df_1min
    # Use groupby on normalized date
    df_date_col = df_1min.copy()
    df_date_col["_date"] = df_date_col.index.normalize()
    day_groups = {
        date: grp.drop(columns=["_date"])
        for date, grp in df_date_col.groupby("_date")
    }

    records: list[dict] = []

    # Collect all days in ORB data
    all_orb_dates = set(orb_daily.index.normalize())

    for date, row in first_trigger.iterrows():
        date_ts = pd.Timestamp(date)
        orb_high = float(row["orb_high"])
        orb_low  = float(row["orb_low"])

        # The 5-min bar that triggered
        # first_trigger is indexed by date (normalized); we need the actual bar time
        # We stored it via groupby.first() which gives the first bar's values
        # But we've lost the bar timestamp — re-find it
        day_5m = triggered[triggered["date"] == date_ts]
        entry_bar_label: pd.Timestamp = day_5m.index[0]
        entry_close: float = float(day_5m.iloc[0]["close"])
        entry_fill:  float = entry_close + SLIPPAGE_ENTRY_PTS

        sl_px:    float = orb_low
        risk_pts: float = entry_fill - sl_px
        if risk_pts <= 0.0:
            continue
        tp_px: float = entry_fill + risk_pts  # 1R

        # Sim bars: 1-min bars starting after trigger 5-min bar ends
        sim_start = entry_bar_label + pd.Timedelta(minutes=5)
        day_bars  = day_groups.get(date_ts)
        if day_bars is None:
            continue

        sim_bars = day_bars[
            (day_bars.index >= sim_start) &
            (day_bars.index.time < _TIME_STOP)
        ]

        exit_px:     float = np.nan
        exit_time:   Optional[pd.Timestamp] = None
        exit_reason: str = "time"

        if sim_bars.empty:
            exit_px     = entry_fill
            exit_time   = entry_bar_label + pd.Timedelta(minutes=4)
            exit_reason = "time"
        else:
            lows  = sim_bars["low"].to_numpy(dtype=float)
            highs = sim_bars["high"].to_numpy(dtype=float)
            sl_mask = lows  <= sl_px
            tp_mask = highs >= tp_px
            first_sl = int(np.argmax(sl_mask)) if sl_mask.any() else len(sl_mask)
            first_tp = int(np.argmax(tp_mask)) if tp_mask.any() else len(tp_mask)

            if sl_mask.any() and first_sl <= first_tp:
                exit_px     = sl_px
                exit_time   = sim_bars.index[first_sl]
                exit_reason = "sl"
            elif tp_mask.any():
                exit_px     = tp_px
                exit_time   = sim_bars.index[first_tp]
                exit_reason = "tp"
            else:
                exit_px     = float(sim_bars.iloc[-1]["close"])
                exit_time   = sim_bars.index[-1]
                exit_reason = "time"

        pnl_pts = exit_px - entry_fill

        records.append({
            "date":           date_ts,
            "orb_high":       orb_high,
            "orb_low":        orb_low,
            "orb_range_pts":  round(orb_high - orb_low, 4),
            "entry_5m_label": entry_bar_label,
            "entry_close_px": entry_close,
            "entry_fill_px":  entry_fill,
            "sl_px":          sl_px,
            "tp_px":          round(tp_px, 4),
            "risk_pts":       round(risk_pts, 4),
            "exit_time":      exit_time,
            "exit_px":        exit_px,
            "exit_reason":    exit_reason,
            "pnl_pts":        round(pnl_pts, 4),
        })

    # ── Step 5: Add no-signal and insufficient-ORB days ──────────────────────
    triggered_dates = set(pd.Timestamp(d) for d in first_trigger.index)
    for date_ts in orb_daily.index:
        dt = pd.Timestamp(date_ts)
        if dt in triggered_dates:
            continue
        records.append({
            "date":           dt,
            "orb_high":       float(orb_daily.loc[date_ts, "orb_high"]),
            "orb_low":        float(orb_daily.loc[date_ts, "orb_low"]),
            "orb_range_pts":  float(orb_daily.loc[date_ts, "orb_high"]
                                   - orb_daily.loc[date_ts, "orb_low"]),
            "entry_5m_label": None,
            "entry_close_px": None,
            "entry_fill_px":  None,
            "sl_px":          None,
            "tp_px":          None,
            "risk_pts":       np.nan,
            "exit_time":      None,
            "exit_px":        None,
            "exit_reason":    "no_signal",
            "pnl_pts":        0.0,
        })

    # Add insufficient-ORB days
    all_trading_days = df_1min.resample("1B").size()
    all_trading_days = all_trading_days[all_trading_days > 0].index.normalize()
    no_orb_dates = set(all_trading_days) - all_orb_dates
    for date_ts in no_orb_dates:
        records.append({
            "date":           pd.Timestamp(date_ts),
            "exit_reason":    "insufficient_orb",
            "pnl_pts":        0.0,
            **{k: np.nan for k in [
                "orb_high", "orb_low", "orb_range_pts",
                "entry_5m_label", "entry_close_px", "entry_fill_px",
                "sl_px", "tp_px", "risk_pts", "exit_time", "exit_px",
            ]},
        })

    if not records:
        return pd.DataFrame()

    df_out = pd.DataFrame(records)
    df_out["date"] = pd.to_datetime(df_out["date"])
    return df_out.set_index("date").sort_index()
