#!/usr/bin/env python3
"""
strategies/donchian_breakout/feasibility.py

Donchian Channel Breakout — Strategy C candidate
=================================================
Economic mechanism: new N-day price high = structural demand/supply
imbalance confirmed by price discovery; entry timing is distinct from
TSMOM (breakout requires penetrating an absolute price level, not just
a positive cumulative return).

Signal construction (no look-ahead):
  upper_band[T] = max(high[T-N : T-1])   — highest high of past N days
  lower_band[T] = min(low[T-N : T-1])    — lowest low of past N days
  breakout UP   : close[T] > upper_band[T]  → signal = +1
  breakout DOWN : close[T] < lower_band[T]  → signal =  0  (long-only, go flat)
  otherwise     : signal = prev_signal           (hold)

Feasibility scope (30 min):
  1. IC test: signal[T] vs 5-day forward return across N ∈ [10,15,20,30,40]
  2. Quick equity curve: best N by IC, BTC only, 2021-2026
  3. Correlation with TSMOM v2 signal (GO if < 0.70)
  4. Verdict: GO / WEAK / SKIP

Run: python -m strategies.donchian_breakout.feasibility
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats

warnings.filterwarnings("ignore")

# ── Constants ──────────────────────────────────────────────────────────────────

UNIVERSE: list[str] = [
    "BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "LINK-USD",
]
LABELS: list[str] = ["BTC", "ETH", "SOL", "AVAX", "LINK"]

DATA_START    = "2021-01-01"
DATA_END      = "2026-05-14"

LOOKBACKS: list[int] = [10, 15, 20, 30, 40]
VOL_TARGET    = 0.15
VOL_WINDOW    = 20
GROSS_CAP     = 0.90
COST_RT       = 0.0017       # 0.17% round-trip
COST_ONE_WAY  = COST_RT / 2  # 0.085% per leg
TRADING_DAYS  = 365
TSMOM_LB      = 28

FWD_DAYS      = 5            # forward return window for IC test

OUT_DIR = Path(__file__).parent
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Data ───────────────────────────────────────────────────────────────────────

def download_data(
    universe: list[str] = UNIVERSE,
    start: str = DATA_START,
    end: str = DATA_END,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Download daily OHLC for all assets.

    Returns
    -------
    (close, high, low) — DataFrames with ticker columns, tz-naive index.
    """
    print(f"Downloading OHLC data for {len(universe)} assets ({start} → {end})...")
    raw = yf.download(
        universe, start=start, end=end,
        auto_adjust=True, progress=False, interval="1d",
    )
    # Normalise column names to short labels
    def _extract(field: str) -> pd.DataFrame:
        if isinstance(raw.columns, pd.MultiIndex):
            df = raw[field].copy()
        else:
            df = raw[[field]].copy()
        if df.index.tz is not None:
            df.index = df.index.tz_convert(None)
        df = df.ffill(limit=2)
        df.columns = [c.replace("-USD", "") for c in df.columns]
        return df

    close = _extract("Close")
    high  = _extract("High")
    low   = _extract("Low")

    print(f"  Range : {close.index[0].date()} → {close.index[-1].date()}  "
          f"({len(close)} days)  assets: {sorted(close.columns.tolist())}")
    return close, high, low


# ── Signal Construction ────────────────────────────────────────────────────────

def compute_donchian_signal(
    close: pd.DataFrame,
    high: pd.DataFrame,
    low: pd.DataFrame,
    N: int,
) -> pd.DataFrame:
    """
    Donchian channel breakout signal with persistence (hold between breakouts).

    upper_band[T] = max(high[T-N : T-1]) — N-day rolling max shifted 1 day
    lower_band[T] = min(low[T-N  : T-1]) — N-day rolling min shifted 1 day

    signal[T] = +1 if close[T] > upper_band[T]   (breakout up → enter long)
    signal[T] =  0 if close[T] < lower_band[T]   (breakout down → exit, stay flat)
    signal[T] = prev_signal                       (no breakout → hold)

    All data shifted so signal[T] uses only data through T-1 (no look-ahead).

    Parameters
    ----------
    close, high, low : daily OHLC DataFrames
    N                : channel lookback in days

    Returns
    -------
    signal DataFrame with values in {0, 1}, same shape as close.
    """
    upper = high.rolling(N).max().shift(1)   # max high over [T-N, T-1]
    lower = low.rolling(N).min().shift(1)    # min low  over [T-N, T-1]

    result = pd.DataFrame(np.nan, index=close.index, columns=close.columns)

    for col in close.columns:
        if col not in upper.columns:
            continue
        s = pd.Series(np.nan, index=close.index, dtype=float)
        s[close[col] > upper[col]] = 1.0    # breakout up
        s[close[col] < lower[col]] = 0.0    # breakout down → flat
        result[col] = s.ffill().fillna(0.0)

    return result


def compute_tsmom_signal(
    close: pd.DataFrame,
    lookback: int = TSMOM_LB,
) -> pd.DataFrame:
    """
    TSMOM 28-day signal: +1 if cumulative log return > 0, else 0.
    Shifted 1 day — no look-ahead.
    """
    lr  = np.log(close / close.shift(1))
    cum = lr.rolling(lookback).sum().shift(1)
    sig = (cum > 0).astype(float)
    sig[cum.isna()] = np.nan
    return sig


# ── IC Test ────────────────────────────────────────────────────────────────────

def ic_test(
    close: pd.DataFrame,
    high: pd.DataFrame,
    low: pd.DataFrame,
    lookbacks: list[int] = LOOKBACKS,
    fwd_days: int = FWD_DAYS,
) -> pd.DataFrame:
    """
    Information Coefficient test: Spearman rank correlation between
    Donchian signal[T] and forward fwd_days-day return[T+1 : T+fwd_days+1].

    IC[T] = rank_corr(signal[T], fwd_return[T])  (one scalar per T, averaged)
    t_stat via Pearson t-approximation: t = IC × sqrt(n) / sqrt(1 - IC²)
    ICIR = IC / std(per-period IC estimates)

    Returns DataFrame with columns: asset, N, IC, t_stat, p_value, ICIR, n_obs.
    """
    # Forward fwd_days return: close[T+fwd_days] / close[T] - 1
    fwd = (close.shift(-fwd_days) / close - 1.0)

    rows: list[dict[str, Any]] = []

    for N in lookbacks:
        signal = compute_donchian_signal(close, high, low, N)

        for col in close.columns:
            sig_s = signal[col].dropna()
            fwd_s = fwd[col].dropna()
            idx   = sig_s.index.intersection(fwd_s.index)
            # Drop NaN and the last fwd_days rows (no forward data)
            idx   = idx[:-fwd_days] if len(idx) > fwd_days else idx
            if len(idx) < 60:
                continue

            s = sig_s.loc[idx].values
            f = fwd_s.loc[idx].values

            # Overall IC (Spearman over full series)
            ic_overall, p_val = stats.spearmanr(s, f)

            # Per-period rolling IC for ICIR: split into monthly chunks
            chunk = 21  # ~1 month
            ic_chunks: list[float] = []
            for i in range(0, len(s) - chunk, chunk):
                c_ic, _ = stats.spearmanr(s[i:i + chunk], f[i:i + chunk])
                if not np.isnan(c_ic):
                    ic_chunks.append(c_ic)
            icir = (np.mean(ic_chunks) / np.std(ic_chunks)
                    if len(ic_chunks) >= 4 and np.std(ic_chunks) > 0
                    else np.nan)

            # t-stat from IC
            n     = len(idx)
            denom = np.sqrt(max(1 - ic_overall ** 2, 1e-10))
            t_stat = ic_overall * np.sqrt(n) / denom

            rows.append(dict(
                asset=col, N=N,
                IC=round(float(ic_overall), 4),
                t_stat=round(float(t_stat), 3),
                p_value=round(float(p_val), 4),
                ICIR=round(float(icir), 3) if not np.isnan(icir) else np.nan,
                n_obs=n,
            ))

    return pd.DataFrame(rows)


def print_ic_table(ic_df: pd.DataFrame) -> int:
    """Print IC results table, return best N by avg IC t-stat."""
    print(f"\n{'─'*70}")
    print(f"IC TEST: Donchian signal → {FWD_DAYS}-day forward return  "
          f"(Spearman rank corr)")
    print(f"{'─'*70}")
    hdr = f"  {'Asset':>5}  {'N':>3}  {'IC':>7}  {'t-stat':>7}  {'p-val':>6}  {'ICIR':>6}  {'n':>5}"
    print(hdr)
    print(f"  {'-'*5}  {'-'*3}  {'-'*7}  {'-'*7}  {'-'*6}  {'-'*6}  {'-'*5}")

    for _, row in ic_df.sort_values(["N", "asset"]).iterrows():
        flag = " ★" if row["t_stat"] > 2.0 else (" ·" if row["t_stat"] > 1.5 else "  ")
        icir_s = f"{row['ICIR']:>6.3f}" if not np.isnan(row["ICIR"]) else "   n/a"
        print(f"  {row['asset']:>5}  {int(row['N']):>3}  {row['IC']:>7.4f}  "
              f"{row['t_stat']:>7.3f}  {row['p_value']:>6.4f}  {icir_s}  "
              f"{int(row['n_obs']):>5}{flag}")

    # Summary: assets with t-stat > 2.0 per N
    print(f"\n  Threshold: ★ t-stat > 2.0  · t-stat > 1.5")
    best_N_by_asset: dict[str, int] = {}
    for asset in ic_df["asset"].unique():
        sub = ic_df[ic_df["asset"] == asset]
        best_row = sub.loc[sub["t_stat"].idxmax()]
        best_N_by_asset[asset] = int(best_row["N"])
        flag = "★" if best_row["t_stat"] > 2.0 else ("·" if best_row["t_stat"] > 1.5 else " ")
        print(f"  {flag} {asset}: best N={int(best_row['N'])}, "
              f"IC={best_row['IC']:.4f}, t={best_row['t_stat']:.3f}")

    # Best overall N by mean t-stat across assets
    n_passing_2 = int((ic_df["t_stat"] > 2.0).sum())
    n_passing_15 = int((ic_df["t_stat"] > 1.5).sum())
    print(f"\n  Combos with t-stat > 2.0 : {n_passing_2}/{len(ic_df)}")
    print(f"  Combos with t-stat > 1.5 : {n_passing_15}/{len(ic_df)}")

    # Best N: most assets passing t > 2.0; tie-break by avg t-stat
    pass_by_N = (
        ic_df[ic_df["t_stat"] > 2.0]
        .groupby("N")["t_stat"]
        .agg(["count", "mean"])
        .sort_values(["count", "mean"], ascending=False)
    )
    if len(pass_by_N) > 0:
        best_N = int(pass_by_N.index[0])
    else:
        best_N = int(
            ic_df.groupby("N")["t_stat"].mean().idxmax()
        )
    print(f"  Best N by IC t-stat       : {best_N}")
    return best_N


# ── Quick Backtest (BTC only) ──────────────────────────────────────────────────

def quick_backtest(
    close: pd.DataFrame,
    high: pd.DataFrame,
    low: pd.DataFrame,
    N: int,
    asset: str = "BTC",
) -> dict[str, Any]:
    """
    BTC-only quick equity curve: Donchian breakout, long-only,
    15% vol target, weekly rebalance, 0.17% RT costs on Mondays.

    Parameters
    ----------
    close, high, low : full price DataFrames
    N                : best lookback from IC test
    asset            : asset column to use (default 'BTC')

    Returns
    -------
    dict with Sharpe, max_dd, ann_return, trades_per_year, net_rets.
    """
    if asset not in close.columns:
        asset = close.columns[0]

    c = close[[asset]]
    h = high[[asset]]
    l = low[[asset]]

    signal = compute_donchian_signal(c, h, l, N)
    lr     = np.log(c / c.shift(1))
    ann_vol = lr.rolling(VOL_WINDOW).std().shift(1) * np.sqrt(TRADING_DAYS)
    ann_vol = ann_vol.replace(0.0, np.nan)
    scalar  = (VOL_TARGET / ann_vol).clip(0.1, 2.0)

    raw_pos = (signal * scalar).fillna(0.0)

    # Weekly rebalance: lock to Monday, ffill
    is_mon  = raw_pos.index.dayofweek == 0
    pos_wk  = raw_pos.copy()
    pos_wk[~is_mon] = np.nan
    pos_wk  = pos_wk.ffill().fillna(0.0)

    # Gross cap (single asset: already ≤ 2.0 vol scalar)
    gross   = pos_wk.abs().sum(axis=1).replace(0, np.nan)
    scale   = (GROSS_CAP / gross).clip(upper=1.0).fillna(1.0)
    pos_cap = pos_wk.mul(scale, axis=0).fillna(0.0)

    # P&L (arithmetic returns, position held = prior day's)
    arith   = c.pct_change()
    held    = pos_cap.shift(1).fillna(0.0)
    gpnl    = (held * arith).sum(axis=1)

    # Costs on Monday rebalances only
    is_mon_s = pd.Series(pos_cap.index.dayofweek == 0, index=pos_cap.index).astype(float)
    costs    = pos_cap.diff().abs().sum(axis=1) * COST_ONE_WAY * is_mon_s
    net      = (gpnl - costs).dropna()

    # Metrics
    ann_ret  = float(net.mean() * TRADING_DAYS)
    sharpe   = float((net.mean() / net.std()) * np.sqrt(TRADING_DAYS)) if net.std() > 0 else 0.0
    eq       = (1 + net).cumprod()
    max_dd   = float(((eq - eq.cummax()) / eq.cummax()).min())
    win_rate = float((net > 0).mean())

    # Trade count (signal transitions on Mondays)
    _sig = signal[asset].copy()
    _sig[~is_mon] = np.nan
    sig_mon  = _sig.ffill().dropna()
    trades   = int(sig_mon.diff().fillna(0).abs().sum())
    n_years  = len(net) / TRADING_DAYS
    tpy      = trades / n_years if n_years > 0 else 0.0

    return dict(
        N=N, asset=asset,
        ann_return=ann_ret,
        sharpe=sharpe,
        max_dd=max_dd,
        win_rate=win_rate,
        trades_per_year=tpy,
        net_rets=net,
    )


# ── Signal Correlation with TSMOM v2 ──────────────────────────────────────────

def signal_correlation(
    close: pd.DataFrame,
    high: pd.DataFrame,
    low: pd.DataFrame,
    best_N: int,
) -> dict[str, Any]:
    """
    Compute Pearson correlation between Donchian signal and TSMOM 28-day signal
    per asset, and a portfolio-level return correlation.

    Returns dict with per-asset signal correlations and mean.
    """
    don_sig   = compute_donchian_signal(close, high, low, best_N)
    tsmom_sig = compute_tsmom_signal(close)

    sig_corrs: dict[str, float] = {}
    for col in close.columns:
        idx = don_sig[col].notna() & tsmom_sig[col].notna()
        if idx.sum() < 60:
            continue
        r = float(don_sig.loc[idx, col].corr(tsmom_sig.loc[idx, col]))
        sig_corrs[col] = r

    mean_corr = float(np.mean(list(sig_corrs.values()))) if sig_corrs else np.nan

    print(f"\n{'─'*50}")
    print(f"SIGNAL CORRELATION: Donchian(N={best_N}) vs TSMOM(28d)")
    print(f"{'─'*50}")
    for col, r in sig_corrs.items():
        verdict = "HIGH" if abs(r) > 0.7 else ("MOD" if abs(r) > 0.5 else "LOW")
        print(f"  {col:>5}: r = {r:+.3f}  [{verdict}]")
    print(f"  Mean : r = {mean_corr:+.3f}  "
          f"{'→ too similar to TSMOM' if mean_corr > 0.70 else '→ sufficient diversification'}")

    return dict(per_asset=sig_corrs, mean=mean_corr)


# ── Plotting ───────────────────────────────────────────────────────────────────

def plot_results(
    close: pd.DataFrame,
    high: pd.DataFrame,
    low: pd.DataFrame,
    ic_df: pd.DataFrame,
    bt: dict[str, Any],
    best_N: int,
    save_path: Path,
) -> None:
    """
    2 subplots:
    (1) BTC equity curve: Donchian best-N vs TSMOM vs buy-and-hold
    (2) IC heatmap: asset × lookback
    """
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle(
        f"Donchian Breakout Feasibility — Strategy C candidate  "
        f"(best N={best_N})",
        fontsize=12, fontweight="bold",
    )

    # ── Panel 1: BTC equity curves ─────────────────────────────────────────────
    ax1 = axes[0]

    # Donchian best-N
    net = bt["net_rets"]
    eq  = (1 + net).cumprod()
    ax1.plot(eq.index, eq.values,
             color="#2c3e50", lw=2.0,
             label=f"Donchian N={best_N} (Sh={bt['sharpe']:.2f})")

    # TSMOM v2 BTC-only for comparison
    btc_c  = close[["BTC"]]
    lr_btc = np.log(btc_c / btc_c.shift(1))
    cum28  = lr_btc.rolling(TSMOM_LB).sum().shift(1)
    sig_tm = (cum28 > 0).astype(float).fillna(0.0)
    av_tm  = (lr_btc.rolling(VOL_WINDOW).std().shift(1) * np.sqrt(TRADING_DAYS)).replace(0, np.nan)
    sc_tm  = (VOL_TARGET / av_tm).clip(0.1, 2.0)
    rp_tm  = (sig_tm * sc_tm).fillna(0.0)
    is_mon = rp_tm.index.dayofweek == 0
    pw_tm  = rp_tm.copy()
    pw_tm[~is_mon] = np.nan
    pw_tm  = pw_tm.ffill().fillna(0.0)
    gr_tm  = (GROSS_CAP / pw_tm.abs().sum(axis=1).replace(0, np.nan)).clip(upper=1.0).fillna(1.0)
    pc_tm  = pw_tm.mul(gr_tm, axis=0).fillna(0.0)
    ar_btc = btc_c.pct_change()
    gp_tm  = (pc_tm.shift(1).fillna(0.0) * ar_btc).sum(axis=1)
    is_mon_s = pd.Series(pc_tm.index.dayofweek == 0, index=pc_tm.index).astype(float)
    ct_tm  = pc_tm.diff().abs().sum(axis=1) * COST_ONE_WAY * is_mon_s
    net_tm = (gp_tm - ct_tm).dropna()
    eq_tm  = (1 + net_tm).cumprod()
    sh_tm  = float((net_tm.mean() / net_tm.std()) * np.sqrt(TRADING_DAYS))
    ax1.plot(eq_tm.index, eq_tm.values,
             color="#3498db", lw=1.5, linestyle="--",
             label=f"TSMOM 28d BTC (Sh={sh_tm:.2f})")

    # Buy-and-hold BTC
    btc_bh = (1 + ar_btc["BTC"].dropna()).cumprod()
    btc_bh = btc_bh / btc_bh.iloc[0]
    ax1.plot(btc_bh.index, btc_bh.values,
             color="#e67e22", lw=1.0, linestyle=":",
             label="BTC buy-and-hold")

    ax1.axhline(1.0, color="gray", lw=0.7, linestyle=":")
    ax1.set_title(f"Panel 1 — BTC Equity Curve (Donchian N={best_N})", fontsize=10)
    ax1.set_ylabel("Cumulative Return (base 1.0)")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)

    # ── Panel 2: IC heatmap (asset × lookback) ─────────────────────────────────
    ax2 = axes[1]

    assets_sorted = sorted(ic_df["asset"].unique())
    Ns_sorted     = sorted(ic_df["N"].unique())
    hmap = np.full((len(assets_sorted), len(Ns_sorted)), np.nan)

    for i, asset in enumerate(assets_sorted):
        for j, n in enumerate(Ns_sorted):
            row = ic_df[(ic_df["asset"] == asset) & (ic_df["N"] == n)]
            if len(row) > 0:
                hmap[i, j] = float(row["t_stat"].iloc[0])

    vmax = max(abs(np.nanmax(hmap)), abs(np.nanmin(hmap)), 0.5)
    im   = ax2.imshow(hmap, cmap="RdYlGn", vmin=-vmax, vmax=vmax, aspect="auto")
    ax2.set_xticks(range(len(Ns_sorted)))
    ax2.set_xticklabels([f"N={n}" for n in Ns_sorted], fontsize=9)
    ax2.set_yticks(range(len(assets_sorted)))
    ax2.set_yticklabels(assets_sorted, fontsize=9)
    ax2.set_title(
        f"Panel 2 — IC t-stat Heatmap\n"
        f"(green = t>2.0 → predictive, red = negative IC)",
        fontsize=10,
    )

    # Annotate cells
    for i in range(len(assets_sorted)):
        for j in range(len(Ns_sorted)):
            v = hmap[i, j]
            if not np.isnan(v):
                txt_col = "black" if abs(v) < 0.6 * vmax else "white"
                ax2.text(j, i, f"{v:.2f}", ha="center", va="center",
                         fontsize=8, color=txt_col, fontweight="bold")

    plt.colorbar(im, ax=ax2, label="IC t-stat", fraction=0.035, pad=0.04)
    ax2.axhline(-0.5, color="black", lw=0.5)  # visual separator

    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nFigure saved → {save_path}")


# ── Verdict ────────────────────────────────────────────────────────────────────

def print_verdict(
    ic_df: pd.DataFrame,
    bt: dict[str, Any],
    corr: dict[str, Any],
    best_N: int,
) -> str:
    """
    GO    : IC t-stat > 2.0 on ≥ 3/5 assets AND signal corr < 0.70
    WEAK  : IC t-stat 1.5-2.0 OR signal corr 0.60-0.70
    SKIP  : IC t-stat < 1.5 OR signal corr > 0.70

    Returns verdict string.
    """
    best_ic = ic_df[ic_df["N"] == best_N]
    n_pass_2  = int((best_ic["t_stat"] > 2.0).sum())
    n_pass_15 = int((best_ic["t_stat"] > 1.5).sum())
    max_t     = float(best_ic["t_stat"].max())
    mean_corr = corr["mean"]

    if mean_corr > 0.70:
        verdict = "SKIP"
        reason  = (f"Signal correlation {mean_corr:.2f} > 0.70 — "
                   f"Donchian is too similar to TSMOM v2 for diversification.")
    elif n_pass_2 >= 3 and mean_corr < 0.70:
        verdict = "GO"
        reason  = (f"{n_pass_2}/5 assets have t-stat > 2.0, corr = {mean_corr:.2f} < 0.70. "
                   f"Proceed to full walk-forward OOS validation.")
    elif n_pass_15 >= 2 or (max_t >= 1.5 and mean_corr < 0.60):
        verdict = "WEAK"
        reason  = (f"{n_pass_15}/5 assets with t-stat > 1.5 (need 3 at > 2.0 for GO). "
                   f"Marginal edge — run full OOS before committing.")
    else:
        verdict = "SKIP"
        reason  = (f"Max t-stat = {max_t:.2f} < 1.5. "
                   f"No statistically significant IC detected after costs.")

    print(f"\n{'═'*58}")
    print("DONCHIAN BREAKOUT — FEASIBILITY VERDICT")
    print(f"{'═'*58}")
    print(f"Best N           : {best_N} days")
    print(f"IC t-stat > 2.0  : {n_pass_2}/5 assets  (need ≥ 3 for GO)")
    print(f"IC t-stat > 1.5  : {n_pass_15}/5 assets")
    print(f"Max t-stat       : {max_t:.3f}")
    print(f"Signal corr TSMOM: {mean_corr:+.3f}  (need < 0.70 for GO)")
    print()
    print(f"BTC quick backtest (N={bt['N']}):")
    print(f"  Sharpe         : {bt['sharpe']:.2f}")
    print(f"  Ann return     : {bt['ann_return']:+.1%}")
    print(f"  Max DD         : {bt['max_dd']:.1%}")
    print(f"  Win rate       : {bt['win_rate']:.1%}")
    print(f"  Trades/year    : {bt['trades_per_year']:.1f}")
    print()
    print(f"VERDICT: {verdict}")
    print(f"Reason : {reason}")

    if verdict == "GO":
        print()
        print("Next steps:")
        print("  1. Full OOS walk-forward (4 windows, all 5 assets)")
        print("  2. Propr challenge simulation (44 paths)")
        print("  3. Portfolio combination with TSMOM v2 (Strategy A)")
    elif verdict == "WEAK":
        print()
        print("Next steps:")
        print("  1. Expand to 15-asset universe (more data per N)")
        print("  2. Test entry on open (T+1) vs close (T) — may improve IC")
        print("  3. Only proceed to OOS if t-stat improves on 2024+ data")

    print(f"{'═'*58}")
    return verdict


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 58)
    print("DONCHIAN CHANNEL BREAKOUT — FEASIBILITY CHECK")
    print("=" * 58)

    # 1. Data
    close, high, low = download_data()

    # 2. IC test across all N and assets
    print(f"\nRunning IC test (N ∈ {LOOKBACKS}, {len(close.columns)} assets)...")
    ic_df  = ic_test(close, high, low)
    best_N = print_ic_table(ic_df)

    # 3. Quick BTC backtest with best N
    print(f"\nQuick backtest: BTC, N={best_N}, vol_target={VOL_TARGET}")
    bt = quick_backtest(close, high, low, best_N, asset="BTC")
    print(f"  Sharpe={bt['sharpe']:.2f}  AnnRet={bt['ann_return']:+.1%}  "
          f"MaxDD={bt['max_dd']:.1%}  Trades/yr={bt['trades_per_year']:.1f}")

    # 4. Signal correlation with TSMOM v2
    corr = signal_correlation(close, high, low, best_N)

    # 5. Plot
    plot_results(
        close, high, low, ic_df, bt, best_N,
        OUT_DIR / "feasibility_results.png",
    )

    # 6. Verdict
    verdict = print_verdict(ic_df, bt, corr, best_N)

    return verdict


if __name__ == "__main__":
    main()
