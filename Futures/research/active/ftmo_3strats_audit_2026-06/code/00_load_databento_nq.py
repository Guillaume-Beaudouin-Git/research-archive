"""
Load databento NQ 1-min OHLCV (2010-06-06 → 2026-05-31) and build a
continuous front-month panel keyed by RTH (09:30-16:00 ET) for the S1 audit.

Steps:
 1. Decode the .dbn.zst file.
 2. For each (date, instrument_id) keep RTH bars.
 3. Build a continuous front-month series by picking, for each calendar day,
    the instrument_id with the highest aggregate volume that day (rollover proxy).
 4. Save:
    - parquet of 1-min OHLCV RTH, columns: ts_eastern, open, high, low, close, volume, instrument_id
    - parquet of daily bars (09:30 open, 16:00 close, day high/low, sum vol).
"""
import os
import sys
from pathlib import Path

import databento as db
import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
SRC = ROOT / "data/GLBX-20260601-FP4HWRA58K/glbx-mdp3-20100606-20260531.ohlcv-1m.dbn.zst"
OUT = ROOT / "Futures/research/active/ftmo_3strats_audit_2026-06/results"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    print(f"[load] reading {SRC.name} (107MB compressed)...", flush=True)
    store = db.DBNStore.from_file(SRC)
    df = store.to_df(pretty_ts=True, price_type="float", map_symbols=True)
    print(f"[load] rows={len(df):,} cols={list(df.columns)}", flush=True)
    print(f"[load] first ts={df.index.min()}  last ts={df.index.max()}", flush=True)

    # Index is ts_event UTC. Convert to ET.
    df = df.copy()
    df.index = df.index.tz_convert("America/New_York")
    df["date_et"] = df.index.normalize().date
    df["time_et"] = df.index.time

    # RTH = 09:30 to 16:00 ET inclusive of 09:30 bar (1-min bars timestamped at start)
    from datetime import time as dtime

    rth_mask = (df["time_et"] >= dtime(9, 30)) & (df["time_et"] < dtime(16, 1))
    df = df.loc[rth_mask].copy()
    print(f"[rth] rows={len(df):,}", flush=True)
    print(f"[rth] unique instrument_ids={df['instrument_id'].nunique()}", flush=True)

    # Pick front-month per day by total daily volume per instrument_id.
    daily_vol = (
        df.groupby(["date_et", "instrument_id"])["volume"].sum().reset_index()
    )
    front = (
        daily_vol.sort_values(["date_et", "volume"], ascending=[True, False])
        .groupby("date_et")
        .head(1)[["date_et", "instrument_id"]]
        .rename(columns={"instrument_id": "front_id"})
    )
    print(f"[front] days={len(front):,}", flush=True)
    front_map = front.set_index("date_et")["front_id"]
    df["front_id"] = df["date_et"].map(front_map)
    df = df.loc[df["instrument_id"] == df["front_id"]].copy()
    print(f"[front] kept rows after front filter={len(df):,}", flush=True)

    # Save 1-min RTH front-month — keep DatetimeIndex (tz-aware)
    keep_cols = ["open", "high", "low", "close", "volume", "instrument_id"]
    out_min = df[keep_cols].copy()
    out_min.index.name = "ts_eastern"
    # Strip tz to make parquet round-trip clean (we'll re-localize in the consumer)
    out_min_naive = out_min.copy()
    out_min_naive.index = out_min_naive.index.tz_localize(None)
    p_min = OUT / "nq_1m_rth_2010_2026.parquet"
    out_min_naive.to_parquet(p_min)
    print(f"[save] {p_min}  rows={len(out_min):,}", flush=True)

    # Build daily summary
    # For each session day: open = first 09:30 minute open, close = last 15:59 (or 16:00) close,
    # high/low = max/min, vol = sum.
    g = df.groupby("date_et")
    open_ = g["open"].first()
    close = g["close"].last()
    high = g["high"].max()
    low = g["low"].min()
    vol = g["volume"].sum()
    n_bars = g.size().rename("n_bars")
    daily = pd.concat(
        [
            open_.rename("open"),
            high.rename("high"),
            low.rename("low"),
            close.rename("close"),
            vol.rename("volume"),
            n_bars,
        ],
        axis=1,
    )
    p_d = OUT / "nq_daily_rth_2010_2026.parquet"
    daily.to_parquet(p_d)
    print(f"[save] {p_d}  rows={len(daily):,}", flush=True)
    print(
        f"[daily] median bars/day={int(daily['n_bars'].median())}  "
        f"min={daily['n_bars'].min()}  max={daily['n_bars'].max()}",
        flush=True,
    )


if __name__ == "__main__":
    main()
