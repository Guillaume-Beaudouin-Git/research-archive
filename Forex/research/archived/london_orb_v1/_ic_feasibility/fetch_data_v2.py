"""
PHASE 1.5 Task 2 — Dukascopy 1-min OHLCV fetcher v2 (rate-limit-safe)
=======================================================================
Changes from v1 (CONCURRENCY=20, no delay, no retry):
  - CONCURRENCY 20 → 5
  - 0.5s sleep after every request (inside semaphore → throttles per-slot throughput)
  - 3 retries with exponential backoff (1s, 4s, 16s) on non-empty errors
  - Per-hour-bar logging: HTTP status + payload size → fetch_data_v2_hourly.log
  - LO fill gate: 07:00-08:59 UTC ≥ 95% required per year-pair
  - Skip logic: existing parquets with LO fill ≥ 95% are preserved, not re-fetched

Output:
  data/raw/dukascopy_{PAIR}_{YEAR}.parquet          (per-year cache)
  data/raw/dukascopy_{PAIR}_2020_2024.parquet       (combined, only if ALL years pass gate)
  _ic_feasibility/fetch_data_v2_hourly.log          (per-hour-bar diagnostics)
  _ic_feasibility.md updated with DATA QUALITY v2 table
"""

from __future__ import annotations
import asyncio
import logging
import lzma
import struct
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiohttp
import numpy as np
import pandas as pd

# ── paths ──────────────────────────────────────────────────────────────────
RAW_DIR    = Path(__file__).parents[4] / "data" / "raw"
ACTIVE_DIR = Path(__file__).parent.parent
IC_MD      = ACTIVE_DIR / "_ic_feasibility.md"
LOG_FILE   = Path(__file__).parent / "fetch_data_v2_hourly.log"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ── fetch config ───────────────────────────────────────────────────────────
PAIRS      = ["EURUSD", "GBPUSD"]
START_YEAR = 2020
END_YEAR   = 2024

BASE_URL = (
    "https://datafeed.dukascopy.com/datafeed"
    "/{pair}/{year}/{month:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
)
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

TICK_STRUCT = struct.Struct(">IIIff")
TICK_SIZE   = 20

CONCURRENCY = 5
DELAY_S     = 0.5          # sleep inside semaphore after every request
MAX_RETRIES = 3
BACKOFF_S   = [1, 4, 16]  # seconds before retry 1, 2, 3

# ── LO fill gate ───────────────────────────────────────────────────────────
LO_START         = "07:00"
LO_END           = "08:59"   # inclusive → 120 bars/weekday (07:00–08:59)
LO_BARS_PER_DAY  = 120
LO_FILL_GATE     = 0.95

# ── logging ────────────────────────────────────────────────────────────────
log = logging.getLogger("duka_v2")
log.setLevel(logging.DEBUG)


def _setup_logging() -> None:
    fh = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setLevel(logging.WARNING)
    sh.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(sh)


# ── bi5 decoding ───────────────────────────────────────────────────────────

def _pair_point(pair: str) -> float:
    return 1e-5 if pair in ("EURUSD", "GBPUSD", "EURGBP", "AUDUSD", "NZDUSD", "USDCHF", "USDCAD") else 1e-3


def _decode_bi5(data: bytes, pair: str, hour_dt: datetime) -> pd.DataFrame:
    if not data:
        return pd.DataFrame()
    try:
        raw = lzma.decompress(data)
    except lzma.LZMAError:
        return pd.DataFrame()
    n = len(raw) // TICK_SIZE
    if n == 0:
        return pd.DataFrame()
    records = [TICK_STRUCT.unpack_from(raw, i * TICK_SIZE) for i in range(n)]
    ms_offsets, asks, bids, ask_vols, bid_vols = zip(*records)
    point = _pair_point(pair)
    return pd.DataFrame({
        "timestamp": [hour_dt + timedelta(milliseconds=int(ms)) for ms in ms_offsets],
        "ask":       [a * point for a in asks],
        "bid":       [b * point for b in bids],
        "ask_vol":   list(ask_vols),
        "bid_vol":   list(bid_vols),
    })


# ── async fetch ────────────────────────────────────────────────────────────

async def _fetch_hour(
    pair: str,
    hour_dt: datetime,
    semaphore: asyncio.Semaphore,
) -> pd.DataFrame:
    url = BASE_URL.format(
        pair=pair,
        year=hour_dt.year,
        month=hour_dt.month - 1,   # Dukascopy months are 0-indexed
        day=hour_dt.day,
        hour=hour_dt.hour,
    )
    tag = f"{pair} {hour_dt.strftime('%Y-%m-%d %H:00')}"

    for attempt in range(MAX_RETRIES + 1):
        status_code = 0
        payload_size = 0
        async with semaphore:
            connector = aiohttp.TCPConnector(force_close=True)
            try:
                async with aiohttp.ClientSession(connector=connector, headers=HEADERS) as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        status_code = resp.status
                        data = await resp.read()
                        payload_size = len(data)

                        if status_code in (204, 404):
                            log.debug(f"{tag} | att={attempt+1} | HTTP {status_code} | {payload_size}B | EMPTY")
                            await asyncio.sleep(DELAY_S)
                            return pd.DataFrame()

                        if status_code == 200:
                            df = _decode_bi5(data, pair, hour_dt)
                            outcome = f"OK({len(df)}ticks)" if not df.empty else "OK(empty_bi5)"
                            log.debug(f"{tag} | att={attempt+1} | HTTP {status_code} | {payload_size}B | {outcome}")
                            await asyncio.sleep(DELAY_S)
                            return df

                        # Non-200 non-empty: retry
                        log.debug(f"{tag} | att={attempt+1} | HTTP {status_code} | {payload_size}B | WILL_RETRY")
                        await asyncio.sleep(DELAY_S)

            except Exception as exc:
                log.debug(f"{tag} | att={attempt+1} | HTTP {status_code} | {payload_size}B | EXC:{type(exc).__name__}")
                await asyncio.sleep(DELAY_S)

        # Released semaphore — exponential backoff before next attempt
        if attempt < MAX_RETRIES:
            wait = BACKOFF_S[attempt]
            log.debug(f"{tag} | backoff {wait}s before attempt {attempt+2}")
            await asyncio.sleep(wait)

    log.warning(f"{tag} | FAIL after {MAX_RETRIES+1} attempts")
    return pd.DataFrame()


def _all_hours(year: int):
    dt  = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    while dt < end:
        if dt.weekday() < 5:
            yield dt
        dt += timedelta(hours=1)


def _ticks_to_ohlcv(ticks: pd.DataFrame) -> pd.DataFrame:
    if ticks.empty:
        return pd.DataFrame()
    ticks = ticks.set_index("timestamp").sort_index()
    mid = (ticks["ask"] + ticks["bid"]) / 2
    vol = ticks["ask_vol"] + ticks["bid_vol"]
    return pd.DataFrame({
        "open":   mid.resample("1min").first(),
        "high":   mid.resample("1min").max(),
        "low":    mid.resample("1min").min(),
        "close":  mid.resample("1min").last(),
        "volume": vol.resample("1min").sum(),
    }).dropna(subset=["open"])


async def _fetch_year_async(pair: str, year: int) -> pd.DataFrame:
    hours = list(_all_hours(year))
    print(f"  {pair} {year}: fetching {len(hours)} weekday hours (C={CONCURRENCY}, delay={DELAY_S}s, retries={MAX_RETRIES})...", flush=True)
    semaphore = asyncio.Semaphore(CONCURRENCY)
    tasks = [_fetch_hour(pair, h, semaphore) for h in hours]

    all_ticks: list[pd.DataFrame] = []
    n_done = n_ok = 0
    for i in range(0, len(tasks), 100):
        results = await asyncio.gather(*tasks[i: i + 100])
        for r in results:
            n_done += 1
            if not r.empty:
                all_ticks.append(r)
                n_ok += 1
        print(f"    {n_done}/{len(hours)} | {n_ok} non-empty ({n_ok/n_done*100:.0f}% overall fill)", flush=True)

    if not all_ticks:
        print(f"  WARNING: {pair} {year} — zero non-empty hours", flush=True)
        return pd.DataFrame()

    return _ticks_to_ohlcv(pd.concat(all_ticks, ignore_index=True))


# ── validation helpers ─────────────────────────────────────────────────────

def _count_weekdays(year: int) -> int:
    dt  = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    count = 0
    while dt < end:
        if dt.weekday() < 5:
            count += 1
        dt += timedelta(days=1)
    return count


def _lo_fill(parquet_path: Path, year: int) -> tuple[int, int, float]:
    """Returns (lo_actual, lo_expected, fill_pct)."""
    df = pd.read_parquet(parquet_path)
    df.index = pd.to_datetime(df.index, utc=True)
    lo_actual   = len(df.between_time(LO_START, LO_END))
    lo_expected = _count_weekdays(year) * LO_BARS_PER_DAY
    fill_pct    = lo_actual / lo_expected if lo_expected > 0 else 0.0
    return lo_actual, lo_expected, fill_pct


def _decide(pair: str, year: int) -> tuple[str, str]:
    """Returns ('skip'|'fetch'|'refetch', reason)."""
    path = RAW_DIR / f"dukascopy_{pair}_{year}.parquet"
    if not path.exists():
        return "fetch", "parquet missing"
    try:
        lo_actual, lo_expected, fill_pct = _lo_fill(path, year)
        if fill_pct >= LO_FILL_GATE:
            return "skip", f"LO fill {fill_pct:.1%} ({lo_actual}/{lo_expected}) ≥ {LO_FILL_GATE:.0%}"
        return "refetch", f"LO fill {fill_pct:.1%} ({lo_actual}/{lo_expected}) < {LO_FILL_GATE:.0%}"
    except Exception as exc:
        return "refetch", f"error reading parquet: {exc}"


# ── markdown table ─────────────────────────────────────────────────────────

def _write_validation_table(val: dict[tuple[str, int], dict]) -> bool:
    """Appends Data Quality v2 block to _ic_feasibility.md. Returns all_pass."""
    rows = sorted(val.items(), key=lambda kv: (kv[0][1], kv[0][0]))
    all_pass = all(v["fill_pct"] >= LO_FILL_GATE for _, v in rows)

    header = (
        "\n---\n\n"
        "## DATA QUALITY v2 (fetch_data_v2.py)\n\n"
        "| Year | Pair | Bars total | LO bars (07:00–08:59) | LO expected | LO fill % | Status |\n"
        "|---|---|---|---|---|---|---|\n"
    )
    body_lines = []
    for (pair, year), info in rows:
        status = "OK ✓" if info["fill_pct"] >= LO_FILL_GATE else "FAIL ✗"
        body_lines.append(
            f"| {year} | {pair} | {info['bars_total']:,} | {info['lo_actual']:,} "
            f"| ~{info['lo_expected']:,} | {info['fill_pct']:.1%} | {status} |\n"
        )

    if all_pass:
        footer = "\n**ALL cells ≥ 95% → Proceed to IC analysis (`python3 run_all.py`).**\n"
    else:
        failed = [f"{p} {y}" for (p, y), info in rows if info["fill_pct"] < LO_FILL_GATE]
        footer = f"\n**GATE FAIL: {', '.join(failed)} — re-fetch these year-pairs before IC analysis.**\n"

    block = header + "".join(body_lines) + footer

    content = IC_MD.read_text(encoding="utf-8") if IC_MD.exists() else ""
    marker = "## DATA QUALITY v2"
    if marker in content:
        # Replace existing block
        start = content.rfind("\n---", 0, content.index(marker))
        start = start if start != -1 else content.index(marker)
        content = content[:start] + block
    else:
        content += block
    IC_MD.write_text(content, encoding="utf-8")
    print(f"\nValidation table written → {IC_MD.name}", flush=True)
    return all_pass


# ── main ───────────────────────────────────────────────────────────────────

def main() -> None:
    _setup_logging()
    log.debug(f"# fetch_data_v2.py — CONCURRENCY={CONCURRENCY} DELAY={DELAY_S}s RETRIES={MAX_RETRIES}")
    print(
        f"Dukascopy fetch v2\n"
        f"  CONCURRENCY={CONCURRENCY}  DELAY={DELAY_S}s  MAX_RETRIES={MAX_RETRIES}\n"
        f"  LO gate: {LO_START}–{LO_END} UTC ≥ {LO_FILL_GATE:.0%}\n"
        f"  Log → {LOG_FILE.name}\n",
        flush=True,
    )

    val: dict[tuple[str, int], dict] = {}

    for pair in PAIRS:
        for year in range(START_YEAR, END_YEAR + 1):
            out_path = RAW_DIR / f"dukascopy_{pair}_{year}.parquet"
            decision, reason = _decide(pair, year)
            print(f"\n[{pair} {year}]  {decision.upper():<8} {reason}", flush=True)
            log.debug(f"\n### {pair} {year} — {decision.upper()}: {reason}")

            if decision == "skip":
                lo_actual, lo_expected, fill_pct = _lo_fill(out_path, year)
                df_cached = pd.read_parquet(out_path)
                val[(pair, year)] = {
                    "bars_total": len(df_cached),
                    "lo_actual":  lo_actual,
                    "lo_expected": lo_expected,
                    "fill_pct":   fill_pct,
                }
                continue

            # Re-fetch
            if out_path.exists():
                out_path.unlink()
                print(f"  Deleted stale parquet: {out_path.name}", flush=True)

            df_year = asyncio.run(_fetch_year_async(pair, year))

            if df_year.empty:
                print(f"  WARNING: {pair} {year} — zero bars, skipping save", flush=True)
                val[(pair, year)] = {
                    "bars_total": 0,
                    "lo_actual":  0,
                    "lo_expected": _count_weekdays(year) * LO_BARS_PER_DAY,
                    "fill_pct":   0.0,
                }
                continue

            df_year.to_parquet(out_path)
            lo_actual, lo_expected, fill_pct = _lo_fill(out_path, year)
            bars_total = len(df_year)
            gate_label = "OK ✓" if fill_pct >= LO_FILL_GATE else "FAIL ✗"
            print(
                f"  Saved {bars_total:,} bars → {out_path.name}\n"
                f"  LO fill: {lo_actual}/{lo_expected} = {fill_pct:.1%}  [{gate_label}]",
                flush=True,
            )
            val[(pair, year)] = {
                "bars_total": bars_total,
                "lo_actual":  lo_actual,
                "lo_expected": lo_expected,
                "fill_pct":   fill_pct,
            }

    # ── Validation summary ─────────────────────────────────────────────────
    print("\n" + "=" * 60, flush=True)
    print("VALIDATION GATE — LO fill ≥ 95% per year-pair", flush=True)
    print("=" * 60, flush=True)
    all_pass = True
    for (pair, year), info in sorted(val.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        ok = info["fill_pct"] >= LO_FILL_GATE
        if not ok:
            all_pass = False
        status = "OK" if ok else "FAIL"
        print(
            f"  {year} {pair:8s}  LO {info['fill_pct']:.1%}"
            f"  ({info['lo_actual']:,}/{info['lo_expected']:,})  [{status}]",
            flush=True,
        )

    # ── Combined parquets ──────────────────────────────────────────────────
    if all_pass:
        print("\n✓ ALL PASS — building combined parquets...", flush=True)
        for pair in PAIRS:
            year_dfs = []
            for year in range(START_YEAR, END_YEAR + 1):
                p = RAW_DIR / f"dukascopy_{pair}_{year}.parquet"
                if p.exists():
                    year_dfs.append(pd.read_parquet(p))
            if year_dfs:
                full = pd.concat(year_dfs).sort_index()
                out = RAW_DIR / f"dukascopy_{pair}_2020_2024.parquet"
                full.to_parquet(out)
                print(f"  {pair}: {len(full):,} bars → {out.name}", flush=True)
    else:
        print(
            "\n✗ GATE FAIL — combined parquets NOT written.\n"
            "  Fix failing year-pairs, then re-run fetch_data_v2.py.\n"
            "  Only passing year-pairs are retained on disk.",
            flush=True,
        )

    # ── Write markdown table ───────────────────────────────────────────────
    _write_validation_table(val)

    if all_pass:
        print("\n→ All gates passed. Run IC analysis:\n  python3 run_all.py\n", flush=True)
    else:
        print("\n→ Re-run fetch_data_v2.py after fixing failures.\n", flush=True)


if __name__ == "__main__":
    main()
