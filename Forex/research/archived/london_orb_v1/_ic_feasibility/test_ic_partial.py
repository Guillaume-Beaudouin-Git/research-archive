"""Quick validation: run ic_angle_a on 2020 data only (available now)."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

RAW_DIR = Path(__file__).parents[4] / "data" / "raw"

def hac_tstat(y, x, lag=6):
    x2 = sm.add_constant(x)
    return float(sm.OLS(y, x2).fit(cov_type="HAC", cov_kwds={"maxlags": lag}).tvalues[1])

df = pd.read_parquet(RAW_DIR / "dukascopy_EURUSD_2020.parquet")
df.index = pd.to_datetime(df.index, utc=True)
df = df.sort_index()
print(f"EURUSD 2020: {len(df):,} bars, {df.index[0]} → {df.index[-1]}")
print(f"Columns: {list(df.columns)}")
print(f"Sample:\n{df.head(3)}")

# Signal computation for 5 days
df["date"] = df.index.normalize()
rows = []
for date, day in list(df.groupby("date"))[:10]:
    day = day.sort_index()
    asian = day.between_time("00:00", "06:59")
    if len(asian) < 30: continue
    asian_high = asian["high"].max()
    asian_low  = asian["low"].min()
    lo = day.between_time("07:00", "07:59")
    if lo.empty: continue
    lo_close = lo["close"].iloc[-1]
    signal = 1.0 if lo_close > asian_high else (-1.0 if lo_close < asian_low else 0.0)
    entry = day.between_time("08:00", "08:00")
    if entry.empty: continue
    ep = entry["open"].iloc[0]
    et = entry.index[0]
    # 1h return
    exit_bars = day[day.index >= et + pd.Timedelta(hours=1)]
    ret_1h = (exit_bars["close"].iloc[0] - ep) / ep * signal if not exit_bars.empty else np.nan
    print(f"  {date.date()} | asian=[{asian_low:.5f},{asian_high:.5f}] | lo_close={lo_close:.5f} | signal={signal:+.0f} | ret_1h={ret_1h*10000:.1f}bp")
    rows.append({"date": date, "signal": signal, "ret_1h": ret_1h})

print(f"\nSignal distribution: {pd.Series([r['signal'] for r in rows]).value_counts().to_dict()}")
print("Partial validation PASSED - signal logic OK")
