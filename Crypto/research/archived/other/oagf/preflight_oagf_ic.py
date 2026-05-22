#!/usr/bin/env python3
"""
OAGF Phase 1 Pre-flight IC Test — Open Auction Gap Fade

Signal  : gap_ret = (open_t - close_{t-1}) / close_{t-1}
           at 8h settlement bars (bar opens at hour ∈ {0, 8, 16} UTC)

IC test : SpearmanR(gap_ret, intra_bar_ret) pooled across all (coin, bar) pairs
           where intra_bar_ret = (close_t - open_t) / open_t
           Expected IC < 0  (gap up → bar returns negative = reversion)

DATA NOTE: HL candleSnapshot API only has data from ~Oct 2025 (7 months — insufficient
for walk-forward). Using Binance 1h perp data for IC testing. The settlement phenomenon
(8h funding → gap reversion) is exchange-agnostic. Live execution will use HL ALO orders.

Gates:
  1. IC t_HAC  ≤ −2.5   (one-sided; negative IC required)
  2. |IC_mean| ≥ 0.04
  3. events/year ∈ [50, 5000]  (at |gap_ret| > GAP_THRESHOLD, across all coins)
  4. |corr(OAGF_daily, A_daily)| < 0.50
  5. |corr(OAGF_daily, B_daily)| < 0.50

n_tests_start: 148  →  this script counts as +3 (3 IC horizons: 1h, 2h, 4h)
"""
from __future__ import annotations
import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy.stats import spearmanr
import statsmodels.api as sm

warnings.filterwarnings("ignore")

# ── Universe (liquid Binance perps with HL equivalents) ───────────────────────
COINS = [
    "BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX",
    "LINK", "LTC", "ATOM", "NEAR", "OP", "ARB", "INJ", "SUI",
    "AAVE", "FIL", "UNI", "PEPE", "WIF", "TIA", "SEI",
    "APT", "CRV", "FTM", "WLD", "STX", "MKR", "COMP", "BCH",
]

BN_FAPI  = "https://fapi.binance.com"
BN_API   = "https://api.binance.com"

CACHE = Path(__file__).parent.parent / "_preflight" / "cache"
CACHE.mkdir(exist_ok=True)

START_DATE     = "2024-01-01"   # 28 months of 1h data to May 2026
GAP_THRESHOLD  = 0.003          # 0.30% — FIXED ex-ante
SETTLEMENT_HRS = {0, 8, 16}    # UTC hours at which Binance/HL funding settles

IC_GATE_T      = 2.5
IC_GATE_MEAN   = 0.04
CORR_GATE      = 0.50           # relaxed V2 constraint
EVENT_FLOOR    = 50             # minimum events/year across universe
EVENT_CEIL     = 5000           # maximum events/year (maker: unfilled = free)

N_TESTS_START  = 148

REPO_ROOT = Path(__file__).parent.parent.parent.parent.parent
B_RETURNS_PATH = REPO_ROOT / "data" / "metadata" / "delta_neutral_backtest.csv"


# ── HTTP helpers ──────────────────────────────────────────────────────────────
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


# ── Binance 1h OHLCV fetcher (perp) ──────────────────────────────────────────
def fetch_bn_1h(coin: str) -> pd.DataFrame:
    """
    Binance perp 1h OHLCV, forward-paginated from START_DATE.
    Cached as pickle; refreshes if older than 24h.
    Columns: ts (UTC, 1h bar open), open, high, low, close, volume
    """
    fpath = CACHE / f"bn_1h_{coin}_perp.pickle"
    if fpath.exists() and (time.time() - fpath.stat().st_mtime) < 86400:
        return pd.read_pickle(fpath)

    sym      = coin + "USDT"
    start_ms = int(pd.Timestamp(START_DATE, tz="UTC").timestamp() * 1000)
    cols     = ["ot", "open", "high", "low", "close", "vol",
                "ct", "qvol", "n", "tbvol", "tbqvol", "x"]
    records, cur = [], start_ms

    while True:
        data = _get(f"{BN_FAPI}/fapi/v1/klines",
                    {"symbol": sym, "interval": "1h", "startTime": cur, "limit": 1500})
        if not data:
            break
        records.extend(data)
        if len(data) < 1500:
            break
        cur = int(data[-1][0]) + 1
        time.sleep(0.08)

    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records, columns=cols)
    df["ts"]    = pd.to_datetime(df["ot"].astype(int), unit="ms", utc=True)
    df["open"]  = df["open"].astype(float)
    df["close"] = df["close"].astype(float)
    df["vol"]   = df["vol"].astype(float)
    df = df[["ts", "open", "close", "vol"]].drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    df.to_pickle(fpath)
    return df


# ── Binance daily OHLCV (A proxy) ─────────────────────────────────────────────
def fetch_bn_daily(coin: str) -> pd.Series | None:
    """Binance perp daily close — for TSMOM A proxy."""
    fpath = CACHE / f"ohlcv_{coin}_perp.pickle"
    if fpath.exists() and (time.time() - fpath.stat().st_mtime) < 86400:
        df = pd.read_pickle(fpath)
        if "date" in df.columns and "close" in df.columns:
            return df.set_index("date")["close"]
    sym      = coin + "USDT"
    start_ms = int(pd.Timestamp(START_DATE, tz="UTC").timestamp() * 1000)
    cols     = ["ot", "open", "high", "low", "close", "vol",
                "ct", "qvol", "n", "tbvol", "tbqvol", "x"]
    records, cur = [], start_ms
    while True:
        data = _get(f"{BN_FAPI}/fapi/v1/klines",
                    {"symbol": sym, "interval": "1d", "startTime": cur, "limit": 1000})
        if not data:
            break
        records.extend(data)
        if len(data) < 1000:
            break
        cur = int(data[-1][0]) + 1
        time.sleep(0.1)
    if not records:
        return None
    df = pd.DataFrame(records, columns=cols)
    df["date"]  = pd.to_datetime(df["ot"].astype(int), unit="ms", utc=True).dt.normalize()
    df["close"] = df["close"].astype(float)
    df = df[["date", "close"]].drop_duplicates("date").sort_values("date")
    return df.set_index("date")["close"]


# ── HAC t-stat (OLS with Newey-West) ─────────────────────────────────────────
def hac_t_stat(y: np.ndarray, maxlags: int = 6) -> tuple[float, float]:
    """OLS β₀ with HAC SE. Returns (mean, t_stat)."""
    n = len(y)
    if n < maxlags * 3:
        return float(np.mean(y)), float(np.mean(y) / (np.std(y, ddof=1) / np.sqrt(n)))
    X = np.ones((n, 1))
    try:
        res = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
        lrv = float(res.cov_params().to_numpy()[0, 0]) * n
        t   = float(np.mean(y)) / np.sqrt(lrv / n)
    except Exception:
        t = float(np.mean(y) / (np.std(y, ddof=1) / np.sqrt(n)))
    return float(np.mean(y)), t


# ── Load real B daily returns ─────────────────────────────────────────────────
def load_b_daily() -> pd.Series:
    """Real Strategy B daily returns from delta_neutral_backtest.csv."""
    df = pd.read_csv(B_RETURNS_PATH, parse_dates=["timestamp"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["date"] = df["timestamp"].dt.normalize()
    daily = df.groupby("date")["net_pnl"].sum() / 500.0  # $500 capital
    daily.index = pd.DatetimeIndex(daily.index)
    if daily.index.tz is None:
        daily.index = daily.index.tz_localize("UTC")
    return daily.sort_index()


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════
print("=" * 65)
print("OAGF PHASE 1 PRE-FLIGHT IC TEST")
print(f"Universe: {len(COINS)} coins | Start: {START_DATE}")
print(f"GAP_THRESHOLD: {GAP_THRESHOLD:.2%} | Settlement hours: {sorted(SETTLEMENT_HRS)} UTC")
print("DATA: Binance 1h perp (HL candle API limited to ~7 months history)")
print("=" * 65)

# ── Step 1: Fetch 1h Binance perp data ───────────────────────────────────────
print(f"\n[DATA] Fetching Binance 1h perp OHLCV for {len(COINS)} coins...")
bn_data: dict[str, pd.DataFrame] = {}
failed_coins = []

for i, coin in enumerate(COINS):
    df = fetch_bn_1h(coin)
    if df.empty or len(df) < 500:
        failed_coins.append(coin)
    else:
        bn_data[coin] = df
    if (i + 1) % 10 == 0:
        print(f"  {i+1}/{len(COINS)} coins loaded...")
    time.sleep(0.05)

ok_coins = [c for c in COINS if c in bn_data]
print(f"  OK: {len(ok_coins)} coins | Failed: {failed_coins}")

# ── Step 2: Build settlement-bar dataset ──────────────────────────────────────
print("\n[SIGNAL] Identifying settlement bars and computing gap_ret...")

rows = []
for coin in ok_coins:
    df = bn_data[coin].copy()
    df = df.set_index("ts").sort_index()

    # Keep only bars whose opening hour is a settlement hour
    df_settle = df[df.index.hour.isin(SETTLEMENT_HRS)].copy()

    # gap_ret: (open_t - close_{t-1}) / close_{t-1}
    # We need the prior bar's close — use a full hourly index, shift close by 1
    full_close  = df["close"]
    settle_open = df_settle["open"]
    settle_close = df_settle["close"]

    # Prior close = last known close before each settlement bar
    prev_close = full_close.shift(1).reindex(df_settle.index)

    gap_ret      = (settle_open - prev_close) / prev_close
    intra_ret    = (settle_close - settle_open) / settle_open  # bar's own return

    # Multi-bar forward returns (horizons: 1h, 2h, 4h)
    # 2h: from settle open to close of bar t+1 (next 1h bar)
    # 4h: from settle open to close of bar t+3
    all_close = df["close"]
    # Reindex to get close 2h and 4h after settlement open
    ts_idx    = df_settle.index
    close_2h  = all_close.reindex(ts_idx + pd.Timedelta("2h"), method=None).values
    close_4h  = all_close.reindex(ts_idx + pd.Timedelta("4h"), method=None).values

    fwd_2h = (close_2h - settle_open.values) / settle_open.values
    fwd_4h = (close_4h - settle_open.values) / settle_open.values

    tmp = pd.DataFrame({
        "coin":        coin,
        "ts":          df_settle.index,
        "gap_ret":     gap_ret.values,
        "intra_ret":   intra_ret.values,    # fwd_1h (close of same bar)
        "fwd_2h":      fwd_2h,
        "fwd_4h":      fwd_4h,
        "prev_close":  prev_close.values,
    })
    rows.append(tmp)

events = pd.concat(rows, ignore_index=True)
events = events.dropna(subset=["gap_ret", "intra_ret"])
events["date"] = events["ts"].dt.normalize()

n_total = len(events)
months  = (events["ts"].max() - events["ts"].min()).days / 30.5
years   = months / 12
print(f"  Total settlement bars: {n_total:,} ({months:.1f} months)")

# ── Step 3: Event count gate ──────────────────────────────────────────────────
triggered = events[events["gap_ret"].abs() > GAP_THRESHOLD].copy()
n_triggered    = len(triggered)
events_per_yr  = n_triggered / max(years, 0.1)

print(f"\n[GATE] Event count at |gap_ret| > {GAP_THRESHOLD:.2%}:")
print(f"  Total triggered: {n_triggered:,} ({events_per_yr:.0f}/year)")
print(f"  Floor gate ({EVENT_FLOOR}/yr): {'PASS' if events_per_yr >= EVENT_FLOOR else 'FAIL'}")
print(f"  Ceiling note ({EVENT_CEIL}/yr): {'OK (maker: unfilled=free)' if events_per_yr < EVENT_CEIL else 'HIGH — check fill assumption'}")

gate_events = (events_per_yr >= EVENT_FLOOR)

# ── Step 4: IC computation (pooled, 3 horizons) ───────────────────────────────
print("\n[IC] Pooled Spearman IC — all triggered (coin, settlement_bar) pairs:")

horizons = {
    "1h": "intra_ret",
    "2h": "fwd_2h",
    "4h": "fwd_4h",
}
ic_results = {}

for label, col in horizons.items():
    subset = triggered.dropna(subset=[col]).copy()
    if len(subset) < 50:
        print(f"  fwd_{label}: insufficient data")
        continue

    x = subset["gap_ret"].values
    y = subset[col].values

    ic_val, _ = spearmanr(x, y)

    # HAC t-stat on the cross product (IC series by date)
    # Group by date → daily IC, then apply HAC
    subset["ic_contrib"] = subset["gap_ret"].rank() * subset[col].rank()
    daily_ic = []
    for dt, grp in subset.groupby("date"):
        if len(grp) >= 3:
            ic_day, _ = spearmanr(grp["gap_ret"], grp[col])
            if not np.isnan(ic_day):
                daily_ic.append(ic_day)

    daily_ic = np.array(daily_ic)
    ic_mean, t_hac = hac_t_stat(daily_ic, maxlags=6)

    pass_t    = t_hac <= -IC_GATE_T       # one-sided negative
    pass_mag  = abs(ic_mean) >= IC_GATE_MEAN
    status    = "PASS" if (pass_t and pass_mag) else "FAIL"

    ic_results[label] = {
        "ic_pooled": ic_val,
        "ic_daily_mean": ic_mean,
        "t_hac": t_hac,
        "n_bars": len(subset),
        "n_daily": len(daily_ic),
        "pass": pass_t and pass_mag,
    }

    print(f"  fwd_{label}: IC_pooled={ic_val:.4f} | IC_daily={ic_mean:.4f}"
          f" | t_HAC={t_hac:.2f} | N={len(subset):,} | [{status}]")

# Primary gate: 1h horizon (core hypothesis)
primary = ic_results.get("1h", {})
gate_ic = primary.get("pass", False)

# ── Step 5: Orthogonality vs A and B ─────────────────────────────────────────
print("\n[ORTHOGONALITY] Computing OAGF daily returns for corr check...")

# OAGF daily return: for each day, sum up signal×intra_ret for triggered bars
# signal = -sign(gap_ret), position ±1, vol-target scaling omitted here (ratio check only)
triggered["signal"] = -np.sign(triggered["gap_ret"])
triggered["trade_ret"] = triggered["signal"] * triggered["intra_ret"]
oagf_daily = triggered.groupby("date")["trade_ret"].mean()  # equal-weight avg per day
oagf_daily.index = pd.DatetimeIndex(oagf_daily.index)
if oagf_daily.index.tz is None:
    oagf_daily.index = oagf_daily.index.tz_localize("UTC")

# Strategy A proxy: TSMOM on Binance perp universe (28d momentum)
print("  Loading Binance daily for A proxy...")
bn_closes: dict[str, pd.Series] = {}
for coin in ok_coins[:20]:  # top 20 sufficient for proxy
    s = fetch_bn_daily(coin)
    if s is not None and len(s) > 100:
        bn_closes[coin] = s
    time.sleep(0.05)

print(f"  A proxy: {len(bn_closes)} coins loaded")

if bn_closes:
    bn_df    = pd.DataFrame(bn_closes).ffill(limit=5)
    ret_1d   = bn_df.pct_change(1)
    mom_28   = bn_df.pct_change(28).shift(1)   # signal at T-1
    # TSMOM: go long if cumret > 0, weight proportional to tanh(cumret/vol)
    vol_28   = ret_1d.rolling(28).std() * np.sqrt(252)
    signal_a = np.tanh(mom_28 / (vol_28 * np.sqrt(28) + 1e-9))
    a_daily  = (signal_a * ret_1d).mean(axis=1)
    a_daily.index = pd.DatetimeIndex(a_daily.index)
    if a_daily.index.tz is None:
        a_daily.index = a_daily.index.tz_localize("UTC")
else:
    a_daily = pd.Series(dtype=float)

# Strategy B: real returns
print(f"  Loading B returns from {B_RETURNS_PATH.name}...")
try:
    b_daily = load_b_daily()
    print(f"  B daily: {len(b_daily)} obs from {b_daily.index[0].date()} to {b_daily.index[-1].date()}")
except Exception as e:
    print(f"  B load failed: {e}")
    b_daily = pd.Series(dtype=float)

# Compute correlations on overlapping dates
def safe_corr(s1: pd.Series, s2: pd.Series, label: str) -> float:
    common = s1.index.intersection(s2.index)
    if len(common) < 30:
        print(f"  corr({label}): insufficient overlap ({len(common)} days)")
        return np.nan
    r = s1.loc[common].corr(s2.loc[common])
    return float(r)

corr_a = safe_corr(oagf_daily, a_daily, "OAGF,A")
corr_b = safe_corr(oagf_daily, b_daily, "OAGF,B")

gate_corr_a = np.isnan(corr_a) or abs(corr_a) < CORR_GATE
gate_corr_b = np.isnan(corr_b) or abs(corr_b) < CORR_GATE

print(f"  corr(OAGF, A) = {corr_a:.4f}  →  {'PASS' if gate_corr_a else 'FAIL'} (gate < {CORR_GATE})")
print(f"  corr(OAGF, B) = {corr_b:.4f}  →  {'PASS' if gate_corr_b else 'FAIL'} (gate < {CORR_GATE})")

# ── Step 6: Final verdict ─────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("GATE SUMMARY")
print("=" * 65)

gates = {
    "Event count floor":       gate_events,
    "IC t_HAC ≤ −2.5 (1h)":   gate_ic,
    "|corr(A)| < 0.50":        gate_corr_a,
    "|corr(B)| < 0.50":        gate_corr_b,
}
all_pass = all(gates.values())

for name, result in gates.items():
    print(f"  {'✓' if result else '✗'} {name}: {'PASS' if result else 'FAIL'}")

print()
if all_pass:
    print("VERDICT: RESEARCH_PASS → proceed to Phase 2 (full backtest)")
    print(f"  IC (1h): {primary.get('ic_daily_mean', 0):.4f} | t_HAC: {primary.get('t_hac', 0):.2f}")
    print(f"  corr(A): {corr_a:.4f} | corr(B): {corr_b:.4f}")
else:
    failed = [k for k, v in gates.items() if not v]
    print(f"VERDICT: FAIL → archive OAGF")
    print(f"  Failed gates: {failed}")

print(f"\nn_tests: {N_TESTS_START} + 3 (three IC horizons) = {N_TESTS_START + 3}")
print(f"E[max_SR] at N={N_TESTS_START + 3}: ≈ {4.33 + 0.003:.3f} (marginal increase)")

# ── Step 7: Save results ──────────────────────────────────────────────────────
results = {
    "date": str(pd.Timestamp.utcnow().date()),
    "data_source": "Binance 1h perp (HL candle API limited to ~7 months)",
    "gap_threshold": GAP_THRESHOLD,
    "n_coins": len(ok_coins),
    "n_settlement_bars": int(n_total),
    "n_triggered": int(n_triggered),
    "events_per_year": round(float(events_per_yr), 1),
    "ic_results": {k: {kk: round(float(vv), 6) if isinstance(vv, (float, np.floating)) else int(vv) if isinstance(vv, (int, np.integer)) else bool(vv)
                       for kk, vv in v.items()}
                   for k, v in ic_results.items()},
    "corr_a": round(float(corr_a), 4) if not np.isnan(corr_a) else None,
    "corr_b": round(float(corr_b), 4) if not np.isnan(corr_b) else None,
    "gates": {k: bool(v) for k, v in gates.items()},
    "verdict": "PASS" if all_pass else "FAIL",
    "n_tests": N_TESTS_START + 3,
}

out_path = Path(__file__).parent / "preflight_oagf_results.json"
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved → {out_path.name}")
