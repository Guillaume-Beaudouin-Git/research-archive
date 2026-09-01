"""
download_pairs.py — Acquisition GBPJPY + croisées manquantes pour Dedale (2026-08).

Réutilise TEL QUEL le décodeur bi5 canonique de data/deep_history_m1/duka_m1_backfill.py
(_fetch, _decode, _session, _decompress) — même endpoint (BID+ASK candles_min_1),
même ordre d'octets O,C,L,H déjà vérifié 0 mismatch vs dukascopy-node (voir
data/deep_history_m1/gate1_decoder_check.py). On n'édite PAS ce fichier canonique ;
on l'importe et on lui fournit un INSTR dict local pour les paires absentes de
data/deep_history_utc/.

Sortie brute (par symbole x année) : scratchpad/duka_raw/<SYM>_<YEAR>.parquet
  (colonnes ts_utc, open, high, low, close, volume, ask_close — mêmes qu'assemble
  amont de duka_m1_backfill.py)

Cache final au format gabarit (scratchpad/m1_cache/EURJPY_M1.parquet) :
  index timestamp_utc (tz-aware UTC, trié, dédupliqué), colonnes open/high/low/close
  (BID OHLC, convention identique à data/deep_history_utc/).

Usage:
  /usr/bin/python3 download_pairs.py --symbol GBPJPY --years 2018-2026 --threads 6
  /usr/bin/python3 download_pairs.py --symbol GBPJPY --years 2007-2017 --threads 6
  /usr/bin/python3 download_pairs.py --assemble --symbol GBPJPY
  /usr/bin/python3 download_pairs.py --status
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[5]   # Algo_claude_dedaledata/
CANON = REPO / "data" / "deep_history_m1" / "duka_m1_backfill.py"
SCRATCH = Path("<SCRATCH>"
               "9fd32b98-b3ee-47bf-93c1-b7c5a1ac70a6/scratchpad")
RAW_DIR = SCRATCH / "duka_raw"
CACHE_DIR = SCRATCH / "m1_cache"
RAW_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location("duka_m1_backfill", CANON)
duka = importlib.util.module_from_spec(spec)
sys.modules["duka_m1_backfill"] = duka
spec.loader.exec_module(duka)   # reuses _fetch / _decode / _session / fetch_day / URL as-is

TODAY = date.today()

# Codes Dukascopy = nom de la paire pour tout le FX (confirmé par SYMBOLS de
# dukascopy_downloader_m5.py, bucket fx_crosses). decimalFactor : 1000 pour les
# croix cotées XXXJPY (3 décimales), 100000 pour les autres (5 décimales) — même
# convention que INSTR existant (EURJPY df=1000, EURGBP df=100000).
NEW_INSTR: dict[str, dict] = {
    # priorité 1
    "GBPJPY": dict(code="GBPJPY", df=1000),
    # priorité 2 — croix yen restantes
    "CADJPY": dict(code="CADJPY", df=1000),
    "NZDJPY": dict(code="NZDJPY", df=1000),
    "CHFJPY": dict(code="CHFJPY", df=1000),
    # priorité 3 — croix restantes
    "EURAUD": dict(code="EURAUD", df=100000),
    "EURCAD": dict(code="EURCAD", df=100000),
    "EURCHF": dict(code="EURCHF", df=100000),
    "GBPAUD": dict(code="GBPAUD", df=100000),
    "GBPCAD": dict(code="GBPCAD", df=100000),
    "GBPCHF": dict(code="GBPCHF", df=100000),
    "AUDCAD": dict(code="AUDCAD", df=100000),
    "AUDCHF": dict(code="AUDCHF", df=100000),
    "AUDNZD": dict(code="AUDNZD", df=100000),
    "NZDCAD": dict(code="NZDCAD", df=100000),
}


def download_year(sym: str, year: int, threads: int = 6, force: bool = False) -> dict:
    cfg = NEW_INSTR[sym]
    out_pq = RAW_DIR / f"{sym}_{year}.parquet"
    if out_pq.exists() and not force:
        d = pd.read_parquet(out_pq)
        return dict(sym=sym, year=year, status="cached", rows=len(d))

    start = date(year, 1, 1)
    end = min(date(year, 12, 31), TODAY)
    if start > end:
        return dict(sym=sym, year=year, status="out_of_range", rows=0)

    days = []
    cur = start
    while cur <= end:
        if cur.weekday() != 5:          # skip Saturday, keep Sun evening open + Mon-Fri
            days.append(cur)
        cur += timedelta(days=1)

    rows: list[dict] = []
    done = err = 0
    print(f"  {sym} {year}: {len(days)} days, {threads}t [{cfg['code']}] …", flush=True)
    with ThreadPoolExecutor(max_workers=threads) as pool:
        futs = {pool.submit(duka.fetch_day, cfg["code"], d, cfg["df"]): d for d in days}
        for fut in as_completed(futs):
            try:
                rows.extend(fut.result())
            except Exception:
                err += 1
            done += 1
            if done % 40 == 0 or done == len(days):
                print(f"\r    {done}/{len(days)} days  rows={len(rows)} err={err}   ",
                      end="", flush=True)
    print()
    if err:
        print(f"   !! {sym} {year}: {err} fetch/decode failures — NOT cached (re-run to retry)",
              flush=True)
        return dict(sym=sym, year=year, status="fetch_err", rows=len(rows), errors=err)
    if not rows:
        return dict(sym=sym, year=year, status="empty", rows=0)

    out = (pd.DataFrame(rows).drop_duplicates("ts_utc").sort_values("ts_utc")
           .reset_index(drop=True))
    o, h, l, c = out["open"], out["high"], out["low"], out["close"]
    eps = 1e-9
    bad = ((h < o - eps) | (h < c - eps) | (h < l - eps) |
           (l > o + eps) | (l > c + eps) |
           (out[["open", "high", "low", "close"]] <= 0).any(axis=1))
    viol = int(bad.sum())
    viol_frac = viol / len(out) if len(out) else 0.0
    if viol_frac > 0.001:
        fdir = RAW_DIR / "_failed"
        fdir.mkdir(exist_ok=True)
        out.to_parquet(fdir / f"{sym}_{year}.parquet", compression="snappy")
        print(f"   !! OHLC GUARD FAIL {sym} {year}: {viol}/{len(out)} "
              f"({viol_frac:.3%}) > 0.1% — NOT cached", flush=True)
        return dict(sym=sym, year=year, status="ohlc_fail", rows=len(out),
                    ohlc_viol=viol, ohlc_viol_frac=round(viol_frac, 6))
    out.to_parquet(out_pq, compression="snappy")
    r = dict(sym=sym, year=year, status="ok", rows=len(out), ohlc_viol=viol,
             ohlc_viol_frac=round(viol_frac, 6),
             start=str(out.ts_utc.min()), end=str(out.ts_utc.max()))
    print(f"  OK {sym} {year}: {r}", flush=True)
    return r


def assemble(sym: str) -> Path | None:
    """Concat all cached per-year raw parquet -> final gabarit-format cache."""
    parts = sorted(RAW_DIR.glob(f"{sym}_*.parquet"))
    parts = [p for p in parts if p.parent.name != "_failed"]
    if not parts:
        print(f"  no raw parts for {sym}")
        return None
    dfs = [pd.read_parquet(p) for p in parts]
    df = pd.concat(dfs, ignore_index=True)
    df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True)
    df = (df.drop_duplicates("ts_utc").sort_values("ts_utc")
            .set_index("ts_utc")[["open", "high", "low", "close"]])
    df.index.name = "timestamp_utc"
    out_pq = CACHE_DIR / f"{sym}_M1.parquet"
    df.to_parquet(out_pq, compression="snappy")
    print(f"  assembled {sym}: {len(df):,} rows -> {out_pq}  "
          f"[{df.index.min()} .. {df.index.max()}]")
    return out_pq


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol")
    ap.add_argument("--years", help="e.g. 2018-2026 or 2024")
    ap.add_argument("--threads", type=int, default=6)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--assemble", action="store_true")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()

    if a.status:
        for pq in sorted(RAW_DIR.glob("*.parquet")):
            if pq.parent.name == "_failed":
                continue
            d = pd.read_parquet(pq, columns=["ts_utc"])
            print(f"  {pq.stem:16} {len(d):>8} rows  {d.ts_utc.min()} .. {d.ts_utc.max()}")
        return

    if a.assemble:
        assemble(a.symbol)
        return

    if not a.symbol or a.symbol not in NEW_INSTR:
        ap.error(f"--symbol must be one of {sorted(NEW_INSTR)}")

    if a.years and "-" in a.years:
        y0, y1 = (int(x) for x in a.years.split("-"))
        years = list(range(y0, y1 + 1))
    elif a.years:
        years = [int(a.years)]
    else:
        years = list(range(2018, TODAY.year + 1))

    for y in years:
        t0 = time.time()
        r = download_year(a.symbol, y, threads=a.threads, force=a.force)
        print(f"   -> {r}  ({time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
