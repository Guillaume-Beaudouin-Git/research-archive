"""
Extract daily (00:00 UTC) close series for the 9 swap-table pairs + GBPJPY.
Sources: main-dir data/deep_history_utc CSVs (read-only, absolute path) for
8 pairs already pre-extracted to /tmp/fxcarry_daily/*.csv via awk; GBPJPY
from the scratchpad M1 parquet cache (2007-2026-08, more recent than the
CSV snapshot).
Output: Forex/research/active/fx_carry_2026-09/data/daily_close.parquet
"""
from __future__ import annotations
import pandas as pd
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parents[1] / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PAIRS_FROM_TMP = ["AUDJPY", "USDJPY", "USDCHF", "USDCAD", "EURUSD", "AUDUSD", "GBPUSD", "NZDUSD"]
TMP_DIR = Path("/tmp/fxcarry_daily")

GBPJPY_PARQUET = Path(
    "<SCRATCH>"
    "9fd32b98-b3ee-47bf-93c1-b7c5a1ac70a6/scratchpad/m1_cache/GBPJPY_M1.parquet"
)


def load_tmp_pair(pair: str) -> pd.Series:
    df = pd.read_csv(TMP_DIR / f"{pair}.csv", header=None, names=["ts", "close"])
    df["ts"] = pd.to_datetime(df["ts"], format="%Y.%m.%d %H:%M:%S", utc=True)
    df = df.drop_duplicates(subset="ts").set_index("ts").sort_index()
    return df["close"].rename(pair)


def load_gbpjpy() -> pd.Series:
    df = pd.read_parquet(GBPJPY_PARQUET, columns=["close"])
    daily = df[df.index.time == pd.Timestamp("00:00:00").time()]["close"]
    daily.index = daily.index.tz_convert("UTC")
    return daily.rename("GBPJPY")


def main() -> None:
    series = {p: load_tmp_pair(p) for p in PAIRS_FROM_TMP}
    series["GBPJPY"] = load_gbpjpy()
    df = pd.DataFrame(series).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    out = OUT_DIR / "daily_close.parquet"
    df.to_parquet(out)
    print("Saved", out, df.shape)
    print(df.describe().T[["count"]])
    print("range:", df.index.min(), "->", df.index.max())


if __name__ == "__main__":
    main()
