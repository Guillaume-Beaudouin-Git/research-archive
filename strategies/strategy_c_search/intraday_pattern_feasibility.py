"""
Test B — 4h Hyperliquid Intraday Pattern Feasibility
Weekly body score (US-session 4h candles) → BTC weekly return IC test.

Hypothesis (Wen, Bouri et al. 2022):
  US-session intraday candle structure aggregated weekly captures
  institutional buying/selling pressure not reflected in weekly OHLC.

Data sources (in priority order):
  1. Hyperliquid API — 4h BTC candles, full history
  2. yfinance hourly BTC-USD — last 730 days
  3. yfinance daily BTC-USD  — full history (reduced resolution fallback)

Signals:
  body_score  = mean(body_ratio) over US-session candles last 5 days
                body_ratio = (close-open) / (high-low+ε) ∈ [-1, +1]
  range_asym  = mean((high-open)/(hl) - (open-low)/(hl)) over same candles
                measures whether open is near the low (bullish) or high (bearish)

PASS criteria (applied to best signal by |t-stat|):
  1. IC t-stat > 1.5
  2. |corr(signal, TSMOM_28d)| < 0.30
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import requests
import warnings
warnings.filterwarnings("ignore")

START         = "2022-01-01"
END           = "2026-05-14"
SUB_START     = "2023-01-01"
ROLL_WIN      = 26
IC_TSTAT_PASS = 1.5
CORR_MAX      = 0.30

HL_URL        = "https://api.hyperliquid.xyz/info"
CHUNK_DAYS    = 90

# US session 4h candle start hours (UTC): nearest to 14:00-22:00 US open
# HL 4h boundaries: 0, 4, 8, 12, 16, 20 UTC
US_HOURS_4H   = frozenset({12, 16, 20})
US_HOURS_1H   = frozenset(range(12, 23))


# ── Data — Hyperliquid 4h ─────────────────────────────────────────────────────

def _hl_chunk(start_ms: int, end_ms: int) -> list:
    payload = {
        "type": "candleSnapshot",
        "req": {"coin": "BTC", "interval": "4h",
                "startTime": start_ms, "endTime": end_ms},
    }
    for attempt in range(2):
        try:
            resp = requests.post(HL_URL, json=payload, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
        except Exception as e:
            if attempt == 1:
                print(f"    chunk {start_ms}–{end_ms}: {e}")
    return []


def fetch_hl_4h(start: str, end: str) -> pd.DataFrame | None:
    """Fetch BTC 4h candles from Hyperliquid in CHUNK_DAYS-day pages."""
    print(f"  [HL 4h] Fetching BTC {start} → {end} ...")
    start_ms = int(pd.Timestamp(start).timestamp() * 1000)
    end_ms   = int(pd.Timestamp(end).timestamp()   * 1000)
    chunk_ms = CHUNK_DAYS * 24 * 3600 * 1000

    all_records: list = []
    cur = start_ms
    while cur < end_ms:
        nxt = min(cur + chunk_ms, end_ms)
        all_records.extend(_hl_chunk(cur, nxt))
        cur = nxt

    if not all_records:
        print("  [HL 4h] empty response")
        return None

    try:
        df = pd.DataFrame(all_records)
        # HL candle fields: t (open time ms), o, h, l, c (strings), v, n
        df["dt"] = pd.to_datetime(df["t"].astype(np.int64), unit="ms", utc=True)
        df = df.set_index("dt").sort_index()
        df = df[~df.index.duplicated(keep="first")]
        for col, name in [("o","open"),("h","high"),("l","low"),("c","close")]:
            df[name] = pd.to_numeric(df[col], errors="coerce")
        df = df[["open","high","low","close"]].dropna()
        print(f"  [HL 4h] {len(df):,} candles: "
              f"{df.index[0].date()} → {df.index[-1].date()}")
        return df
    except Exception as e:
        print(f"  [HL 4h] parse error: {e}")
        return None


# ── Data — yfinance hourly fallback ──────────────────────────────────────────

def fetch_yf_hourly() -> pd.DataFrame | None:
    """yfinance hourly BTC-USD (max 730 days from today)."""
    import yfinance as yf
    end_dt   = pd.Timestamp(END)
    start_dt = end_dt - pd.Timedelta(days=729)
    print(f"  [YF 1h] {start_dt.date()} → {end_dt.date()} ...")
    try:
        raw = yf.download("BTC-USD",
                          start=start_dt.strftime("%Y-%m-%d"),
                          end=end_dt.strftime("%Y-%m-%d"),
                          interval="1h", auto_adjust=True, progress=False)
        if raw.empty:
            print("  [YF 1h] empty")
            return None
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.droplevel(1)
        raw.index = pd.to_datetime(raw.index, utc=True)
        raw = raw.rename(columns={"Open":"open","High":"high",
                                   "Low":"low","Close":"close"})
        raw = raw[["open","high","low","close"]].dropna()
        print(f"  [YF 1h] {len(raw):,} candles: "
              f"{raw.index[0].date()} → {raw.index[-1].date()}")
        return raw
    except Exception as e:
        print(f"  [YF 1h] {e}")
        return None


def fetch_yf_daily() -> pd.DataFrame | None:
    """Last-resort: yfinance daily BTC-USD (reduced resolution)."""
    import yfinance as yf
    print(f"  [YF daily] {START} → {END} ...")
    try:
        raw = yf.download("BTC-USD", start=START, end=END,
                           auto_adjust=True, progress=False)
        if raw.empty:
            return None
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.droplevel(1)
        raw.index = pd.to_datetime(raw.index, utc=True)
        raw = raw.rename(columns={"Open":"open","High":"high",
                                   "Low":"low","Close":"close"})
        raw = raw[["open","high","low","close"]].dropna()
        print(f"  [YF daily] {len(raw):,} bars: "
              f"{raw.index[0].date()} → {raw.index[-1].date()}")
        return raw
    except Exception as e:
        print(f"  [YF daily] {e}")
        return None


# ── Feature engineering ───────────────────────────────────────────────────────

def _candle_freq_hours(idx: pd.DatetimeIndex) -> float:
    """Estimate median candle duration in hours."""
    diffs = idx.to_series().diff().dt.total_seconds().dropna()
    return float(diffs.median()) / 3600.0


def build_weekly_signals(candles: pd.DataFrame,
                         is_daily: bool = False) -> pd.DataFrame:
    """
    Compute per-candle features, filter to US session, aggregate weekly.

    body_ratio ∈ [-1, +1]: +1 = full bull candle, -1 = full bear candle
    range_asym ∈ [-1, +1]: +1 = open near low (all upside), -1 = open near high (all downside)
    """
    hl = candles["high"] - candles["low"] + 1e-8
    c  = candles.copy()
    c["body_ratio"] = (c["close"] - c["open"]) / hl
    c["range_asym"] = ((c["high"] - c["open"]) / hl
                       - (c["open"] - c["low"]) / hl)

    if not is_daily:
        freq = _candle_freq_hours(c.index)
        if freq >= 3.0:
            us_mask = c.index.hour.isin(US_HOURS_4H)
            session_label = f"US-session 4h (hours {sorted(US_HOURS_4H)})"
        else:
            us_mask = c.index.hour.isin(US_HOURS_1H)
            session_label = f"US-session 1h (hours 12-22)"

        n_us  = int(us_mask.sum())
        n_tot = len(c)
        print(f"  Candle freq: ~{freq:.1f}h | {session_label}")
        print(f"  US session: {n_us:,} / {n_tot:,} candles ({n_us/n_tot:.1%})")

        if n_us < 200:
            print("  [WARNING] too few US-session candles — using all candles")
        else:
            c = c[us_mask]

    weekly = pd.DataFrame({
        "body_score": c["body_ratio"].resample("W-FRI").mean(),
        "range_asym": c["range_asym"].resample("W-FRI").mean(),
    })
    weekly = weekly.dropna(how="all")
    # Strip timezone so index aligns with tz-naive yfinance daily data
    if weekly.index.tz is not None:
        weekly.index = weekly.index.tz_localize(None)
    return weekly


# ── IC metrics ────────────────────────────────────────────────────────────────

def ic_metrics(sig: pd.Series, out: pd.Series) -> dict:
    df = pd.DataFrame({"s": sig, "o": out}).dropna()
    n  = len(df)
    if n < 10:
        return dict(ic=np.nan, t_stat=np.nan, icir=np.nan, n=n)
    ic     = float(df["s"].corr(df["o"]))
    denom  = np.sqrt(max(1.0 - ic**2, 1e-12))
    t_stat = ic * np.sqrt(max(n - 2, 0)) / denom
    roll   = df["s"].rolling(ROLL_WIN).corr(df["o"])
    icir   = float(roll.mean() / (roll.std() + 1e-12))
    return dict(ic=ic, t_stat=t_stat, icir=icir, n=n)


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> dict:
    print("=" * 60)
    print("TEST B — 4h INTRADAY PATTERN (US SESSION)")
    print("=" * 60)

    # 1. Fetch intraday candles
    candles  = fetch_hl_4h(START, END)
    is_daily = False

    if candles is None or len(candles) < 500:
        n_got = 0 if candles is None else len(candles)
        print(f"\n  [HL] got {n_got} candles — trying yfinance hourly ...")
        candles = fetch_yf_hourly()

    if candles is None or len(candles) < 500:
        n_got = 0 if candles is None else len(candles)
        print(f"\n  [1h] got {n_got} candles — falling back to daily ...")
        candles  = fetch_yf_daily()
        is_daily = True

    if candles is None or len(candles) < 50:
        print("\n  SKIP — all data sources failed or insufficient")
        return {"verdict": "SKIP", "ic_full": np.nan, "t_stat": np.nan,
                "icir": np.nan, "ic_sub": np.nan, "tsmom_corr": np.nan,
                "best_signal": "N/A", "data_source": "none"}

    data_source = ("HL 4h" if not is_daily and len(candles) > 500
                   else "YF 1h" if not is_daily
                   else "YF daily")

    # 2. Build weekly signals from intraday candles
    features = build_weekly_signals(candles, is_daily=is_daily)
    print(f"  Weekly signal rows: {len(features)}  "
          f"({features.index[0].date()} → {features.index[-1].date()})")

    # 3. BTC daily → weekly outcome
    import yfinance as yf
    _btc_raw = yf.download("BTC-USD", start=START, end=END,
                             auto_adjust=True, progress=False)
    if isinstance(_btc_raw.columns, pd.MultiIndex):
        btc_px = _btc_raw["Close"].squeeze()
    else:
        btc_px = _btc_raw["Close"].squeeze()
    btc_px.index = pd.to_datetime(btc_px.index)
    btc_log = np.log(btc_px / btc_px.shift(1))
    btc_w   = btc_log.resample("W-FRI").sum()
    outcome = btc_w.shift(-1)   # next week's BTC return

    # 4. TSMOM 28d proxy
    tsmom_proxy = btc_log.rolling(28).sum().shift(1)
    tsmom_w     = tsmom_proxy.resample("W-FRI").last()

    # 5. IC tests for both signals; pick best by |t-stat|
    sig_results: dict[str, dict] = {}

    print()
    print("─" * 55)
    for col in ["body_score", "range_asym"]:
        sig      = features[col]
        m_full   = ic_metrics(sig, outcome)
        sig_sub  = sig[sig.index >= pd.Timestamp(SUB_START)]
        out_sub  = outcome[outcome.index >= pd.Timestamp(SUB_START)]
        m_sub    = ic_metrics(sig_sub, out_sub)

        corr_df  = pd.DataFrame({"s": sig, "t": tsmom_w}).dropna()
        corr     = float(corr_df["s"].corr(corr_df["t"]))

        pass_ic   = not np.isnan(m_full["t_stat"]) and m_full["t_stat"] > IC_TSTAT_PASS
        pass_corr = abs(corr) < CORR_MAX
        verdict   = "PASS" if (pass_ic and pass_corr) else "FAIL"

        print(f"  Signal: {col}")
        print(f"  IC (full): {m_full['ic']:+.4f}  |  t-stat: {m_full['t_stat']:+.3f}"
              f"  |  ICIR: {m_full['icir']:+.3f}  (N={m_full['n']})")
        print(f"  IC (2023+):{m_sub['ic']:+.4f}  (N={m_sub['n']})")
        print(f"  Corr TSMOM: {corr:+.3f}")
        print(f"  Gate 1 — t-stat > {IC_TSTAT_PASS}: {'✓' if pass_ic else '✗'}  "
              f"Gate 2 — |corr| < {CORR_MAX}: {'✓' if pass_corr else '✗'}")
        print(f"  Verdict: {verdict}")
        print("─" * 55)

        sig_results[col] = dict(
            ic_full=m_full["ic"], t_stat=m_full["t_stat"],
            icir=m_full["icir"], ic_sub=m_sub["ic"],
            tsmom_corr=corr, verdict=verdict,
        )

    # 6. Select best signal
    best_col = max(sig_results,
                   key=lambda c: abs(sig_results[c].get("t_stat") or 0))
    best = dict(sig_results[best_col])
    best["best_signal"] = best_col
    best["data_source"] = data_source

    print(f"\n  Best signal: {best_col} (|t-stat| = {abs(best['t_stat']):.3f})")
    print(f"  VERDICT (Test B): {best['verdict']}")

    return best


if __name__ == "__main__":
    main()
