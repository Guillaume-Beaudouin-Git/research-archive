"""tz_verification.py — empirical check that deep_history_utc EURUSD is TRUE UTC.

Run once at migration (2026-06-10) before re-running step0/step1 on the new source.
The old source (m5_indices/EURUSD_M1.csv) was EET/EEST broker time mislabeled UTC,
so every fix window in the original study was shifted by +2h/+3h of true time.

Markers (median spread / mean tick_volume by minute-of-day, DST-pure months
Dec-Feb = winter, Jun-Aug = summer):
1. Broker rollover spread spike must sit at ~21:00-22:05 UTC (17:00 NY / MT5 server
   midnight converted), NOT at 00:00 — where the EET-era run saw it ("Tokyo fix"
   med 17 pts / p95 46 pts was the rollover artifact).
2. WMR London fix tick_volume bump: 15:55-16:05 UTC in winter, 14:55-15:05 UTC in
   summer, vs the surrounding 3h baseline. The seasonally-shifted control window
   must NOT show the same bump.
3. Tokyo fix 00:50-01:00 UTC spread must be moderate (Asian session, not rollover).

Output: printed table — quoted verbatim in FIX_REVERSAL_TZ_MIGRATION.md.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[4]
SRC = REPO / "data/deep_history_utc/EURUSD_M1.csv"


def main() -> None:
    df = pd.read_csv(SRC, usecols=["timestamp_utc", "spread", "tick_volume"])
    ts = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S",
                        errors="coerce")
    df = df.loc[ts.notna()].copy()
    ts = ts.dropna()
    df["mod"] = ts.dt.hour * 60 + ts.dt.minute
    df["month"] = ts.dt.month
    print(f"[load] {len(df):,} rows | {ts.min()} -> {ts.max()}")

    winter = df[df["month"].isin([12, 1, 2])]
    summer = df[df["month"].isin([6, 7, 8])]

    # -- 1. rollover spike: top minutes by median spread (all year) -----------
    sp = df[df["spread"] > 0]
    med_by_min = sp.groupby("mod")["spread"].median().sort_values(ascending=False)
    print("\n[1] Top-8 minutes-of-day by MEDIAN spread (expect ~21:00-22:05 UTC):")
    for mod, v in med_by_min.head(8).items():
        print(f"    {mod // 60:02d}:{mod % 60:02d} UTC  med={v:.0f} pts")

    # -- 2. WMR London fix volume bump (seasonal) ------------------------------
    def vol_ratio(d: pd.DataFrame, lo: int, hi: int, base_lo: int, base_hi: int
                  ) -> tuple[float, float, float]:
        win = d[(d["mod"] >= lo) & (d["mod"] < hi)]["tick_volume"].mean()
        base = d[(d["mod"] >= base_lo) & (d["mod"] < base_hi)]["tick_volume"].mean()
        return win, base, win / base

    w_fix = 15 * 60 + 55, 16 * 60 + 5     # 15:55-16:05 UTC
    s_fix = 14 * 60 + 55, 15 * 60 + 5     # 14:55-15:05 UTC
    base_w = 14 * 60, 17 * 60
    base_s = 13 * 60, 16 * 60
    print("\n[2] WMR London fix tick_volume bump (window mean / 3h-baseline mean):")
    for label, d, fix, base in [
        ("winter @15:55-16:05 (expected bump)", winter, w_fix, base_w),
        ("winter @14:55-15:05 (control)",       winter, s_fix, base_s),
        ("summer @14:55-15:05 (expected bump)", summer, s_fix, base_s),
        ("summer @15:55-16:05 (control)",       summer, w_fix, base_w),
    ]:
        win, base_v, ratio = vol_ratio(d, fix[0], fix[1], base[0], base[1])
        print(f"    {label:42s} win={win:7.1f} base={base_v:7.1f} "
              f"ratio={ratio:.2f}")

    # -- 3. Tokyo fix window spread (true 00:50-01:00 UTC) ---------------------
    tok = sp[(sp["mod"] >= 50) & (sp["mod"] < 60)]["spread"]
    print(f"\n[3] Tokyo fix 00:50-01:00 UTC spread: med={tok.median():.0f} pts  "
          f"p95={tok.quantile(0.95):.0f} pts  N={len(tok):,}")
    print("    (EET-era run measured med=17 / p95=46 pts here — the rollover artifact)")

    # -- old 'rollover at midnight' control ------------------------------------
    mid = sp[(sp["mod"] >= 23 * 60 + 55) | (sp["mod"] < 5)]["spread"]
    print(f"[3b] Midnight 23:55-00:05 UTC spread: med={mid.median():.0f} pts  "
          f"p95={mid.quantile(0.95):.0f} pts (true-UTC midnight = mid-Asia, "
          f"should be moderate)")


if __name__ == "__main__":
    main()
