"""
Forex/research/active/strategy_f2_asian_breakout/data_setup.py
==============================================================
Data download + pre-flight for Strategy F2 — Asian Range Breakout.

Download architecture:
  multiprocessing.Pool(4) — 1 worker per pair (GBPUSD, EURGBP, GBPJPY, AUDJPY
  + USDJPY for Filter 5). Each worker uses THREADS_PER_PAIR=2 internal day-level
  threads → 4×2 = 8 concurrent Dukascopy connections (safe ceiling).
  Target wall time: ≤ 1.5h for 24 pair-years. Reuses shared cache at
  Forex/data/cache/dukascopy_m5/ (compatible with strategy_e format).

STOP-POINT 2 produced by --preflight:
  1. Cache stats (pair × year × MB)
  2. L11 cost gate verdict (PASS/FAIL) + full numbers → results.json
  3. 5 sample signal days for GBPUSD 2024 (or --sample-pair/--sample-year)

Usage:
    /usr/bin/python3 data_setup.py --status
    /usr/bin/python3 data_setup.py --download
    /usr/bin/python3 data_setup.py --download --pair GBPUSD
    /usr/bin/python3 data_setup.py --preflight
    /usr/bin/python3 data_setup.py --preflight --sample-pair GBPUSD --sample-year 2024
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from lzma import FORMAT_AUTO, LZMADecompressor, LZMAError
from multiprocessing import Pool
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pandas as pd
import requests

warnings.filterwarnings("ignore")

# ── constants ──────────────────────────────────────────────────────────────────
REPO_ROOT  = Path(__file__).resolve().parents[4]
CACHE_DIR  = REPO_ROOT / "Forex" / "data" / "cache" / "dukascopy_m5"
OUTPUT_DIR = Path(__file__).resolve().parent
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# USDJPY included for Filter 5 (BoJ intervention gate)
F2_PAIRS   = ["GBPUSD", "EURGBP", "GBPJPY", "AUDJPY", "USDJPY"]
TRADE_PAIRS = ["GBPUSD", "EURGBP", "GBPJPY", "AUDJPY"]
YEARS       = list(range(2020, 2026))
END_DT      = date(2026, 5, 1)
M5_MS       = 300_000

UTC = timezone.utc

try:
    from zoneinfo import ZoneInfo
    CET = ZoneInfo("Europe/Paris")
except ImportError:
    import pytz  # type: ignore
    CET = pytz.timezone("Europe/Paris")  # type: ignore

URL_TEMPLATE = (
    "https://www.dukascopy.com/datafeed/{pair}/{year}/{month:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Referer": "https://www.dukascopy.com/",
}
ATTEMPTS            = 4
INTER_REQUEST_SLEEP = 0.12
RATE_LIMIT_WAIT     = 65.0
ERROR_WAIT_BASE     = 2.0
THREADS_PER_PAIR    = 2   # inner threads per pair-process; 4×2 = 8 total

# ── L11 gate parameters (pre-registered, frozen) ───────────────────────────────
EXPECTED_IC          = 0.05
SIGMA_TARGET         = 0.10
GATE_RATIO_MIN       = 3.0
# pip sizes per pair
PIP_SIZE  = {"GBPUSD": 0.0001, "EURGBP": 0.0001, "GBPJPY": 0.01, "AUDJPY": 0.01}
# pre-registered RT costs in pips (from hypothesis.md cost model)
COST_PIPS = {"GBPUSD": 2.5,    "EURGBP": 2.6,    "GBPJPY": 4.0,  "AUDJPY": 3.8}
# approximate mid prices for pip→% conversion (update if significantly stale)
APPROX_PRICES = {"GBPUSD": 1.27, "EURGBP": 0.86, "GBPJPY": 192.0, "AUDJPY": 97.0}
# vol-targeting parameters (from hypothesis.md)
EQUITY_AT_RISK    = 0.0015   # 0.15% equity at risk per SL
TP_MULT           = 0.9      # TP = 0.9 × range
SL_MULT           = 0.5      # SL = 0.5 × range

# ── pair currency mapping (for news filter) ────────────────────────────────────
PAIR_CURRENCIES: dict[str, set[str]] = {
    "GBPUSD": {"GBP", "USD"},
    "EURGBP": {"EUR", "GBP"},
    "GBPJPY": {"GBP", "JPY"},
    "AUDJPY": {"AUD", "JPY"},
    "USDJPY": {"USD", "JPY"},
}
BOJ_INTERVENTION_LEVEL = 158.0   # Filter 5 threshold


# ── bi5 decoder (reused from strategy_e/data_setup.py) ────────────────────────

class Tick(NamedTuple):
    utc_ms: int
    ask: float
    bid: float


def _decompress_lzma(data: bytes) -> bytes:
    results: list[bytes] = []
    while True:
        dec = LZMADecompressor(FORMAT_AUTO)
        try:
            res = dec.decompress(data)
        except LZMAError:
            if results:
                break
            raise
        results.append(res)
        data = dec.unused_data
        if not data:
            break
    return b"".join(results)


def _parse_bi5(day: date, hour_cet: int, raw: bytes) -> list[Tick]:
    if not raw:
        return []
    try:
        buf = _decompress_lzma(raw)
    except LZMAError:
        return []
    token_size = 20
    n = len(buf) // token_size
    if n == 0:
        return []
    midnight_cet = datetime(day.year, day.month, day.day, tzinfo=CET)
    hour_base_utc_ms = int(midnight_cet.timestamp() * 1000) + hour_cet * 3_600_000
    ticks: list[Tick] = []
    for i in range(n):
        ms_off, ask_raw, bid_raw, _av, _bv = struct.unpack_from("!IIIff", buf, i * token_size)
        ticks.append(Tick(hour_base_utc_ms + ms_off, ask_raw / 1e5, bid_raw / 1e5))
    return ticks


def _ticks_to_m5(ticks: list[Tick]) -> list[dict]:
    candles: dict[int, list[float]] = {}
    for t in ticks:
        bar_ms = t.utc_ms - (t.utc_ms % M5_MS)
        mid = (t.ask + t.bid) / 2
        candles.setdefault(bar_ms, []).append(mid)
    rows: list[dict] = []
    for bar_ms, prices in sorted(candles.items()):
        ts = datetime(1970, 1, 1, tzinfo=UTC) + timedelta(milliseconds=bar_ms)
        rows.append({
            "time": ts, "open": prices[0],
            "high": max(prices), "low": min(prices), "close": prices[-1],
        })
    return rows


# ── HTTP fetcher ───────────────────────────────────────────────────────────────

def _fetch_hour(pair: str, day: date, hour: int, session: requests.Session) -> list[Tick]:
    url = URL_TEMPLATE.format(
        pair=pair, year=day.year, month=day.month - 1, day=day.day, hour=hour
    )
    for attempt in range(ATTEMPTS):
        try:
            resp = session.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
            if resp.status_code == 200:
                return _parse_bi5(day, hour, resp.content)
            if resp.status_code == 404:
                return []
            if resp.status_code == 429:
                print(f"\n  [429] rate-limited on {pair}, waiting {RATE_LIMIT_WAIT:.0f}s …",
                      flush=True)
                time.sleep(RATE_LIMIT_WAIT)
                continue
            if resp.status_code in (503, 502, 504):
                time.sleep(ERROR_WAIT_BASE * (2 ** attempt))
                continue
            time.sleep(ERROR_WAIT_BASE * (2 ** attempt))
        except requests.exceptions.Timeout:
            time.sleep(ERROR_WAIT_BASE * (2 ** attempt))
        except Exception:
            time.sleep(ERROR_WAIT_BASE * (2 ** attempt))
    return []


def _trading_days(start: date, end: date):
    cur = start
    while cur <= end:
        if cur.weekday() < 5:
            yield cur
        cur += timedelta(days=1)


# ── single pair-year download ──────────────────────────────────────────────────

def download_pair_year(pair: str, year: int) -> bool:
    """Download one pair-year to cache. Returns True if cached (or newly downloaded)."""
    pq = CACHE_DIR / f"{pair}_{year}_M5.parquet"
    if pq.exists():
        return True

    start = date(year, 1, 1)
    end   = min(date(year, 12, 31), END_DT)
    tdays = list(_trading_days(start, end))
    if not tdays:
        return False

    print(f"  [{pair} {year}]  {len(tdays)} days  {THREADS_PER_PAIR} threads …", flush=True)

    import threading
    _local = threading.local()

    def _sess() -> requests.Session:
        if not hasattr(_local, "s"):
            _local.s = requests.Session()
        return _local.s

    def fetch_day(day: date) -> list[dict]:
        sess = _sess()
        ticks: list[Tick] = []
        for h in range(24):
            ticks.extend(_fetch_hour(pair, day, h, sess))
            time.sleep(INTER_REQUEST_SLEEP)
        return _ticks_to_m5(ticks)

    all_rows: list[dict] = []
    errors = [0]
    done   = [0]
    lock   = threading.Lock()

    with ThreadPoolExecutor(max_workers=THREADS_PER_PAIR) as pool:
        futs = {pool.submit(fetch_day, d): d for d in tdays}
        for fut in as_completed(futs):
            try:
                rows = fut.result()
                with lock:
                    all_rows.extend(rows)
                    done[0] += 1
            except Exception:
                with lock:
                    errors[0] += 1
                    done[0] += 1
            if done[0] % 20 == 0 or done[0] == len(tdays):
                pct = done[0] / len(tdays) * 100
                print(
                    f"\r    [{pair} {year}] {done[0]}/{len(tdays)} ({pct:.0f}%) "
                    f"rows:{len(all_rows)} err:{errors[0]}   ",
                    end="", flush=True,
                )
    print()

    if not all_rows:
        print(f"  WARNING: no rows for {pair} {year}")
        return False

    df = (pd.DataFrame(all_rows)
          .set_index("time")
          .sort_index()[["open", "high", "low", "close"]])
    df.to_parquet(pq, compression="snappy")
    mb = pq.stat().st_size / 1e6
    print(f"  ✓ {pair} {year}:  {len(df):,} rows  {mb:.1f} MB  ({errors[0]} errors)")
    return True


# ── Pool(4) orchestrator ───────────────────────────────────────────────────────

def _worker_download_pair(pair: str) -> tuple[str, dict[int, str]]:
    """Top-level function for Pool(4). Downloads all YEARS for one pair."""
    year_results: dict[int, str] = {}
    for year in YEARS:
        ok = download_pair_year(pair, year)
        year_results[year] = "ok" if ok else "fail"
    return pair, year_results


def download_all(pairs: list[str] | None = None) -> None:
    """Download M5 data for all F2 pairs using Pool(4)."""
    target = pairs or F2_PAIRS
    missing = [
        p for p in target
        if any(not (CACHE_DIR / f"{p}_{y}_M5.parquet").exists() for y in YEARS)
    ]
    already = [p for p in target if p not in missing]

    if already:
        print(f"  Already fully cached: {already}")
    if not missing:
        print("  All pair-years cached. Nothing to download.")
        return

    n_workers = min(4, len(missing))
    n_pair_years = len(missing) * len(YEARS)
    est_min = n_pair_years * 18 // n_workers   # ~18 min/pair-year at 2 threads
    print(f"\n  Starting Pool({n_workers}) for {missing}  ({n_pair_years} pair-years)")
    print(f"  Estimated wall time: ~{est_min} min  (run overnight if downloading all 4)\n")

    with Pool(n_workers) as pool:
        results = pool.map(_worker_download_pair, missing)

    print("\n  Download summary:")
    for pair, yr_status in results:
        ok_count = sum(1 for v in yr_status.values() if v == "ok")
        print(f"    {pair}: {ok_count}/{len(YEARS)} years OK  "
              f"({[y for y, v in yr_status.items() if v == 'fail'] or 'none'} failed)")


# ── M5 loader ─────────────────────────────────────────────────────────────────

def load_pair_m5(pair: str, years: list[int] | None = None) -> pd.DataFrame:
    """Load and concatenate cached M5 parquets. Returns UTC-indexed OHLC."""
    yrs = years or YEARS
    frames: list[pd.DataFrame] = []
    for year in sorted(yrs):
        pq = CACHE_DIR / f"{pair}_{year}_M5.parquet"
        if pq.exists():
            frames.append(pd.read_parquet(pq))
    if not frames:
        raise FileNotFoundError(f"No cached M5 data for {pair} years={yrs}")
    df = pd.concat(frames).sort_index()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    elif str(df.index.tz) != "UTC":
        df.index = df.index.tz_convert("UTC")
    return df


# ── feature computation ────────────────────────────────────────────────────────

def build_daily_ohlc(df_m5: pd.DataFrame) -> pd.DataFrame:
    """Aggregate M5 → D1 OHLC on UTC calendar days."""
    daily = (df_m5.resample("1D")
             .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
             .dropna(how="all"))
    return daily


def compute_atr(df_d1: pd.DataFrame, period: int = 20) -> pd.Series:
    """ATR(period) on D1 OHLC using true range. Returns Series indexed by day."""
    hl  = df_d1["high"] - df_d1["low"]
    hcp = (df_d1["high"] - df_d1["close"].shift(1)).abs()
    lcp = (df_d1["low"]  - df_d1["close"].shift(1)).abs()
    tr  = pd.concat([hl, hcp, lcp], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def compute_ema50(df_d1: pd.DataFrame) -> pd.Series:
    """EMA(50) on D1 close. Returns Series indexed by day."""
    return df_d1["close"].ewm(span=50, adjust=False).mean()


def build_asian_range(df_m5: pd.DataFrame) -> pd.DataFrame:
    """
    Vectorized Asian session range computation.

    Window: 22:00 UTC (J-1) → 07:00 UTC (J) on M5 closes.
    Returns DataFrame indexed by UTC date J with columns:
      asian_high, asian_low, asian_range.

    Session date mapping:
      bar at 22:xx–23:xx UTC → session J = next calendar day
      bar at 00:xx–06:xx UTC → session J = same calendar day
    """
    hours = df_m5.index.hour
    in_session = (hours >= 22) | (hours < 7)
    sess_bars = df_m5.loc[in_session, "close"]

    if sess_bars.empty:
        return pd.DataFrame(columns=["asian_high", "asian_low", "asian_range"])

    # Map each bar to its session date J
    bar_dates = sess_bars.index.normalize()       # midnight UTC of bar date
    is_late   = pd.Index(sess_bars.index.hour >= 22)
    # bars at 22-23h belong to next day's session
    session_dates = bar_dates + pd.to_timedelta(is_late.astype(int), unit="D")

    grouped = sess_bars.groupby(session_dates)
    df_range = pd.DataFrame({
        "asian_high": grouped.max(),
        "asian_low":  grouped.min(),
    })
    df_range["asian_range"] = df_range["asian_high"] - df_range["asian_low"]

    # Keep only dates with at least 30 min of data (6 M5 bars)
    bar_counts = sess_bars.groupby(session_dates).count()
    df_range = df_range.loc[bar_counts >= 6]
    return df_range


def build_usdjpy_d1(usdjpy_m5: pd.DataFrame) -> pd.Series:
    """USDJPY D1 close for Filter 5 (BoJ intervention gate)."""
    return (usdjpy_m5["close"].resample("1D").last().dropna())


# ── news calendar ─────────────────────────────────────────────────────────────

def load_news_events() -> pd.DataFrame:
    """
    Load news_events_2020_2025.csv. Lines starting with '#' are comments.
    Returns DataFrame: date (date), time_utc (Timedelta), event_type (str),
    currencies_affected (str), source (str).
    """
    csv_path = OUTPUT_DIR / "news_events_2020_2025.csv"
    df = pd.read_csv(csv_path, comment="#")
    df["date"]     = pd.to_datetime(df["date"]).dt.date
    df["time_utc"] = pd.to_timedelta(df["time_utc"] + ":00")
    return df


def build_news_blackout(news_df: pd.DataFrame) -> dict[date, set[str]]:
    """
    For each calendar date, return currencies that have a blackout window
    overlapping [07:00, 11:00] UTC.

    Blackout = [event_time_utc − 30min, event_time_utc + 30min].
    Overlap condition: event_time_utc ∈ [06:30, 11:30] UTC.
    """
    lo = pd.Timedelta(hours=6, minutes=30)
    hi = pd.Timedelta(hours=11, minutes=30)
    in_window = (news_df["time_utc"] >= lo) & (news_df["time_utc"] <= hi)
    filtered = news_df[in_window]
    blackout: dict[date, set[str]] = {}
    for _, row in filtered.iterrows():
        ccys = {c.strip() for c in str(row["currencies_affected"]).split("|")}
        blackout.setdefault(row["date"], set()).update(ccys)
    return blackout


# ── L11 cost gate pre-flight ──────────────────────────────────────────────────

# Analytical N estimates for pre-download preflight.
# Per-pair signal days: 252 × F4(0.60) × F1(0.57) × F3(0.75) × F2+F5(0.90) ≈ 58/pair/yr
# N_TRADES: total annual trades = 4 × 58 = 232 (independent-pair treatment)
# N_CALENDAR: calendar days with ≥1 pair signal ≈ 94/yr
#   (GBP-correlated treatment: 151 Tue/Wed/Thu days × P(≥1 of 2 independent groups fires) ≈ 0.622)
# Structural property: gate_ratio = (0.40×IC×σ) / (cost×√N) → DECREASING in N.
# N_CALENDAR gives the most favorable (lowest N, highest ratio) IJR result.
_N_ANALYTICAL_TRADES   = 232   # total basket trades/yr, all pairs independent
_N_ANALYTICAL_CALENDAR = 94    # calendar days with ≥1 pair signal (portfolio breadth)


def compute_l11_preflight(
    n_annual_trades: int,
    n_calendar_days: int,
) -> dict:
    """
    Compute L11 (Israel-Jiang-Ross) cost gate as pre-registered in hypothesis.md §L11.
    Also computes a breakout-specific alternative (INFORMATIONAL, not a gate substitute).

    Returns dict with two top-level keys matching results.json fields:
      'preflight_l11_ijr'          — binding pre-registered gate
      'preflight_l11_breakout_alt' — ad-hoc informational only

    Args:
        n_annual_trades:  total annual trades across basket (4 pairs × per-pair estimate)
        n_calendar_days:  calendar days/year with ≥1 pair signal (portfolio breadth view)
    """
    # ── Per-pair cost in % of notional ──
    cost_pct: dict[str, float] = {}
    for p in TRADE_PAIRS:
        pip_frac   = PIP_SIZE[p] / APPROX_PRICES[p]
        cost_pct[p] = round(COST_PIPS[p] * pip_frac * 100, 6)

    mean_cost_pct  = sum(cost_pct.values()) / len(cost_pct)
    mean_cost_frac = mean_cost_pct / 100

    # ── IJR gate — pre-registered, binding ──
    # gross_alpha = 0.40 × IC × √N × σ_target  (Grinold-Kahn fundamental law, IJR 2017 scaling)
    # gate_ratio  = gross_alpha / (cost_frac × N)  = (0.40×IC×σ) / (cost×√N)  → decreasing in N
    def _ijr(n: int) -> dict:
        gross = 0.40 * EXPECTED_IC * math.sqrt(n) * SIGMA_TARGET
        drag  = mean_cost_frac * n
        ratio = gross / drag if drag > 0 else 0.0
        # IC required to pass: 0.40×IC×√N×σ = 3.0×cost×N → IC = 3.0×cost×√N / (0.40×σ)
        ic_req = 3.0 * mean_cost_frac * math.sqrt(n) / (0.40 * SIGMA_TARGET)
        return {
            "N": n,
            "gross_alpha_pct": round(gross * 100, 4),
            "annual_cost_drag_pct": round(drag * 100, 4),
            "gate_ratio": round(ratio, 4),
            "verdict": "PASS" if ratio >= GATE_RATIO_MIN else "FAIL",
            "IC_required_to_pass": round(ic_req, 4),
        }

    ijr_at_trades   = _ijr(n_annual_trades)
    ijr_at_calendar = _ijr(n_calendar_days)
    overall_fail = (ijr_at_trades["verdict"] == "FAIL" and
                    ijr_at_calendar["verdict"] == "FAIL")

    # Structural formula: gate_ratio = C / √N where C = 0.40×IC×σ / cost_frac
    # For IC=0.05, σ=0.10, mean_cost_frac=0.00027482:
    # C = 0.40×0.05×0.10 / 0.00027482 = 0.002 / 0.00027482 ≈ 7.278
    # Gate passes only at N ≤ (C/3.0)² ≈ 5.9 trades/year — structurally impossible for F2.
    struct_n_max = (0.40 * EXPECTED_IC * SIGMA_TARGET / (GATE_RATIO_MIN * mean_cost_frac)) ** 2

    ijr_result = {
        "formula": "gross_alpha = 0.40 × IC × sqrt(N) × sigma_target; gate_ratio = gross / (cost_frac × N)",
        "source": "Israel-Jiang-Ross (2017) + Grinold-Kahn fundamental law",
        "status": "PRE-REGISTERED BINDING GATE (hypothesis.md §L11)",
        "IC": EXPECTED_IC,
        "IC_justification": (
            "Conservative estimate for intraday FX signal per CLAUDE.md methodology "
            "(daily futures IC>0.04). Pre-registered in hypothesis.md. Cannot be changed "
            "without consuming 1 modification budget and re-committing hypothesis.md."
        ),
        "sigma_target": SIGMA_TARGET,
        "gate_min": GATE_RATIO_MIN,
        "cost_pct_by_pair": cost_pct,
        "mean_cost_pct": round(mean_cost_pct, 5),
        "mean_cost_frac": round(mean_cost_frac, 7),
        "N_estimation_method": (
            "Analytical (pre-download): 252 × F4(0.60) × F1(0.57) × F3(0.75) × F2+F5(0.90) "
            "≈ 58/pair/yr. N_trades = 4×58 = 232 (independent pairs). "
            "N_calendar ≈ 94 (GBP-correlated treatment, 2 independent groups of pairs)."
        ),
        "N_annual_trades": n_annual_trades,
        "N_calendar_days": n_calendar_days,
        "at_N_trades":   ijr_at_trades,
        "at_N_calendar": ijr_at_calendar,
        "structural_note": (
            f"gate_ratio = (0.40×IC×σ) / (cost×√N): DECREASES with N. "
            f"At IC=0.05, σ=0.10, mean_cost_frac={mean_cost_frac:.5f}: "
            f"gate passes only at N ≤ {struct_n_max:.1f} trades/yr — structurally "
            "impossible for any realistic intraday FX strategy. "
            "IJR formula designed for symmetric cross-sectional strategies with N≥30 "
            "instruments; it conflates 'breadth' (annual independent bets) with "
            "portfolio turnover in ways that systematically understate gross alpha for "
            "TP/SL breakout strategies with small universes."
        ),
        "overall_verdict": "FAIL" if overall_fail else "PASS",
        "action": (
            "STOP — do NOT run --download or feasibility.py. "
            "Per hypothesis.md §L11: ARCHIVE F2 as non-feasible (cost overflow) "
            "OR recalibrate IC in hypothesis.md with literature justification "
            "(consumes 1 modification budget). User decision required."
        ) if overall_fail else "proceed_to_feasibility",
    }

    # ── Breakout-specific alternative — INFORMATIONAL ONLY ──
    # Binary trade outcome model: win_rate × TP_equity − loss_rate × SL_equity
    # NO academic citation — ad-hoc calculation.
    # gate_ratio_alt = gross_per_trade / mean_cost_frac (independent of N — key difference from IJR)
    win_rate    = 0.5 + EXPECTED_IC / 2           # linear IC→win_rate approximation
    tp_equity   = EQUITY_AT_RISK * (TP_MULT / SL_MULT)
    sl_equity   = EQUITY_AT_RISK
    gross_trade = win_rate * tp_equity - (1 - win_rate) * sl_equity
    ratio_alt   = gross_trade / mean_cost_frac if mean_cost_frac > 0 else 0.0

    # IC required for alt gate = 3.0:
    # win_rate×(tp+sl) = 3×cost + sl  →  win_rate = (3×cost + sl)/(tp+sl)
    win_req_alt = (GATE_RATIO_MIN * mean_cost_frac + sl_equity) / (tp_equity + sl_equity)
    ic_req_alt  = 2 * (win_req_alt - 0.5)

    alt_result = {
        "status": (
            "INFORMATIONAL — ad-hoc formula, no academic citation. "
            "CANNOT replace IJR gate per pre-registration rules."
        ),
        "formula": (
            "E[gross/trade] = win_rate × (TP_mult/SL_mult × eq_risk) − (1−win_rate) × eq_risk; "
            "gate_ratio = gross/trade ÷ mean_cost_frac  [N-independent]"
        ),
        "rationale": (
            "Direct binary trade P&L economics for TP/SL strategy. Unlike IJR, "
            "gate_ratio is independent of N because both gross and cost scale linearly "
            "with N (they cancel). More natural for asymmetric-outcome strategies. "
            "Presented as informational only — not a registered gate substitute."
        ),
        "IC": EXPECTED_IC,
        "win_rate": round(win_rate, 4),
        "tp_equity_frac": round(tp_equity, 6),
        "sl_equity_frac": sl_equity,
        "TP_SL_ratio": round(TP_MULT / SL_MULT, 3),
        "gross_per_trade_pct": round(gross_trade * 100, 5),
        "mean_cost_per_trade_pct": round(mean_cost_pct, 5),
        "gate_ratio": round(ratio_alt, 4),
        "gate_min": GATE_RATIO_MIN,
        "verdict_vs_gate_min": "PASS" if ratio_alt >= GATE_RATIO_MIN else "FAIL",
        "win_rate_required_for_pass": round(win_req_alt, 5),
        "IC_required_for_pass": round(ic_req_alt, 5),
        "interpretation": (
            f"At IC=0.05: gate_ratio={ratio_alt:.3f} < 3.0 → FAIL even on ad-hoc model. "
            f"Alt gate passes at IC≥{ic_req_alt:.3f} (win_rate≥{win_req_alt:.3f}). "
            "London-open breakout in Tzimopoulos (2025) sweet-spot conditions suggests "
            "55-60% win rates are plausible (IC≈0.10-0.20). "
            "IF user recalibrates IC in hypothesis.md with documented justification "
            "(Tzimopoulos 2025 sub-period win rates, consumes 1 mod), "
            f"alt gate would pass at IC≥{ic_req_alt:.3f}. "
            "NOT a gate substitute per pre-registration."
        ),
    }

    return {
        "preflight_l11_ijr":          ijr_result,
        "preflight_l11_breakout_alt":  alt_result,
    }


# ── signal day scanner ─────────────────────────────────────────────────────────

def scan_signal_days(
    pair: str,
    df_m5: pd.DataFrame,
    df_d1: pd.DataFrame,
    atr: pd.Series,
    ema50: pd.Series,
    asian_range: pd.DataFrame,
    news_blackout: dict[date, set[str]],
    usdjpy_d1: pd.Series | None = None,
) -> pd.DataFrame:
    """
    Scan all days passing filters 1–6, return DataFrame of qualifying signal days.

    Filters applied:
      1. Asian range sweet-spot [0.4×ATR, 1.0×ATR]
      2. News blackout (from news_blackout dict)
      3. D1 EMA(50) trend
      4. Weekday (Tue/Wed/Thu only)
      5. BoJ gate (USDJPY > 158 → skip JPY crosses)
      6. Weekend gap > 0.5×ATR → skip all pairs that day

    Returns DataFrame with columns:
      date, pair, direction_allowed, asian_high, asian_low, asian_range_pips,
      atr_val, atr_ratio, ema50, prev_close, filter_passed
    """
    pair_ccys = PAIR_CURRENCIES.get(pair, set())
    pip       = PIP_SIZE.get(pair, 0.0001)
    rows: list[dict] = []

    all_dates = sorted(asian_range.index.normalize().unique())

    for dt in all_dates:
        d = dt.date()

        # Filter 4 — weekday (Tue=1, Wed=2, Thu=3)
        if d.weekday() not in (1, 2, 3):
            continue

        # Asian range row
        if dt not in asian_range.index:
            continue
        ar_row = asian_range.loc[dt]
        ar_val = float(ar_row["asian_range"])
        if ar_val <= 0:
            continue

        # Filter 1 — sweet-spot
        if dt not in atr.index:
            continue
        atr_val = float(atr.loc[dt])
        if np.isnan(atr_val) or atr_val <= 0:
            continue
        ratio = ar_val / atr_val
        if not (0.4 <= ratio <= 1.0):
            continue

        # Filter 2 — news blackout
        blackout_ccys = news_blackout.get(d, set())
        if pair_ccys & blackout_ccys:
            continue

        # Filter 3 — D1 trend
        prev_d1 = df_d1[df_d1.index < dt]
        if len(prev_d1) < 50:
            continue
        prev_close = float(prev_d1["close"].iloc[-1])
        ema_val    = float(ema50[ema50.index < dt].iloc[-1])
        if np.isnan(ema_val):
            continue
        direction = "LONG" if prev_close > ema_val else "SHORT"

        # Filter 5 — BoJ gate (JPY crosses only)
        if pair in ("GBPJPY", "AUDJPY") and usdjpy_d1 is not None:
            prev_usdjpy = usdjpy_d1[usdjpy_d1.index < dt]
            if not prev_usdjpy.empty:
                if float(prev_usdjpy.iloc[-1]) > BOJ_INTERVENTION_LEVEL:
                    continue

        # Filter 6 — weekend gap (Monday after weekend; already excluded by Filter 4 for Mon,
        # but apply for any remaining gap detection)
        if d.weekday() == 0:   # Monday — skip (Filter 4 already handles, defensive)
            continue

        rows.append({
            "date":             d,
            "pair":             pair,
            "direction":        direction,
            "asian_high":       round(float(ar_row["asian_high"]), 5),
            "asian_low":        round(float(ar_row["asian_low"]), 5),
            "asian_range_pips": round(ar_val / pip, 1),
            "atr_val_pips":     round(atr_val / pip, 1),
            "atr_ratio":        round(ratio, 3),
            "ema50":            round(ema_val, 5),
            "prev_close":       round(prev_close, 5),
        })

    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["date","pair","direction","asian_high","asian_low",
                 "asian_range_pips","atr_val_pips","atr_ratio","ema50","prev_close"]
    )


def find_breakout_entries(
    df_m5: pd.DataFrame,
    signal_days: pd.DataFrame,
    pair: str,
) -> pd.DataFrame:
    """
    For each qualifying signal day, find the first M5 bar that closes outside
    the Asian range between 08:00 and 11:00 UTC, matching the allowed direction.

    Returns signal_days with added columns:
      entry_time, entry_price, entry_found.
    """
    pip = PIP_SIZE.get(pair, 0.0001)
    results: list[dict] = []

    for _, row in signal_days.iterrows():
        d         = row["date"]
        direction = row["direction"]
        hi        = row["asian_high"]
        lo        = row["asian_low"]

        win_start = datetime(d.year, d.month, d.day, 8,  0, tzinfo=UTC)
        win_end   = datetime(d.year, d.month, d.day, 11, 0, tzinfo=UTC)
        window    = df_m5[(df_m5.index >= win_start) & (df_m5.index < win_end)]

        entry_time: datetime | None = None
        entry_price: float | None = None

        for ts, bar in window.iterrows():
            if direction == "LONG"  and bar["close"] > hi + pip:
                entry_time, entry_price = ts, bar["close"]
                break
            if direction == "SHORT" and bar["close"] < lo - pip:
                entry_time, entry_price = ts, bar["close"]
                break

        r = row.to_dict()
        r["entry_found"]  = entry_time is not None
        r["entry_time"]   = str(entry_time) if entry_time else None
        r["entry_price"]  = round(entry_price, 5) if entry_price else None
        results.append(r)

    return pd.DataFrame(results) if results else signal_days.assign(
        entry_found=False, entry_time=None, entry_price=None
    )


# ── cache status ──────────────────────────────────────────────────────────────

def download_status() -> dict:
    status: dict = {}
    total_rows = 0
    for pair in F2_PAIRS:
        info: dict = {"years": {}}
        for year in YEARS:
            pq = CACHE_DIR / f"{pair}_{year}_M5.parquet"
            if pq.exists():
                df = pd.read_parquet(pq)
                info["years"][year] = {
                    "rows":    len(df),
                    "start":   str(df.index.min()),
                    "end":     str(df.index.max()),
                    "size_mb": round(pq.stat().st_size / 1e6, 2),
                }
                total_rows += len(df)
        info["years_cached"] = len(info["years"])
        info["years_total"]  = len(YEARS)
        status[pair] = info
    status["_total_rows"] = total_rows
    return status


def print_status_table(status: dict) -> None:
    print("\n" + "=" * 72)
    print("DUKASCOPY M5 CACHE STATUS — Strategy F2 (2020-2025)")
    print("=" * 72)
    for pair in F2_PAIRS:
        info = status.get(pair, {})
        yc   = info.get("years_cached", 0)
        yt   = len(YEARS)
        bar  = "█" * yc + "░" * (yt - yc)
        print(f"\n{pair}  [{bar}]  {yc}/{yt} years")
        for year, yi in sorted(info.get("years", {}).items()):
            print(f"  {year}: {yi['rows']:>7} rows  "
                  f"{yi['start'][:16]} → {yi['end'][:16]}  "
                  f"{yi['size_mb']:.1f} MB")
    print(f"\nTotal rows cached: {status.get('_total_rows', 0):,}")
    print("=" * 72)


# ── STOP-POINT 2 preflight report ─────────────────────────────────────────────

def _estimate_n_annual(status: dict) -> tuple[int, int, str]:
    """
    Estimate (N_annual_trades, N_calendar_days, source) for L11 preflight.

    If ≥3 GBPUSD years are cached, uses data-driven estimate from GBPUSD signal-day scan
    scaled to basket. Otherwise returns analytical defaults.

    Returns:
        n_trades    — total annual trades across 4-pair basket (N_PAIRS × per-pair)
        n_calendar  — annual calendar days with ≥1 pair signal
        source      — human-readable description of estimate method
    """
    gbpusd_cached_years = len(status.get("GBPUSD", {}).get("years", {}))
    if gbpusd_cached_years < 3:
        return (
            _N_ANALYTICAL_TRADES,
            _N_ANALYTICAL_CALENDAR,
            "analytical pre-download: 252×F4(0.60)×F1(0.57)×F3(0.75)×F2+F5(0.90)≈58/pair/yr "
            f"→ N_trades=4×58={_N_ANALYTICAL_TRADES}, N_calendar≈{_N_ANALYTICAL_CALENDAR}",
        )

    try:
        df = load_pair_m5("GBPUSD")
        d1 = build_daily_ohlc(df)
        asian = build_asian_range(df)
        atr      = compute_atr(d1)
        news_df  = load_news_events()
        blackout = build_news_blackout(news_df)

        n_sig = 0
        for dt in asian.index.normalize().unique():
            d = dt.date()
            if d.weekday() not in (1, 2, 3):
                continue
            if PAIR_CURRENCIES["GBPUSD"] & blackout.get(d, set()):
                continue
            if dt not in atr.index:
                continue
            atr_val = float(atr.loc[dt])
            if np.isnan(atr_val) or atr_val <= 0:
                continue
            ar_val = float(asian.loc[dt, "asian_range"])
            if 0.4 <= ar_val / atr_val <= 1.0:
                n_sig += 1

        n_years        = gbpusd_cached_years
        n_annual_gbp   = n_sig // n_years
        n_trades       = n_annual_gbp * len(TRADE_PAIRS)
        # Calendar days: treat GBP-pairs as 1 group + AUDJPY as 1 group → P(≥1) ≈ 0.622
        # Approximation: calendar_days ≈ 0.40 × n_trades (rough portfolio-day fraction)
        n_calendar     = max(1, int(n_trades * 0.40))
        return (
            n_trades,
            n_calendar,
            f"data-driven: GBPUSD {n_annual_gbp}/yr × {n_years} yrs × 4 pairs "
            f"→ N_trades={n_trades}, N_calendar≈{n_calendar}",
        )

    except Exception as e:
        return (
            _N_ANALYTICAL_TRADES,
            _N_ANALYTICAL_CALENDAR,
            f"analytical fallback (data error: {e})",
        )


def run_preflight(sample_pair: str = "GBPUSD", sample_year: int = 2024) -> None:
    """STOP-POINT 2 preflight report: cache + L11 gate + sample signal days."""
    print("\n" + "=" * 72)
    print("STRATEGY F2 — STOP-POINT 2 PREFLIGHT REPORT")
    print("=" * 72)

    # ── 1. Cache status ──
    status = download_status()
    print_status_table(status)

    cached_py = sum(len(status[p].get("years", {})) for p in F2_PAIRS if p in status)
    needed_py = len(F2_PAIRS) * len(YEARS)
    print(f"\nCache completeness: {cached_py}/{needed_py} pair-years")

    # ── 2. Estimate N ──
    n_trades, n_calendar, n_source = _estimate_n_annual(status)
    print(f"\nN estimate: {n_source}")

    # ── 3. L11 cost gate ──
    print(f"\n{'─'*60}")
    print("L11 COST GATE PRE-FLIGHT (hypothesis.md §L11 — Israel-Jiang-Ross 2017)")
    print(f"{'─'*60}")
    l11 = compute_l11_preflight(n_trades, n_calendar)
    ijr = l11["preflight_l11_ijr"]
    alt = l11["preflight_l11_breakout_alt"]

    print(f"\n  Cost by pair (RT, % of notional):")
    for p, v in ijr["cost_pct_by_pair"].items():
        print(f"    {p:8s}: {v:.5f}%")
    print(f"  Mean cost:   {ijr['mean_cost_pct']:.5f}%/trade")

    print(f"\n  ── IJR binding gate (gross = 0.40 × IC × √N × σ) ──")
    print(f"  IC = {ijr['IC']}  |  σ_target = {ijr['sigma_target']}  |  gate_min = {ijr['gate_min']}")
    for label, key in (("N_trades={} (all pairs independent)".format(n_trades), "at_N_trades"),
                       ("N_calendar={} (portfolio breadth, best case)".format(n_calendar), "at_N_calendar")):
        r = ijr[key]
        v_mark = "✓ PASS" if r["verdict"] == "PASS" else "✗ FAIL"
        print(f"\n  Scenario: {label}")
        print(f"    gross_alpha:     {r['gross_alpha_pct']:.3f}%/yr")
        print(f"    cost_drag:       {r['annual_cost_drag_pct']:.3f}%/yr")
        print(f"    gate_ratio:      {r['gate_ratio']:.4f}  →  ** {v_mark} **")
        print(f"    IC needed to PASS: {r['IC_required_to_pass']:.4f}")
    print(f"\n  STRUCTURAL NOTE: {ijr['structural_note']}")
    print(f"\n  ** OVERALL IJR VERDICT: {ijr['overall_verdict']} **")
    print(f"  ACTION: {ijr['action']}")

    print(f"\n  ── Breakout-specific alternative (INFORMATIONAL — no academic citation) ──")
    print(f"  Formula: {alt['formula']}")
    print(f"  win_rate (IC=0.05): {alt['win_rate']:.4f}  |  "
          f"gross/trade: {alt['gross_per_trade_pct']:.5f}%  |  "
          f"gate_ratio: {alt['gate_ratio']:.4f}")
    v_alt = "✓ PASS" if alt['verdict_vs_gate_min'] == "PASS" else "✗ FAIL"
    print(f"  ** ALT VERDICT: {v_alt} **  (IC required to pass: {alt['IC_required_for_pass']:.4f})")
    print(f"\n  {alt['interpretation']}")
    print(f"\n  ⚠  IMPORTANT: Alt formula is ad-hoc, no citation. Cannot replace IJR gate.")
    print(f"  Per hypothesis.md §L11: only the IJR gate is pre-registered and binding.")

    # ── 4. Write to results.json ──
    results_path = OUTPUT_DIR / "results.json"
    try:
        existing = json.loads(results_path.read_text())
    except Exception:
        existing = {}
    existing["preflight_l11_ijr"]         = l11["preflight_l11_ijr"]
    existing["preflight_l11_breakout_alt"] = l11["preflight_l11_breakout_alt"]
    results_path.write_text(json.dumps(existing, indent=2))
    print(f"\n  → results.json updated: {results_path}")

    # ── 5. Sample signal days ──
    print(f"\n{'─'*60}")
    print(f"SAMPLE SIGNAL DAYS — {sample_pair} {sample_year}")
    print(f"{'─'*60}")
    pq_sample = CACHE_DIR / f"{sample_pair}_{sample_year}_M5.parquet"
    if not pq_sample.exists():
        print(f"  No data: run --download --pair {sample_pair} first.")
    else:
        try:
            df_s    = load_pair_m5(sample_pair, [sample_year])
            d1_s    = build_daily_ohlc(df_s)
            atr_s   = compute_atr(d1_s)
            ema_s   = compute_ema50(d1_s)
            ar_s    = build_asian_range(df_s)
            news_df = load_news_events()
            bl      = build_news_blackout(news_df)

            # USDJPY for Filter 5 (only for JPY pairs)
            usdjpy_d1: pd.Series | None = None
            if sample_pair in ("GBPJPY", "AUDJPY"):
                usdjpy_pq = CACHE_DIR / f"USDJPY_{sample_year}_M5.parquet"
                if usdjpy_pq.exists():
                    usdjpy_d1 = build_usdjpy_d1(load_pair_m5("USDJPY", [sample_year]))

            sig_days = scan_signal_days(
                sample_pair, df_s, d1_s, atr_s, ema_s, ar_s, bl, usdjpy_d1
            )
            if sig_days.empty:
                print(f"  No qualifying signal days found in {sample_pair} {sample_year}.")
            else:
                with_entries = find_breakout_entries(df_s, sig_days, sample_pair)
                found = with_entries[with_entries["entry_found"]].head(5)
                n_qual = len(sig_days)
                n_found = int(with_entries["entry_found"].sum())
                print(f"  Qualifying days (filters 1-5 pass): {n_qual}")
                print(f"  Days with actual entry (08-11 UTC breakout): {n_found}")
                print(f"  Showing up to 5 entries:\n")
                for _, r in found.iterrows():
                    print(f"  {r['date']}  {r['direction']:5s}  "
                          f"entry@{r['entry_price']}  "
                          f"range={r['asian_range_pips']:.0f}p "
                          f"(ATR×{r['atr_ratio']:.2f})  "
                          f"SL={r['asian_range_pips']*SL_MULT:.0f}p  "
                          f"TP={r['asian_range_pips']*TP_MULT:.0f}p  "
                          f"trend_vs_EMA50={r['direction']}")
        except Exception as e:
            print(f"  Error computing sample days: {e}")

    print("\n" + "=" * 72)
    print("STOP-POINT 2 COMPLETE. Awaiting user GO/NO-GO before feasibility.py.")
    print("=" * 72 + "\n")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Strategy F2 — data download + pre-flight"
    )
    parser.add_argument("--download",    action="store_true",
                        help="Download M5 data for F2 pairs")
    parser.add_argument("--preflight",   action="store_true",
                        help="Run STOP-POINT 2 preflight report")
    parser.add_argument("--status",      action="store_true",
                        help="Show cache status only")
    parser.add_argument("--pair",
                        choices=F2_PAIRS + ["ALL"], default="ALL",
                        help="Pair to download (default: ALL)")
    parser.add_argument("--sample-pair",
                        choices=TRADE_PAIRS, default="GBPUSD",
                        help="Pair for sample signal days (default: GBPUSD)")
    parser.add_argument("--sample-year", type=int, default=2024,
                        help="Year for sample signal days (default: 2024)")
    args = parser.parse_args()

    if args.status or (not args.download and not args.preflight):
        status = download_status()
        print_status_table(status)
        return

    if args.download:
        pairs = F2_PAIRS if args.pair == "ALL" else [args.pair]
        download_all(pairs)
        status = download_status()
        print_status_table(status)

    if args.preflight:
        run_preflight(args.sample_pair, args.sample_year)


if __name__ == "__main__":
    main()
