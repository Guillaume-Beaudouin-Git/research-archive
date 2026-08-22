#!/usr/bin/env python
"""READ-ONLY empirical source fingerprint + coverage + quality for the
MT5-schema OHLCV CSVs in data/panels/m5_indices/ (and Binance contrast files).
Writes audit/_intermediate/mt5_fingerprint.json incrementally. Modifies no data."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
PANEL = ROOT / "data" / "panels" / "m5_indices"
OUT = ROOT / "audit" / "_intermediate"
OUT.mkdir(parents=True, exist_ok=True)
OUTJSON = OUT / "mt5_fingerprint.json"

JOBS = [
    ("EURUSD", "EURUSD_M1.csv", "mt5_ftmo", "M1"),
    ("GBPUSD", "GBPUSD_M1.csv", "mt5_ftmo", "M1"),
    ("USDJPY", "USDJPY_M1.csv", "mt5_ftmo", "M1"),
    ("USDCHF", "USDCHF_M1.csv", "mt5_ftmo", "M1"),
    ("USDCAD", "USDCAD_M1.csv", "mt5_ftmo", "M1"),
    ("AUDUSD", "AUDUSD_M1.csv", "mt5_ftmo", "M1"),
    ("NZDUSD", "NZDUSD_M1.csv", "mt5_ftmo", "M1"),
    ("EURGBP", "EURGBP_M1.csv", "mt5_ftmo", "M1"),
    ("EURJPY", "EURJPY_M1.csv", "mt5_ftmo", "M1"),
    ("AUDJPY", "AUDJPY_M1.csv", "mt5_ftmo", "M1"),
    ("US500", "US500_M1.csv", "mt5_ftmo", "M1"),
    ("US100", "US100_M1.csv", "mt5_ftmo", "M1"),
    ("US30", "US30_M1.csv", "mt5_ftmo", "M1"),
    ("US2000", "US2000_M1.csv", "mt5_ftmo", "M1"),
    ("GER40", "GER40_M1.csv", "mt5_ftmo", "M1"),
    ("US500_M5", "US500_M5.csv", "mt5_ftmo", "M5"),
    ("US100_M5", "US100_M5.csv", "mt5_ftmo", "M5"),
    ("XAUUSD", "XAUUSD_M1.csv", "mt5_ftmo", "M1"),
    ("BTCUSD_mt5", "BTCUSD_M1.csv", "mt5_ftmo", "M1"),
    ("ETHUSD_binance", "binance/ETHUSD_M1.csv", "binance", "M1"),
    ("BTCUSD_binance", "binance/BTCUSD_M1.csv", "binance", "M1"),
    ("SOLUSD_binance", "binance/SOLUSD_M1.csv", "binance", "M1"),
]

def parse_ts(s, group):
    if group == "binance":
        return pd.to_datetime(s, format="%Y-%m-%d %H:%M:%S", errors="coerce")
    t = pd.to_datetime(s, format="%Y.%m.%d %H:%M:%S", errors="coerce")
    if t.isna().mean() > 0.5:
        t = pd.to_datetime(s, errors="coerce")
    return t

def digits_from_str(close_str):
    samp = close_str.dropna().astype(str)
    samp = samp[samp.str.contains(".", regex=False)].head(20000)
    if len(samp) == 0:
        return 0
    return int(samp.str.split(".").str[-1].str.len().mode().iloc[0])

def mode_float(arr):
    if len(arr) == 0:
        return None
    vals, counts = np.unique(arr, return_counts=True)
    return float(vals[np.argmax(counts)])

def fingerprint(label, relpath, group, reso):
    p = PANEL / relpath
    r = {"label": label, "path": str(p.relative_to(ROOT)), "group": group,
         "resolution_label": reso, "exists": p.exists()}
    if not p.exists():
        r["error"] = "missing"; return r
    r["size_mb"] = round(p.stat().st_size / 1e6, 1)
    with open(p, "r") as fh:
        header = fh.readline().strip().split(",")
    r["columns"] = header
    want = [c for c in ["timestamp_utc","open","high","low","close","tick_volume","spread","real_volume"] if c in header]
    df = pd.read_csv(p, usecols=want, dtype={"timestamp_utc": str, "close": str}, engine="c")
    r["rows_raw"] = int(len(df))
    r["digits"] = digits_from_str(df["close"])
    # NaN counts on full column (pre-filter)
    r["nan_counts"] = {c: int(pd.to_numeric(df[c], errors="coerce").isna().sum())
                       for c in ["open","high","low","close"] if c in df.columns}
    ts = parse_ts(df["timestamp_utc"], group)
    valid = ts.notna().values
    r["ts_unparseable"] = int((~valid).sum())
    def col(name):
        return pd.to_numeric(df[name], errors="coerce").values[valid] if name in df.columns else None
    o, h, l, c = col("open"), col("high"), col("low"), col("close")
    sp, tv, rv = col("spread"), col("tick_volume"), col("real_volume")
    tsv = ts.values[valid].astype("datetime64[ns]")
    r["rows"] = int(len(tsv))
    # nonmonotonic in original order
    r["nonmonotonic_count"] = int((np.diff(tsv) < np.timedelta64(0)).sum())
    # sort everything by ts
    so = np.argsort(tsv, kind="mergesort")
    tsv = tsv[so]; o, h, l, c = o[so], h[so], l[so], c[so]
    if sp is not None: sp = sp[so]
    if tv is not None: tv = tv[so]
    if rv is not None: rv = rv[so]
    tidx = pd.DatetimeIndex(tsv)
    r["first_ts"] = str(tidx[0]); r["last_ts"] = str(tidx[-1])
    # dup + step
    ddiff = np.diff(tsv).astype("timedelta64[s]").astype(float)
    r["dup_count"] = int((ddiff == 0).sum())
    nzstep = ddiff[ddiff > 0]
    r["modal_step_sec"] = mode_float(nzstep)
    r["median_step_sec"] = float(np.median(nzstep)) if len(nzstep) else None
    step = r["modal_step_sec"] or (60.0 if reso == "M1" else 300.0)
    hours = tidx.hour.values
    liq = (hours >= 13) & (hours < 16)
    # ---- spread ----
    if sp is not None:
        spv = sp[~np.isnan(sp)]
        r["spread_present"] = True
        r["spread_is_integer"] = bool(np.allclose(spv, np.round(spv))) if len(spv) else None
        r["spread_allzero"] = bool((spv == 0).all()) if len(spv) else None
        r["spread_neg_count"] = int((spv < 0).sum())
        r["spread_zero_count"] = int((spv == 0).sum())
        r["spread_zero_frac"] = float((spv == 0).mean()) if len(spv) else None
        if len(spv) and not r["spread_allzero"]:
            qs = np.quantile(spv, [0, .01, .05, .5, .95, 1.0])
            for k, qq in zip(["spread_min","spread_p1","spread_p5","spread_p50","spread_p95","spread_max"], qs):
                r[k] = float(qq)
            nz = spv[spv > 0]
            r["spread_mult5_frac"] = float((nz % 5 == 0).mean())
            r["spread_mult10_frac"] = float((nz % 10 == 0).mean())
            vals, counts = np.unique(nz, return_counts=True)
            topi = np.argsort(counts)[::-1][:6]
            r["spread_top_values"] = {str(int(vals[i])): int(counts[i]) for i in topi}
            r["spread_modal_value"] = int(vals[np.argmax(counts)])
            spl = sp[liq]; spl = spl[~np.isnan(spl)]
            if len(spl):
                r["spread_min_liquidhrs"] = float(spl.min())
                r["spread_p50_liquidhrs"] = float(np.median(spl))
            if r["digits"] in (3, 5):
                r["spread_p50_pips"] = round(r["spread_p50"] / 10.0, 3)
                r["spread_min_pips"] = round(r["spread_min"] / 10.0, 3)
    else:
        r["spread_present"] = False
    # ---- tick_volume ----
    if tv is not None:
        tvv = tv[~np.isnan(tv)]
        r["tickvol_median_all"] = float(np.median(tvv)) if len(tvv) else None
        tvl = tv[liq]; tvl = tvl[~np.isnan(tvl)]
        r["tickvol_median_liquidhrs"] = float(np.median(tvl)) if len(tvl) else None
        r["tickvol_max"] = float(np.nanmax(tv)) if len(tvv) else None
    # ---- real_volume ----
    if rv is not None:
        rvv = np.nan_to_num(rv)
        r["realvol_all_zero"] = bool((rvv == 0).all())
        r["realvol_max"] = float(rvv.max())
    # ---- OHLC validity ----
    hmax = np.maximum.reduce([o, c, l]); lmin = np.minimum.reduce([o, c, h])
    r["ohlc_high_violation"] = int(np.nansum(h < hmax))
    r["ohlc_low_violation"] = int(np.nansum(l > lmin))
    r["ohlc_high_lt_low"] = int(np.nansum(h < l))
    r["nonpositive_price_rows"] = int(np.nansum((o <= 0) | (h <= 0) | (l <= 0) | (c <= 0)))
    # close->open gaps
    with np.errstate(divide="ignore", invalid="ignore"):
        gap = np.log(o[1:] / c[:-1])
    gap = gap[np.isfinite(gap)]
    if len(gap) > 100:
        z = (gap - gap.mean()) / (gap.std() + 1e-12)
        r["gap_abs_z_gt10"] = int((np.abs(z) > 10).sum())
        r["gap_max_abs_logret"] = float(np.abs(gap).max())
    # ---- gaps weekend vs intraweek + sessions ----
    u = np.unique(tsv)
    du = np.diff(u).astype("timedelta64[s]").astype(float)
    st = pd.DatetimeIndex(u[:-1]); en = pd.DatetimeIndex(u[1:])
    big = du > step * 3
    bst, ben, bsec = st[big], en[big], du[big]
    wk = np.zeros(len(bsec), dtype=bool)
    for i in range(len(bsec)):
        a, b = bst[i], ben[i]
        # weekend if a Saturday lies in (a, b] and gap is long
        has_sat = ((pd.date_range(a.normalize(), b.normalize(), freq="D").weekday == 5).any())
        wk[i] = bool(has_sat and bsec[i] >= 8 * 3600)
    iw = ~wk
    r["weekend_gap_count"] = int(wk.sum())
    r["intraweek_gap_count"] = int(iw.sum())
    if iw.any():
        iw_sec = bsec[iw]; iw_st = bst[iw]; iw_en = ben[iw]
        order = np.argsort(iw_sec)[::-1][:8]
        r["largest_intraweek_gaps"] = [
            {"from": str(iw_st[i]), "to": str(iw_en[i]), "hours": round(float(iw_sec[i]) / 3600, 2)}
            for i in order]
        small = iw_sec < 7200
        if small.any():
            tod = iw_st[small].strftime("%H:%M")
            vc = pd.Series(tod).value_counts().head(3)
            r["intraweek_small_gap_modal_tod_utc"] = {k: int(v) for k, v in vc.items()}
    if wk.any():
        r["weekly_open_modal_tod_utc"] = str(pd.Series(ben[wk].strftime("%a %H:%M")).mode().iloc[0])
        r["weekly_close_modal_tod_utc"] = str(pd.Series(bst[wk].strftime("%a %H:%M")).mode().iloc[0])
    # completeness ex-weekends (vs 24x5; upper bound for non-24h instruments)
    bdays = int(np.busday_count(tidx[0].date(), (tidx[-1] + pd.Timedelta(days=1)).date()))
    expected = bdays * 86400 / step if step else None
    r["business_days_span"] = bdays
    r["expected_bars_24x5"] = int(expected) if expected else None
    r["completeness_pct_24x5"] = round(100 * r["rows"] / expected, 1) if expected else None
    del df
    return r

def main():
    results = {}
    if OUTJSON.exists():
        try: results = json.loads(OUTJSON.read_text())
        except Exception: results = {}
    for label, relpath, group, reso in JOBS:
        print(f"[fingerprint] {label} ...", flush=True)
        try:
            r = fingerprint(label, relpath, group, reso)
        except Exception as e:
            import traceback; traceback.print_exc()
            r = {"label": label, "error": f"{type(e).__name__}: {e}"}
        results[label] = r
        OUTJSON.write_text(json.dumps(results, indent=2, default=str))
        print(f"   rows={r.get('rows')} digits={r.get('digits')} step={r.get('modal_step_sec')}s "
              f"sp_p50={r.get('spread_p50')} sp_min={r.get('spread_min')} zero%={r.get('spread_zero_frac')} "
              f"rv0={r.get('realvol_all_zero')} tvLiq={r.get('tickvol_median_liquidhrs')} "
              f"dup={r.get('dup_count')} iwgap={r.get('intraweek_gap_count')} "
              f"compl={r.get('completeness_pct_24x5')} open={r.get('weekly_open_modal_tod_utc')}", flush=True)
    print(f"\nWROTE {OUTJSON}")

if __name__ == "__main__":
    main()
