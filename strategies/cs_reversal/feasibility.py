"""
Cross-Sectional 1-Month Reversal — Feasibility Check
=====================================================
Economic mechanism: crypto LOSERS mean-revert (short side of CS momentum
lost money because losers bounced back — README §6.3). Goes LONG the
3 worst performers by 4-week return, equal vol-weighted.

Universe : BTC ETH SOL AVAX LINK DOGE ADA DOT LTC BCH (10 assets)
Data     : yfinance daily 2021-01-01 → 2026-05-14
Rebalance: weekly (Monday), long-only, gross cap 90%
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy import stats
from pathlib import Path

# ── Constants ────────────────────────────────────────────────────────────────
ASSETS      = ["BTC-USD","ETH-USD","SOL-USD","AVAX-USD","LINK-USD",
               "DOGE-USD","ADA-USD","DOT-USD","LTC-USD","BCH-USD"]
LABELS      = [a.replace("-USD","") for a in ASSETS]
START       = "2021-01-01"
END         = "2026-05-14"
LOOKBACK    = 20          # 4-week return
TSMOM_LB    = 28          # TSMOM signal lookback
LONG_N      = 3           # worst-N to go long
VOL_WINDOW  = 20
VOL_TARGET  = 0.15
GROSS_CAP   = 0.90
TRADING_DAYS = 365
COST_PER_LEG = 0.00085   # one-way

OUT_DIR = Path(__file__).parent
OUT_PNG = OUT_DIR / "feasibility_results.png"


# ── Data ─────────────────────────────────────────────────────────────────────
def download_data():
    print(f"\nDownloading price data for {len(ASSETS)} assets ({START} → {END})...")
    raw = yf.download(ASSETS, start=START, end=END, auto_adjust=True, progress=False)
    close = raw["Close"].dropna(how="all")
    # drop assets with >10% missing
    valid = close.columns[close.isna().mean() < 0.10]
    close = close[valid].ffill()
    labels = [c.replace("-USD","") for c in close.columns]
    print(f"  Range : {close.index[0].date()} → {close.index[-1].date()}"
          f"  ({len(close)} days)  assets: {labels}")
    return close


# ── Signals ──────────────────────────────────────────────────────────────────
def compute_cs_signal(close: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a DataFrame (same index as close) with position = 1/0.
    On each Monday: rank assets by 20-day lookback log return (ascending),
    top-3 losers get signal=1, rest=0.
    Signal is locked weekly (ffill between Mondays).
    """
    lr = np.log(close / close.shift(1))
    lookback_ret = lr.rolling(LOOKBACK).sum().shift(1)  # no look-ahead

    raw_signal = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    for date in close.index:
        if date.dayofweek != 0:  # only compute on Mondays
            continue
        row = lookback_ret.loc[date].dropna()
        if len(row) < LONG_N:
            continue
        worst = row.nsmallest(LONG_N).index
        raw_signal.loc[date, worst] = 1.0

    # Lock to Monday, ffill
    is_mon = raw_signal.index.dayofweek == 0
    signal = raw_signal.copy()
    signal[~is_mon] = np.nan
    signal = signal.ffill().fillna(0.0)
    return signal


def compute_tsmom_signal(close: pd.DataFrame) -> pd.DataFrame:
    """Binary TSMOM signal: 1 if 28-day log return > 0, else 0."""
    cum = np.log(close / close.shift(1)).rolling(TSMOM_LB).sum().shift(1)
    signal = (cum > 0).astype(float).fillna(0.0)
    is_mon = signal.index.dayofweek == 0
    sig_locked = signal.copy()
    sig_locked[~is_mon] = np.nan
    sig_locked = sig_locked.ffill().fillna(0.0)
    return sig_locked


# ── Positions ────────────────────────────────────────────────────────────────
def build_positions(close: pd.DataFrame, signal: pd.DataFrame) -> pd.DataFrame:
    """Vol-weighted positions from binary signal."""
    lr     = np.log(close / close.shift(1))
    ann_vol = lr.rolling(VOL_WINDOW).std().shift(1) * np.sqrt(TRADING_DAYS)
    ann_vol = ann_vol.replace(0.0, np.nan)
    scalar  = (VOL_TARGET / ann_vol).clip(0.1, 2.0)

    raw_pos = signal * scalar
    # Weekly lock already in signal; but vol scalar also needs locking
    is_mon  = raw_pos.index.dayofweek == 0
    pos     = raw_pos.copy()
    pos[~is_mon] = np.nan
    pos     = pos.ffill().fillna(0.0)

    # Gross cap
    gross   = pos.sum(axis=1).replace(0, np.nan)
    scale   = (GROSS_CAP / gross).clip(upper=1.0).fillna(1.0)
    pos_cap = pos.mul(scale, axis=0).fillna(0.0)
    return pos_cap


def compute_pnl(close: pd.DataFrame, positions: pd.DataFrame) -> pd.Series:
    arith    = close.pct_change()
    held     = positions.shift(1).fillna(0.0)
    gross_pnl = (held * arith).sum(axis=1)

    # Costs only on Monday rebalance days
    is_mon   = pd.Series(positions.index.dayofweek == 0, index=positions.index).astype(float)
    turnover = positions.diff().abs().sum(axis=1)
    costs    = turnover * COST_PER_LEG * is_mon

    return gross_pnl - costs


# ── IC Test ───────────────────────────────────────────────────────────────────
def run_ic_test(close: pd.DataFrame, signal: pd.DataFrame) -> dict:
    """
    IC = Spearman rank_corr(signal[T], forward_5d_return[T]) pooled across all assets.
    Returns pooled IC, t-stat, ICIR.
    """
    fwd5 = np.log(close / close.shift(1)).rolling(5).sum().shift(-5)

    all_ic  = []
    all_sig = []
    all_fwd = []

    for col in close.columns:
        s = signal[col].dropna()
        f = fwd5[col].reindex(s.index).dropna()
        idx = s.reindex(f.index).dropna().index
        if len(idx) < 50:
            continue
        all_sig.extend(s[idx].values)
        all_fwd.extend(f[idx].values)

    n_pooled = len(all_sig)
    ic_pooled, _ = stats.spearmanr(all_sig, all_fwd)

    # Monthly IC for ICIR
    monthly_ic = []
    sig_df   = signal.stack().reset_index()
    sig_df.columns = ["date","asset","signal"]
    fwd5_df  = fwd5.stack().reset_index()
    fwd5_df.columns = ["date","asset","fwd5"]
    merged = sig_df.merge(fwd5_df, on=["date","asset"]).dropna()
    merged["month"] = merged["date"].dt.to_period("M")
    for _, grp in merged.groupby("month"):
        if len(grp) < 5:
            continue
        ic, _ = stats.spearmanr(grp["signal"], grp["fwd5"])
        monthly_ic.append(ic)

    icir = np.mean(monthly_ic) / np.std(monthly_ic) if np.std(monthly_ic) > 0 else 0.0
    t_stat = ic_pooled * np.sqrt(n_pooled) / np.sqrt(max(1 - ic_pooled**2, 1e-9))

    return dict(ic=ic_pooled, t_stat=t_stat, icir=icir, n=n_pooled, monthly_ic=monthly_ic)


# ── Disagreement Analysis ─────────────────────────────────────────────────────
def compute_disagreement(cs_signal: pd.DataFrame, tm_signal: pd.DataFrame) -> float:
    """
    % of (week, asset) observations where CS reversal signal contradicts TSMOM.
    Contradiction: CS=1 (want to be long loser) and TM=0 (TSMOM says not long).
    """
    # Only look at weeks where CS signal is 1 (active positions)
    cs_mon = cs_signal[cs_signal.index.dayofweek == 0]
    tm_mon = tm_signal.reindex(cs_mon.index)

    active   = cs_mon == 1.0
    disagree = active & (tm_mon == 0.0)

    pct = disagree.sum().sum() / active.sum().sum() if active.sum().sum() > 0 else 0.0
    return float(pct)


# ── Worst-TSMOM-weeks test ────────────────────────────────────────────────────
def worst_tsmom_weeks_test(close: pd.DataFrame,
                            cs_pnl: pd.Series,
                            tm_pnl: pd.Series,
                            n_worst: int = 20) -> dict:
    """
    Identify the 20 worst weekly returns for TSMOM, compute average CS return.
    """
    # Aggregate daily to weekly (Monday→Sunday buckets)
    tm_weekly  = (1 + tm_pnl).resample("W-MON").prod() - 1
    cs_weekly  = (1 + cs_pnl).resample("W-MON").prod() - 1
    idx        = tm_weekly.index.intersection(cs_weekly.index)
    tm_w       = tm_weekly.loc[idx]
    cs_w       = cs_weekly.loc[idx]

    worst_idx  = tm_w.nsmallest(n_worst).index
    cs_on_worst = cs_w.loc[worst_idx]
    avg_cs      = float(cs_on_worst.mean())
    pct_pos     = float((cs_on_worst > 0).mean())

    return dict(avg_cs_ret=avg_cs, pct_positive=pct_pos,
                worst_tm_avg=float(tm_w.loc[worst_idx].mean()))


# ── Sharpe / metrics ─────────────────────────────────────────────────────────
def sharpe(r: pd.Series, ann: int = TRADING_DAYS) -> float:
    r = r.dropna()
    if r.std() == 0:
        return 0.0
    return float((r.mean() / r.std()) * np.sqrt(ann))


def max_dd(r: pd.Series) -> float:
    eq = (1 + r.fillna(0)).cumprod()
    return float(((eq - eq.cummax()) / eq.cummax()).min())


def ann_ret(r: pd.Series, ann: int = TRADING_DAYS) -> float:
    return float(r.dropna().mean() * ann)


# ── Plotting ──────────────────────────────────────────────────────────────────
def plot_results(close, cs_positions, cs_pnl, tm_pnl, ic_result, disagreement):
    fig = plt.figure(figsize=(14, 10))
    gs  = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)

    ax1 = fig.add_subplot(gs[0, :])   # equity curves — full width
    ax2 = fig.add_subplot(gs[1, 0])   # monthly IC distribution
    ax3 = fig.add_subplot(gs[1, 1])   # exposure heatmap

    # ── Panel 1: Equity curves ───────────────────────────────────────────────
    cum_cs = (1 + cs_pnl.fillna(0)).cumprod()
    cum_tm = (1 + tm_pnl.fillna(0)).cumprod()
    ax1.plot(cum_cs.index, cum_cs.values, label=f"CS Reversal  (Sh={sharpe(cs_pnl):.2f})", lw=1.8, color="steelblue")
    ax1.plot(cum_tm.index, cum_tm.values, label=f"TSMOM v2      (Sh={sharpe(tm_pnl):.2f})", lw=1.4, color="darkorange", alpha=0.8)
    ax1.axhline(1.0, color="grey", lw=0.5, ls="--")
    ax1.set_title("CS 1-Month Reversal vs TSMOM v2 — Equity Curve", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Cumulative return")
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # ── Panel 2: Monthly IC histogram ────────────────────────────────────────
    mic = ic_result["monthly_ic"]
    ax2.hist(mic, bins=20, color="steelblue", edgecolor="white", alpha=0.8)
    ax2.axvline(0, color="grey", lw=0.8, ls="--")
    ax2.axvline(ic_result["ic"], color="red", lw=1.5, ls="--",
                label=f"Pooled IC={ic_result['ic']:.3f}")
    ax2.set_title("Monthly IC Distribution (CS signal → 5-day fwd return)", fontsize=10, fontweight="bold")
    ax2.set_xlabel("Spearman IC")
    ax2.set_ylabel("Count")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # ── Panel 3: Per-asset exposure over time ────────────────────────────────
    weekly_exp = cs_positions.resample("W-MON").last()
    weekly_exp.columns = [c.replace("-USD","") for c in weekly_exp.columns]
    # Show stacked bar of which assets are in the portfolio
    signal_counts = (weekly_exp > 0).astype(int)
    bottom = np.zeros(len(signal_counts))
    colors = plt.cm.tab10(np.linspace(0, 1, len(signal_counts.columns)))
    for i, col in enumerate(signal_counts.columns):
        vals = signal_counts[col].values.astype(float)
        ax3.bar(signal_counts.index, vals, bottom=bottom, color=colors[i],
                label=col, width=7, alpha=0.85)
        bottom += vals
    ax3.set_title("Weekly Portfolio Composition (long assets)", fontsize=10, fontweight="bold")
    ax3.set_ylabel("# assets long")
    ax3.legend(fontsize=6, ncol=2, loc="upper right")
    ax3.grid(True, alpha=0.2)

    fig.suptitle(
        f"CS 1-Month Reversal — Feasibility  |  IC t-stat={ic_result['t_stat']:.2f}  "
        f"ICIR={ic_result['icir']:.2f}  Disagreement={disagreement:.0%}",
        fontsize=12, fontweight="bold"
    )
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    print(f"\nFigure saved → {OUT_PNG}")
    plt.close(fig)


# ── Verdict ───────────────────────────────────────────────────────────────────
def print_verdict(ic_result, disagreement, sharpe_cs, worst_test):
    t  = ic_result["t_stat"]
    ic = ic_result["ic"]

    print("\n" + "═"*60)
    print("CS 1-MONTH REVERSAL — FEASIBILITY VERDICT")
    print("═"*60)
    print(f"  IC (pooled)          : {ic:+.4f}")
    print(f"  IC t-stat            : {t:.2f}  (need > 1.5 for GO)")
    print(f"  ICIR                 : {ic_result['icir']:.2f}")
    print(f"  Equity Sharpe        : {sharpe_cs:.2f}")
    print(f"  % TSMOM disagreement : {disagreement:.1%}  (need > 35% for GO)")
    print(f"  Worst-20-TSMOM-weeks : CS avg={worst_test['avg_cs_ret']:+.2%}  "
          f"({worst_test['pct_positive']:.0%} positive)  |  "
          f"TSMOM avg={worst_test['worst_tm_avg']:+.2%}")

    if t > 1.5 and disagreement > 0.35:
        verdict = "GO"
        reason  = f"IC t-stat={t:.2f} > 1.5 AND disagreement={disagreement:.0%} > 35%"
    elif t < 1.0 or disagreement < 0.25:
        verdict = "SKIP"
        reason  = (f"IC t-stat={t:.2f} < 1.0" if t < 1.0
                   else f"Disagreement={disagreement:.0%} < 25%")
    else:
        verdict = "WEAK"
        reason  = f"IC t-stat={t:.2f} borderline or disagreement={disagreement:.0%} borderline"

    print(f"\n  VERDICT: {verdict}")
    print(f"  Reason : {reason}")
    print("═"*60)
    return verdict


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("CS 1-MONTH REVERSAL — FEASIBILITY CHECK")
    print("=" * 60)

    close = download_data()

    print("\nComputing signals...")
    cs_signal  = compute_cs_signal(close)
    tm_signal  = compute_tsmom_signal(close)

    cs_positions = build_positions(close, cs_signal)

    print("Computing P&L...")
    cs_pnl = compute_pnl(close, cs_positions)

    # TSMOM PnL for comparison (long-only, vol-weighted)
    tm_positions = build_positions(close, tm_signal)
    tm_pnl       = compute_pnl(close, tm_positions)

    print("\nRunning IC test...")
    ic_result = run_ic_test(close, cs_signal)

    print("\nComputing TSMOM disagreement...")
    disagreement = compute_disagreement(cs_signal, tm_signal)

    print("\nRunning worst-TSMOM-weeks test...")
    worst_test = worst_tsmom_weeks_test(close, cs_pnl, tm_pnl)

    # ── Print IC results ─────────────────────────────────────────────────────
    print("\n" + "─"*60)
    print("IC TEST: CS Reversal signal → 5-day forward return")
    print("─"*60)
    print(f"  Pooled IC            : {ic_result['ic']:+.4f}")
    print(f"  Pooled t-stat        : {ic_result['t_stat']:.2f}")
    print(f"  ICIR                 : {ic_result['icir']:.2f}")
    print(f"  n (obs)              : {ic_result['n']:,}")

    print("\n" + "─"*60)
    print("DISAGREEMENT: CS Reversal vs TSMOM signal")
    print("─"*60)
    print(f"  % weeks CS long a TSMOM-negative asset: {disagreement:.1%}")

    print("\n" + "─"*60)
    print("EQUITY METRICS")
    print("─"*60)
    sh_cs = sharpe(cs_pnl)
    sh_tm = sharpe(tm_pnl)
    print(f"  CS Reversal  — Sharpe: {sh_cs:.2f}  MaxDD: {max_dd(cs_pnl):.1%}  AnnRet: {ann_ret(cs_pnl):+.1%}")
    print(f"  TSMOM v2     — Sharpe: {sh_tm:.2f}  MaxDD: {max_dd(tm_pnl):.1%}  AnnRet: {ann_ret(tm_pnl):+.1%}")

    # Correlation between the two daily PnL streams
    common = cs_pnl.index.intersection(tm_pnl.index)
    corr   = float(cs_pnl.loc[common].corr(tm_pnl.loc[common]))
    print(f"  PnL correlation (CS vs TSMOM): {corr:+.3f}")

    print("\n" + "─"*60)
    print("WORST-20-TSMOM-WEEKS TEST")
    print("─"*60)
    print(f"  TSMOM avg return on worst 20 weeks : {worst_test['worst_tm_avg']:+.2%}")
    print(f"  CS avg return on those same weeks  : {worst_test['avg_cs_ret']:+.2%}")
    print(f"  CS positive on those weeks         : {worst_test['pct_positive']:.0%}")

    plot_results(close, cs_positions, cs_pnl, tm_pnl, ic_result, disagreement)

    verdict = print_verdict(ic_result, disagreement, sh_cs, worst_test)

    # Return summary dict for comparison table
    return dict(
        strategy="CS Reversal",
        ic_tstat=ic_result["t_stat"],
        sharpe=sh_cs,
        corr_tsmom=corr,
        disagreement=disagreement,
        verdict=verdict,
    )


if __name__ == "__main__":
    main()
