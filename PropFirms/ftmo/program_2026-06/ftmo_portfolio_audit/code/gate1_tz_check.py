"""
gate1_tz_check.py — INDEPENDENT empirical timezone verification (audit Gate 1).

Hard rule: verify timezone EMPIRICALLY; do not trust the "timestamp_utc" label or
the MANIFEST claim. READ-ONLY on all source data.

Methods (modal-session / price-alignment):
  1. US30 (deep_history_utc): bar-density by hour-of-day. A US index cash session
     should show bars concentrated 13:30-20:00 UTC if the stamp is TRUE UTC
     (EDT 09:30-16:00 -> 13:30-20:00 UTC summer; EST -> 14:30-21:00 winter).
     If EET-mislabeled (UTC+2/+3), the window would sit at ~15:30-22:00.
  2. EURUSD panel vs deep: price-alignment. For an overlapping window, find the
     integer hour shift s that maximizes corr(panel_close(t), deep_close(t+s)).
     s=0 -> panel is true UTC; s=+2/+3 -> panel is EET/EEST (stamp ahead of UTC).
  3. BTCUSD panel: hour-of-day activity + day-count; infer via shared exporter with
     EURUSD panel. Cross-check vs binance BTC (genuinely UTC).
  4. Recount US30 daily UTC vs EET days to explain the 3754 vs 3279 anomaly.

Outputs: results/gate1_tz.json  + console summary.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
DEEP = ROOT / "data/deep_history_utc"
PANEL = ROOT / "data/panels/m5_indices"
OUT = ROOT / "research/ftmo_portfolio_audit/results"
OUT.mkdir(parents=True, exist_ok=True)

FMT = "%Y.%m.%d %H:%M:%S"


def read_ts(path, cols=("timestamp_utc",), year=None):
    df = pd.read_csv(path, usecols=list(cols))
    ts = pd.to_datetime(df["timestamp_utc"], format=FMT, errors="coerce")
    df = df.drop(columns=["timestamp_utc"]).assign(ts=ts).dropna(subset=["ts"]).set_index("ts").sort_index()
    if year is not None:
        df = df.loc[str(year)]
    return df


def hour_profile(idx) -> pd.Series:
    return pd.Series(1, index=idx).groupby(idx.hour).count()


def main():
    res = {}

    # ---- 1. US30 deep_history_utc: session window by hour-of-day --------------
    print("[1] US30 deep_history_utc hour-of-day bar density (2024) ...", flush=True)
    us30 = read_ts(DEEP / "US30_M1.csv", year=2024)
    hp = hour_profile(us30.index)
    hp_frac = (hp / hp.sum()).round(4)
    active_hours = hp_frac[hp_frac > 0.005].index.tolist()  # hours holding >0.5% of bars
    res["us30_hour_density_2024"] = hp_frac.to_dict()
    res["us30_active_hours_utc"] = active_hours
    res["us30_modal_window"] = [min(active_hours), max(active_hours)] if active_hours else None
    print("    active UTC hours:", active_hours)
    print("    -> US cash 13:30-20:00 UTC (DST) would give hours 13..20; EET-mislabel -> 15..22")

    # day-of-week × hour (Sunday presence -> CFD around-the-clock vs cash-only)
    dow = us30.index.dayofweek
    res["us30_bars_by_dow_2024"] = pd.Series(1, index=us30.index).groupby(dow).count().to_dict()

    # ---- 2. EURUSD panel vs deep: price-alignment offset ---------------------
    print("[2] EURUSD panel-vs-deep price alignment (2024-06) ...", flush=True)
    ed = read_ts(DEEP / "EURUSD_M1.csv", cols=("timestamp_utc", "close"), year=2024)
    ep = read_ts(PANEL / "EURUSD_M1.csv", cols=("timestamp_utc", "close"), year=2024)
    # restrict to a clean summer month (EEST = UTC+3) to disambiguate +2 vs +3
    ed_m = ed.loc["2024-06"]["close"].resample("1min").last()
    ep_m = ep.loc["2024-06"]["close"].resample("1min").last()
    best = {}
    for s in range(-4, 5):
        shifted = ed_m.shift(-s * 60)  # deep moved by s hours
        j = pd.concat([ep_m.rename("panel"), shifted.rename("deep")], axis=1).dropna()
        if len(j) > 1000:
            best[s] = float(j["panel"].corr(j["deep"]))
    best_shift = max(best, key=best.get) if best else None
    res["eurusd_panel_align_corr_by_hourshift"] = {str(k): round(v, 6) for k, v in best.items()}
    res["eurusd_panel_best_hourshift_vs_deep"] = best_shift
    print("    corr by hour-shift (panel vs deep shifted):",
          {k: round(v, 5) for k, v in best.items()})
    print(f"    -> best shift = {best_shift}h  (0=panel is UTC; +2/+3=panel is EET/EEST)")

    # ---- 3. BTCUSD panel hour activity + vs binance --------------------------
    print("[3] BTCUSD panel hour-of-day (2024) + binance cross-check ...", flush=True)
    bp = read_ts(PANEL / "BTCUSD_M1.csv", cols=("timestamp_utc", "close"), year=2024)
    res["btc_panel_hour_density_2024"] = (hour_profile(bp.index) /
                                          len(bp)).round(4).to_dict()
    binp = PANEL / "binance/BTCUSD_M1.csv"
    if binp.exists():
        try:
            bb = read_ts(binp, cols=("timestamp_utc", "close"), year=2024)
            bp_m = bp.loc["2024-06"]["close"].resample("1min").last()
            bb_m = bb.loc["2024-06"]["close"].resample("1min").last()
            bbest = {}
            for s in range(-4, 5):
                shifted = bb_m.shift(-s * 60)
                j = pd.concat([bp_m.rename("panel"), shifted.rename("bin")], axis=1).dropna()
                if len(j) > 1000:
                    bbest[s] = float(j["panel"].corr(j["bin"]))
            res["btc_panel_vs_binance_corr_by_hourshift"] = {str(k): round(v, 6) for k, v in bbest.items()}
            res["btc_panel_best_hourshift_vs_binance"] = max(bbest, key=bbest.get) if bbest else None
            print("    BTC panel vs binance corr by shift:", {k: round(v, 5) for k, v in bbest.items()})
            print(f"    -> best shift = {res['btc_panel_best_hourshift_vs_binance']}h (binance=UTC truth)")
        except Exception as e:
            res["btc_binance_error"] = str(e)
            print("    binance check failed:", e)

    # ---- 4. US30 daily UTC vs EET day-count anomaly --------------------------
    print("[4] US30 daily UTC vs EET day recount ...", flush=True)
    d_utc = pd.read_parquet(ROOT / "research/s076_replication/daily/US30_UTC.parquet")
    d_eet = pd.read_parquet(ROOT / "research/s076_replication/daily/US30_EET.parquet")
    # weekend days present?
    res["us30_daily_utc_n"] = int(len(d_utc))
    res["us30_daily_eet_n"] = int(len(d_eet))
    res["us30_daily_utc_weekend_days"] = int((d_utc.index.dayofweek >= 5).sum())
    res["us30_daily_eet_weekend_days"] = int((d_eet.index.dayofweek >= 5).sum())
    # tiny-bar days (a UTC midnight split can create sliver days)
    res["us30_daily_utc_per_year"] = d_utc.groupby(d_utc.index.year).size().to_dict()
    res["us30_daily_eet_per_year"] = d_eet.groupby(d_eet.index.year).size().to_dict()
    print(f"    UTC days={len(d_utc)} (weekend={res['us30_daily_utc_weekend_days']}), "
          f"EET days={len(d_eet)} (weekend={res['us30_daily_eet_weekend_days']})")

    (OUT / "gate1_tz.json").write_text(json.dumps(res, indent=2, default=str))
    print("\nwrote", OUT / "gate1_tz.json")


if __name__ == "__main__":
    main()
