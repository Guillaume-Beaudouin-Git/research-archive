"""
assemble_commodities.py — TRACK B: format net-new commodity Dukascopy caches into the canonical
8-col schema in TRUE UTC. NO FTMO splice (commodities have no existing FTMO M1 except gold, untouched).

Spread basis (STEP 4, honest — ftmo_specs has NO spread column, so spec-anchor is unavailable):
  - XAGUSD (silver, metal like gold) -> 'gold-proxy': raw ECN spread × gold's hour-of-UTC ECN→MT5
    multiplier (fitted on the 2024 FTMO-XAU vs Duka-XAU overlap).
  - all others (energies/copper/ags) -> 'ECN_RAW_UNCALIBRATED': raw Dukascopy ask−bid spread.
Tag goes in the MANIFEST, schema stays 8 cols. real_volume=0 (Dukascopy has none); volume availability
reported per instrument.

Output: data/deep_history_utc/<SYM>_M1.csv  + reports/commodity_assembly.json
"""
from __future__ import annotations
import json, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
import duka_m1_backfill as D  # noqa: E402
from duka_commodities import COMM  # noqa: E402

OUT = D.BASE.parent / "deep_history_utc"
PANEL = D.BASE.parent / "panels" / "m5_indices"
REP = D.BASE / "reports"; REP.mkdir(exist_ok=True)
SCHEMA = ["timestamp_utc", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
TZ = "Europe/Bucharest"
XAU_POINT = 1e-2  # FTMO gold (digits=2)


def fmt(s, dp):
    return pd.to_numeric(s, errors="coerce").round(dp).map("{:.5f}".format)


def gold_hour_ratio() -> dict:
    """Hour-of-UTC median(FTMO_XAU_spread / Duka_XAU_spread) on the 2024 overlap -> ECN→MT5 proxy."""
    duka = pd.read_parquet(D.CACHE / "XAUUSD_2024.parquet")
    duka["ts"] = pd.to_datetime(duka["ts_utc"]); duka["dpts"] = ((duka["ask_close"] - duka["close"]) / XAU_POINT).round().clip(lower=0)
    f = pd.read_csv(PANEL / "XAUUSD_M1.csv", usecols=["timestamp_utc", "spread"])
    ts = pd.to_datetime(f["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    utc = ts.dt.tz_localize(TZ, ambiguous=True, nonexistent="shift_forward").dt.tz_convert("UTC").dt.tz_localize(None)
    f = f.assign(ts=utc, fpts=pd.to_numeric(f["spread"], errors="coerce"))
    f = f[(f["ts"] >= "2024-01-01") & (f["ts"] < "2025-01-01")]
    m = duka.merge(f[["ts", "fpts"]], on="ts", how="inner")
    m = m[m["dpts"] > 0]; m["hour"] = m["ts"].dt.hour
    overall = float((m["fpts"] / m["dpts"]).median())
    r = {}
    for h in range(24):
        b = m[m["hour"] == h]
        r[h] = float((b["fpts"] / b["dpts"]).median()) if len(b) >= 50 else overall
        if not np.isfinite(r[h]) or r[h] <= 0:
            r[h] = overall
    r["_overall"] = overall
    r["_n"] = len(m)
    return r


def assemble(sym: str, cfg: dict, gratio: dict | None) -> dict:
    files = sorted(D.CACHE.glob(f"{sym}_*.parquet"))
    if not files:
        return dict(symbol=sym, status="no_cache")
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    df["ts"] = pd.to_datetime(df["ts_utc"])
    df = df.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    # drop OHLC-invalid bars (rare Dukascopy candle glitches) -> 0-violation deliverable; count reported
    eps = 1e-9
    bad = ((df["high"] < df["open"] - eps) | (df["high"] < df["close"] - eps) | (df["high"] < df["low"] - eps) |
           (df["low"] > df["open"] + eps) | (df["low"] > df["close"] + eps) |
           ((df["open"] <= 0) | (df["high"] <= 0) | (df["low"] <= 0) | (df["close"] <= 0)))
    n_ohlc_dropped = int(bad.sum())
    if n_ohlc_dropped:
        df = df[~bad].reset_index(drop=True)
    point, dp = cfg["point"], cfg["dp"]
    ecn = ((df["ask_close"] - df["close"]) / point).round().clip(lower=0)
    if sym == "XAGUSD" and gratio is not None:
        hr = df["ts"].dt.hour.map({h: gratio[h] for h in range(24)})
        spread = (ecn * hr).round().clip(lower=0).astype("int64")
        basis = f"gold-proxy (×XAU hour-of-UTC ECN→MT5, overall×{gratio['_overall']:.2f}, n={gratio['_n']})"
    else:
        spread = ecn.astype("int64")
        basis = "ECN_RAW_UNCALIBRATED"
    vol = df["volume"].round()
    out = pd.DataFrame({
        "timestamp_utc": df["ts"].dt.strftime("%Y.%m.%d %H:%M:%S"),
        "open": fmt(df["open"], dp), "high": fmt(df["high"], dp),
        "low": fmt(df["low"], dp), "close": fmt(df["close"], dp),
        "tick_volume": vol.astype("int64").astype(str), "spread": spread.astype(str), "real_volume": "0",
    })
    # validation
    o, h, l, c = (pd.to_numeric(out[x]) for x in ("open", "high", "low", "close"))
    eps = 1e-9
    ohlc_viol = int((((h < o - eps) | (h < c - eps) | (h < l - eps) | (l > o + eps) | (l > c + eps)) |
                     ((o <= 0) | (h <= 0) | (l <= 0) | (c <= 0))).sum())
    dts = df["ts"]
    d = dts.diff().dropna()
    big = d[d > pd.Timedelta(minutes=2)]
    wk = big[(dts.loc[big.index].dt.dayofweek == 0) | (big > pd.Timedelta(hours=20))]
    out[SCHEMA].to_csv(OUT / f"{sym}_M1.csv", index=False)
    return dict(symbol=sym, code=cfg["code"], decimalFactor=cfg["df"], point=point, status="ok",
                rows=len(out), start=str(dts.min()), end=str(dts.max()),
                cache_years=sorted({int(f.stem.split("_")[1]) for f in files}),
                monotonic=bool(dts.is_monotonic_increasing), dups=int(dts.duplicated().sum()),
                ohlc_violations=ohlc_viol, ohlc_dropped=n_ohlc_dropped, spread_negative=int((spread < 0).sum()),
                spread_zero_frac=round(float((spread == 0).mean()), 4), spread_median=int(spread.median()),
                spread_p95=int(spread.quantile(0.95)), spread_basis=basis,
                tick_volume_zero_frac=round(float((vol == 0).mean()), 4),
                tick_volume_all_zero=bool((vol == 0).all()), real_volume="all-zero (Dukascopy has none)",
                intraweek_gaps_gt2min=int(len(big) - len(wk)),
                max_gap_hours=round(d.max().total_seconds() / 3600, 2) if len(d) else 0)


def main() -> None:
    import sys
    syms = sys.argv[1:] or list(COMM)
    gratio = None
    if "XAGUSD" in syms:
        gratio = gold_hour_ratio()
        print(f"gold-proxy ratio: overall ×{gratio['_overall']:.3f} (n={gratio['_n']})", flush=True)
    reps = []
    for s in syms:
        r = assemble(s, COMM[s], gratio)
        reps.append(r)
        print(f"  {s:9} {r.get('status')} rows={r.get('rows')} {str(r.get('start'))[:10]}->{str(r.get('end'))[:10]} "
              f"mono={r.get('monotonic')} dups={r.get('dups')} ohlc✗={r.get('ohlc_violations')} "
              f"sprd_med={r.get('spread_median')} z%={r.get('spread_zero_frac')} basis={r.get('spread_basis','')[:18]} "
              f"vol0%={r.get('tick_volume_zero_frac')}", flush=True)
    json.dump(reps, open(REP / "commodity_assembly.json", "w"), indent=2, default=str)
    print(f"\nreport -> {REP/'commodity_assembly.json'}")


if __name__ == "__main__":
    main()
