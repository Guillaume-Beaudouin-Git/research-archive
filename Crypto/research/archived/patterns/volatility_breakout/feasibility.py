"""
strategies/volatility_breakout/feasibility.py — Volatility Squeeze Breakout

Hypothesis: Bollinger Band squeeze (volatility contraction) reliably precedes
a directional breakout. Signal fires INFREQUENTLY (~15-25 times/year) at
specific vol conditions → different mechanism from TSMOM (always in market).

Signal construction:
  BB(20, 2): 20-day MA ± 2 standard deviations.
  BB_width[T] = (upper[T] - lower[T]) / MA20[T]   ← normalized, no look-ahead
  squeeze[T]  = BB_width[T] < percentile(BB_width[T-126:T], 20)
  breakout_up[T] = squeeze[T-1] AND close[T] > upper_band[T]
  Signal: +1 on breakout_up, hold 10 trading days; flat otherwise (long-only).

Assets: BTC-USD, ETH-USD, SOL-USD (yfinance daily, 2020-2026)
Walk-forward: 3 non-overlapping OOS windows (2023, 2024, 2025)

VERDICT:
  PROMISING if Sharpe > 0.8 AND corr(TSMOM) < 0.50 AND positive 2+/3 WF windows
  SKIP if Sharpe < 0.5 OR corr > 0.60
"""

import os, sys, time, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import yfinance as yf
from scipy.stats import spearmanr

warnings.filterwarnings("ignore")
np.random.seed(42)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
ASSETS   = {"BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD"}
START    = "2020-01-01"
END      = "2026-05-17"

BB_PERIOD   = 20    # Bollinger Band period
BB_STD      = 2.0   # standard deviations
SQ_WINDOW   = 126   # days for percentile calculation (~6 months)
SQ_PCT      = 20    # squeeze = bottom 20th percentile of BB width
HOLD_DAYS   = 10    # days to hold after breakout signal
COST_RT     = 0.0017

WF_WINDOWS = [
    {"name": "WF1", "train_end": "2022-12-31", "test_start": "2023-01-01", "test_end": "2023-12-31"},
    {"name": "WF2", "train_end": "2023-12-31", "test_start": "2024-01-01", "test_end": "2024-12-31"},
    {"name": "WF3", "train_end": "2024-12-31", "test_start": "2025-01-01", "test_end": "2025-12-31"},
]

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ─── DATA FETCH ───────────────────────────────────────────────────────────────

def fetch_ohlcv(ticker: str, start: str = START, end: str = END) -> pd.DataFrame:
    """Fetch OHLCV from yfinance. Handles both old and new column formats."""
    try:
        df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        # Handle MultiIndex columns (yfinance 1.x)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        # Normalise column names
        df.columns = [c.lower() for c in df.columns]
        for col in ["open", "high", "low", "close", "volume"]:
            if col not in df.columns:
                return pd.DataFrame()
        df.index = pd.to_datetime(df.index)
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        return df[["open", "high", "low", "close", "volume"]].dropna()
    except Exception as e:
        print(f"  yfinance error for {ticker}: {e}")
        return pd.DataFrame()


# ─── BOLLINGER BANDS ──────────────────────────────────────────────────────────

def compute_bollinger(close: pd.Series,
                       period: int = BB_PERIOD,
                       n_std: float = BB_STD) -> pd.DataFrame:
    """Returns DataFrame with [ma, upper, lower, bb_width]."""
    ma    = close.rolling(period).mean()
    std   = close.rolling(period).std()
    upper = ma + n_std * std
    lower = ma - n_std * std
    bb_w  = (upper - lower) / ma.replace(0, np.nan)
    return pd.DataFrame({
        "ma": ma, "upper": upper, "lower": lower, "bb_width": bb_w
    }, index=close.index)


# ─── SQUEEZE DETECTION ────────────────────────────────────────────────────────

def detect_squeeze(bb_width: pd.Series,
                    window: int = SQ_WINDOW,
                    pct: float = SQ_PCT) -> pd.Series:
    """
    squeeze[T] = 1 if bb_width[T] < {pct}th percentile of bb_width[T-window:T].
    Rolling, fully look-ahead free.
    """
    threshold = bb_width.rolling(window, min_periods=window // 2).quantile(pct / 100)
    return (bb_width < threshold).astype(float)


# ─── BREAKOUT SIGNAL ─────────────────────────────────────────────────────────

def compute_breakout_signal(close: pd.Series, bb: pd.DataFrame,
                             squeeze: pd.Series) -> pd.Series:
    """
    breakout_up[T] = squeeze[T-1] AND close[T] > upper_band[T]
    Returns binary signal: 1 = long entry, 0 = no new entry.
    (breakout_down ignored — long-only only)
    """
    prev_squeeze = squeeze.shift(1)
    return ((prev_squeeze == 1) & (close > bb["upper"])).astype(float)


def apply_hold(entry_signal: pd.Series, hold_days: int = HOLD_DAYS) -> pd.Series:
    """
    Convert point-in-time entry signals to held positions.
    position[T] = 1 if any entry in [T-hold_days+1, T], else 0.
    """
    pos = pd.Series(0.0, index=entry_signal.index)
    for i in range(len(entry_signal)):
        if entry_signal.iloc[i] == 1:
            end = min(i + hold_days, len(entry_signal))
            pos.iloc[i:end] = 1.0
    return pos


# ─── TSMOM v3 ─────────────────────────────────────────────────────────────────

def compute_tsmom(close: pd.Series) -> pd.Series:
    """
    TSMOM v3 daily position: tanh(cumret_28d / vol_28d), long-only clip.
    Returns daily signal series [0, 1].
    """
    lr   = np.log(close / close.shift(1)).dropna()
    cr28 = lr.rolling(28).sum()
    v28  = lr.rolling(28).std() * np.sqrt(28)
    sig  = np.tanh(cr28 / v28.replace(0, np.nan)).clip(lower=0)
    return sig


# ─── BACKTEST ─────────────────────────────────────────────────────────────────

def backtest_asset(close: pd.Series, position: pd.Series,
                   tsmom_daily: pd.Series,
                   start: str = START, end: str = END) -> dict:
    """
    Daily backtest. cost charged on 0→1 entries.
    Returns Sharpe, MaxDD, trades/yr, corr(TSMOM), win_rate.
    """
    mask  = (close.index >= pd.Timestamp(start, tz="UTC")) & \
            (close.index <= pd.Timestamp(end, tz="UTC"))
    c  = close[mask]
    p  = position.reindex(c.index).fillna(0)
    ts = tsmom_daily.reindex(c.index).fillna(0)

    ret    = np.log(c / c.shift(1)).fillna(0)
    entry  = (p.diff() > 0).astype(float)
    bar_r  = p.shift(1).fillna(0) * ret - entry * COST_RT
    cum_r  = bar_r.cumsum()

    if bar_r.std() == 0 or len(bar_r.dropna()) < 30:
        return {"sharpe": np.nan, "maxdd": np.nan, "trades_yr": 0,
                "corr_tsmom": np.nan, "win_rate": np.nan, "n_days": 0,
                "cum_ret": pd.Series(dtype=float), "bar_ret": pd.Series(dtype=float)}

    n_yrs     = max((c.index[-1] - c.index[0]).days / 365.25, 0.1)
    sharpe    = bar_r.mean() / bar_r.std() * np.sqrt(252)
    maxdd     = (cum_r - cum_r.cummax()).min()
    trades_yr = entry.sum() / n_yrs

    # Win rate: proportion of held-period chunks with positive return
    trade_rets = []
    in_trade = False
    trade_r = []
    for i in range(len(p)):
        if p.iloc[i] == 1 and not in_trade:
            in_trade = True
            trade_r = []
        if in_trade:
            trade_r.append(bar_r.iloc[i])
        if (p.iloc[i] == 0 or i == len(p) - 1) and in_trade and trade_r:
            trade_rets.append(sum(trade_r))
            in_trade = False
            trade_r = []
    win_rate = np.mean([r > 0 for r in trade_rets]) if trade_rets else np.nan

    # Correlation with TSMOM returns
    tsmom_ret = ts.shift(1).fillna(0) * ret
    common_t  = bar_r.index.intersection(tsmom_ret.index)
    corr_t    = (bar_r.loc[common_t].corr(tsmom_ret.loc[common_t])
                 if len(common_t) >= 30 else np.nan)

    # Signal overlap: what % of breakout days is TSMOM also long?
    bk_on = p > 0
    ts_on = ts > 0
    overlap = (bk_on & ts_on).sum() / max(bk_on.sum(), 1)

    return {
        "sharpe": sharpe, "maxdd": maxdd, "trades_yr": trades_yr,
        "win_rate": win_rate, "corr_tsmom": corr_t, "overlap_tsmom": overlap,
        "n_days": len(bar_r.dropna()),
        "cum_ret": cum_r, "bar_ret": bar_r
    }


# ─── WALK-FORWARD ─────────────────────────────────────────────────────────────

def run_walk_forward(close: pd.Series, position: pd.Series,
                     tsmom_daily: pd.Series,
                     windows: list[dict]) -> list[dict]:
    """
    Evaluate strategy Sharpe on each OOS test window.
    'Train' step: observe BB_width distribution (no parameters to fit in WF sense;
    the rolling 20th percentile is already computed from look-back data only).
    """
    results = []
    for w in windows:
        res = backtest_asset(close, position, tsmom_daily,
                             start=w["test_start"], end=w["test_end"])
        results.append({
            "name": w["name"],
            "test_period": f"{w['test_start'][:7]} → {w['test_end'][:7]}",
            "sharpe": res["sharpe"], "maxdd": res["maxdd"],
            "trades_yr": res["trades_yr"], "win_rate": res["win_rate"],
            "cum_ret": res["cum_ret"]
        })
    return results


# ─── FIGURE ──────────────────────────────────────────────────────────────────

def make_figure(asset_results: dict, wf_results: dict,
                close_dict: dict, bb_dict: dict,
                squeeze_dict: dict, position_dict: dict,
                tsmom_dict: dict) -> None:

    fig = plt.figure(figsize=(20, 14))
    fig.suptitle(
        "Volatility Squeeze Breakout — Strategy C Candidate\n"
        f"BB(20,2) squeeze < {SQ_PCT}th pct ({SQ_WINDOW}d)  |  Hold {HOLD_DAYS} days  |  Long-only",
        fontsize=12, fontweight="bold", y=0.998
    )
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.50, wspace=0.35)

    colors = {"BTC": "#2166ac", "ETH": "#4dac26", "SOL": "#d73027"}

    # ── Panel 1: BTC price + BB bands + squeeze markers ──────────────────────
    ax1 = fig.add_subplot(gs[0, :2])
    btc_close = close_dict.get("BTC", pd.Series(dtype=float))
    if len(btc_close) > 0:
        btc_bb   = bb_dict.get("BTC", pd.DataFrame())
        btc_sq   = squeeze_dict.get("BTC", pd.Series(dtype=float))
        btc_pos  = position_dict.get("BTC", pd.Series(dtype=float))
        # Show 2022-2026 only
        mask = btc_close.index >= pd.Timestamp("2022-01-01", tz="UTC")
        c_  = btc_close[mask]
        bb_ = btc_bb.reindex(c_.index) if len(btc_bb) > 0 else pd.DataFrame()
        sq_ = btc_sq.reindex(c_.index) if len(btc_sq) > 0 else pd.Series(dtype=float)
        p_  = btc_pos.reindex(c_.index).fillna(0) if len(btc_pos) > 0 else pd.Series(dtype=float)

        ax1.semilogy(c_.index, c_.values, color="black", lw=1, label="BTC close")
        if len(bb_) > 0 and "upper" in bb_.columns:
            ax1.semilogy(bb_.index, bb_["upper"].values, color="#4393c3",
                         lw=0.8, ls="--", alpha=0.7, label="BB upper/lower")
            ax1.semilogy(bb_.index, bb_["lower"].values, color="#4393c3",
                         lw=0.8, ls="--", alpha=0.7)
        # Shade position periods
        if len(p_) > 0:
            ax1.fill_between(p_.index, c_.min(), c_.max(),
                             where=p_.values > 0, color="#1a9850", alpha=0.15,
                             label="Signal ON (hold 10d)")
        # Mark squeeze periods
        if len(sq_) > 0:
            sq_mask = sq_ == 1
            ax1.scatter(sq_.index[sq_mask],
                        c_.reindex(sq_.index[sq_mask]).values,
                        color="orange", s=8, zorder=5, alpha=0.6, label="Squeeze day")
    ax1.set_title("BTC: Price + BB Bands + Squeeze Markers (2022→2026)", fontsize=10)
    ax1.set_ylabel("Price (log)"); ax1.legend(fontsize=8, loc="upper left"); ax1.grid(alpha=0.3)

    # ── Panel 2: BB width + squeeze threshold ─────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 2])
    if len(btc_close) > 0 and len(btc_bb) > 0:
        mask = btc_close.index >= pd.Timestamp("2022-01-01", tz="UTC")
        bw   = bb_dict["BTC"]["bb_width"].reindex(btc_close[mask].index)
        thr  = bw.rolling(SQ_WINDOW, min_periods=SQ_WINDOW//2).quantile(SQ_PCT / 100)
        ax2.plot(bw.index, bw.values, color="#888888", lw=1, label="BB width")
        ax2.plot(thr.index, thr.values, color="#d73027", lw=1.5, ls="--",
                 label=f"{SQ_PCT}th pct threshold")
        ax2.fill_between(bw.index, thr.values, bw.values,
                         where=bw.values < thr.values, color="orange", alpha=0.4,
                         label="Squeeze")
    ax2.set_title("BTC BB Width + Squeeze Threshold", fontsize=10)
    ax2.set_ylabel("BB width (normalized)"); ax2.legend(fontsize=8); ax2.grid(alpha=0.3)
    ax2.xaxis.set_major_locator(plt.MaxNLocator(4))

    # ── Panels 3-5: Equity curves per asset ───────────────────────────────────
    for j, asset in enumerate(["BTC", "ETH", "SOL"]):
        ax = fig.add_subplot(gs[1, j])
        res = asset_results.get(asset, {})
        if "cum_ret" in res and len(res["cum_ret"]) > 0:
            cum = res["cum_ret"]
            ax.plot(cum.index, cum.values * 100, color=colors[asset], lw=2,
                    label=f"{asset} breakout  Sharpe={res['sharpe']:.2f}")
            # TSMOM reference
            ts = tsmom_dict.get(asset, pd.Series(dtype=float))
            c_ = close_dict.get(asset, pd.Series(dtype=float))
            if len(ts) > 0 and len(c_) > 0:
                lr_  = np.log(c_ / c_.shift(1)).fillna(0)
                ts_r = ts.shift(1).fillna(0) * lr_
                ts_cum = ts_r.cumsum()
                ax.plot(ts_cum.index, ts_cum.values * 100, color="gray",
                        lw=1, ls="--", alpha=0.7, label="TSMOM ref")
            ax.axhline(0, color="black", lw=0.5)
        ax.set_title(f"{asset} Equity Curve (log ret %)\n"
                     f"Sharpe={res.get('sharpe', np.nan):.2f}  "
                     f"MaxDD={res.get('maxdd', 0)*100:.1f}%  "
                     f"t/yr={res.get('trades_yr', 0):.0f}",
                     fontsize=9)
        ax.set_ylabel("Cum log return (%)"); ax.legend(fontsize=7); ax.grid(alpha=0.3)
        ax.xaxis.set_major_locator(plt.MaxNLocator(4))

    # ── Panel 6: Walk-forward Sharpe bars ─────────────────────────────────────
    ax = fig.add_subplot(gs[2, 0])
    wf_names = [w["name"] for w in WF_WINDOWS]
    x = np.arange(len(wf_names))
    width = 0.25
    for k, asset in enumerate(["BTC", "ETH", "SOL"]):
        wf_sh = [wf_results.get(asset, [{}]*3)[i].get("sharpe", np.nan)
                 for i in range(len(WF_WINDOWS))]
        ax.bar(x + k * width, wf_sh, width=width, label=asset,
               color=colors[asset], edgecolor="white")
    ax.axhline(0, color="black", lw=0.8)
    ax.axhline(0.8, color="#d73027", ls="--", lw=1, label="Target (0.8)")
    ax.set_xticks(x + width)
    ax.set_xticklabels([f"{w['name']}\n({w['test_start'][:4]})" for w in WF_WINDOWS])
    ax.set_title("Walk-Forward OOS Sharpe", fontsize=10)
    ax.set_ylabel("Sharpe"); ax.legend(fontsize=8); ax.grid(alpha=0.3, axis="y")

    # ── Panel 7: Signal overlap with TSMOM ────────────────────────────────────
    ax = fig.add_subplot(gs[2, 1])
    assets = list(asset_results.keys())
    corrs  = [asset_results[a].get("corr_tsmom", np.nan) for a in assets]
    ovlps  = [asset_results[a].get("overlap_tsmom", np.nan) for a in assets]
    x = np.arange(len(assets))
    ax.bar(x - 0.2, corrs, width=0.35, label="corr(returns, TSMOM_ret)",
           color=[colors[a] for a in assets], edgecolor="white")
    ax.bar(x + 0.2, ovlps, width=0.35, label="overlap(position, TSMOM>0)",
           color=[colors[a] for a in assets], alpha=0.4, edgecolor="black")
    ax.axhline(0.50, color="#d73027", ls="--", lw=1, label="corr limit 0.50")
    ax.axhline(0, color="black", lw=0.5)
    ax.set_xticks(x); ax.set_xticklabels(assets)
    ax.set_title("Correlation & Overlap with TSMOM", fontsize=10)
    ax.set_ylabel("Value"); ax.legend(fontsize=7); ax.grid(alpha=0.3, axis="y")

    # ── Panel 8: Summary table ────────────────────────────────────────────────
    ax = fig.add_subplot(gs[2, 2])
    ax.axis("off")
    lines = ["═══ RESULTS SUMMARY ═══\n"]
    lines.append(f"{'Asset':>5} {'Sharpe':>7} {'MaxDD':>8} {'t/yr':>6} "
                 f"{'WinR':>6} {'corr':>6}")
    lines.append("─" * 44)
    for asset in ["BTC", "ETH", "SOL"]:
        r = asset_results.get(asset, {})
        if r:
            lines.append(
                f"{asset:>5} {r.get('sharpe', np.nan):>7.3f} "
                f"{r.get('maxdd', 0)*100:>7.1f}% {r.get('trades_yr', 0):>6.0f} "
                f"{r.get('win_rate', np.nan):>6.1%} {r.get('corr_tsmom', np.nan):>6.3f}"
            )
    lines.append("\nWalk-Forward OOS Sharpe:")
    for asset in ["BTC", "ETH", "SOL"]:
        wf = wf_results.get(asset, [])
        if wf:
            wf_sh = [f"{w.get('sharpe', np.nan):.2f}" for w in wf]
            lines.append(f"  {asset}: {' | '.join(wf_sh)}")
    lines.append(f"\nVERDICT:")
    all_sharpes = [asset_results.get(a, {}).get("sharpe", -99) for a in ["BTC","ETH","SOL"]]
    all_corrs   = [abs(asset_results.get(a, {}).get("corr_tsmom", 99)) for a in ["BTC","ETH","SOL"]]
    best_sh  = max(all_sharpes)
    best_corr = min(all_corrs)
    wf_positive = {a: sum(1 for w in wf_results.get(a,[]) if w.get("sharpe",0)>0)
                   for a in ["BTC","ETH","SOL"]}
    if best_sh > 0.8 and best_corr < 0.50 and max(wf_positive.values()) >= 2:
        v = "PROMISING"
    elif best_sh > 0.5 and best_corr < 0.60:
        v = "WEAK"
    else:
        v = "SKIP"
    lines.append(f"  >>> {v}")
    lines.append(f"  Best Sharpe: {best_sh:.3f}")
    lines.append(f"  Best corr(TSMOM): {best_corr:.3f}")

    ax.text(0.03, 0.97, "\n".join(lines), transform=ax.transAxes,
            va="top", ha="left", fontsize=8.5, fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#f0f4ff",
                      edgecolor="#2166ac"))

    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "feasibility_results.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n  Figure → {out_path}")
    plt.close()


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("VOLATILITY SQUEEZE BREAKOUT — Strategy C Candidate")
    print(f"BB(20,2) squeeze < {SQ_PCT}th pct ({SQ_WINDOW}d lookback)  |  Hold {HOLD_DAYS}d")
    print(f"Assets: {', '.join(ASSETS.keys())}  |  Daily (yfinance)  |  2020-2026")
    print("=" * 70)

    # ── 1. Fetch data ─────────────────────────────────────────────────────────
    print("\n[1/4] Fetching OHLCV from yfinance…")
    close_dict: dict[str, pd.Series] = {}
    full_dict:  dict[str, pd.DataFrame] = {}
    for name, ticker in ASSETS.items():
        print(f"  {name} ({ticker})… ", end="", flush=True)
        df = fetch_ohlcv(ticker)
        if df.empty:
            print("FAILED")
        else:
            full_dict[name]  = df
            close_dict[name] = df["close"]
            print(f"OK ({len(df)} days, "
                  f"{df.index[0].date()} → {df.index[-1].date()})")

    if "BTC" not in close_dict:
        print("ERROR: BTC data unavailable."); return

    # ── 2. Build signals ──────────────────────────────────────────────────────
    print("\n[2/4] Computing BB squeeze signals…")
    bb_dict       = {}
    squeeze_dict  = {}
    breakout_dict = {}
    position_dict = {}
    tsmom_dict    = {}

    for asset, close in close_dict.items():
        bb     = compute_bollinger(close, BB_PERIOD, BB_STD)
        sq     = detect_squeeze(bb["bb_width"], SQ_WINDOW, SQ_PCT)
        bk_up  = compute_breakout_signal(close, bb, sq)
        pos    = apply_hold(bk_up, HOLD_DAYS)
        ts     = compute_tsmom(close)

        bb_dict[asset]       = bb
        squeeze_dict[asset]  = sq
        breakout_dict[asset] = bk_up
        position_dict[asset] = pos
        tsmom_dict[asset]    = ts

        n_sq  = sq.sum()
        n_bk  = bk_up.sum()
        n_pos = (pos > 0).sum()
        pct_active = (pos > 0).mean()
        print(f"  {asset}: squeeze_days={n_sq:.0f}  "
              f"breakouts={n_bk:.0f}  "
              f"position_days={n_pos:.0f} ({pct_active:.1%} active)")

    # Overlap of signal with TSMOM
    for asset in close_dict:
        ts = tsmom_dict[asset]
        pos = position_dict[asset]
        common = pos.index.intersection(ts.index)
        if len(common) > 100:
            bk_on = (pos.reindex(common) > 0)
            ts_on = (ts.reindex(common) > 0)
            overlap = (bk_on & ts_on).sum() / max(bk_on.sum(), 1)
            print(f"  {asset}: {overlap:.1%} of breakout days TSMOM also long")

    # ── 3. Backtest all assets ────────────────────────────────────────────────
    print("\n[3/4] Backtesting (2020-2026)…")
    asset_results = {}
    for asset, close in close_dict.items():
        pos = position_dict[asset]
        ts  = tsmom_dict[asset]
        res = backtest_asset(close, pos, ts)
        asset_results[asset] = res
        print(f"\n  {asset}:")
        print(f"    Sharpe:      {res['sharpe']:+.3f}")
        print(f"    MaxDD:       {res['maxdd']*100:.1f}%")
        print(f"    Trades/yr:   {res['trades_yr']:.0f}  "
              f"(cost ≈ {res['trades_yr'] * COST_RT * 100:.2f}%/yr)")
        print(f"    Win rate:    {res.get('win_rate', np.nan):.1%}")
        print(f"    corr(TSMOM): {res['corr_tsmom']:+.3f}")
        print(f"    overlap:     {res.get('overlap_tsmom', np.nan):.1%}")

    # ── 4. Walk-forward ───────────────────────────────────────────────────────
    print("\n[4/4] Walk-forward validation…")
    wf_results = {}
    for asset, close in close_dict.items():
        pos = position_dict[asset]
        ts  = tsmom_dict[asset]
        wf  = run_walk_forward(close, pos, ts, WF_WINDOWS)
        wf_results[asset] = wf
        print(f"\n  {asset}:")
        for w in wf:
            print(f"    {w['name']} ({w['test_period']}): "
                  f"Sharpe={w['sharpe']:+.3f}  "
                  f"MaxDD={w.get('maxdd',0)*100:.1f}%  "
                  f"t/yr={w['trades_yr']:.0f}")
        pos_count = sum(1 for w in wf if w["sharpe"] > 0)
        print(f"    → Positive in {pos_count}/3 WF windows")

    # Figure
    make_figure(asset_results, wf_results, close_dict, bb_dict,
                squeeze_dict, position_dict, tsmom_dict)

    # ── VERDICT ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)

    all_sharpes = [asset_results.get(a, {}).get("sharpe", -99)
                   for a in ["BTC", "ETH", "SOL"] if a in asset_results]
    all_corrs   = [abs(asset_results.get(a, {}).get("corr_tsmom", 99))
                   for a in ["BTC", "ETH", "SOL"] if a in asset_results]
    best_sh   = max(all_sharpes) if all_sharpes else np.nan
    best_corr = min(all_corrs)   if all_corrs  else np.nan

    wf_positive = {}
    for asset in close_dict:
        wf_positive[asset] = sum(1 for w in wf_results.get(asset, [])
                                 if w.get("sharpe", 0) > 0)

    print(f"  Best asset Sharpe:    {best_sh:+.3f}  (target > 0.8)")
    print(f"  Min corr(TSMOM):      {best_corr:+.3f}  (target < 0.50)")
    print(f"  WF positive windows:  {wf_positive}")
    print()

    for asset in close_dict:
        r = asset_results[asset]
        print(f"  {asset}: Sharpe={r['sharpe']:+.3f}  "
              f"corr={r['corr_tsmom']:+.3f}  "
              f"WF={wf_positive.get(asset,0)}/3")

    print()
    max_wf = max(wf_positive.values()) if wf_positive else 0
    if best_sh > 0.8 and best_corr < 0.50 and max_wf >= 2:
        verdict = "PROMISING — Sharpe > 0.8, low TSMOM corr, consistent walk-forward"
        action  = "Accept as Strategy C. Test A+B+C with best asset."
    elif best_sh > 0.5 and best_corr < 0.60:
        verdict = "WEAK — some signal but below PROMISING threshold"
        action  = "Consider as TSMOM overlay (filter entry). Not as standalone C."
    elif best_sh > 0.5 and best_corr >= 0.60:
        verdict = "SKIP — corr(TSMOM) too high; no diversification benefit"
        action  = "Signal too correlated with momentum to add portfolio value."
    else:
        verdict = "SKIP — Sharpe too low across all assets"
        action  = "Volatility squeeze breakout not viable as Strategy C."

    print(f"  >>> {verdict}")
    print(f"  Next step: {action}")
    print()
    print("  Key diagnostic: does squeeze → breakout have predictive power,")
    print("  or is it just a lagged momentum signal (correlated with TSMOM)?")
    print("  Answer: see corr(TSMOM) in results above.")


if __name__ == "__main__":
    main()
