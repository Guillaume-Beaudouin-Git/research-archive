"""
Combined Macro + Google Trends Scaler Backtest
===============================================

Tests macro lag-1 composite and Google Trends attention z-score as combined
position multipliers on TSMOM v3 C1 baseline (14-asset crypto universe).

Both signals passed IC screening independently:
  Macro lag 1w:  IC +0.089, t-stat +1.606, corr_TSMOM +0.17 → GO
  Google Trends: IC +0.088, t-stat +1.407, corr_TSMOM +0.09 → SCALER

Scaler logic (no look-ahead):
  A. Macro mult  = 1.00 + 0.30 × tanh(macro_lag1 / rolling_std_52w)
     Range: [0.70, 1.30] — never zeroes out TSMOM
  B. Trends mult = 1.00 if zscore > 0.5 else 0.75 (binary)
  Combined: macro_mult × trends_mult, clipped to [0.50, 1.50]

Walk-forward: 4 expanding windows (same as tsmom_v3/backtest.py).
DSR: n=8 tests (C0, C1, C4, C5, C6, macro lag, trends, combined).

Usage:
    /usr/bin/python3 strategies/strategy_c_search/combined_scaler_backtest.py
"""

from __future__ import annotations

import os
import sys
import time
sys.path.insert(0, "<HOME>/Desktop/Algo_claude")

import warnings
import numpy as np
import pandas as pd
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

import yfinance as yf

from strategies.tsmom_v3.signal import continuous_signal, build_positions
from strategies.tsmom_v2_propfirm.config import UNIVERSE, MIN_LISTING_DATES
from dsr import deflated_sharpe_ratio

# ── Constants ──────────────────────────────────────────────────────────────────
DATA_START   = "2020-01-01"
DATA_END     = "2026-05-14"
OOS_START    = "2023-01-01"
VOL_TARGET   = 0.18
COST_PER_LEG = 0.00085   # 0.085% one-way = 0.17% RT
TRADING_DAYS = 365
N_DSR_TESTS  = 8         # C0,C1,C4,C5,C6,macro_lag,trends,combined

WALK_FOLDS = [
    {"label": "W1-2023",   "test_start": "2023-01-01", "test_end": "2023-12-31"},
    {"label": "W2-2024",   "test_start": "2024-01-01", "test_end": "2024-12-31"},
    {"label": "W3-2024H2", "test_start": "2024-07-01", "test_end": "2024-12-31"},
    {"label": "W4-2025",   "test_start": "2025-01-01", "test_end": "2025-12-31"},
]

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ══════════════════════════════════════════════════════════════════════════════
# DATA DOWNLOAD
# ══════════════════════════════════════════════════════════════════════════════

def download_universe() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Download 14-asset universe. Returns (close, log_ret)."""
    print(f"Downloading {len(UNIVERSE)}-asset universe ({DATA_START}→{DATA_END}) ...")
    raw = yf.download(UNIVERSE, start=DATA_START, end=DATA_END,
                      auto_adjust=True, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw = raw["Close"]
    raw.index = pd.to_datetime(raw.index)
    for asset, min_date in MIN_LISTING_DATES.items():
        if asset in raw.columns:
            raw.loc[raw.index < pd.Timestamp(min_date), asset] = np.nan
    raw = raw.ffill()
    available = [c for c in UNIVERSE if c in raw.columns
                 and raw[c].dropna().shape[0] > 100]
    raw = raw[available]
    log_ret = np.log(raw / raw.shift(1)).clip(-1.0, 1.0)
    print(f"  {len(available)} assets  "
          f"{raw.index[0].date()} → {raw.index[-1].date()}")
    return raw, log_ret


def download_macro() -> pd.DataFrame:
    """Download SPY, DX-Y.NYB, ^VIX for macro scaler."""
    tickers = ["SPY", "DX-Y.NYB", "^VIX"]
    raw = yf.download(tickers, start=DATA_START, end=DATA_END,
                      auto_adjust=True, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw = raw["Close"]
    raw.index = pd.to_datetime(raw.index)
    return raw


# ── Wikipedia pageviews ────────────────────────────────────────────────────────

_WIKI_BASE = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
    "en.wikipedia/all-access/user/Bitcoin/daily/{start}/{end}"
)

def _wiki_chunk(start: str, end: str) -> list:
    url = _WIKI_BASE.format(start=start, end=end)
    try:
        resp = requests.get(url, timeout=20,
                            headers={"User-Agent": "algo-research/1.0"})
        if resp.status_code != 200:
            return []
        return [
            (pd.Timestamp(str(it["timestamp"])[:8], format="%Y%m%d"),
             int(it["views"]))
            for it in resp.json().get("items", [])
        ]
    except Exception as e:
        print(f"    [wiki] chunk {start}–{end}: {e}")
        return []


def fetch_wikipedia() -> pd.Series | None:
    """Bitcoin Wikipedia daily pageviews aggregated to weekly (W-FRI)."""
    print("  [wiki] Fetching Bitcoin Wikipedia pageviews ...")
    chunks = [
        ("20200101", "20201231"), ("20210101", "20211231"),
        ("20220101", "20221231"), ("20230101", "20231231"),
        ("20240101", "20241231"), ("20250101", "20260514"),
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


def fetch_pytrends(keyword: str = "bitcoin") -> pd.Series | None:
    """Google Trends weekly data via pytrends (last 5 years)."""
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return None
    try:
        pt = TrendReq(hl="en-US", tz=360)
        pt.build_payload([keyword], timeframe="today 5-y", geo="", gprop="")
        time.sleep(1.5)
        df = pt.interest_over_time()
        if df.empty:
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


# ══════════════════════════════════════════════════════════════════════════════
# SCALER CONSTRUCTION
# ══════════════════════════════════════════════════════════════════════════════

def build_macro_mult(macro_df: pd.DataFrame,
                     daily_index: pd.DatetimeIndex) -> pd.Series:
    """
    Macro scaler — lag 1 week, tanh normalized.

    Daily (shift(1) no look-ahead):
        composite = spy_mom_1m - dxy_mom_1m - 0.5 * vix_chg_6d

    Weekly: resample W-FRI + additional shift(1) = confirmed lag 1 week.
    Normalize via rolling 52-week std.
    macro_mult = 1.00 + 0.30 * tanh(score / std)  → range [0.70, 1.30]

    Returns daily series (forward-filled; default 1.0 during warm-up).
    """
    # Identify columns flexibly
    spy_col = "SPY" if "SPY" in macro_df.columns else None
    dxy_col = next((c for c in macro_df.columns
                    if "DX" in c.upper() or "NYB" in c.upper()), None)
    vix_col = next((c for c in macro_df.columns
                    if "VIX" in c.upper()), None)

    if not spy_col or not dxy_col or not vix_col:
        missing = [n for n, c in [("SPY", spy_col), ("DXY", dxy_col),
                                   ("VIX", vix_col)] if not c]
        print(f"  [macro] WARNING: missing {missing} — macro_mult = 1.0")
        return pd.Series(1.0, index=daily_index, name="macro_mult")

    spy = macro_df[spy_col]
    dxy = macro_df[dxy_col]
    vix = macro_df[vix_col]

    # Daily components (all shift(1) = no look-ahead)
    spy_mom = (spy / spy.shift(21) - 1).shift(1)
    dxy_mom = (dxy / dxy.shift(21) - 1).shift(1)
    vix_chg = (vix - vix.shift(6)).shift(1)

    # Simplified composite: best IC components at lag 1
    composite = spy_mom - dxy_mom - 0.5 * vix_chg

    # Weekly W-FRI + 1-week lag (confirmed IC t-stat +1.606)
    comp_w    = composite.resample("W-FRI").last()
    comp_lag1 = comp_w.shift(1)

    # Normalize: rolling 52-week std
    roll_std  = comp_lag1.rolling(52).std()
    norm      = np.tanh(comp_lag1 / (roll_std + 1e-8))

    # Multiplier: neutral=1.0, strong+→1.30, strong-→0.70
    macro_mult_w = 1.00 + 0.30 * norm
    macro_mult_w.name = "macro_mult"

    # Forward-fill to daily (default 1.0 = no scaling during warm-up)
    mult_d = macro_mult_w.reindex(daily_index).ffill().fillna(1.0)
    print(f"  [macro] mult range: [{mult_d.min():.3f}, {mult_d.max():.3f}]  "
          f"mean={mult_d.mean():.4f}")
    return mult_d


def build_trends_mult(daily_index: pd.DatetimeIndex) -> pd.Series:
    """
    Attention scaler — binary: 1.00 if zscore > 0.5 else 0.75.
    Z-score: (raw[T-1] - mean_4w[T-1]) / std_4w[T-1]  (no look-ahead).
    Returns daily series (default 1.0 where no data / during warm-up).
    """
    print("\n  [trends] Fetching attention data ...")
    raw = fetch_pytrends()
    if raw is None:
        print("  [trends] pytrends failed — trying Wikipedia ...")
        raw = fetch_wikipedia()

    if raw is None or len(raw) < 20:
        print("  [trends] all sources failed — trends_mult = 1.0")
        return pd.Series(1.0, index=daily_index, name="trends_mult")

    # Align to W-FRI
    attention_w = raw.resample("W-FRI").last()

    # Z-score with no look-ahead (same formula as feasibility test)
    shifted   = attention_w.shift(1)
    roll_mean = shifted.rolling(4).mean()
    roll_std  = shifted.rolling(4).std()
    zscore    = (shifted - roll_mean) / (roll_std + 1e-8)

    # Binary multiplier: NaN → 1.0, zscore > 0.5 → 1.0, else → 0.75
    trends_mult_w = pd.Series(
        np.where(zscore.isna(), 1.0, np.where(zscore > 0.5, 1.0, 0.75)),
        index=zscore.index,
        name="trends_mult",
    )

    pct_high = float((trends_mult_w == 1.0).mean())
    print(f"  [trends] {len(trends_mult_w)} weekly obs  "
          f"| {pct_high:.1%} weeks at 1.0 (high attention / no-data)")

    # Forward-fill to daily (default 1.0 = no scaling where no data)
    mult_d = trends_mult_w.reindex(daily_index).ffill().fillna(1.0)
    return mult_d


def build_combined_mult(
    macro_mult_d:  pd.Series,
    trends_mult_d: pd.Series,
) -> pd.Series:
    """Combined scaler clipped to [0.50, 1.50]."""
    combined = (macro_mult_d * trends_mult_d).clip(0.50, 1.50)
    combined.name = "combined_mult"
    return combined


# ══════════════════════════════════════════════════════════════════════════════
# P&L ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def compute_pnl(close: pd.DataFrame, positions: pd.DataFrame) -> pd.Series:
    """Mean-convention P&L with costs on Monday rebalance only."""
    arith  = close.pct_change().fillna(0.0)
    held   = positions.shift(1).fillna(0.0)
    gross  = (held * arith).mean(axis=1)
    is_mon = pd.Series(close.index.dayofweek == 0,
                       index=close.index).astype(float)
    costs  = (positions.diff().abs()
              * COST_PER_LEG
              * is_mon.values.reshape(-1, 1)).mean(axis=1)
    return gross - costs


def scale_positions(positions: pd.DataFrame, mult: pd.Series) -> pd.DataFrame:
    """Apply scalar multiplier (same for all assets), aligned by index."""
    mult_aligned = mult.reindex(positions.index).ffill().fillna(1.0)
    return positions.mul(mult_aligned, axis=0)


# ══════════════════════════════════════════════════════════════════════════════
# METRICS
# ══════════════════════════════════════════════════════════════════════════════

def _sharpe(pnl: pd.Series) -> float:
    r = pnl.dropna()
    if len(r) < 5 or r.std() == 0:
        return np.nan
    return float(r.mean() / r.std() * np.sqrt(TRADING_DAYS))


def _full_metrics(pnl: pd.Series) -> dict:
    r = pnl.dropna()
    if len(r) < 5 or r.std() == 0:
        return {"sharpe": np.nan, "max_dd": np.nan, "win_rate": np.nan}
    sh  = r.mean() / r.std() * np.sqrt(TRADING_DAYS)
    eq  = (1 + r).cumprod()
    mdd = float((eq / eq.cummax() - 1).min())
    rw  = r.resample("W-MON").sum()
    wr  = float((rw > 0).mean())
    return {"sharpe": sh, "max_dd": mdd, "win_rate": wr}


# ══════════════════════════════════════════════════════════════════════════════
# FIGURE
# ══════════════════════════════════════════════════════════════════════════════

def _plot(
    pnl_c1:        pd.Series,
    pnl_combined:  pd.Series,
    combined_mult: pd.Series,
    fold_labels:   list[str],
    fold_c1:       list[float],
    fold_comb:     list[float],
    macro_mult:    pd.Series,
    trends_mult:   pd.Series,
) -> str:
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.suptitle("Combined Macro + Google Trends Scaler — OOS Results",
                 fontsize=13, y=0.98)

    # 1 — Equity curves
    ax = axes[0, 0]
    eq_c1   = (1 + pnl_c1.dropna()).cumprod()
    eq_comb = (1 + pnl_combined.dropna()).cumprod()
    ax.plot(eq_c1.index,   eq_c1.values,   label="C1 baseline",
            color="steelblue", lw=1.5)
    ax.plot(eq_comb.index, eq_comb.values, label="+ combined scaler",
            color="darkorange", lw=1.5, ls="--")
    ax.set_title("Equity Curve (OOS 2023–2026)", fontsize=10)
    ax.set_ylabel("Cumulative return")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 2 — Scaler value over time
    ax = axes[0, 1]
    ax.fill_between(
        combined_mult.index, combined_mult.values, 1.0,
        where=combined_mult.values > 1.0,
        alpha=0.35, color="green", label="scale > 1.0",
    )
    ax.fill_between(
        combined_mult.index, combined_mult.values, 1.0,
        where=combined_mult.values <= 1.0,
        alpha=0.35, color="red", label="scale < 1.0",
    )
    ax.plot(combined_mult.index, combined_mult.values,
            color="black", lw=0.7)
    ax.axhline(1.0, color="gray", lw=0.8, ls="--")
    ax.set_title("Combined Scaler Over Time (OOS)", fontsize=10)
    ax.set_ylabel("Multiplier")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # 3 — Walk-forward Sharpe bars
    ax = axes[1, 0]
    x = np.arange(len(fold_labels))
    w = 0.35
    ax.bar(x - w / 2, fold_c1,   w, label="C1 baseline",
           color="steelblue", alpha=0.85)
    ax.bar(x + w / 2, fold_comb, w, label="Combined scaler",
           color="darkorange", alpha=0.85)
    ax.axhline(0, color="black", lw=0.5)
    ax.set_title("Walk-Forward Sharpe (4 windows)", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(fold_labels, fontsize=8)
    ax.set_ylabel("Sharpe")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3, axis="y")

    # 4 — Combined scaler distribution
    ax = axes[1, 1]
    vals = combined_mult.dropna().values
    ax.hist(vals, bins=50, color="steelblue", alpha=0.7, edgecolor="white")
    ax.axvline(1.0, color="black", lw=1.2, ls="--", label="neutral")
    ax.axvline(vals.mean(), color="red", lw=1.2, ls=":",
               label=f"mean={vals.mean():.3f}")
    ax.set_title("Combined Scaler Distribution (OOS)", fontsize=10)
    ax.set_xlabel("Multiplier value")
    ax.set_ylabel("Days")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "combined_scaler_results.png")
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
# NEXT STEPS
# ══════════════════════════════════════════════════════════════════════════════

def _print_next_steps() -> None:
    print()
    print("  Next research direction: Glassnode free tier")
    print("  ┌──────────────────────────────────────────────────────────────┐")
    print("  │ MVRV Z-score, active addresses, exchange netflow            │")
    print("  │ Sign up: glassnode.com (free, no card required)             │")
    print("  │ Endpoint: api.glassnode.com/v1/metrics/market/mvrv_z_score  │")
    print("  │   ?a=BTC&i=24h&api_key=<free_tier_key>                      │")
    print("  │ MVRV < 1.0 = holders underwater = structural bear signal    │")
    print("  │ Economic mechanism stronger than VIX/Trends.                │")
    print("  │ Test IC before subscribing to paid tier.                    │")
    print("  └──────────────────────────────────────────────────────────────┘")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("=" * 70)
    print("COMBINED SCALER BACKTEST — MACRO LAG-1 + GOOGLE TRENDS")
    print("=" * 70)

    # ── 1. Universe data ──────────────────────────────────────────────────────
    close, log_ret = download_universe()

    # ── 2. Macro scaler ───────────────────────────────────────────────────────
    print("\nBuilding macro scaler ...")
    macro_df      = download_macro()
    macro_mult_d  = build_macro_mult(macro_df, close.index)

    # ── 3. Trends scaler ──────────────────────────────────────────────────────
    trends_mult_d = build_trends_mult(close.index)

    # ── 4. Combined scaler ────────────────────────────────────────────────────
    combined_mult_d = build_combined_mult(macro_mult_d, trends_mult_d)

    print(f"\n  Macro mult:   mean={macro_mult_d.mean():.4f}  "
          f"std={macro_mult_d.std():.4f}  "
          f"range=[{macro_mult_d.min():.3f}, {macro_mult_d.max():.3f}]")
    print(f"  Trends mult:  mean={trends_mult_d.mean():.4f}  "
          f"std={trends_mult_d.std():.4f}")
    print(f"  Combined:     mean={combined_mult_d.mean():.4f}  "
          f"std={combined_mult_d.std():.4f}  "
          f"range=[{combined_mult_d.min():.3f}, {combined_mult_d.max():.3f}]")

    # ── 5. TSMOM v3 C1 baseline positions ────────────────────────────────────
    print("\nBuilding C1 baseline positions ...")
    pos_c1 = build_positions(continuous_signal(log_ret, 28), log_ret, VOL_TARGET)

    # ── 6. Scaled positions ───────────────────────────────────────────────────
    pos_macro    = scale_positions(pos_c1, macro_mult_d)
    pos_trends   = scale_positions(pos_c1, trends_mult_d)
    pos_combined = scale_positions(pos_c1, combined_mult_d)

    # ── 7. P&L ────────────────────────────────────────────────────────────────
    pnl_c1       = compute_pnl(close, pos_c1)
    pnl_macro    = compute_pnl(close, pos_macro)
    pnl_trends   = compute_pnl(close, pos_trends)
    pnl_combined = compute_pnl(close, pos_combined)

    # ── 8. OOS metrics ────────────────────────────────────────────────────────
    pnl_c1_oos       = pnl_c1[OOS_START:]
    pnl_combined_oos = pnl_combined[OOS_START:]

    m_c1       = _full_metrics(pnl_c1_oos)
    m_macro    = _full_metrics(pnl_macro[OOS_START:])
    m_trends   = _full_metrics(pnl_trends[OOS_START:])
    m_combined = _full_metrics(pnl_combined_oos)

    # ── 9. OOS results table ──────────────────────────────────────────────────
    W = 32
    print(f"\n{'═'*72}")
    print("OOS RESULTS (2023-01-01 → 2026-05-14)")
    print(f"{'═'*72}")
    print(f"  {'Config':<{W}} {'Sharpe':>8} {'MaxDD':>8} {'WinRate':>8}")
    print("  " + "─" * 56)
    for label, m in [
        ("TSMOM v3 (C1) baseline",    m_c1),
        ("+ macro scaler only",        m_macro),
        ("+ trends scaler only",       m_trends),
        ("+ combined scaler",          m_combined),
    ]:
        sh = f"{m['sharpe']:.2f}" if not np.isnan(m['sharpe']) else " N/A"
        dd = f"{m['max_dd']:.1%}" if not np.isnan(m['max_dd']) else " N/A"
        wr = f"{m['win_rate']:.1%}" if not np.isnan(m['win_rate']) else " N/A"
        print(f"  {label:<{W}} {sh:>8} {dd:>8} {wr:>8}")
    print("  " + "─" * 56)

    # ── 10. Walk-forward ──────────────────────────────────────────────────────
    print(f"\n{'═'*72}")
    print("WALK-FORWARD (4 windows)")
    print(f"{'═'*72}")
    print(f"  {'Window':<12} {'C1':>8} {'Combined':>10} {'Win?':>6}")
    print("  " + "─" * 42)

    wf_wins    = 0
    fold_labels: list[str]   = []
    fold_c1:    list[float]  = []
    fold_comb:  list[float]  = []

    for fold in WALK_FOLDS:
        ts, te = fold["test_start"], fold["test_end"]
        sh_c1   = _sharpe(pnl_c1[ts:te])
        sh_comb = _sharpe(pnl_combined[ts:te])
        win = (not np.isnan(sh_comb) and not np.isnan(sh_c1)
               and sh_comb > sh_c1)
        if win:
            wf_wins += 1
        fold_labels.append(fold["label"])
        fold_c1.append(sh_c1 if not np.isnan(sh_c1) else 0.0)
        fold_comb.append(sh_comb if not np.isnan(sh_comb) else 0.0)
        print(f"  {fold['label']:<12} {sh_c1:>8.3f} {sh_comb:>10.3f} "
              f"{'✓' if win else '✗':>6}")

    print("  " + "─" * 42)
    print(f"  {'WF wins':<12} {'':>8} {'':>10} {wf_wins}/4")

    # ── 11. DSR correction ────────────────────────────────────────────────────
    print(f"\n{'═'*72}")
    print(f"DSR CORRECTION (n={N_DSR_TESTS} tests)")
    print(f"{'═'*72}")

    dsr = deflated_sharpe_ratio(
        pnl_combined_oos.dropna().values,
        n_trials=N_DSR_TESTS,
        periods_per_year=TRADING_DAYS,
    )

    # DSR-adjusted Sharpe = raw Sharpe × DSR probability (deflation by luck factor)
    dsr_adj_sharpe = dsr["sharpe"] * dsr["dsr"]

    print(f"  n tests              : {N_DSR_TESTS}")
    print(f"  OOS observations     : {dsr['n_obs']}")
    print(f"  Raw Sharpe           : {dsr['sharpe']:.3f}")
    print(f"  E[max SR] benchmark  : {dsr['sr_benchmark']:.3f}  "
          f"(expected best from {N_DSR_TESTS} random trials)")
    print(f"  DSR probability      : {dsr['dsr']:.3f}  "
          f"({'PASS ≥0.95' if dsr['passed'] else 'FAIL <0.95'})")
    print(f"  DSR-adjusted Sharpe  : {dsr_adj_sharpe:.3f}  "
          f"{'(≥ 1.0 — genuine)' if dsr_adj_sharpe >= 1.0 else '(< 1.0 — likely luck)'}")
    print(f"  Skewness             : {dsr['skewness']:.3f}")
    print(f"  Excess kurtosis      : {dsr['excess_kurtosis']:.3f}")

    # ── 12. Verdict ───────────────────────────────────────────────────────────
    sh_comb  = m_combined["sharpe"]
    sh_base  = m_c1["sharpe"]
    dsr_ok   = dsr["passed"]

    print(f"\n{'═'*72}")
    print("VERDICT")
    print(f"{'═'*72}")

    if (not np.isnan(sh_comb) and sh_comb > 1.5
            and wf_wins >= 3 and dsr_ok):
        print(f"  IMPLEMENT")
        print(f"  Sharpe improvement: {sh_base:.2f} → {sh_comb:.2f}, "
              f"WF {wf_wins}/4, DSR passed")
        print(f"  Action: add macro_scaler() + trends_scaler() to")
        print(f"          tsmom_v2_propfirm/signal.py as optional multipliers")
        print(f"          combined_mult applied before gross cap, default enabled")
    else:
        # Determine WEAK vs SKIP
        is_weak = (not np.isnan(sh_comb)
                   and (1.35 <= sh_comb <= 1.5 or wf_wins >= 2))
        if is_weak:
            print(f"  WEAK — improvement too small/unstable. Accept C1 at {sh_base:.2f}.")
            sh_str = f"{sh_comb:.2f}" if not np.isnan(sh_comb) else "N/A"
            print(f"  Sharpe: {sh_base:.2f} → {sh_str}  |  WF {wf_wins}/4  |  "
                  f"DSR {'✓' if dsr_ok else '✗'}")
            print(f"  Operational complexity not justified by this margin.")
        else:
            print(f"  SKIP — signals don't survive portfolio context.")
            sh_str = f"{sh_comb:.2f}" if not np.isnan(sh_comb) else "N/A"
            print(f"  Sharpe: {sh_base:.2f} → {sh_str}  |  WF {wf_wins}/4")
        _print_next_steps()

    # ── 13. Figure ────────────────────────────────────────────────────────────
    out_path = _plot(
        pnl_c1_oos, pnl_combined_oos,
        combined_mult_d[OOS_START:],
        fold_labels, fold_c1, fold_comb,
        macro_mult_d[OOS_START:],
        trends_mult_d[OOS_START:],
    )
    print(f"\n  Figure: {out_path}")


if __name__ == "__main__":
    main()
