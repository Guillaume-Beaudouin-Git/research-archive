"""
Resolve MT5 US100 timezone by aligning the daily volume-spike timestamp with
the NQ databento RTH-open volume spike (09:30 ET cash open).

Hypotheses:
  - MT5 timestamp is true UTC  → 09:30 ET = 14:30 UTC (winter) / 13:30 UTC (summer)
  - MT5 timestamp is GMT+2/+3 server-time → 09:30 ET = 16:30 server-winter / 16:30 server-summer

We compute for each session day in 2024:
  - the UTC hour at which MT5 tick_volume peaks
  - the UTC hour at which databento NQ tick volume peaks
  - the offset
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
MT5 = ROOT / "data/ftmo_universe/intraday_m1/indices/US100_M1.csv"
DBN = ROOT / "Futures/research/active/ftmo_3strats_audit_2026-06/results/nq_1m_rth_2010_2026.parquet"


def main() -> None:
    print("[load] MT5 US100 M1 (2024 only)")
    mt5 = pd.read_csv(MT5, parse_dates=["timestamp_utc"],
                      date_format="%Y.%m.%d %H:%M:%S")
    mt5["timestamp_utc"] = pd.to_datetime(mt5["timestamp_utc"], utc=True)
    mt5 = mt5.set_index("timestamp_utc").sort_index()
    mt5 = mt5.loc["2024-01-01":"2024-12-31"]
    mt5["date"] = mt5.index.date
    mt5["hour"] = mt5.index.hour
    mt5["min"] = mt5.index.minute

    # MT5 hour where session volume peaks per day
    g = mt5.groupby(["date", "hour"])["tick_volume"].sum().reset_index()
    mt5_peak = g.sort_values("tick_volume", ascending=False).groupby("date").head(1)
    mt5_peak = mt5_peak.rename(columns={"hour": "mt5_peak_hour"})

    # Same for databento (use volume column)
    print("[load] NQ databento (2024 only)")
    dbn = pd.read_parquet(DBN)
    dbn.index = pd.to_datetime(dbn.index)
    dbn_2024 = dbn.loc["2024-01-01":"2024-12-31"].copy()
    # The databento file was saved tz-naive (we converted to ET and stripped tz in loader),
    # so the timestamps are already ET. Convert to UTC for comparison.
    dbn_2024.index = (
        dbn_2024.index.tz_localize("America/New_York").tz_convert("UTC")
    )
    dbn_2024["date_utc"] = dbn_2024.index.date
    dbn_2024["hour_utc"] = dbn_2024.index.hour

    # Need per-session-day grouping by US trading day (ET date)
    dbn_2024_et = dbn_2024.copy()
    dbn_2024_et.index = dbn_2024_et.index.tz_convert("America/New_York")
    dbn_2024_et["date_et"] = dbn_2024_et.index.date
    dbn_2024_et["hour_utc"] = dbn_2024_et.index.tz_convert("UTC").hour

    g2 = dbn_2024_et.groupby(["date_et", "hour_utc"])["volume"].sum().reset_index()
    dbn_peak = g2.sort_values("volume", ascending=False).groupby("date_et").head(1)
    dbn_peak = dbn_peak.rename(columns={"hour_utc": "dbn_peak_hour"})

    # Merge
    merged = (
        mt5_peak[["date", "mt5_peak_hour"]]
        .merge(dbn_peak[["date_et", "dbn_peak_hour"]], left_on="date", right_on="date_et")
    )
    merged["offset"] = merged["mt5_peak_hour"] - merged["dbn_peak_hour"]
    print(f"[match] aligned sessions={len(merged)}")
    print("\n[offset distribution MT5_peak_h - databento_peak_h]")
    print(merged["offset"].value_counts().sort_index().to_string())
    print(f"\n[median MT5 peak hour]: {int(merged['mt5_peak_hour'].median())} UTC")
    print(f"[median databento peak hour]: {int(merged['dbn_peak_hour'].median())} UTC")
    print(
        "Interpretation: if median offset ≈ 0 → MT5 timestamps are true UTC. "
        "If median offset ≈ +1/+2 → MT5 is server-time (GMT+1/+2). "
        "If median offset ≈ −5/−4 → MT5 may be in ET."
    )

    # Compare volume profile
    print("\n[NQ databento volume profile by UTC hour, 2024]")
    nq_prof = (
        dbn_2024_et.groupby(dbn_2024_et.index.tz_convert("UTC").hour)["volume"]
        .sum()
        .sort_index()
    )
    print(nq_prof.to_string())

    print("\n[MT5 US100 volume profile by UTC hour, 2024]")
    mt5_prof = mt5.groupby("hour")["tick_volume"].sum().sort_index()
    print(mt5_prof.to_string())


if __name__ == "__main__":
    main()
