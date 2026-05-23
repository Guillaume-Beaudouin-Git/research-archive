"""
PREVIEW: IC analysis on EURUSD 2020 only (1 year).
N will be small (~200 breakout days); only a directional signal check, not final IC.
For final results, run ic_angle_a.py and ic_angle_b.py after full 2020-2024 data.
"""

from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

RAW_DIR = Path(__file__).parents[4] / "data" / "raw"
PAIR = "EURUSD"
YEAR = 2020


def hac_tstat(y, x, lag=6):
    x2 = sm.add_constant(x)
    return float(sm.OLS(y, x2).fit(cov_type="HAC", cov_kwds={"maxlags": lag}).tvalues[1])


def main():
    path = RAW_DIR / f"dukascopy_{PAIR}_{YEAR}.parquet"
    if not path.exists():
        print(f"ERROR: {path} not found")
        sys.exit(1)

    df = pd.read_parquet(path)
    df.index = pd.to_datetime(df.index, utc=True)
    df = df.sort_index()
    print(f"EURUSD {YEAR}: {len(df):,} bars, {df.index[0]} → {df.index[-1]}")

    df["date"] = df.index.normalize()
    rows = []
    for date, day in df.groupby("date"):
        day = day.sort_index()
        asian = day.between_time("00:00", "06:59")
        lo    = day.between_time("07:00", "07:59")
        if len(asian) < 30 or lo.empty:
            continue
        asian_high = asian["high"].max()
        asian_low  = asian["low"].min()
        lo_close   = lo["close"].iloc[-1]
        lo_high    = lo["high"].max()
        lo_low     = lo["low"].min()

        sig  = 1.0 if lo_close > asian_high else (-1.0 if lo_close < asian_low else 0.0)
        sig_hl = 1.0 if (lo_high > asian_high and lo_low >= asian_low) else \
                 (-1.0 if (lo_low < asian_low and lo_high <= asian_high) else 0.0)

        entry_bars = day.between_time("08:00", "08:00")
        if entry_bars.empty:
            continue
        ep = entry_bars["open"].iloc[0]
        et = entry_bars.index[0]

        fwd = {}
        for h in [1, 2, 4]:
            exit_bars = day[day.index >= et + pd.Timedelta(hours=h)]
            fwd[f"ret_{h}h"] = (exit_bars["close"].iloc[0] - ep) / ep * sig if not exit_bars.empty else np.nan
            fwd[f"ret_{h}h_hl"] = (exit_bars["close"].iloc[0] - ep) / ep * sig_hl if not exit_bars.empty else np.nan

        rows.append({"date": date, "signal": sig, "signal_hl": sig_hl, **fwd})

    df_s = pd.DataFrame(rows)
    print(f"\nTotal trading days: {len(df_s)}")

    for sig_col, label in [("signal", "close-based"), ("signal_hl", "HL-based")]:
        active = df_s[df_s[sig_col] != 0]
        N = len(active)
        print(f"\n[{label}] Breakout days: {N}/{len(df_s)}")
        print(f"  {'Horizon':<10} {'IC':>8} {'t_HAC':>8} {'N':>6}")
        for h in [1, 2, 4]:
            col = f"ret_{h}h" if sig_col == "signal" else f"ret_{h}h_hl"
            sub = active.dropna(subset=[col])
            if len(sub) < 30:
                continue
            sig_v = sub[sig_col].values
            ret_v = sub[col].values
            ic, _ = stats.spearmanr(sig_v, ret_v)
            t = hac_tstat(ret_v, sig_v, lag=4)  # lag=4 for 1h data
            print(f"  {h}h{'':<7} {ic:>+8.4f} {t:>+8.2f} {len(sub):>6}")


if __name__ == "__main__":
    main()
