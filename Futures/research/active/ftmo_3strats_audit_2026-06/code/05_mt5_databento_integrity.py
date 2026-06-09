"""
Integrity check: MT5 US100 M1 vs databento NQ 1-min (RTH overlap).

Tasks:
  (1) Confirm where MT5 US100 M1 becomes "real" intraday (bars/day ≈ 390)
      vs "disguised daily" (bars/day ≈ 1).
  (2) Compare spread distribution by hour-of-day (ET) — focus on 11:00 ET
      (S1 entry) to validate the report's assumed cost model.
  (3) Correlate intraday RTH returns: US100 MT5 vs NQ databento, year by year.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
MT5 = ROOT / "data/ftmo_universe/intraday_m1/indices/US100_M1.csv"
DBN = ROOT / "Futures/research/active/ftmo_3strats_audit_2026-06/results/nq_1m_rth_2010_2026.parquet"
RES = ROOT / "Futures/research/active/ftmo_3strats_audit_2026-06/results"


def main() -> None:
    print(f"[load] MT5 US100 M1 from {MT5}", flush=True)
    mt5 = pd.read_csv(
        MT5,
        parse_dates=["timestamp_utc"],
        date_format="%Y.%m.%d %H:%M:%S",
    )
    mt5["timestamp_utc"] = pd.to_datetime(mt5["timestamp_utc"], utc=True)
    mt5 = mt5.set_index("timestamp_utc").sort_index()
    print(f"[mt5] rows={len(mt5):,} time={mt5.index.min()} → {mt5.index.max()}", flush=True)

    # Convert to ET
    mt5_et = mt5.tz_convert("America/New_York").copy()
    mt5_et["date_et"] = mt5_et.index.normalize().date
    mt5_et["t_et"] = mt5_et.index.time

    # (1) Bars per day, per year — to find true intraday start
    bpd = mt5_et.groupby("date_et").size()
    yearly = bpd.groupby(pd.Index(bpd.index).map(lambda d: d.year)).agg(
        ["median", "mean", "min", "max", "count"]
    )
    print("\n[bars/day by year]\n" + yearly.to_string(), flush=True)
    yearly.to_csv(RES / "mt5_us100_bars_per_day_by_year.csv")

    # (2) Spread by hour-of-day (ET), restricted to RTH-ish hours and 2021+
    from datetime import time
    rth = (mt5_et["t_et"] >= time(9, 30)) & (mt5_et["t_et"] < time(16, 0))
    period = mt5_et.index.year >= 2021
    sub = mt5_et.loc[rth & period].copy()
    sub["hour_et"] = sub.index.hour
    sub["min_et"] = sub.index.minute
    # bucket: 09:30, 10:00, ..., 15:30
    sub["bucket"] = sub["hour_et"].astype(str).str.zfill(2) + ":" + (
        sub["min_et"] // 30 * 30
    ).astype(str).str.zfill(2)
    spr_h = (
        sub.groupby("bucket")["spread"]
        .agg(["median", "mean", lambda x: x.quantile(0.95)])
    )
    spr_h.columns = ["median", "mean", "p95"]
    print("\n[spread MT5 by 30-min RTH bucket, 2021+ (points)]\n" + spr_h.to_string(), flush=True)
    spr_h.to_csv(RES / "mt5_us100_spread_by_hour_rth.csv")

    # Convert spread points → bps (assumes 1 MT5 point = 0.01 USD; US100 ~ 18000)
    # Approx price = median close in 2024
    px_median = float(mt5_et.loc["2024-01-01":"2024-12-31", "close"].median())
    print(f"[spread→bps] US100 median 2024 close ≈ {px_median:.1f}", flush=True)
    # Hypothesis A: 1 point = 0.01 USD (FTMO US100 typical)
    bps_A = spr_h["median"] * 0.01 / px_median * 1e4
    bps_A.name = "median_bps_A_pt0.01"
    # Hypothesis B: 1 point = 0.1 USD
    bps_B = spr_h["median"] * 0.1 / px_median * 1e4
    bps_B.name = "median_bps_B_pt0.1"
    bps_tab = pd.concat([spr_h["median"], bps_A, bps_B], axis=1)
    print("\n[spread → bps under point conventions]\n" + bps_tab.to_string(), flush=True)
    bps_tab.to_csv(RES / "mt5_us100_spread_bps.csv")

    # (3) Intraday return correlation: US100 MT5 vs NQ databento (overlap)
    dbn = pd.read_parquet(DBN)
    dbn.index = pd.to_datetime(dbn.index)
    dbn["date_et"] = dbn.index.normalize().date
    dbn["t_et"] = dbn.index.time

    from datetime import time as dt
    # For each session day, compute (open(09:30), open(11:00)) for both
    def session_keys(df: pd.DataFrame, label: str) -> pd.DataFrame:
        o930 = df[df["t_et"] == dt(9, 30)].groupby("date_et")["open"].first()
        o1100 = df[df["t_et"] == dt(11, 0)].groupby("date_et")["open"].first()
        close16 = df.groupby("date_et")["close"].last()
        out = pd.DataFrame({"o930": o930, "o1100": o1100, "close16": close16})
        out["ret_0930_1100"] = out["o1100"] / out["o930"] - 1
        out["ret_1100_close"] = out["close16"] / out["o1100"] - 1
        out["ret_open_close"] = out["close16"] / out["o930"] - 1
        out.columns = [f"{label}_{c}" for c in out.columns]
        return out

    mt5_k = session_keys(mt5_et, "mt5")
    dbn_k = session_keys(dbn, "dbn")
    merged = mt5_k.join(dbn_k, how="inner")
    merged.index = pd.to_datetime(merged.index)
    print(f"\n[merge] common session days={len(merged):,}", flush=True)

    # Year-by-year correlation for ret_0930_1100 and ret_open_close
    merged["year"] = merged.index.year
    yearly_corr = []
    for y, g in merged.groupby("year"):
        if len(g) < 50:
            continue
        c_signal = g[["mt5_ret_0930_1100", "dbn_ret_0930_1100"]].corr().iloc[0, 1]
        c_full = g[["mt5_ret_open_close", "dbn_ret_open_close"]].corr().iloc[0, 1]
        yearly_corr.append(
            {"year": int(y), "n_days": int(len(g)), "corr_signal_ret": c_signal, "corr_open_close": c_full}
        )
    cdf = pd.DataFrame(yearly_corr)
    print("\n[year-by-year corr MT5 vs databento RTH intraday]\n" + cdf.to_string(index=False), flush=True)
    cdf.to_csv(RES / "mt5_vs_databento_corr_by_year.csv", index=False)

    # Bonus: 2018-2020 confirmation that MT5 is "daily disguised"
    pre = merged.loc["2018-01-01":"2020-12-31"]
    post = merged.loc["2021-01-01":"2025-12-31"]
    print(
        f"\n[pre 2021] n={len(pre)} | corr_signal_ret={pre[['mt5_ret_0930_1100','dbn_ret_0930_1100']].corr().iloc[0,1]:.3f}",
        flush=True,
    )
    print(
        f"[post 2021] n={len(post)} | corr_signal_ret={post[['mt5_ret_0930_1100','dbn_ret_0930_1100']].corr().iloc[0,1]:.3f}",
        flush=True,
    )

    summary = {
        "mt5_bars_per_day_by_year_csv": "results/mt5_us100_bars_per_day_by_year.csv",
        "mt5_spread_by_hour_csv": "results/mt5_us100_spread_by_hour_rth.csv",
        "mt5_spread_bps_csv": "results/mt5_us100_spread_bps.csv",
        "mt5_vs_databento_corr_csv": "results/mt5_vs_databento_corr_by_year.csv",
        "pre_2021_corr_signal_ret": float(pre[['mt5_ret_0930_1100','dbn_ret_0930_1100']].corr().iloc[0,1]) if len(pre) > 50 else None,
        "post_2021_corr_signal_ret": float(post[['mt5_ret_0930_1100','dbn_ret_0930_1100']].corr().iloc[0,1]),
        "us100_median_close_2024": px_median,
    }
    (RES / "mt5_databento_integrity.json").write_text(json.dumps(summary, indent=2))
    print(f"\n[save] {RES / 'mt5_databento_integrity.json'}", flush=True)


if __name__ == "__main__":
    main()
