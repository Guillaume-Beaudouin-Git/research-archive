"""
assemble.py  (TRUE-UTC edition)
===============================
Splice the existing MT5/FTMO authoritative M1 CSVs with Dukascopy deep-history
backfill/top-up (from duka_m1_backfill.py cache), producing extended series in
**TRUE UTC**.

TZ DIRECTION (overrides the prior EET convention):
  - Existing MT5 files carry broker EET/EEST wall-clock mislabeled `timestamp_utc`.
    We localize them to 'Europe/Bucharest' and convert to **true UTC** (flagging,
    never crashing on, the spring nonexistent hour + autumn ambiguous hour).
  - Dukascopy backfill is already true UTC -> left as-is.
  - Splice + spread hour-of-day bucketing happen in TRUE UTC.
  - Output column stays named `timestamp_utc` but now holds TRUE UTC.

SPREAD CALIBRATION (on the 2024 overlap, true UTC):
  raw Duka spread = round((ask_close - bid_close)/point). Per instrument, bucket by
  hour-of-day (UTC) and fit BOTH an additive (MT5 ≈ Duka + offset_h) and a
  multiplicative (MT5 ≈ Duka × ratio_h) map; pick the one with lower error on a
  held-out (last-30%-by-time) overlap slice. Apply the chosen map to ALL Dukascopy
  rows (pre-existing backfill AND post-existing top-up). Existing spreads are NEVER
  modified. Indices: optionally round calibrated spreads to the existing spread tick.

Existing OHLCV/volume/spread/real_volume values are kept VERBATIM (strings); only the
timestamp is recomputed to true UTC. Output: data/deep_history_utc/<SYM>_M1.csv +
reports/assembly_report.{json,csv}.

Usage:
  /usr/bin/python3 assemble.py --symbol EURUSD
  /usr/bin/python3 assemble.py --symbol EURUSD --gate     # gate-2 thresholds, exit nonzero on fail
  /usr/bin/python3 assemble.py --all
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from duka_m1_backfill import INSTR, CACHE  # noqa: E402

BASE = Path(__file__).resolve().parent
EXIST_DIR = BASE.parent / "panels" / "m5_indices"
OUT = BASE.parent / "deep_history_utc"; OUT.mkdir(parents=True, exist_ok=True)
REP = BASE / "reports"; REP.mkdir(exist_ok=True)
SCHEMA = ["timestamp_utc", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
TZ = "Europe/Bucharest"
CAL_MIN_SAMPLES = 50          # per-hour min sample to trust a bucket param
CAL_YEAR = 2024
TEST_FRAC = 0.30              # held-out tail fraction for model selection


# ----------------------------------------------------------------------------- IO
def load_existing(sym: str) -> pd.DataFrame:
    """Existing MT5 CSV: OHLCV/spread kept verbatim (str); timestamp -> true UTC."""
    p = EXIST_DIR / f"{sym}_M1.csv"
    df = pd.read_csv(p, dtype=str, keep_default_na=False)
    local = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    utc, n_amb, n_ne = eet_to_utc(local)
    df["_ts"] = utc
    df.attrs["n_ambiguous"] = n_amb
    df.attrs["n_nonexistent"] = n_ne
    return df


def eet_to_utc(naive_local: pd.Series):
    """EET/EEST wall-clock (naive) -> true UTC (naive). Returns (utc, n_amb, n_ne)."""
    idx = pd.DatetimeIndex(naive_local)
    # flag counts (never crash): ambiguous = autumn fall-back hour, nonexistent = spring gap
    try:
        a_t = idx.tz_localize(TZ, ambiguous=True, nonexistent="shift_forward")
        a_f = idx.tz_localize(TZ, ambiguous=False, nonexistent="shift_forward")
        n_amb = int((a_t != a_f).sum())
        ne_f = a_t
        ne_b = idx.tz_localize(TZ, ambiguous=True, nonexistent="shift_backward")
        n_ne = int((ne_f != ne_b).sum())
    except Exception:
        n_amb = n_ne = -1  # flag: count unavailable
    # primary: infer DST from monotonic order; fallback: assume first occurrence = DST
    try:
        loc = idx.tz_localize(TZ, ambiguous="infer", nonexistent="shift_forward")
    except Exception:
        loc = idx.tz_localize(TZ, ambiguous=True, nonexistent="shift_forward")
    utc = loc.tz_convert("UTC").tz_localize(None)
    return pd.Series(utc, index=naive_local.index), n_amb, n_ne


def load_duka(sym: str) -> pd.DataFrame | None:
    files = sorted(CACHE.glob(f"{sym}_*.parquet"))   # non-recursive: ignores _failed/
    if not files:
        return None
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    df = df.drop_duplicates("ts_utc").sort_values("ts_utc").reset_index(drop=True)
    df["ts_utc"] = pd.to_datetime(df["ts_utc"])      # already true UTC, naive
    return df


# ------------------------------------------------------------------- spread model
def _per_hour(frame: pd.DataFrame, col: str, min_n: int):
    """Per-hour median of `col` with overall-median fallback for thin buckets."""
    overall = float(frame[col].median()) if len(frame) else 0.0
    if not np.isfinite(overall):
        overall = 0.0
    out = {}
    for h in range(24):
        b = frame.loc[frame["hour"] == h, col]
        v = float(b.median()) if len(b) >= min_n else overall
        out[h] = v if np.isfinite(v) else overall
    return out, overall


def _apply(duka_pts: pd.Series, hour: pd.Series, params: dict, kind: str) -> pd.Series:
    p = hour.map(params).astype(float)
    pred = (duka_pts + p) if kind == "additive" else (duka_pts * p)
    return pred.round().clip(lower=0)


def fit_spread_model(overlap: pd.DataFrame) -> dict:
    """Fit additive & multiplicative hour maps; select by held-out MAE. Refit chosen on all."""
    ov = overlap.sort_values("_ts").reset_index(drop=True)
    ov["add_val"] = ov["ex_spread"] - ov["duka_pts"]
    pos = ov["duka_pts"] > 0
    ov["mult_val"] = np.where(pos, ov["ex_spread"] / ov["duka_pts"].where(pos, np.nan), np.nan)
    n = len(ov)
    cut = int(n * (1 - TEST_FRAC))
    train, test = ov.iloc[:cut], ov.iloc[cut:]

    add_tr, add_overall = _per_hour(train, "add_val", CAL_MIN_SAMPLES)
    mult_tr, mult_overall = _per_hour(train[pos.iloc[:cut].values] if cut else train,
                                      "mult_val", CAL_MIN_SAMPLES)
    res = {"overlap_rows": n, "test_rows": len(test)}
    if len(test) >= 50:
        add_pred = _apply(test["duka_pts"], test["hour"], add_tr, "additive")
        mult_pred = _apply(test["duka_pts"], test["hour"], mult_tr, "multiplicative")
        mae_add = float((add_pred - test["ex_spread"]).abs().mean())
        mae_mult = float((mult_pred - test["ex_spread"]).abs().mean())
    else:
        mae_add, mae_mult = 0.0, np.inf  # too thin -> default additive
    chosen = "additive" if mae_add <= mae_mult else "multiplicative"
    # refit chosen on the FULL overlap for application
    if chosen == "additive":
        params, overall = _per_hour(ov, "add_val", CAL_MIN_SAMPLES)
    else:
        params, overall = _per_hour(ov[pos], "mult_val", CAL_MIN_SAMPLES)
    res.update(model=chosen, mae_add=round(mae_add, 4), mae_mult=round(mae_mult, 4),
               params=params, overall=round(overall, 6))
    return res


def detect_index_tick(ex_spread_pos: pd.Series) -> int:
    """Largest tick g in {50,25,20,10,5} with >=80% of positive existing spreads divisible."""
    v = ex_spread_pos[ex_spread_pos > 0]
    if len(v) < 100:
        return 1
    for g in (50, 25, 20, 10, 5):
        if float((v % g == 0).mean()) >= 0.80:
            return g
    return 1


def fmt_prices(s: pd.Series, dp: int) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").round(dp).map("{:.5f}".format)


def _duka_to_out(sub: pd.DataFrame, dp: int, point: float, params: dict, kind: str,
                 index_tick: int) -> pd.DataFrame:
    """Format a Dukascopy subframe into the canonical schema with calibrated spread."""
    if sub.empty:
        return pd.DataFrame(columns=SCHEMA + ["_ts"])
    pts = ((sub["ask_close"] - sub["close"]) / point).round().clip(lower=0)
    cal = _apply(pts, sub["ts_utc"].dt.hour, params, kind)
    if index_tick > 1:
        cal = (cal / index_tick).round() * index_tick
    cal = cal.astype("int64").clip(lower=0)
    return pd.DataFrame({
        "timestamp_utc": sub["ts_utc"].dt.strftime("%Y.%m.%d %H:%M:%S"),
        "open": fmt_prices(sub["open"], dp), "high": fmt_prices(sub["high"], dp),
        "low": fmt_prices(sub["low"], dp), "close": fmt_prices(sub["close"], dp),
        "tick_volume": sub["volume"].round().astype("int64").astype(str),
        "spread": cal.astype(str), "real_volume": "0", "_ts": sub["ts_utc"].values,
    })


def _internal_fill_bars(duka: pd.DataFrame, ex_ts, es, ee, threshold_h: float) -> pd.DataFrame:
    """Dukascopy bars inside the existing range that fall in existing-data gaps LONGER than
    threshold_h (real multi-day outages Dukascopy can fill). Weekends/holidays naturally stay
    empty because Dukascopy has no bars there either. Excludes any timestamp already present."""
    exs = pd.Series(pd.DatetimeIndex(ex_ts).sort_values())
    d = exs.diff()
    big = pd.DataFrame({"a": exs.shift(1), "b": exs})[d > pd.Timedelta(hours=threshold_h)].dropna()
    inside = duka[(duka["ts_utc"] > es) & (duka["ts_utc"] < ee)]
    if big.empty or inside.empty:
        return inside.iloc[0:0]
    ts = inside["ts_utc"].values
    keep = np.zeros(len(inside), dtype=bool)
    for a, b in zip(big["a"].values, big["b"].values):
        keep |= (ts > a) & (ts < b)
    sub = inside[keep]
    return sub[~sub["ts_utc"].isin(set(ex_ts))]


def _dense_start(ts: pd.Series, frac: float = 0.5, roll_days: int = 63) -> pd.Timestamp:
    """First day from which the existing MT5 data is DENSE. A day counts as covered only
    if its bar count >= frac * max(rolling median, global median) of the file's own
    nonzero bars/day. MT5 exports carry stray bars (1-23/day) far before their true M1
    depth; the previous existence check ("any bar present") mistook those for coverage
    and blocked Dukascopy backfill (US500/US100 2018-01->2021-09 + GER40 2019-12->2021-12
    holes, bar-density audit 2026-06-10). The global-median floor prevents a long stray
    run from passing against its own rolling median."""
    days = ts.dt.normalize().value_counts().sort_index()
    med_global = float(days.median())
    roll = days.rolling(roll_days, center=True, min_periods=1).median()
    dense = days[days.values >= frac * np.maximum(roll.values, med_global)]
    return dense.index[0] if len(dense) else days.index[0]


# ------------------------------------------------------------------------- assemble
def assemble(sym: str, gate: bool = False, fill_internal: bool = False,
             fill_threshold_h: float = 48.0) -> dict:
    cfg = INSTR[sym]
    point, dp, grp = cfg["point"], cfg["dp"], cfg["grp"]
    exist = load_existing(sym)
    es_raw = exist["_ts"].min()
    ds = _dense_start(exist["_ts"])
    n_stray = int((exist["_ts"] < ds).sum())
    if n_stray:
        exist = exist[exist["_ts"] >= ds].reset_index(drop=True)
    es, ee = exist["_ts"].min(), exist["_ts"].max()
    rep = dict(symbol=sym, code=cfg["code"], group=grp,
               sources="MT5/FTMO-Demo (existing, EET/EEST->UTC) + Dukascopy M1-candle (backfill/top-up, UTC)",
               tz_handling=f"existing localized {TZ}->UTC; ambiguous=infer(fallback DST); nonexistent=shift_forward",
               exist_start_raw_utc=str(es_raw), exist_dense_start_utc=str(ds),
               stray_rows_dropped=n_stray,
               exist_start_utc=str(es), exist_end_utc=str(ee), exist_rows=len(exist),
               n_ambiguous_bars=exist.attrs.get("n_ambiguous"),
               n_nonexistent_bars=exist.attrs.get("n_nonexistent"))

    duka = load_duka(sym)
    if duka is None or duka.empty:
        rep["status"] = "no_duka_cache"
        return rep
    rep["duka_cache_years"] = sorted({int(p.stem.split("_")[1]) for p in CACHE.glob(f"{sym}_*.parquet")})

    # ---- overlap (inside existing UTC range) for calibration + corr ----
    ov = duka[(duka["ts_utc"] >= es) & (duka["ts_utc"] <= ee)].copy()
    ov["duka_pts"] = ((ov["ask_close"] - ov["close"]) / point).round().clip(lower=0)
    ex = exist[["_ts", "spread", "close"]].copy()
    ex["ex_spread"] = pd.to_numeric(ex["spread"], errors="coerce")
    ex["ex_close"] = pd.to_numeric(ex["close"], errors="coerce")
    m = ov.merge(ex[["_ts", "ex_spread", "ex_close"]], left_on="ts_utc", right_on="_ts", how="inner")
    m["hour"] = m["ts_utc"].dt.hour
    rep["overlap_rows"] = len(m)
    if len(m) > 100:
        rep["overlap_corr"] = round(float(m["close"].corr(m["ex_close"])), 6)

    # ---- fit spread model ----
    if len(m) >= 200:
        model = fit_spread_model(m)
        params, kind = model["params"], model["model"]
        rep.update(spread_model=kind, spread_mae_test_add=model["mae_add"],
                   spread_mae_test_mult=model["mae_mult"], spread_overall_param=model["overall"])
    else:
        kind = "additive"
        overall = float((m["ex_spread"] - m["duka_pts"]).median()) if len(m) else 0.0
        params = {h: overall for h in range(24)}
        rep.update(spread_model="additive(thin_overlap)", spread_thin_overlap=True,
                   spread_overall_param=round(overall, 4))

    index_tick = detect_index_tick(ex["ex_spread"]) if grp == "P2idx" else 1
    if index_tick > 1:
        rep["index_spread_tick_round"] = index_tick

    # ---- backfill = duka strictly outside existing UTC range ----
    bf = duka[(duka["ts_utc"] < es) | (duka["ts_utc"] > ee)].copy()
    rep["backfill_before_rows"] = int((duka["ts_utc"] < es).sum())
    rep["backfill_after_rows"] = int((duka["ts_utc"] > ee).sum())
    if not bf.empty:
        bf_pts = ((bf["ask_close"] - bf["close"]) / point).round().clip(lower=0)
        rep["backfill_start_utc"] = str(bf["ts_utc"].min())
        rep["backfill_end_utc"] = str(bf["ts_utc"].max())
        rep["spread_raw_median"] = float(bf_pts.median())
        bf_out = _duka_to_out(bf, dp, point, params, kind, index_tick)
        rep["spread_cal_median"] = float(pd.to_numeric(bf_out["spread"]).median())
    else:
        bf_out = pd.DataFrame(columns=SCHEMA + ["_ts"])

    # ---- internal-gap fill (opt-in): fill existing-data OUTAGES > threshold with Dukascopy ----
    # (weekends/holidays stay empty: Dukascopy has no bars there either). Existing always wins.
    if fill_internal:
        ifb = _internal_fill_bars(duka, exist["_ts"].values, es, ee, fill_threshold_h)
        int_out = _duka_to_out(ifb, dp, point, params, kind, index_tick)
        rep["internal_fill_rows"] = len(int_out)
        rep["internal_fill_threshold_h"] = fill_threshold_h
        if len(int_out):
            rep["internal_fill_start_utc"] = str(ifb["ts_utc"].min())
            rep["internal_fill_end_utc"] = str(ifb["ts_utc"].max())
    else:
        int_out = pd.DataFrame(columns=SCHEMA + ["_ts"])

    # ---- existing rows verbatim, timestamp -> true UTC ----
    ex_out = pd.DataFrame({
        "timestamp_utc": exist["_ts"].dt.strftime("%Y.%m.%d %H:%M:%S"),
        "open": exist["open"], "high": exist["high"], "low": exist["low"],
        "close": exist["close"], "tick_volume": exist["tick_volume"],
        "spread": exist["spread"], "real_volume": exist["real_volume"],
        "_ts": exist["_ts"].values,
    })

    before = bf_out[bf_out["_ts"] < es]
    after = bf_out[bf_out["_ts"] > ee]
    # order matters: ex_out before int_out so existing WINS any timestamp collision on dedup
    full = pd.concat([before, ex_out, int_out, after], ignore_index=True)
    full = full.sort_values("_ts", kind="stable").reset_index(drop=True)
    dup_mask = full["_ts"].duplicated()
    if int(dup_mask.sum()):
        full = full[~dup_mask].reset_index(drop=True)

    # ---- validation ----
    dts = full["_ts"]
    sp = pd.to_numeric(full["spread"], errors="coerce")
    rep["final_rows"] = len(full)
    rep["final_start_utc"] = str(dts.min())
    rep["final_end_utc"] = str(dts.max())
    rep["dups_removed"] = int(dup_mask.sum())
    rep["monotonic_increasing"] = bool(dts.is_monotonic_increasing)
    rep["spread_negative"] = int((sp < 0).sum())
    rep["spread_zero_frac"] = round(float((sp == 0).mean()), 4)
    rep["spread_max"] = int(sp.max()) if len(sp) else 0
    # OHLC validity on the assembled file (existing strings + backfill)
    o = pd.to_numeric(full["open"], errors="coerce"); h = pd.to_numeric(full["high"], errors="coerce")
    lo = pd.to_numeric(full["low"], errors="coerce"); c = pd.to_numeric(full["close"], errors="coerce")
    eps = 1e-9
    rep["ohlc_violations"] = int((((h < o - eps) | (h < c - eps) | (h < lo - eps) |
                                   (lo > o + eps) | (lo > c + eps)) |
                                  (full[["open", "high", "low", "close"]].apply(
                                      lambda x: pd.to_numeric(x, errors="coerce")) <= 0).any(axis=1)).sum())
    # gaps
    d = dts.diff().dropna()
    big = d[d > pd.Timedelta(minutes=2)]
    wk = big[(dts.loc[big.index].dt.dayofweek.isin([0])) | (big > pd.Timedelta(hours=20))]
    rep["intraweek_gaps_gt2min"] = int(len(big) - len(wk))
    rep["max_gap_hours"] = round(d.max().total_seconds() / 3600, 2) if len(d) else 0
    # seam continuity: |log return| across the before->existing and existing->after joins
    rep["seam_before"] = _seam_jump(full, es, point) if rep["backfill_before_rows"] else None
    rep["seam_after"] = _seam_jump(full, ee, point, after=True) if rep["backfill_after_rows"] else None

    rep["status"] = "ok"
    out_file = OUT / f"{sym}_M1.csv"
    if not gate:
        full[SCHEMA].to_csv(out_file, index=False)
        rep["out_file"] = str(out_file)

    if gate:
        # GATE-2 thresholds
        thr = dict(ohlc=rep["ohlc_violations"] == 0, mono=rep["monotonic_increasing"],
                   dups=rep["dups_removed"] == 0,
                   corr=rep.get("overlap_corr", 0) >= 0.999,
                   has_backfill=rep["backfill_before_rows"] > 0)
        rep["gate2"] = thr
        rep["gate2_pass"] = all(thr.values())
    return rep


def _seam_jump(full: pd.DataFrame, boundary, point: float, after: bool = False):
    """|price step| (in points) across a splice seam — flags discontinuities."""
    c = pd.to_numeric(full["close"], errors="coerce").values
    ts = full["_ts"].values
    idx = np.searchsorted(ts, np.datetime64(boundary))
    if after:
        i = idx
    else:
        i = idx  # boundary is first existing ts; seam is between i-1 (backfill) and i (existing)
    if i <= 0 or i >= len(c):
        return None
    step_pts = abs(c[i] - c[i - 1]) / point
    dt_min = (ts[i] - ts[i - 1]) / np.timedelta64(1, "m")
    return dict(step_points=round(float(step_pts), 1), gap_minutes=round(float(dt_min), 1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol")
    ap.add_argument("--symbols", help="comma list, e.g. GER40,US30")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--gate", action="store_true", help="gate-2 mode: thresholds, no final write, exit code")
    ap.add_argument("--fill-internal", action="store_true",
                    help="fill existing-data outages > threshold with Dukascopy (e.g. GER40 2018, US30 2019-08)")
    ap.add_argument("--fill-threshold-h", type=float, default=48.0)
    a = ap.parse_args()
    if a.symbols:
        syms = [s.strip() for s in a.symbols.split(",") if s.strip()]
    else:
        syms = [a.symbol] if a.symbol else (list(INSTR) if a.all else [])
    if not syms:
        ap.error("need --symbol / --symbols / --all")
    reps = []
    for s in syms:
        try:
            r = assemble(s, gate=a.gate, fill_internal=a.fill_internal,
                         fill_threshold_h=a.fill_threshold_h)
        except Exception as e:  # noqa: BLE001
            r = dict(symbol=s, status="error", error=repr(e))
        reps.append(r)
        print(f"{s}: {r.get('status')} | final {r.get('final_rows')} rows "
              f"{str(r.get('final_start_utc'))[:10]}->{str(r.get('final_end_utc'))[:10]} "
              f"| corr {r.get('overlap_corr','-')} | spread={r.get('spread_model','-')} "
              f"| mono {r.get('monotonic_increasing')} dups {r.get('dups_removed')} "
              f"ohlc_viol {r.get('ohlc_violations')} | gaps {r.get('intraweek_gaps_gt2min','-')}"
              f"{' | fill='+str(r.get('internal_fill_rows')) if a.fill_internal else ''}"
              f"{'  GATE2='+('PASS' if r.get('gate2_pass') else 'FAIL') if a.gate else ''}", flush=True)
    if not a.gate:
        # MERGE into the existing full report (don't clobber other instruments' entries)
        rj = REP / "assembly_report.json"
        existing = {x["symbol"]: x for x in json.load(open(rj))} if rj.exists() else {}
        for r in reps:
            existing[r["symbol"]] = r
        merged = [existing[s] for s in INSTR if s in existing]
        with open(rj, "w") as f:
            json.dump(merged, f, indent=2, default=str)
        pd.DataFrame(merged).to_csv(REP / "assembly_report.csv", index=False)
        print(f"\nreports -> {rj} ({len(merged)} instruments)")
    if a.gate:
        ok = all(r.get("gate2_pass") for r in reps)
        print(f"\nGATE 2 OVERALL: {'PASS' if ok else 'FAIL'}")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
