#!/usr/bin/env python3
"""
Phase 1 pre-flight IC tests — 3 candidate angles in parallel.

  1. CS-FS  : Cross-Sectional Funding Spread
               IC(funding_rate_8h_lag1  → fwd_7d_return)
               |corr(CS-FS portfolio, A proxy)| and |corr(CS-FS, B proxy)|

  2. PMR    : Perp-Spot Basis Mean-Reversion
               IC(basis_zscore_lag1 → fwd_{3d,7d,14d}_return)
               Identify optimal holding horizon.

  3. FRA-DN : Funding Rate Acceleration (delta-neutral)
               IC(funding_accel_lag1 → fwd_7d_return), FRA+ AND FRA-

Decision gate: IC > 0.04, t > 2.5, |ρ_A| < 0.3, |ρ_B| < 0.3
"""
from __future__ import annotations
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")

# ── Universe (liquid Binance perps, ~36 months history available) ─────────────
COINS = [
    "BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX",
    "LINK", "LTC", "ATOM", "NEAR", "OP", "ARB", "INJ", "SUI",
    "AAVE", "FIL", "UNI", "PEPE", "WIF", "TIA", "SEI", "MKR",
    "FTM", "MATIC", "BCH", "APT", "COMP", "CRV",
]

BN_FAPI = "https://fapi.binance.com"
BN_API  = "https://api.binance.com"

CACHE = Path(__file__).parent / "cache"
CACHE.mkdir(exist_ok=True)

START_DATE = "2023-06-01"   # HL funding starts May 2023; use June for safety
IC_GATE_MEAN = 0.04
IC_GATE_T    = 2.5
CORR_GATE    = 0.30

# ── HTTP helper ───────────────────────────────────────────────────────────────
def _get(url: str, params: dict | None = None, retries: int = 3) -> list | None:
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=20)
            if r.status_code == 200:
                return r.json()
            time.sleep(0.3 * (attempt + 1))
        except Exception:
            time.sleep(1)
    return None


# ── Data fetchers ─────────────────────────────────────────────────────────────
def fetch_funding(coin: str) -> pd.DataFrame:
    """Binance perp funding rate history, forward-paginated from START_DATE, cached."""
    sym = coin + "USDT"
    fpath = CACHE / f"funding_{coin}.pickle"
    if fpath.exists() and (time.time() - fpath.stat().st_mtime) < 86400:
        return pd.read_pickle(fpath)

    start_ms = int(pd.Timestamp(START_DATE, tz="UTC").timestamp() * 1000)
    records, cur_start = [], start_ms

    while True:
        data = _get(f"{BN_FAPI}/fapi/v1/fundingRate",
                    {"symbol": sym, "limit": 1000, "startTime": cur_start})
        if not data:
            break
        records.extend(data)
        if len(data) < 1000:
            break
        cur_start = int(data[-1]["fundingTime"]) + 1
        time.sleep(0.15)

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    df["ts"] = pd.to_datetime(df["fundingTime"].astype(int), unit="ms", utc=True)
    df["rate"] = df["fundingRate"].astype(float)
    df = (df[["ts", "rate"]].drop_duplicates("ts").sort_values("ts"))
    df.to_pickle(fpath)
    return df


def fetch_ohlcv(coin: str, months: int = 22, spot: bool = False) -> pd.DataFrame:
    """Binance daily OHLCV (perp or spot), cached."""
    sym = coin + "USDT"
    tag = "spot" if spot else "perp"
    fpath = CACHE / f"ohlcv_{coin}_{tag}.pickle"
    if fpath.exists() and (time.time() - fpath.stat().st_mtime) < 86400:
        return pd.read_pickle(fpath)

    base     = BN_API if spot else BN_FAPI
    endpoint = "/api/v3/klines" if spot else "/fapi/v1/klines"
    start_ms = int((time.time() - months * 30.5 * 86400) * 1000)

    cols = ["ot", "open", "high", "low", "close", "vol",
            "ct", "qvol", "n", "tbvol", "tbqvol", "x"]
    records = []
    cur_start = start_ms

    while True:
        data = _get(f"{base}{endpoint}",
                    {"symbol": sym, "interval": "1d",
                     "startTime": cur_start, "limit": 1000})
        if not data:
            break
        records.extend(data)
        if len(data) < 1000:
            break
        cur_start = int(data[-1][0]) + 1
        time.sleep(0.1)

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records, columns=cols)
    df["date"] = pd.to_datetime(df["ot"].astype(int), unit="ms", utc=True).dt.normalize()
    df["close"] = df["close"].astype(float)
    df["vol"]   = df["vol"].astype(float)
    df = df[["date", "close", "vol"]].drop_duplicates("date").sort_values("date")
    cutoff = pd.Timestamp(START_DATE, tz="UTC")
    df = df[df["date"] >= cutoff]
    df.to_pickle(fpath)
    return df


# ── Signal helpers ────────────────────────────────────────────────────────────
def funding_to_daily(df: pd.DataFrame) -> pd.Series:
    """Aggregate 8h funding rates to daily sum (3 payments/day)."""
    df = df.copy()
    df["date"] = df["ts"].dt.normalize()
    return df.groupby("date")["rate"].sum()


def cs_spearman_ic(signal_wide: pd.DataFrame,
                   fwd_wide: pd.DataFrame,
                   freq: str = "W-FRI") -> pd.Series:
    """
    Weekly cross-sectional Spearman IC.
    signal_wide: (date, coin) signal; fwd_wide: (date, coin) forward return.
    """
    # Align on the same dates
    common = signal_wide.index.intersection(fwd_wide.index)
    sig = signal_wide.loc[common]
    fwd = fwd_wide.loc[common]

    # Resample to weekly (end-of-week)
    sig_w = sig.resample(freq).last()
    fwd_w = fwd.resample(freq).last()
    common_w = sig_w.index.intersection(fwd_w.index)

    ics = []
    for dt in common_w:
        s = sig_w.loc[dt].dropna()
        f = fwd_w.loc[dt].dropna()
        shared = s.index.intersection(f.index)
        if len(shared) < 10:
            continue
        ic, _ = spearmanr(s[shared], f[shared])
        if not np.isnan(ic):
            ics.append(ic)

    return pd.Series(ics)


def t_stat(series: pd.Series) -> float:
    n = len(series)
    if n < 4:
        return np.nan
    return series.mean() / (series.std(ddof=1) / np.sqrt(n))


# ── Download all data ─────────────────────────────────────────────────────────
print("=" * 65)
print("PHASE 1 PRE-FLIGHT IC TESTS")
print(f"Universe: {len(COINS)} coins | Start: {START_DATE}")
print("=" * 65)

print("\n[DATA] Downloading funding + OHLCV...")
fund: dict[str, pd.Series] = {}     # coin → daily funding Series (date index)
perp: dict[str, pd.Series] = {}     # coin → daily close Series
spot_px: dict[str, pd.Series] = {}  # coin → daily spot close

for i, coin in enumerate(COINS):
    # Funding
    f = fetch_funding(coin)
    if not f.empty:
        fund[coin] = funding_to_daily(f)
    # Perp OHLCV
    p = fetch_ohlcv(coin, months=22, spot=False)
    if not p.empty:
        perp[coin] = p.set_index("date")["close"]
    # Spot OHLCV (for PMR)
    s = fetch_ohlcv(coin, months=22, spot=True)
    if not s.empty:
        spot_px[coin] = s.set_index("date")["close"]
    if (i + 1) % 10 == 0:
        print(f"  {i+1}/{len(COINS)} coins loaded...")

print(f"  Fund OK: {len(fund)} coins | Perp OK: {len(perp)} coins | Spot OK: {len(spot_px)} coins")

# Intersect universe to coins with all three data sources
ok_coins = sorted(set(fund) & set(perp) & set(spot_px))
print(f"  Full data (fund+perp+spot): {len(ok_coins)} coins → {ok_coins[:8]}…")

# Build wide DataFrames (date × coin)
_all_dates = sorted(set(d for c in ok_coins for d in perp[c].index))
idx = pd.DatetimeIndex(_all_dates)
if idx.tz is None:
    idx = idx.tz_localize("UTC")

perp_wide  = pd.DataFrame({c: perp[c]    for c in ok_coins}, index=idx).sort_index()
spot_wide  = pd.DataFrame({c: spot_px[c] for c in ok_coins}, index=idx).sort_index()
fund_wide  = pd.DataFrame({c: fund[c]    for c in ok_coins}, index=idx).sort_index()

# Fill funding forward within each day (3 payments → daily sum already; fill gaps)
fund_wide  = fund_wide.ffill(limit=3)
perp_wide  = perp_wide.ffill(limit=3)
spot_wide  = spot_wide.ffill(limit=3)

# ── Pre-compute returns ───────────────────────────────────────────────────────
ret_1d  = perp_wide.pct_change(1)
ret_3d  = perp_wide.pct_change(3).shift(-3)   # forward-looking at time T
ret_7d  = perp_wide.pct_change(7).shift(-7)
ret_14d = perp_wide.pct_change(14).shift(-14)

# TSMOM proxy (A): equal-weight portfolio of all coin daily returns
tsmom_proxy = ret_1d[ok_coins].mean(axis=1)

# Strategy B proxy: WLD and STX daily perp returns (coins used in backtest)
# If those coins aren't in ok_coins, use top-5 by avg funding as proxy
b_coins = [c for c in ["WLD", "STX", "TRUMP", "WIF"] if c in ok_coins]
if len(b_coins) >= 2:
    b_proxy = ret_1d[b_coins].mean(axis=1)
else:
    # Use top-5 highest average funding coins as B proxy
    avg_fund = fund_wide.mean()
    b_coins_fallback = avg_fund.nlargest(5).index.tolist()
    b_proxy = ret_1d[b_coins_fallback].mean(axis=1)
    print(f"  B proxy (fallback): {b_coins_fallback}")

print(f"  B proxy coins: {b_coins if b_coins else b_coins_fallback}")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1 — CS-FS: Cross-Sectional Funding Spread
# Signal: funding_rate_lag1 (most recent 8h rate, lag-1 day) → fwd_7d_return
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 65)
print("[1] CS-FS — Cross-Sectional Funding Spread")
print("─" * 65)

# Signal: daily total funding, shifted 1 day (lag-1, no look-ahead)
cs_fs_signal = fund_wide.shift(1)

ic_cs_fs = cs_spearman_ic(cs_fs_signal, ret_7d, freq="W-FRI")
n_cs_fs   = len(ic_cs_fs)
mean_cs_fs = ic_cs_fs.mean()
t_cs_fs   = t_stat(ic_cs_fs)
pct_pos_cs_fs = (ic_cs_fs > 0).mean() * 100

print(f"  IC(funding_rate_lag1 → fwd_7d) — N={n_cs_fs} weeks")
print(f"    mean_IC = {mean_cs_fs:+.4f}  |  t = {t_cs_fs:+.2f}  |  IC>0 in {pct_pos_cs_fs:.0f}% of weeks")

# IC sub-periods
for label, start, end in [("2023-H2", "2023-06", "2024-01"),
                            ("2024",    "2024-01", "2025-01"),
                            ("2025",    "2025-01", "2026-01"),
                            ("2026",    "2026-01", "2027-01")]:
    sub = ic_cs_fs[ic_cs_fs.index[ic_cs_fs.index >= 0]:] if hasattr(ic_cs_fs.index, 'year') else ic_cs_fs
    # We need dated ICs for sub-period breakdown — recompute with dates
    pass  # done below in a second pass

# Recompute with dates for sub-period analysis
def cs_spearman_ic_dated(signal_wide, fwd_wide, freq="W-FRI"):
    common = signal_wide.index.intersection(fwd_wide.index)
    sig = signal_wide.loc[common]
    fwd = fwd_wide.loc[common]
    sig_w = sig.resample(freq).last()
    fwd_w = fwd.resample(freq).last()
    common_w = sig_w.index.intersection(fwd_w.index)
    result = []
    for dt in common_w:
        s = sig_w.loc[dt].dropna()
        f = fwd_w.loc[dt].dropna()
        shared = s.index.intersection(f.index)
        if len(shared) < 10:
            continue
        ic, _ = spearmanr(s[shared], f[shared])
        if not np.isnan(ic):
            result.append((dt, ic))
    return pd.Series(dict(result))

ic_cs_fs_dated = cs_spearman_ic_dated(cs_fs_signal, ret_7d)
for label, y0, y1 in [("2024", 2024, 2025), ("2025", 2025, 2026), ("2026", 2026, 2027)]:
    sub = ic_cs_fs_dated[(ic_cs_fs_dated.index.year >= y0) & (ic_cs_fs_dated.index.year < y1)]
    if len(sub) >= 4:
        print(f"    {label}: IC={sub.mean():+.4f}  t={t_stat(sub):+.2f}  N={len(sub)}")

# Orthogonality check: simulate CS-FS long-short daily portfolio return
# Long top-5 funding coins, short bottom-5 funding coins (daily rebalance for now)
n_legs = 5
cs_fs_port = pd.Series(dtype=float, index=fund_wide.index)
for dt in fund_wide.index[28:]:
    sig_today = cs_fs_signal.loc[dt].dropna()
    if len(sig_today) < 2 * n_legs:
        cs_fs_port[dt] = np.nan
        continue
    long_coins  = sig_today.nlargest(n_legs).index
    short_coins = sig_today.nsmallest(n_legs).index
    long_ret  = ret_1d.loc[dt, long_coins].mean()
    short_ret = ret_1d.loc[dt, short_coins].mean()
    cs_fs_port[dt] = long_ret - short_ret

cs_fs_port = cs_fs_port.dropna()
corr_A_csfs = abs(np.corrcoef(
    cs_fs_port.reindex(tsmom_proxy.index).dropna(),
    tsmom_proxy.reindex(cs_fs_port.index).dropna()
)[0, 1]) if len(cs_fs_port) > 30 else np.nan

corr_B_csfs = abs(np.corrcoef(
    cs_fs_port.reindex(b_proxy.index).dropna(),
    b_proxy.reindex(cs_fs_port.index).dropna()
)[0, 1]) if len(cs_fs_port) > 30 else np.nan

print(f"  |corr(CS-FS port, A proxy)| = {corr_A_csfs:.3f}  [gate < {CORR_GATE}]")
print(f"  |corr(CS-FS port, B proxy)| = {corr_B_csfs:.3f}  [gate < {CORR_GATE}]")

gate_csfs = (
    abs(mean_cs_fs) >= IC_GATE_MEAN and
    abs(t_cs_fs) >= IC_GATE_T and
    corr_A_csfs < CORR_GATE and
    corr_B_csfs < CORR_GATE
)
print(f"  CS-FS gate: {'PASS ✓' if gate_csfs else 'FAIL ✗'}")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2 — PMR: Perp-Spot Basis Mean-Reversion
# Signal: z-score(basis) lag-1 → fwd_{3d,7d,14d}_return
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 65)
print("[2] PMR — Perp-Spot Basis Mean-Reversion")
print("─" * 65)

# Basis = (perp / spot - 1) × 100, in percent
basis_wide = (perp_wide / spot_wide - 1) * 100
# Rolling 90-day z-score per coin
basis_mean = basis_wide.rolling(90, min_periods=30).mean()
basis_std  = basis_wide.rolling(90, min_periods=30).std()
basis_z    = (basis_wide - basis_mean) / basis_std.clip(lower=1e-8)
pmr_signal = basis_z.shift(1)   # lag-1

gate_pmr = False
best_pmr_horizon = None
best_pmr_t = -999

for horizon, fwd_ret in [(3, ret_3d), (7, ret_7d), (14, ret_14d)]:
    ic_pmr = cs_spearman_ic(pmr_signal, fwd_ret, freq="W-FRI")
    n_pmr = len(ic_pmr)
    mean_pmr = ic_pmr.mean()
    t_pmr = t_stat(ic_pmr)
    pct_pos_pmr = (ic_pmr > 0).mean() * 100
    print(f"  IC(basis_z_lag1 → fwd_{horizon:2d}d): IC={mean_pmr:+.4f}  t={t_pmr:+.2f}"
          f"  N={n_pmr}  IC>0={pct_pos_pmr:.0f}%")
    if abs(t_pmr) > abs(best_pmr_t):
        best_pmr_t = t_pmr
        best_pmr_horizon = horizon

# Portfolio-level correlation (long coins where basis_z < 0, short where basis_z > 0
# i.e., fade expensive perps vs spot)
pmr_port = pd.Series(dtype=float, index=basis_z.index)
for dt in basis_z.index[90:]:
    sig_today = pmr_signal.loc[dt].dropna()
    if len(sig_today) < 10:
        pmr_port[dt] = np.nan
        continue
    # PMR: buy when basis_z LOW (perp cheap vs spot), sell when basis_z HIGH
    long_coins  = sig_today.nsmallest(5).index    # low basis_z = perp cheap
    short_coins = sig_today.nlargest(5).index     # high basis_z = perp expensive
    long_ret  = ret_1d.loc[dt, long_coins].mean()
    short_ret = ret_1d.loc[dt, short_coins].mean()
    pmr_port[dt] = long_ret - short_ret

pmr_port = pmr_port.dropna()
corr_A_pmr = abs(np.corrcoef(
    pmr_port.reindex(tsmom_proxy.index).dropna(),
    tsmom_proxy.reindex(pmr_port.index).dropna()
)[0, 1]) if len(pmr_port) > 30 else np.nan
corr_B_pmr = abs(np.corrcoef(
    pmr_port.reindex(b_proxy.index).dropna(),
    b_proxy.reindex(pmr_port.index).dropna()
)[0, 1]) if len(pmr_port) > 30 else np.nan

print(f"  Best horizon: {best_pmr_horizon}d (highest |t|={abs(best_pmr_t):.2f})")
print(f"  |corr(PMR port, A proxy)| = {corr_A_pmr:.3f}  [gate < {CORR_GATE}]")
print(f"  |corr(PMR port, B proxy)| = {corr_B_pmr:.3f}  [gate < {CORR_GATE}]")

gate_pmr = (
    abs(best_pmr_t) >= IC_GATE_T and
    corr_A_pmr < CORR_GATE and
    corr_B_pmr < CORR_GATE
)
print(f"  PMR gate: {'PASS ✓' if gate_pmr else 'FAIL ✗'}")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3 — FRA-DN: Funding Rate Acceleration, delta-neutral
# Signal: funding_accel = daily_funding - rolling_mean_28d(daily_funding)
# Test both FRA+ and FRA- without pre-judging direction
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 65)
print("[3] FRA-DN — Funding Rate Acceleration (delta-neutral)")
print("─" * 65)

# Acceleration: deviation of daily funding from its 28d rolling mean
fund_mean_28 = fund_wide.rolling(28, min_periods=14).mean()
fund_accel   = fund_wide - fund_mean_28
fra_signal   = fund_accel.shift(1)

ic_fra = cs_spearman_ic_dated(fra_signal, ret_7d)
n_fra   = len(ic_fra)
mean_fra = ic_fra.mean()
t_fra   = t_stat(ic_fra)
pct_pos_fra = (ic_fra > 0).mean() * 100

print(f"  IC(fund_accel_lag1 → fwd_7d) — N={n_fra} weeks")
print(f"    FRA+  IC={mean_fra:+.4f}  t={t_fra:+.2f}  IC>0={pct_pos_fra:.0f}%")
print(f"    FRA-  IC={-mean_fra:+.4f}  t={-t_fra:+.2f}  IC>0={100-pct_pos_fra:.0f}%")

# Sub-periods
for label, y0, y1 in [("2024", 2024, 2025), ("2025", 2025, 2026), ("2026", 2026, 2027)]:
    sub = ic_fra[(ic_fra.index.year >= y0) & (ic_fra.index.year < y1)]
    if len(sub) >= 4:
        print(f"    {label}: IC={sub.mean():+.4f}  t={t_stat(sub):+.2f}  N={len(sub)}")

# Determine best direction
best_fra_dir = "FRA+" if abs(mean_fra) == mean_fra else "FRA-"
best_fra_signal = fra_signal if mean_fra > 0 else -fra_signal

# Portfolio correlation
fra_port = pd.Series(dtype=float, index=fund_wide.index)
for dt in fund_wide.index[28:]:
    sig_today = best_fra_signal.loc[dt].dropna()
    if len(sig_today) < 10:
        fra_port[dt] = np.nan
        continue
    long_coins  = sig_today.nlargest(5).index
    short_coins = sig_today.nsmallest(5).index
    long_ret  = ret_1d.loc[dt, long_coins].mean()
    short_ret = ret_1d.loc[dt, short_coins].mean()
    fra_port[dt] = long_ret - short_ret

fra_port = fra_port.dropna()
corr_A_fra = abs(np.corrcoef(
    fra_port.reindex(tsmom_proxy.index).dropna(),
    tsmom_proxy.reindex(fra_port.index).dropna()
)[0, 1]) if len(fra_port) > 30 else np.nan
corr_B_fra = abs(np.corrcoef(
    fra_port.reindex(b_proxy.index).dropna(),
    b_proxy.reindex(fra_port.index).dropna()
)[0, 1]) if len(fra_port) > 30 else np.nan

print(f"  Best direction: {best_fra_dir}")
print(f"  |corr(FRA port, A proxy)| = {corr_A_fra:.3f}  [gate < {CORR_GATE}]")
print(f"  |corr(FRA port, B proxy)| = {corr_B_fra:.3f}  [gate < {CORR_GATE}]")

gate_fra = (
    abs(mean_fra) >= IC_GATE_MEAN and
    abs(t_fra) >= IC_GATE_T and
    corr_A_fra < CORR_GATE and
    corr_B_fra < CORR_GATE
)
print(f"  FRA-DN gate: {'PASS ✓' if gate_fra else 'FAIL ✗'}")


# ═══════════════════════════════════════════════════════════════════════════════
# DECISION TABLE
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 65)
print("DECISION TABLE")
print("=" * 65)
print(f"  {'Angle':<12} {'mean_IC':>8} {'t-stat':>8} {'|ρ_A|':>7} {'|ρ_B|':>7} {'Gate':>6}")
print(f"  {'─'*12} {'─'*8} {'─'*8} {'─'*7} {'─'*7} {'─'*6}")
print(f"  {'CS-FS':<12} {mean_cs_fs:>+8.4f} {t_cs_fs:>+8.2f} {corr_A_csfs:>7.3f} {corr_B_csfs:>7.3f} {'PASS' if gate_csfs else 'FAIL':>6}")
print(f"  {'PMR':<12} {'—':>8} {best_pmr_t:>+8.2f} {corr_A_pmr:>7.3f} {corr_B_pmr:>7.3f} {'PASS' if gate_pmr else 'FAIL':>6}")
print(f"  {'FRA-DN':<12} {mean_fra:>+8.4f} {t_fra:>+8.2f} {corr_A_fra:>7.3f} {corr_B_fra:>7.3f} {'PASS' if gate_fra else 'FAIL':>6}")
print(f"\n  Gates: |mean_IC| ≥ {IC_GATE_MEAN}, |t| ≥ {IC_GATE_T}, |ρ_A| < {CORR_GATE}, |ρ_B| < {CORR_GATE}")

passing = [
    ("CS-FS", gate_csfs, abs(mean_cs_fs), abs(t_cs_fs)),
    ("PMR",   gate_pmr,  0.0,             abs(best_pmr_t)),
    ("FRA-DN",gate_fra,  abs(mean_fra),   abs(t_fra)),
]
winners = [(name, ic, t) for name, ok, ic, t in passing if ok]

if winners:
    # Score: composite of IC and t-stat (equal weight)
    best = max(winners, key=lambda x: x[1] * 0.4 + x[2] * 0.6)
    print(f"\n  SELECTED ANGLE → {best[0]}")
    print(f"  Proceed to PHASE 2 (full data infrastructure + backtest).")
else:
    print(f"\n  ALL ANGLES FAIL GATE 1.")
    print(f"  Conclusion: free-data crypto edge orthogonal to A+B is")
    print(f"  structurally exhausted in this universe.")
    print(f"  → STOP. Archive mission. Write post-mortem.")

print("=" * 65)
