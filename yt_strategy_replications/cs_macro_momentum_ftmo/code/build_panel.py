"""Resample deep_history_utc M1 -> daily panel (one pass, cached to parquet).

Per UTC calendar day and per instrument we keep:
    open, high, low, close      (first open / max / min / last close of the day)
    spread_med, spread_p95      (MT5 spread column, in *points*)
    n_bars                      (bar-count, used for the data-quality audit)

The M1 estate is ~5.5 GB of CSV; this module is the only thing that ever touches
it. Everything downstream reads ``cache/daily_panel.parquet``.

Point size is inferred from the observed price granularity and cross-checked
against ``measured_specs`` (digits) for the four instruments the frozen yaml
covers; see DIGITS below.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("<HOME>/Desktop/Algo_claude/data/deep_history_utc")
HERE = Path(__file__).resolve().parent.parent
CACHE = HERE / "cache"

# Universe frozen in PREREGISTRATION.md section 2 (16 instruments).
UNIVERSE = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD",
    "US30", "US100", "US500", "GER40",
    "XAUUSD", "XAGUSD", "COPPER",
    "UKOIL", "USOIL", "NGAS",
]
# NOTE (documented deviation, see RESULTS.md): PREREGISTRATION section 2 heads the universe
# "16" but enumerates FX(7) + indices(4) + metals(3) + energy(3) = 17 named instruments.
# The enumeration is explicit and the count is not; we trade the 17 enumerated names and
# report the discrepancy rather than dropping an arbitrary instrument to reach 16.

# digits: point = 10**-digits. Inferred from min price granularity, cross-checked with
# measured_specs for XAUUSD(2), USDJPY(3), US100(2), GER40(2).
DIGITS = {
    "EURUSD": 5, "GBPUSD": 5, "USDJPY": 3, "AUDUSD": 5, "USDCAD": 5,
    "USDCHF": 5, "NZDUSD": 5,
    "US30": 2, "US100": 2, "US500": 2, "GER40": 2,
    "XAUUSD": 2, "XAGUSD": 3, "COPPER": 4,
    "UKOIL": 3, "USOIL": 3, "NGAS": 4,
}

CHUNK = 2_000_000


def resample_symbol(sym: str) -> pd.DataFrame:
    path = RAW / f"{sym}_M1.csv"
    agg: dict[str, dict] = {}
    spreads: dict[str, list[np.ndarray]] = {}
    reader = pd.read_csv(
        path,
        usecols=["timestamp_utc", "open", "high", "low", "close", "spread"],
        dtype={"open": "float64", "high": "float64", "low": "float64",
               "close": "float64", "spread": "float32"},
        chunksize=CHUNK,
    )
    for chunk in reader:
        chunk["d"] = chunk["timestamp_utc"].str.slice(0, 10)
        g = chunk.groupby("d", sort=False)
        first_open = g["open"].first()
        last_close = g["close"].last()
        hi = g["high"].max()
        lo = g["low"].min()
        cnt = g.size()
        for d in first_open.index:
            a = agg.get(d)
            if a is None:
                agg[d] = {"open": first_open[d], "high": hi[d], "low": lo[d],
                          "close": last_close[d], "n_bars": int(cnt[d])}
            else:
                a["high"] = max(a["high"], hi[d])
                a["low"] = min(a["low"], lo[d])
                a["close"] = last_close[d]
                a["n_bars"] += int(cnt[d])
        for d, sub in chunk.groupby("d", sort=False)["spread"]:
            spreads.setdefault(d, []).append(sub.to_numpy())

    rows = []
    for d, a in agg.items():
        sp = np.concatenate(spreads[d])
        sp = sp[np.isfinite(sp)]
        rows.append({
            "date": d, "symbol": sym,
            "open": a["open"], "high": a["high"], "low": a["low"], "close": a["close"],
            "n_bars": a["n_bars"],
            "spread_med": float(np.median(sp)) if sp.size else np.nan,
            "spread_p95": float(np.percentile(sp, 95)) if sp.size else np.nan,
            "spread_zero_frac": float((sp == 0).mean()) if sp.size else np.nan,
        })
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], format="%Y.%m.%d")
    return df.sort_values("date").reset_index(drop=True)


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    syms = sys.argv[1:] or UNIVERSE
    for sym in syms:
        out = CACHE / f"daily_{sym}.parquet"
        if out.exists():
            print(f"[skip] {sym}", flush=True)
            continue
        df = resample_symbol(sym)
        df.to_parquet(out, index=False)
        print(f"[ok] {sym} rows={len(df)} {df.date.min().date()}->{df.date.max().date()}",
              flush=True)


if __name__ == "__main__":
    main()
