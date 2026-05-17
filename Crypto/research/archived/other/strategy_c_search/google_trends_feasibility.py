"""
Test D — Google Trends 'bitcoin' attention signal (Liu & Tsyvinski 2021).

Hypothesis: weekly search volume for "bitcoin" reflects retail attention,
which predicts BTC returns (continuation or reversal mechanism).
Documented in Liu & Tsyvinski (2021, Journal of Finance).

Data sources (in priority order):
  1. pytrends — Google Trends scraper (pip install pytrends, free)
  2. Wikipedia pageviews API — Bitcoin article daily views (free, reliable)

Signal: z-score of weekly attention vs 4-week rolling mean (no look-ahead).

PASS: |IC t-stat| > 1.5 AND |corr(attention, TSMOM_28d)| < 0.30
SCALER: 1.0 ≤ |t-stat| < 1.5 AND |corr| < 0.30 (worth testing as position scaler)
"""

from __future__ import annotations

import time
import numpy as np
import pandas as pd
import requests
import warnings
warnings.filterwarnings("ignore")

START     = "2020-01-01"
END       = "2026-05-14"
SUB_START = "2023-01-01"
ROLL_WIN  = 26
IC_PASS   = 1.5
CORR_MAX  = 0.30


# ── Data: pytrends ────────────────────────────────────────────────────────────

def _ensure_pytrends() -> bool:
    """Install pytrends if not present. Returns True if available."""
    try:
        import pytrends  # noqa: F401
        return True
    except ImportError:
        print("  [pytrends] not installed — trying pip install ...")
        import subprocess
        r = subprocess.run(
            ["/usr/bin/python3", "-m", "pip", "install", "pytrends", "--quiet"],
            capture_output=True,
        )
        if r.returncode == 0:
            print("  [pytrends] installed")
            return True
        print(f"  [pytrends] install failed: {r.stderr.decode()[:120]}")
        return False


def fetch_pytrends(keyword: str = "bitcoin") -> pd.Series | None:
    """
    Pull weekly Google Trends for `keyword`, last 5 years.
    Returns Series with weekly DatetimeIndex (Sunday) or None on failure.
    """
    if not _ensure_pytrends():
        return None
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="en-US", tz=360)
        pt.build_payload([keyword], timeframe="today 5-y", geo="", gprop="")
        time.sleep(1.5)   # avoid rate-limit
        df = pt.interest_over_time()
        if df.empty:
            print("  [pytrends] empty result")
            return None
        if "isPartial" in df.columns:
            df = df.drop(columns=["isPartial"])
        s = df[keyword].astype(float)
        s.index = pd.to_datetime(s.index)
        print(f"  [pytrends] {len(s)} weekly obs: "
              f"{s.index[0].date()} → {s.index[-1].date()}")
        return s
    except Exception as e:
        print(f"  [pytrends] failed: {e}")
        return None


# ── Data: Wikipedia pageviews ─────────────────────────────────────────────────

_WIKI_BASE = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
    "en.wikipedia/all-access/user/Bitcoin/daily/{start}/{end}"
)

def _wiki_chunk(start: str, end: str) -> list[tuple[pd.Timestamp, int]]:
    """Fetch one chunk of Wikipedia pageviews. Returns list of (date, views)."""
    url = _WIKI_BASE.format(start=start, end=end)
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "algo-research/1.0"})
        if resp.status_code != 200:
            return []
        items = resp.json().get("items", [])
        return [
            (pd.Timestamp(str(it["timestamp"])[:8], format="%Y%m%d"),
             int(it["views"]))
            for it in items
        ]
    except Exception as e:
        print(f"  [wiki] chunk {start}-{end}: {e}")
        return []


def fetch_wikipedia() -> pd.Series | None:
    """
    Wikipedia daily BTC pageviews, aggregated to weekly.
    Fetched in 1-year chunks (API limit safety).
    """
    print("  [wiki] Fetching Bitcoin Wikipedia pageviews ...")
    chunks = [
        ("20200101", "20201231"),
        ("20210101", "20211231"),
        ("20220101", "20221231"),
        ("20230101", "20231231"),
        ("20240101", "20241231"),
        ("20250101", "20260514"),
    ]
    records: list = []
    for s, e in chunks:
        records.extend(_wiki_chunk(s, e))

    if not records:
        print("  [wiki] no data returned")
        return None

    daily = pd.Series(dict(records)).sort_index()
    daily = daily[~daily.index.duplicated(keep="first")]
    weekly = daily.resample("W-FRI").sum().astype(float)
    print(f"  [wiki] {len(weekly)} weekly obs: "
          f"{weekly.index[0].date()} → {weekly.index[-1].date()}")
    return weekly


# ── Signal construction ───────────────────────────────────────────────────────

def build_zscore(raw: pd.Series) -> pd.Series:
    """
    Attention z-score (no look-ahead).
    zscore[T] = (raw[T-1] − mean4[T-1]) / (std4[T-1] + ε)
    Uses shift(1) so value at T is based entirely on data ≤ T-1.
    """
    shifted   = raw.shift(1)
    roll_mean = shifted.rolling(4).mean()
    roll_std  = shifted.rolling(4).std()
    z = (shifted - roll_mean) / (roll_std + 1e-8)
    z.name = "attention_zscore"
    return z


# ── IC metrics ────────────────────────────────────────────────────────────────

def _ic(sig: pd.Series, out: pd.Series) -> dict:
    df = pd.DataFrame({"s": sig, "o": out}).dropna()
    n  = len(df)
    if n < 10:
        return dict(ic=np.nan, t_stat=np.nan, icir=np.nan, n=n)
    ic     = float(df["s"].corr(df["o"]))
    t_stat = ic * np.sqrt(max(n - 2, 0)) / np.sqrt(max(1 - ic**2, 1e-12))
    roll   = df["s"].rolling(ROLL_WIN).corr(df["o"])
    icir   = float(roll.mean() / (roll.std() + 1e-12))
    return dict(ic=ic, t_stat=t_stat, icir=icir, n=n)


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> dict:
    print("=" * 60)
    print("TEST D — GOOGLE TRENDS ATTENTION SIGNAL")
    print("=" * 60)

    # 1. Attention data
    print("\n  [1] Trying pytrends ...")
    raw = fetch_pytrends()
    if raw is None:
        print("  [2] Fallback: Wikipedia pageviews ...")
        raw = fetch_wikipedia()

    if raw is None or len(raw) < 20:
        print("\n  SKIP — all attention data sources failed or insufficient")
        return {"verdict": "SKIP", "ic_full": np.nan, "t_stat": np.nan,
                "icir": np.nan, "ic_sub": np.nan, "tsmom_corr": np.nan,
                "direction": "unknown", "data_source": "none"}

    # data_src tracked by which fetch succeeded (raw assigned above)
    data_src = "pytrends" if raw is not None and fetch_wikipedia is not None and len(raw) > 0 else "wikipedia"
    # Simpler: check if pytrends name in index or just tag by print output
    # Actually track it by checking whether Wikipedia fetch was needed
    # (fetch_pytrends prints '[pytrends] N weekly obs' if successful)
    # We re-check: if raw came from pytrends it was set before the None check
    # Use a sentinel: pytrends returns Weekly-Sun index, wikipedia returns W-FRI
    _sample_dow = raw.index[:3].dayofweek.tolist() if len(raw) >= 3 else []
    data_src = "pytrends" if 6 in _sample_dow or 0 in _sample_dow else "wikipedia"

    # Align to Friday close
    attention_w = raw.resample("W-FRI").last()

    # 2. Z-score signal (no look-ahead)
    zscore = build_zscore(attention_w)

    # 3. BTC weekly outcome
    import yfinance as yf
    _raw = yf.download("BTC-USD", start=START, end=END,
                       auto_adjust=True, progress=False)
    if isinstance(_raw.columns, pd.MultiIndex):
        btc_px = _raw["Close"].squeeze()
    else:
        btc_px = _raw["Close"].squeeze()
    btc_px.index = pd.to_datetime(btc_px.index)
    btc_log   = np.log(btc_px / btc_px.shift(1))
    btc_w     = btc_log.resample("W-FRI").sum()
    outcome   = btc_w.shift(-1)

    # 4. TSMOM 28d proxy
    tsmom_w = btc_log.rolling(28).sum().shift(1).resample("W-FRI").last()

    # 5. IC tests
    m_full = _ic(zscore, outcome)

    z_sub   = zscore[zscore.index >= pd.Timestamp(SUB_START)]
    o_sub   = outcome[outcome.index >= pd.Timestamp(SUB_START)]
    m_sub   = _ic(z_sub, o_sub)

    df_c       = pd.DataFrame({"z": zscore, "t": tsmom_w}).dropna()
    tsmom_corr = float(df_c["z"].corr(df_c["t"]))

    # Direction: positive IC = continuation (high attention → BTC up)
    direction = "continuation" if (m_full["ic"] or 0) > 0 else "reversal"

    print(f"\n  Data source    : {data_src}")
    print(f"  Weekly obs     : {m_full['n']} (full) / {m_sub['n']} (2023+)")
    print(f"  IC (full)      : {m_full['ic']:+.4f}")
    print(f"  t-stat         : {m_full['t_stat']:+.3f}")
    print(f"  ICIR (26w)     : {m_full['icir']:+.3f}")
    print(f"  IC (2023+)     : {m_sub['ic']:+.4f}")
    print(f"  Corr TSMOM_28d : {tsmom_corr:+.3f}")
    print(f"  Direction      : {direction}  "
          f"({'high attention → BTC↑' if direction == 'continuation' else 'high attention → BTC↓'})")

    pass_ic   = not np.isnan(m_full["t_stat"]) and abs(m_full["t_stat"]) > IC_PASS
    pass_corr = abs(tsmom_corr) < CORR_MAX

    if pass_ic and pass_corr:
        verdict = "PASS"
    elif not np.isnan(m_full["t_stat"]) and abs(m_full["t_stat"]) > 1.0 and pass_corr:
        verdict = "SCALER"
    else:
        verdict = "FAIL"

    print(f"\n  Gate 1 — |t-stat| > {IC_PASS}:  "
          f"{'✓' if pass_ic else '✗'}  ({abs(m_full['t_stat'] or 0):.3f})")
    print(f"  Gate 2 — |corr| < {CORR_MAX}:   "
          f"{'✓' if pass_corr else '✗'}  ({abs(tsmom_corr):.3f})")
    print(f"\n  VERDICT (Test D): {verdict}")

    return {
        "ic_full":    m_full["ic"],
        "t_stat":     m_full["t_stat"],
        "icir":       m_full["icir"],
        "ic_sub":     m_sub["ic"],
        "tsmom_corr": tsmom_corr,
        "verdict":    verdict,
        "direction":  direction,
        "data_source": data_src,
    }


if __name__ == "__main__":
    main()
