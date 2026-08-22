"""
nq_databento_ingest.py
======================

Ingest Databento NQ.FUT ohlcv-1m DBN (parent symbol → all outright contracts)
into a clean continuous-front-month parquet for the ORB engine.

Pipeline:
  1. Load DBN via databento lib, decompress zstd transparently.
  2. Filter spread symbols (anything containing '-' is a calendar spread).
  3. Per ET trading date, pick front-month = symbol with max RTH volume.
  4. Build continuous series = bars where symbol == front-month for the day.
  5. Flag is_roll_day where front-month differs from previous trading day.
  6. Data quality:
     - OHLC sanity
     - Volume spike at 09:30 ET (cash open) + DST spot-checks
     - OR window gap check (09:30-09:45 ET, 15 bars/day required)
     - Cross condition.json for degraded days
  7. Write parquet to data/raw/ + sidecar JSON metadata.
  8. Reconcile vs US100 CFD (m5_indices/m1_panel.parquet) on overlap.

NOT a downloader. Reads from data/GLBX-20260601-FP4HWRA58K/ already on disk.
"""
from __future__ import annotations

import json
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import databento as db

ROOT = Path(__file__).resolve().parents[3]
DBN_DIR = ROOT / "data" / "GLBX-20260601-FP4HWRA58K"
DBN_FILE = DBN_DIR / "glbx-mdp3-20100606-20260531.ohlcv-1m.dbn.zst"
COND_FILE = DBN_DIR / "condition.json"
META_FILE = DBN_DIR / "metadata.json"

RAW_DIR = ROOT / "data" / "raw"
META_DIR = ROOT / "data" / "metadata"
PARQUET_OUT = RAW_DIR / "NQ_1min_databento_2010-2026.parquet"
META_OUT = META_DIR / "NQ_1min_databento_2010-2026.json"

OUTPUT_DIR = ROOT / "data" / "ftmo_research" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ── Step 1 — Load ─────────────────────────────────────────────────────────────
def load_dbn() -> pd.DataFrame:
    log(f"Loading DBN: {DBN_FILE.name} (107MB compressed)")
    store = db.DBNStore.from_file(DBN_FILE)
    df = store.to_df()  # decompresses + parses fixed-point prices
    log(f"Loaded shape: {df.shape}")
    log(f"Date range:   {df.index.min()} → {df.index.max()}")
    log(f"Unique symbols: {df['symbol'].nunique()}")
    return df


# ── Step 2 — Filter spreads ───────────────────────────────────────────────────
def filter_spreads(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    is_spread = df["symbol"].str.contains("-", na=False)
    n_spread = int(is_spread.sum())
    n_total = len(df)
    out = df[~is_spread].copy()
    spread_symbols = sorted(df.loc[is_spread, "symbol"].unique().tolist())
    log(f"Filtered {n_spread:,}/{n_total:,} spread rows "
        f"({len(spread_symbols)} distinct spread symbols)")
    return out, {
        "n_spread_rows_dropped": n_spread,
        "n_distinct_spreads": len(spread_symbols),
        "spread_sample": spread_symbols[:10],
    }


# ── Step 3-4 — Front-month + continuous series ────────────────────────────────
def build_continuous(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    # UTC → ET (tz-aware view)
    ts_et = df.index.tz_convert("US/Eastern")
    df = df.copy()
    df["ts_et"] = ts_et
    df["date_et"] = ts_et.date
    t = ts_et.time
    df["is_rth"] = (t >= pd.Timestamp("09:30").time()) & (t < pd.Timestamp("16:00").time())

    # Per (date_et, symbol) RTH volume
    rth = df[df["is_rth"]]
    vol_by = rth.groupby(["date_et", "symbol"])["volume"].sum()
    if vol_by.empty:
        raise RuntimeError("No RTH rows after filtering — investigate.")
    # date → front-month symbol
    front = (
        vol_by.groupby(level=0)
        .idxmax()
        .apply(lambda t: t[1])
        .rename("front_month")
    )
    log(f"Front-month series: {len(front)} trading dates")
    log(f"Distinct front contracts: {front.nunique()}")

    # is_roll_day = front-month changed vs prior trading date
    front_change = (front != front.shift(1)) & front.shift(1).notna()
    roll_dates = front[front_change].index.tolist()
    log(f"Roll days detected: {len(roll_dates)} "
        f"(expected ~{(2026 - 2010) * 4} quarterly rolls)")

    # Map front-month onto every row by date
    df["front_month"] = df["date_et"].map(front)
    cont = df[df["symbol"] == df["front_month"]].copy()
    # Tag is_roll_day
    roll_set = set(roll_dates)
    cont["is_roll_day"] = cont["date_et"].isin(roll_set)

    log(f"Continuous series shape: {cont.shape}")
    return cont, {
        "n_trading_dates": int(len(front)),
        "n_distinct_front_contracts": int(front.nunique()),
        "n_roll_days": int(len(roll_dates)),
        "roll_dates_sample_first10": [str(d) for d in roll_dates[:10]],
        "roll_dates_sample_last10": [str(d) for d in roll_dates[-10:]],
        "front_first": str(front.iloc[0]),
        "front_last": str(front.iloc[-1]),
    }


# ── Step 5 — Data quality ─────────────────────────────────────────────────────
def dq_ohlc(df: pd.DataFrame) -> dict:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    v_high = ((h >= o) & (h >= c) & (h >= l)).sum()
    v_low = ((l <= o) & (l <= c) & (l <= h)).sum()
    v_vol = (df["volume"] >= 0).sum()
    n = len(df)
    violations = {
        "high_violations": n - int(v_high),
        "low_violations": n - int(v_low),
        "volume_negative": n - int(v_vol),
        "n_rows": n,
    }
    log(f"OHLC sanity: high_violations={violations['high_violations']}, "
        f"low_violations={violations['low_violations']}, "
        f"vol_neg={violations['volume_negative']}")
    return violations


def dq_cash_open(df: pd.DataFrame) -> dict:
    """Cash-open volume spike: argmax(volume) in 09:25-09:35 ET window per date."""
    ts_et = df["ts_et"]
    in_win = (ts_et.dt.time >= pd.Timestamp("09:25").time()) & \
             (ts_et.dt.time <= pd.Timestamp("09:35").time())
    s = df[in_win].copy()
    s["minute_et"] = s["ts_et"].dt.strftime("%H:%M")
    idx = s.groupby("date_et")["volume"].idxmax()
    spike_minutes = s.loc[idx, "minute_et"].value_counts().sort_index()
    pct_at_0930 = float(spike_minutes.get("09:30", 0) / spike_minutes.sum())
    log(f"Cash-open spike at 09:30 ET: {pct_at_0930*100:.2f}% of days "
        f"(distribution {dict(spike_minutes.head(10))})")
    return {
        "pct_spike_at_0930_et": pct_at_0930,
        "spike_minute_distribution": {k: int(v) for k, v in spike_minutes.items()},
    }


def dq_dst_spotcheck(df: pd.DataFrame) -> dict:
    """For each year, check 09:30 ET maps to 13:30 UTC (DST) or 14:30 UTC (std)."""
    samples = []
    years = sorted(set(df["date_et"].apply(lambda d: d.year)))
    for y in years:
        # Find a Monday after DST start (2nd Sun of March) and after DST end (1st Sun of Nov)
        # Use any business day in late March (DST active) and late November (std time).
        for tag, m, d_start in (("DST", 3, 16), ("STD", 11, 8)):
            target = None
            for offset in range(0, 14):
                t = pd.Timestamp(year=y, month=m, day=d_start + offset)
                if t.weekday() < 5:  # Mon-Fri
                    target = t.date()
                    break
            if target is None:
                continue
            row = df[
                (df["date_et"] == target) &
                (df["ts_et"].dt.strftime("%H:%M") == "09:30")
            ]
            if len(row):
                utc_str = row.index[0].strftime("%H:%M")
                expected = "13:30" if tag == "DST" else "14:30"
                samples.append({
                    "year": y, "tag": tag, "date": str(target),
                    "utc_at_0930_et": utc_str, "expected": expected,
                    "ok": utc_str == expected,
                })
    bad = [s for s in samples if not s["ok"]]
    log(f"DST spot-checks: {len(samples)} samples, {len(bad)} mismatches")
    return {"n_samples": len(samples), "n_mismatches": len(bad),
            "samples_first5": samples[:5], "mismatches": bad}


def dq_or_window_gaps(df: pd.DataFrame) -> dict:
    """In OR 09:30-09:45 ET, expect 15 bars per session. Flag days with < 15."""
    ts_et = df["ts_et"]
    in_or = (ts_et.dt.time >= pd.Timestamp("09:30").time()) & \
            (ts_et.dt.time < pd.Timestamp("09:45").time())
    s = df[in_or]
    bars_per_day = s.groupby("date_et").size()
    bad = bars_per_day[bars_per_day < 15]
    log(f"OR-window gaps: {len(bad)}/{len(bars_per_day)} days have <15 bars in 09:30-09:45")
    return {
        "n_sessions_with_or_window": int(len(bars_per_day)),
        "n_sessions_or_gap": int(len(bad)),
        "or_gap_examples_first10": [
            {"date": str(d), "bars": int(b)} for d, b in bad.head(10).items()
        ],
    }


def dq_degraded_days() -> dict:
    cond = json.loads(COND_FILE.read_text())
    degraded = [c for c in cond if c.get("condition") != "available"]
    log(f"Degraded days from condition.json: {len(degraded)}/{len(cond)} "
        f"({100*len(degraded)/len(cond):.2f}%)")
    by_condition = {}
    for c in degraded:
        by_condition.setdefault(c["condition"], []).append(c["date"])
    summary = {k: {"count": len(v), "examples_first10": v[:10]}
               for k, v in by_condition.items()}
    return {
        "n_degraded_days": len(degraded),
        "n_total_condition_days": len(cond),
        "by_condition": summary,
    }


# ── Step 6 — Persist ──────────────────────────────────────────────────────────
def write_parquet(df: pd.DataFrame) -> dict:
    """Write canonical parquet. Schema:
       index: timestamp_utc (DatetimeIndex, UTC tz-aware)
       cols : open, high, low, close (float32), volume (int64),
              symbol (str), is_roll_day (bool), is_rth (bool)
    """
    out = df[["open", "high", "low", "close", "volume",
              "symbol", "is_roll_day", "is_rth"]].copy()
    for c in ("open", "high", "low", "close"):
        out[c] = out[c].astype("float32")
    out["volume"] = out["volume"].astype("int64")
    out["symbol"] = out["symbol"].astype("string")
    out.index.name = "timestamp_utc"
    out.sort_index(inplace=True)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    META_DIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(PARQUET_OUT, engine="pyarrow", compression="snappy")
    size_mb = PARQUET_OUT.stat().st_size / 1e6
    log(f"Wrote parquet: {PARQUET_OUT.name} ({size_mb:.1f} MB, {len(out):,} rows)")
    return {
        "parquet_path": str(PARQUET_OUT),
        "size_mb": round(size_mb, 2),
        "rows": int(len(out)),
        "date_start": out.index[0].isoformat(),
        "date_end": out.index[-1].isoformat(),
        "columns": list(out.columns),
    }


# ── Step 7 — Reconciliation vs US100 CFD ──────────────────────────────────────
def reconcile_vs_us100(cont: pd.DataFrame) -> dict:
    """Compare new NQ-futures continuous to US100 CFD over 2022-2025 overlap.

    Stats:
      - Daily-returns correlation
      - Mean ORB range (09:30:09:45 ET high-low, in points — different magnitudes
        across instruments, so we compare RELATIVE ORB range as % of daily open)
      - Daily R-multiple count and hit-rate at 1.5R TP / 0.5R SL (iter_10-like)
    """
    panel = ROOT / "data" / "panels" / "m5_indices" / "m1_panel.parquet"
    if not panel.exists():
        log(f"WARNING: US100 panel not found at {panel}; skipping reconciliation")
        return {"skipped": True, "reason": f"file not found: {panel}"}

    pan = pd.read_parquet(panel)
    if "US100" not in pan.columns:
        # m1_panel might be multi-instrument with nested columns. Try
        # GER40 file as test of repo state.
        log(f"WARNING: 'US100' column missing in m1_panel; columns={list(pan.columns)[:10]}")
        return {"skipped": True, "reason": "US100 column missing in m1_panel"}

    us100 = pan["US100"].dropna()
    # Convention from orb_core.py: m1_panel index is tz-naive ET wall-clock
    if not isinstance(us100.index, pd.DatetimeIndex):
        us100.index = pd.to_datetime(us100.index)
    if us100.index.tz is not None:
        us100.index = us100.index.tz_localize(None)
    # That gives us US100 close-only (single column). Need OHLC? m1_panel may
    # only carry close. Check structure.
    log(f"US100 series shape: {us100.shape}; head: {us100.head(2).to_dict()}")

    # Take continuous NQ in 2022-2025 RTH, convert to tz-naive ET to align
    nq = cont[cont["is_rth"]].copy()
    nq.index = nq["ts_et"].dt.tz_localize(None)
    nq = nq.loc["2022":"2025"]
    nq_close = nq["close"]

    # Restrict US100 to same window
    us100 = us100.loc["2022":"2025"]

    # 1-min returns correlation on common index
    common = nq_close.index.intersection(us100.index)
    if len(common) < 1000:
        log(f"Too few common minutes (n={len(common)}) for correlation")
        return {"skipped": False, "warn": "few common minutes",
                "n_common_minutes": int(len(common))}

    rn = nq_close.loc[common].astype("float64").pct_change().dropna()
    ru = us100.loc[common].astype("float64").pct_change().dropna()
    idx2 = rn.index.intersection(ru.index)
    corr = float(rn.loc[idx2].corr(ru.loc[idx2]))

    # Mean ORB range as % of daily open
    def orb_range_pct(close_series: pd.Series, sym_hl_df: pd.DataFrame | None = None):
        """Approx ORB: max(close)-min(close) in 09:30-09:44, % of 09:30 close."""
        df_ = close_series.to_frame("close")
        df_["t"] = df_.index.time
        in_or = (df_["t"] >= pd.Timestamp("09:30").time()) & \
                (df_["t"] <  pd.Timestamp("09:45").time())
        df_["d"] = df_.index.date
        g = df_[in_or].groupby("d")["close"].agg(["max", "min", "first"])
        return ((g["max"] - g["min"]) / g["first"]).rename("or_pct")

    or_nq = orb_range_pct(nq_close)
    or_us = orb_range_pct(us100)
    common_d = or_nq.index.intersection(or_us.index)
    or_corr = float(or_nq.loc[common_d].corr(or_us.loc[common_d]))
    mean_or_nq = float(or_nq.loc[common_d].mean())
    mean_or_us = float(or_us.loc[common_d].mean())

    log(f"Reconciliation:")
    log(f"  1-min returns corr (NQ futures vs US100 CFD): {corr:.4f}")
    log(f"  ORB% corr (per day): {or_corr:.4f}")
    log(f"  mean ORB%: NQ futures = {mean_or_nq*100:.4f}%, "
        f"US100 CFD = {mean_or_us*100:.4f}%")

    # Verdict
    if corr >= 0.95 and or_corr >= 0.85:
        verdict = "MATCH"
    elif corr >= 0.85 and or_corr >= 0.70:
        verdict = "PARTIAL_MATCH"
    else:
        verdict = "DIVERGENCE"

    return {
        "skipped": False,
        "verdict": verdict,
        "n_common_minutes": int(len(idx2)),
        "n_common_days": int(len(common_d)),
        "returns_corr_1min": corr,
        "orb_pct_corr_daily": or_corr,
        "mean_orb_pct_nq_futures": mean_or_nq,
        "mean_orb_pct_us100_cfd": mean_or_us,
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> dict:
    t0 = time.time()
    df_raw = load_dbn()
    df_filtered, spread_stats = filter_spreads(df_raw)
    cont, front_stats = build_continuous(df_filtered)

    dq = {
        "ohlc": dq_ohlc(cont),
        "cash_open": dq_cash_open(cont),
        "dst_spotcheck": dq_dst_spotcheck(cont),
        "or_window_gaps": dq_or_window_gaps(cont),
        "degraded_days": dq_degraded_days(),
    }

    parquet_meta = write_parquet(cont)

    recon = reconcile_vs_us100(cont)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_dbn": str(DBN_FILE.relative_to(ROOT)),
        "spread_filter": spread_stats,
        "front_month": front_stats,
        "data_quality": dq,
        "parquet": parquet_meta,
        "reconciliation": recon,
        "runtime_seconds": round(time.time() - t0, 1),
    }

    # Sidecar metadata
    META_OUT.write_text(json.dumps(summary, indent=2, default=str))
    # Also dump to output for the report
    (OUTPUT_DIR / "nq_databento_ingest_summary.json").write_text(
        json.dumps(summary, indent=2, default=str)
    )
    log(f"Done in {time.time()-t0:.1f}s. Summary → {META_OUT}")
    return summary


if __name__ == "__main__":
    summary = main()
    # Compact stdout summary
    print("\n========= SUMMARY =========")
    print(json.dumps({
        "rows": summary["parquet"]["rows"],
        "date_start": summary["parquet"]["date_start"],
        "date_end": summary["parquet"]["date_end"],
        "size_mb": summary["parquet"]["size_mb"],
        "n_trading_dates": summary["front_month"]["n_trading_dates"],
        "n_roll_days": summary["front_month"]["n_roll_days"],
        "ohlc_violations": (
            summary["data_quality"]["ohlc"]["high_violations"] +
            summary["data_quality"]["ohlc"]["low_violations"]
        ),
        "pct_spike_at_0930_et": summary["data_quality"]["cash_open"]["pct_spike_at_0930_et"],
        "dst_mismatches": summary["data_quality"]["dst_spotcheck"]["n_mismatches"],
        "or_gap_days": summary["data_quality"]["or_window_gaps"]["n_sessions_or_gap"],
        "degraded_days": summary["data_quality"]["degraded_days"]["n_degraded_days"],
        "reconciliation_verdict": summary["reconciliation"].get("verdict"),
    }, indent=2))
