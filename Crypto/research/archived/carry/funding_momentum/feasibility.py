"""
strategies/funding_momentum/feasibility.py — Funding Rate Momentum

Strategy B uses funding LEVEL (earn carry when funding > threshold).
This tests funding MOMENTUM (trend in the rate itself):

  Rising funding = increasing leverage bias = momentum builds
  Falling funding = deleveraging = positioning unwind = reversal risk

Signal:
  funding_trend[T] = mean_funding_7d[T-1] - mean_funding_14d[T-8]
  funding_momentum_z[T] = zscore(funding_trend, trailing 60 days)
  Long BTC when z > +0.5, flat when z < -0.5, flat in neutral zone.

Data: BTC 8h HL funding rate.
  Primary: load strategies/cs_carry/data/BTC_hl_funding.csv (2024-01 → 2026-05)
  Extended: fetch HL API for 2023-05 → 2023-12 (bear period completion)

Critical test: must be distinct from TSMOM and funding LEVEL (Strategy B).
  corr(funding_momentum, tsmom_28d)  < 0.40 → genuinely new signal
  corr(funding_momentum, funding_lvl) < 0.60 → not just a level proxy

VERDICT: GO if IC t-stat > 1.5 AND corr(TSMOM) < 0.40
         AND positive in both sub-periods (2023 bear, 2024-26 bull)
"""

import os, sys, time, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")
np.random.seed(42)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
HL_URL      = "https://api.hyperliquid.xyz/info"
BIN_URL     = "https://api.binance.com/api/v3/klines"
DATA_DIR    = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "cs_carry", "data"
)
BTC_CSV     = os.path.join(DATA_DIR, "BTC_hl_funding.csv")

COST_RT     = 0.0017
VOL_TGT     = 0.15
Z_LONG_THR  = 0.5    # long when z > +0.5
Z_FLAT_THR  = -0.5   # flat when z < -0.5 (includes neutral zone -0.5 to +0.5)
ROLL_TREND  = 60     # days for z-score baseline

# Sub-periods
PERIOD_BEAR  = ("2023-05-01", "2023-12-31")
PERIOD_BULL  = ("2024-01-01", "2026-05-17")

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ─── DATA FETCH ───────────────────────────────────────────────────────────────

def _hl_post(payload: dict, timeout: int = 30) -> list:
    for attempt in range(3):
        try:
            r = requests.post(HL_URL, json=payload, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == 2: raise
            time.sleep(2 ** attempt)
    return []


def fetch_hl_funding_range(coin: str = "BTC",
                            start: str = "2023-05-01",
                            end:   str = "2023-12-31") -> pd.Series:
    """Fetch HL funding history for a date range. Returns hourly series."""
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ms   = int(pd.Timestamp(end,   tz="UTC").timestamp() * 1000)
    chunk_ms = int(180 * 24 * 3600 * 1000)  # 6 months
    all_rows: list = []
    t = start_ms
    while t < end_ms:
        chunk_end = min(t + chunk_ms, end_ms)
        try:
            rows = _hl_post({"type": "fundingHistory", "coin": coin,
                             "startTime": t, "endTime": chunk_end})
        except Exception:
            rows = []
        if rows:
            all_rows.extend(rows)
            t = int(rows[-1]["time"]) + 1
        else:
            t = chunk_end + 1
        time.sleep(0.25)
    if not all_rows:
        return pd.Series(dtype=float, name="funding_rate")
    df = pd.DataFrame(all_rows)
    df["time"] = pd.to_datetime(df["time"].astype(np.int64), unit="ms", utc=True)
    s = (df.set_index("time")["fundingRate"]
           .astype(float).sort_index()
           .loc[~df.set_index("time").index.duplicated(keep="last")])
    return s


def load_and_extend_funding() -> pd.Series:
    """
    Load cached CSV + fetch missing periods from HL API.
    Combines into a single hourly BTC funding series.
    """
    parts: list[pd.Series] = []

    # 1. Load cached CSV
    if os.path.exists(BTC_CSV):
        df = pd.read_csv(BTC_CSV, index_col=0)
        df.index = pd.to_datetime(df.index, format="mixed", utc=True)
        # Handle both column name formats
        col = df.columns[0]
        s   = df[col].astype(float).sort_index()
        s   = s[~s.index.duplicated(keep="last")]
        print(f"  Cached CSV: {len(s)} rows  "
              f"({s.index[0].date()} → {s.index[-1].date()})")
        csv_start = s.index[0]
        parts.append(s)
    else:
        csv_start = pd.Timestamp("2024-01-01", tz="UTC")
        print(f"  No cache found at {BTC_CSV}")

    # 2. Fetch 2023 bear period (HL funding history starts May 2023)
    print(f"\n  Fetching HL funding 2023-05 → 2023-12 (bear period)…")
    s_2023 = fetch_hl_funding_range("BTC", start="2023-05-01", end="2023-12-31")
    if len(s_2023) > 0:
        print(f"  2023 data: {len(s_2023)} records  "
              f"({s_2023.index[0].date()} → {s_2023.index[-1].date()})")
        parts.append(s_2023)
    else:
        print("  2023 data: FAILED")

    # 3. Fetch recent gap (if any) past CSV end
    if parts:
        latest_ts = max(s.index[-1] for s in parts)
        now_ts    = pd.Timestamp.now(tz="UTC")
        if (now_ts - latest_ts).days > 3:
            gap_start = (latest_ts + pd.Timedelta(hours=1)).strftime("%Y-%m-%d")
            print(f"\n  Fetching HL funding gap {gap_start} → now…")
            s_gap = fetch_hl_funding_range("BTC", start=gap_start,
                                            end=now_ts.strftime("%Y-%m-%d"))
            if len(s_gap) > 0:
                print(f"  Gap data: {len(s_gap)} records")
                parts.append(s_gap)

    if not parts:
        raise RuntimeError("No funding data available")

    # Combine + deduplicate
    combined = pd.concat(parts).sort_index()
    combined = combined[~combined.index.duplicated(keep="last")]
    return combined.rename("funding_rate")


# ─── BTC DAILY PRICE ─────────────────────────────────────────────────────────

def fetch_btc_daily_binance(start: str = "2023-01-01") -> pd.Series:
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    now_ms   = int(pd.Timestamp.now(tz="UTC").timestamp() * 1000)
    day_ms   = 86_400_000
    all_rows: list = []
    while start_ms < now_ms:
        params = {"symbol": "BTCUSDT", "interval": "1d",
                  "startTime": start_ms, "limit": 1000}
        r = requests.get(BIN_URL, params=params, timeout=15)
        r.raise_for_status()
        rows = r.json()
        if not rows: break
        all_rows.extend(rows)
        start_ms = int(rows[-1][0]) + day_ms
        time.sleep(0.12)
    df = pd.DataFrame(all_rows, columns=[
        "open_time","o","h","l","close","vol","close_time","qvol","n","tb","tq","_"
    ])
    ts = pd.to_datetime(df["open_time"].astype(np.int64), unit="ms", utc=True)
    s  = pd.Series(df["close"].astype(float).values, index=ts, name="BTC")
    return s[~s.index.duplicated(keep="last")].sort_index()


# ─── SIGNAL CONSTRUCTION ──────────────────────────────────────────────────────

def build_funding_signal(funding_hourly: pd.Series) -> pd.DataFrame:
    """
    Resample hourly funding to daily mean.
    Compute funding_trend = 7d_mean[T-1] - 14d_mean[T-8]
    Z-score vs trailing 60 days.
    Return daily DataFrame with cols: [funding_daily, fund_7d, fund_14d,
                                       funding_trend, trend_z, signal].
    """
    # Daily mean of 8h funding rate
    funding_daily = funding_hourly.resample("D").mean().dropna()

    # 7-day rolling mean (shift 1 = yesterday)
    fund_7d  = funding_daily.rolling(7,  min_periods=5).mean()
    # 14-day rolling mean (shift 8 = 8 days ago)
    fund_14d = funding_daily.rolling(14, min_periods=10).mean()

    # Trend: recent 7d vs delayed 14d
    funding_trend = fund_7d.shift(1) - fund_14d.shift(8)

    # Z-score vs trailing 60-day window
    roll_mean = funding_trend.rolling(ROLL_TREND, min_periods=30).mean()
    roll_std  = funding_trend.rolling(ROLL_TREND, min_periods=30).std()
    trend_z   = ((funding_trend - roll_mean) / roll_std.replace(0, np.nan))

    # Daily signal
    signal = pd.Series(0.0, index=trend_z.index)
    signal[trend_z > Z_LONG_THR]  = 1.0   # long
    signal[trend_z < Z_FLAT_THR]  = 0.0   # flat (same as neutral)
    # middle zone [-0.5, +0.5] = flat

    return pd.DataFrame({
        "funding_daily": funding_daily,
        "fund_7d":       fund_7d,
        "fund_14d":      fund_14d,
        "funding_trend": funding_trend,
        "trend_z":       trend_z,
        "signal":        signal,
    })


def resample_weekly(df_daily: pd.DataFrame) -> pd.DataFrame:
    """Resample daily signal metrics to weekly (W-FRI, last value)."""
    return df_daily.resample("W-FRI").last().dropna(subset=["trend_z"])


# ─── TSMOM v3 ─────────────────────────────────────────────────────────────────

def compute_tsmom_weekly(btc_close: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Returns (tsmom_weekly_returns, tsmom_weekly_signal)."""
    lr   = np.log(btc_close / btc_close.shift(1)).dropna()
    cr28 = lr.rolling(28).sum()
    v28  = lr.rolling(28).std() * np.sqrt(28)
    sig  = np.tanh(cr28 / v28.replace(0, np.nan)).clip(lower=0)
    return sig.resample("W-FRI").sum(), sig.resample("W-FRI").last()


# ─── IC TEST ─────────────────────────────────────────────────────────────────

def ic_test(weekly_z: pd.Series, btc_close: pd.Series) -> dict:
    """rank_corr(z[T], BTC_return_next_week[T+1])."""
    btc_wk  = np.log(btc_close / btc_close.shift(1)).resample("W-FRI").sum()
    fwd_ret = btc_wk.shift(-1)
    common  = weekly_z.dropna().index.intersection(fwd_ret.dropna().index)
    if len(common) < 10:
        return {"ic": np.nan, "t_stat": np.nan, "p_val": np.nan, "n": 0}
    z   = weekly_z.reindex(common)
    r   = fwd_ret.reindex(common)
    ic, p_val = spearmanr(z, r)
    n  = len(common)
    t  = ic * np.sqrt(n - 2) / np.sqrt(max(1 - ic**2, 1e-9))
    return {"ic": ic, "t_stat": t, "p_val": p_val, "n": n,
            "z_series": z, "ret_series": r}


# ─── BACKTEST ─────────────────────────────────────────────────────────────────

def compute_vol_scalar(btc_close: pd.Series) -> pd.Series:
    lr    = np.log(btc_close / btc_close.shift(1)).dropna()
    rv    = lr.rolling(28).std() * np.sqrt(252)
    return (VOL_TGT / rv.resample("W-FRI").last().replace(0, np.nan)).clip(0.1, 2.0)


def backtest(weekly_signal: pd.Series, btc_close: pd.Series,
             tsmom_wk_ret: pd.Series, tsmom_wk_sig: pd.Series,
             start: str = "2023-05-01", end: str = "2026-05-17") -> dict:
    """
    Long-only, vol-scaled. Signal at T → position for week T+1.
    """
    btc_wk_ret = np.log(btc_close / btc_close.shift(1)).resample("W-FRI").sum()
    v_sc       = compute_vol_scalar(btc_close)

    mask = ((weekly_signal.index >= pd.Timestamp(start, tz="UTC")) &
            (weekly_signal.index <= pd.Timestamp(end,   tz="UTC")))
    sig  = weekly_signal[mask]

    common = (sig.index.intersection(btc_wk_ret.index)
                        .intersection(v_sc.index))
    if len(common) < 10:
        return {"sharpe": np.nan, "maxdd": np.nan, "corr_tsmom": np.nan,
                "corr_level": np.nan, "trades_yr": 0, "n_weeks": 0}

    s   = sig.reindex(common)
    r   = btc_wk_ret.reindex(common)
    v   = v_sc.reindex(common, method="ffill").fillna(1.0)

    # Position = signal × vol_scalar, lagged 1 week
    pos    = (s * v).shift(1).fillna(0)
    entry  = (pos.diff() > 0).astype(float)
    bar_r  = pos * r - entry * COST_RT
    cum_r  = bar_r.cumsum()

    n_yrs = max((common[-1] - common[0]).days / 365.25, 0.1)
    sh    = bar_r.mean() / bar_r.std() * np.sqrt(52) if bar_r.std() > 0 else 0.0
    maxdd = (cum_r - cum_r.cummax()).min()

    # Correlation with TSMOM returns
    common_t  = bar_r.index.intersection(tsmom_wk_ret.index)
    corr_tsmom = (bar_r.loc[common_t].corr(tsmom_wk_ret.loc[common_t])
                  if len(common_t) >= 10 else np.nan)

    # Signal overlap: corr of position with TSMOM signal
    common_s  = s.index.intersection(tsmom_wk_sig.index)
    sig_corr  = (s.loc[common_s].corr(tsmom_wk_sig.loc[common_s])
                 if len(common_s) >= 10 else np.nan)

    return {
        "sharpe": sh, "maxdd": maxdd, "corr_tsmom": corr_tsmom,
        "sig_corr_tsmom": sig_corr, "trades_yr": entry.sum() / n_yrs,
        "n_weeks": len(common), "cum_ret": cum_r, "bar_ret": bar_r
    }


# ─── FIGURE ──────────────────────────────────────────────────────────────────

def make_figure(df_daily: pd.DataFrame, weekly_z: pd.Series,
                ic_res: dict, bt_full: dict, bt_bear: dict, bt_bull: dict,
                tsmom_wk_ret: pd.Series, btc_close: pd.Series) -> None:

    fig, axes = plt.subplots(2, 3, figsize=(20, 12))
    fig.suptitle(
        "Funding Rate Momentum — Strategy C Candidate (Signal 29)\n"
        "Signal: z-score of funding trend (7d vs 14d)  |  "
        "Long BTC when z > 0.5  |  Weekly rebalance",
        fontsize=12, fontweight="bold"
    )

    # Panel 1: Funding daily + trend Z-score
    ax1 = axes[0, 0]
    ax1b = ax1.twinx()
    fd = df_daily["funding_daily"] * 1e4  # basis points
    tz = df_daily["trend_z"]
    fd_2023  = fd[fd.index >= "2023-05-01"]
    tz_2023  = tz[tz.index >= "2023-05-01"]
    ax1.fill_between(fd_2023.index, 0, fd_2023.values,
                     where=fd_2023.values > 0, color="#4393c3", alpha=0.5)
    ax1.fill_between(fd_2023.index, 0, fd_2023.values,
                     where=fd_2023.values < 0, color="#d73027", alpha=0.5)
    ax1.axhline(0, color="black", lw=0.5)
    ax1b.plot(tz_2023.index, tz_2023.values, color="#2166ac", lw=1.2,
              label="Trend z-score")
    ax1b.axhline(Z_LONG_THR,  color="#1a9850", ls="--", lw=1, label=f"Long thr ({Z_LONG_THR})")
    ax1b.axhline(Z_FLAT_THR, color="#d73027", ls="--", lw=1, label=f"Flat thr ({Z_FLAT_THR})")
    ax1.set_title("BTC Funding Rate (bps) + Trend Z-Score", fontsize=10)
    ax1.set_ylabel("Daily funding (bps)"); ax1b.set_ylabel("Trend Z")
    ax1b.legend(fontsize=8, loc="upper right"); ax1.grid(alpha=0.3)

    # Panel 2: Funding level vs funding trend scatter
    ax = axes[0, 1]
    fl = df_daily["fund_7d"].dropna()
    tr = df_daily["funding_trend"].dropna()
    common_sc = fl.index.intersection(tr.index)
    ax.scatter(fl.reindex(common_sc) * 1e4, tr.reindex(common_sc) * 1e5,
               alpha=0.2, s=10, color="#4393c3")
    ax.axhline(0, color="black", lw=0.5)
    ax.axvline(0, color="black", lw=0.5, ls="--")
    corr_lvl = fl.reindex(common_sc).corr(tr.reindex(common_sc))
    ax.set_title(f"Funding Level vs Trend\ncorr={corr_lvl:+.3f}  "
                 f"(target: < 0.60)", fontsize=10)
    ax.set_xlabel("Funding level (bps/day)"); ax.set_ylabel("Funding trend (×1e5)")
    ax.grid(alpha=0.3)

    # Panel 3: IC scatter
    ax = axes[0, 2]
    if ic_res.get("n", 0) > 0:
        zs = ic_res.get("z_series", pd.Series(dtype=float))
        rs = ic_res.get("ret_series", pd.Series(dtype=float)) * 100
        ax.scatter(zs, rs, alpha=0.4, s=20, color="#2166ac")
        if len(zs) > 3:
            c = np.polyfit(zs, rs, 1)
            xl = np.linspace(zs.min(), zs.max(), 50)
            ax.plot(xl, np.polyval(c, xl), color="#d73027", lw=2)
    ax.axhline(0, color="black", lw=0.5)
    ax.axvline(Z_LONG_THR, color="#1a9850", ls="--", lw=1, label="Long thr")
    ax.set_title(
        f"IC: funding_momentum_z[T] vs BTC ret[T+1]\n"
        f"IC={ic_res.get('ic', np.nan):+.4f}  t={ic_res.get('t_stat', np.nan):+.3f}  "
        f"n={ic_res.get('n', 0)}",
        fontsize=10
    )
    ax.set_xlabel("Funding momentum z-score"); ax.set_ylabel("Next-week BTC return (%)")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # Panel 4: Equity curve (full + sub-periods)
    ax = axes[1, 0]
    for res, color, lbl in [
        (bt_full, "#2166ac", f"Full  Sharpe={bt_full.get('sharpe', np.nan):.3f}"),
        (bt_bear, "#d73027", f"Bear  Sharpe={bt_bear.get('sharpe', np.nan):.3f}"),
        (bt_bull, "#1a9850", f"Bull  Sharpe={bt_bull.get('sharpe', np.nan):.3f}"),
    ]:
        if "cum_ret" in res and len(res["cum_ret"]) > 0:
            cum = res["cum_ret"]
            ax.plot(cum.index, cum.values * 100, color=color, lw=1.5, label=lbl)
    # TSMOM reference
    ts_cum = tsmom_wk_ret[tsmom_wk_ret.index >= "2023-05-01"].cumsum()
    ax.plot(ts_cum.index, ts_cum.values * 100, color="gray", lw=1, ls="--",
            alpha=0.7, label="TSMOM v3 ref")
    ax.axhline(0, color="black", lw=0.5)
    ax.set_title("Equity Curve (log return, %)", fontsize=10)
    ax.set_ylabel("Cum log return (%)"); ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # Panel 5: Weekly z-score time series
    ax = axes[1, 1]
    ax.fill_between(weekly_z.index, 0, weekly_z.values,
                    where=weekly_z.values > Z_LONG_THR,
                    color="#1a9850", alpha=0.5, label="Long")
    ax.fill_between(weekly_z.index, 0, weekly_z.values,
                    where=weekly_z.values < 0,
                    color="#d73027", alpha=0.3, label="Negative")
    ax.plot(weekly_z.index, weekly_z.values, color="#2166ac", lw=1.5)
    ax.axhline(Z_LONG_THR,  color="#1a9850", ls="--", lw=1)
    ax.axhline(Z_FLAT_THR, color="#d73027", ls="--", lw=1)
    ax.axhline(0, color="black", lw=0.5)
    ax.set_title(f"Funding Momentum Z-score Weekly\n"
                 f"ON={( weekly_z > Z_LONG_THR).mean():.1%}  "
                 f"FLAT={((weekly_z >= Z_FLAT_THR) & (weekly_z <= Z_LONG_THR)).mean():.1%}",
                 fontsize=10)
    ax.set_ylabel("Z-score"); ax.legend(fontsize=8); ax.grid(alpha=0.3)

    # Panel 6: Summary table
    ax = axes[1, 2]
    ax.axis("off")
    ct = bt_full.get("corr_tsmom", np.nan)
    cs = bt_full.get("sig_corr_tsmom", np.nan)
    ic_t = ic_res.get("t_stat", np.nan)
    sh   = bt_full.get("sharpe", np.nan)
    go   = (ic_t > 1.5 and abs(ct) < 0.40
            and bt_bear.get("sharpe", -99) > 0
            and bt_bull.get("sharpe", -99) > 0)
    txt = (
        "═══ FUNDING MOMENTUM SUMMARY ═══\n\n"
        f"IC (full period):\n"
        f"  IC    = {ic_res.get('ic', np.nan):+.4f}\n"
        f"  t     = {ic_t:+.3f}  (target > 1.5)\n"
        f"  n     = {ic_res.get('n', 0)}\n\n"
        f"Portfolio (full period):\n"
        f"  Sharpe   = {sh:+.3f}\n"
        f"  MaxDD    = {bt_full.get('maxdd', 0)*100:.1f}%\n"
        f"  t/yr     = {bt_full.get('trades_yr', 0):.0f}\n\n"
        f"Sub-periods:\n"
        f"  Bear 2023: Sharpe={bt_bear.get('sharpe', np.nan):+.3f}\n"
        f"  Bull 2024-26: Sharpe={bt_bull.get('sharpe', np.nan):+.3f}\n\n"
        f"Correlation tests:\n"
        f"  corr(returns, TSMOM_ret) = {ct:+.3f}\n"
        f"  corr(signal, TSMOM_sig)  = {cs:+.3f}\n"
        f"  (target: both < 0.40)\n\n"
        f"VERDICT:\n"
        f"  GO if: IC t>1.5 AND corr<0.40\n"
        f"         AND positive both sub-periods\n"
        f"  >>> {'GO ✓' if go else 'SKIP ✗'}"
    )
    ax.text(0.04, 0.97, txt, transform=ax.transAxes,
            va="top", ha="left", fontsize=9.5, fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#f0f4ff",
                      edgecolor="#2166ac"))

    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "feasibility_results.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n  Figure → {out_path}")
    plt.close()


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("FUNDING RATE MOMENTUM — Signal 29")
    print("Signal: trend in BTC HL funding (7d vs 14d), z-scored vs 60d baseline")
    print("=" * 70)

    # ── 1. Funding data ───────────────────────────────────────────────────────
    print("\n[1/5] Loading + extending funding rate history…")
    funding_hourly = load_and_extend_funding()
    print(f"\n  Combined: {len(funding_hourly)} hourly records  "
          f"({funding_hourly.index[0].date()} → {funding_hourly.index[-1].date()})")

    # ── 2. BTC daily price ────────────────────────────────────────────────────
    print("\n[2/5] Fetching BTC daily price from Binance…")
    btc_close = fetch_btc_daily_binance(start="2023-01-01")
    print(f"  {len(btc_close)} days  "
          f"({btc_close.index[0].date()} → {btc_close.index[-1].date()})")

    # ── 3. Signal construction ────────────────────────────────────────────────
    print("\n[3/5] Building funding momentum signal…")
    df_daily = build_funding_signal(funding_hourly)
    wk_df    = resample_weekly(df_daily)

    weekly_z = wk_df["trend_z"].dropna()
    print(f"  Daily signal: {len(df_daily)} rows  "
          f"({df_daily.index[0].date()} → {df_daily.index[-1].date()})")
    print(f"  Weekly z-score: {len(weekly_z)} weeks")
    print(f"  Z-score stats: "
          f"mean={weekly_z.mean():+.3f}  "
          f"p25={weekly_z.quantile(0.25):+.3f}  "
          f"p50={weekly_z.quantile(0.50):+.3f}  "
          f"p75={weekly_z.quantile(0.75):+.3f}")
    print(f"  Signal ON (z>{Z_LONG_THR}): {(weekly_z > Z_LONG_THR).mean():.1%} of weeks")
    print(f"  Signal FLAT (z<{Z_FLAT_THR}): {(weekly_z < Z_FLAT_THR).mean():.1%} of weeks")
    print(f"  Neutral zone: {((weekly_z >= Z_FLAT_THR) & (weekly_z <= Z_LONG_THR)).mean():.1%}")

    # Correlation between funding level and trend
    fl = df_daily["fund_7d"].dropna()
    tr = df_daily["funding_trend"].dropna()
    common_c = fl.index.intersection(tr.index)
    corr_lvl = fl.reindex(common_c).corr(tr.reindex(common_c))
    print(f"\n  corr(funding_level, funding_trend) = {corr_lvl:+.3f}  (target < 0.60)")

    # ── 4. TSMOM reference ────────────────────────────────────────────────────
    print("\n[4/5] Computing TSMOM v3 and IC test…")
    tsmom_wk_ret, tsmom_wk_sig = compute_tsmom_weekly(btc_close)

    ic_res = ic_test(weekly_z, btc_close)
    print(f"  IC       = {ic_res['ic']:+.4f}")
    print(f"  t-stat   = {ic_res['t_stat']:+.3f}  (p={ic_res.get('p_val', np.nan):.4f})")
    print(f"  N weeks  = {ic_res['n']}")

    # Sub-period IC
    for name, s, e in [("2023 (bear)", "2023-05-01", "2023-12-31"),
                        ("2024-26 (bull)", "2024-01-01", "2026-12-31")]:
        sub_z  = weekly_z[(weekly_z.index >= s) & (weekly_z.index < e)]
        ic_sub = ic_test(sub_z, btc_close)
        print(f"  {name}: IC={ic_sub.get('ic', np.nan):+.4f}  "
              f"t={ic_sub.get('t_stat', np.nan):+.3f}  n={ic_sub.get('n', 0)}")

    # ── 5. Backtest ───────────────────────────────────────────────────────────
    print("\n[5/5] Backtest (vol-scaled 15%, weekly rebalance)…")
    bt_full = backtest(weekly_z, btc_close, tsmom_wk_ret, tsmom_wk_sig,
                       start="2023-05-01")
    bt_bear = backtest(weekly_z, btc_close, tsmom_wk_ret, tsmom_wk_sig,
                       start="2023-05-01", end="2023-12-31")
    bt_bull = backtest(weekly_z, btc_close, tsmom_wk_ret, tsmom_wk_sig,
                       start="2024-01-01")

    print(f"\n  ── RESULTS ──")
    print(f"  {'Period':<25} {'Sharpe':>7} {'MaxDD':>8} {'t/yr':>6}")
    print(f"  {'─'*50}")
    for name, res in [("Full (2023-05→2026)", bt_full),
                       ("Bear (2023-05→2023-12)", bt_bear),
                       ("Bull (2024→2026)", bt_bull)]:
        print(f"  {name:<25} {res['sharpe']:>7.3f} "
              f"{res['maxdd']*100:>7.1f}% {res['trades_yr']:>6.0f}")

    print(f"\n  corr(returns, TSMOM weekly):  {bt_full['corr_tsmom']:+.3f}")
    print(f"  corr(signal, TSMOM signal):   {bt_full['sig_corr_tsmom']:+.3f}")
    print(f"  corr(level, trend):           {corr_lvl:+.3f}")

    make_figure(df_daily, weekly_z, ic_res, bt_full, bt_bear, bt_bull,
                tsmom_wk_ret, btc_close)

    # ── VERDICT ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    ic_t = ic_res.get("t_stat", 0)
    ct   = abs(bt_full.get("corr_tsmom", 1))
    sh   = bt_full.get("sharpe", -99)
    bear_ok = bt_bear.get("sharpe", -99) > 0
    bull_ok = bt_bull.get("sharpe", -99) > 0

    print(f"\n  ┌{'─'*30}┬{'─'*8}┬{'─'*10}┬{'─'*11}┐")
    print(f"  │ {'Signal':<28} │{'t-stat':>6}  │{'Sharpe':>8}  │{'corr(TSMOM)':>9} │")
    print(f"  ├{'─'*30}┼{'─'*8}┼{'─'*10}┼{'─'*11}┤")
    print(f"  │ {'Funding momentum z-score':<28} │{ic_t:>+6.3f}  │{sh:>+8.3f}  │{bt_full['corr_tsmom']:>+9.3f} │")
    print(f"  └{'─'*30}┴{'─'*8}┴{'─'*10}┴{'─'*11}┘")
    print()

    if ic_t > 1.5 and ct < 0.40 and bear_ok and bull_ok:
        verdict = "GO — IC significant, low TSMOM corr, consistent sub-periods"
        action  = "Accept as Strategy C candidate. Test A+B+C portfolio weight."
    elif ic_t > 1.0 and ct < 0.50:
        verdict = "WEAK — marginal IC significance or slightly too correlated"
        action  = "Track. Consider testing on longer history when more HL data available."
    elif ct > 0.50:
        verdict = "SKIP — too correlated with TSMOM (momentum proxy)"
        action  = "Funding trend = lagged BTC momentum. No diversification value."
    else:
        verdict = "SKIP — IC not significant"
        action  = "Funding rate changes do not predict BTC returns at weekly frequency."

    print(f"  IC t-stat:         {ic_t:+.3f}  (target > 1.5)")
    print(f"  corr(TSMOM):       {ct:+.3f}  (target < 0.40)")
    print(f"  Bear sub-period:   {'✓ positive' if bear_ok else '✗ negative'}")
    print(f"  Bull sub-period:   {'✓ positive' if bull_ok else '✗ negative'}")
    print()
    print(f"  >>> {verdict}")
    print(f"  Next step: {action}")
    print()
    print(f"  Note: funding data available from May 2023 only (HL launch).")
    print(f"  Bear period limited to 8 months — sub-period analysis has low N.")


if __name__ == "__main__":
    main()
