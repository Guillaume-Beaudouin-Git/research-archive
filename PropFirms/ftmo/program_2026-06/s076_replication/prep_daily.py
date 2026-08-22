"""
prep_daily.py — build DAILY bars from M1 for the S076 Ross Hook replication.

Session convention (deployment target = MT5/FTMO daily candle = broker server day):
  PRIMARY  = EET/EEST server day (Europe/Bucharest).
  SENSITIVITY = UTC-midnight day (to confirm results aren't boundary-sensitive).

Sources:
  - data/deep_history_utc/*_M1.csv : TRUE UTC naive  -> localize UTC, convert Europe/Bucharest for EET.
  - data/panels/m5_indices/{US2000,BTCUSD}_M1.csv : EET-naive (already server time) -> naive date for EET;
    localize Europe/Bucharest -> UTC for the UTC set.

Daily bar: open=first, high=max, low=min, close=last, tick_volume=sum,
           spread_open=spread at the day's first minute (entry cost), spread_mean=mean spread (points).
Output: research/s076_replication/daily/{SYM}_{EET,UTC}.parquet  + coverage.csv
READ-ONLY on all source data.
"""
from __future__ import annotations
import sys
import warnings
import pandas as pd
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path("<HOME>/Desktop/Algo_claude")
DEEP = ROOT / "data/deep_history_utc"
PANEL = ROOT / "data/panels/m5_indices"
OUT = ROOT / "research/s076_replication/daily"; OUT.mkdir(parents=True, exist_ok=True)
TZ = "Europe/Bucharest"

# sym -> (path, src_tz, class)
INSTR = {
    "US500": (DEEP / "US500_M1.csv", "utc", "index"),
    "US100": (DEEP / "US100_M1.csv", "utc", "index"),
    "US30":  (DEEP / "US30_M1.csv",  "utc", "index"),
    "GER40": (DEEP / "GER40_M1.csv", "utc", "index"),
    "US2000": (PANEL / "US2000_M1.csv", "eet", "index"),
    "XAUUSD": (DEEP / "XAUUSD_M1.csv", "utc", "commodity"),
    "BTCUSD": (PANEL / "BTCUSD_M1.csv", "eet", "crypto"),
    "EURUSD": (DEEP / "EURUSD_M1.csv", "utc", "fx"), "GBPUSD": (DEEP / "GBPUSD_M1.csv", "utc", "fx"),
    "EURGBP": (DEEP / "EURGBP_M1.csv", "utc", "fx"), "NZDUSD": (DEEP / "NZDUSD_M1.csv", "utc", "fx"),
    "USDCHF": (DEEP / "USDCHF_M1.csv", "utc", "fx"), "AUDJPY": (DEEP / "AUDJPY_M1.csv", "utc", "fx"),
    "EURJPY": (DEEP / "EURJPY_M1.csv", "utc", "fx"), "AUDUSD": (DEEP / "AUDUSD_M1.csv", "utc", "fx"),
    "USDCAD": (DEEP / "USDCAD_M1.csv", "utc", "fx"), "USDJPY": (DEEP / "USDJPY_M1.csv", "utc", "fx"),
}


def _daily(df: pd.DataFrame, day) -> pd.DataFrame:
    df = df.assign(_day=day)
    g = df.groupby("_day", sort=True)
    out = pd.DataFrame({
        "open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
        "close": g["close"].last(), "tick_volume": g["tick_volume"].sum(),
        "spread_open": g["spread"].first(), "spread_mean": g["spread"].mean(),
    })
    out.index = pd.to_datetime(list(out.index)); out.index.name = "date"
    return out.sort_index()


def build(sym: str) -> dict:
    path, src, cls = INSTR[sym]
    df = pd.read_csv(path, usecols=["timestamp_utc", "open", "high", "low", "close", "tick_volume", "spread"])
    ts = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")  # naive
    if src == "utc":
        eet_day = ts.dt.tz_localize("UTC").dt.tz_convert(TZ).dt.date
        utc_day = ts.dt.date
    else:  # eet-naive
        eet_day = ts.dt.date
        utc_day = ts.dt.tz_localize(TZ, ambiguous=True, nonexistent="shift_forward").dt.tz_convert("UTC").dt.date
    d_eet = _daily(df, list(eet_day))
    d_utc = _daily(df, list(utc_day))
    d_eet.to_parquet(OUT / f"{sym}_EET.parquet")
    d_utc.to_parquet(OUT / f"{sym}_UTC.parquet")
    return dict(sym=sym, cls=cls, src=src, rows_m1=len(df),
                days_eet=len(d_eet), start=str(d_eet.index.min().date()), end=str(d_eet.index.max().date()))


def main() -> None:
    syms = sys.argv[1:] or list(INSTR)
    cov = []
    for s in syms:
        r = build(s)
        cov.append(r)
        print(f"  {s:7} [{r['cls']:9}] {r['days_eet']:5}d {r['start']}->{r['end']} (m1={r['rows_m1']:,})", flush=True)
    pd.DataFrame(cov).to_csv(OUT / "coverage.csv", index=False)
    print(f"\ncoverage -> {OUT/'coverage.csv'}")


if __name__ == "__main__":
    main()
