"""
Crypto Monthly Seasonality — Feasibility Check
===============================================
Economic mechanism: BTC halving cycles + institutional year-end
rebalancing create structural calendar patterns. Signal is PURELY
TIME-BASED — zero correlation with any price signal.

Signal:
  STRONG  months (full 15% vol target):  Oct, Nov, Dec, Jan, Apr
  NEUTRAL months (half 7.5% vol target): Feb, Mar
  WEAK    months (flat, 0%):             May, Jun, Jul, Aug, Sep

Assets: BTC-USD, ETH-USD
Data  : 2017-01-01 → 2026-05-14 (longer history for seasonality)
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
ASSETS        = ["BTC-USD", "ETH-USD"]
LABELS        = ["BTC", "ETH"]
START_LONG    = "2017-01-01"
START_OOS     = "2021-01-01"
END           = "2026-05-14"
VOL_WINDOW    = 20
VOL_TARGET_STRONG  = 0.150
VOL_TARGET_NEUTRAL = 0.075
TRADING_DAYS  = 365
COST_PER_LEG  = 0.00085

STRONG_MONTHS  = {10, 11, 12, 1, 4}
NEUTRAL_MONTHS = {2, 3}
WEAK_MONTHS    = {5, 6, 7, 8, 9}
MONTH_NAMES    = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

TSMOM_LB      = 28

OUT_DIR = Path(__file__).parent
OUT_PNG = OUT_DIR / "feasibility_results.png"


# ── Data ─────────────────────────────────────────────────────────────────────
def download_data(start=START_LONG):
    print(f"\nDownloading {LABELS} ({start} → {END})...")
    raw   = yf.download(ASSETS, start=start, end=END, auto_adjust=True, progress=False)
    close = raw["Close"].ffill()
    print(f"  Range : {close.index[0].date()} → {close.index[-1].date()}"
          f"  ({len(close)} rows)")
    return close


# ── Seasonality signal ────────────────────────────────────────────────────────
def season_vol_target(month: int) -> float:
    if month in STRONG_MONTHS:
        return VOL_TARGET_STRONG
    elif month in NEUTRAL_MONTHS:
        return VOL_TARGET_NEUTRAL
    else:
        return 0.0


def compute_season_signal(close: pd.DataFrame) -> pd.DataFrame:
    """Returns per-asset vol-scaled positions based on calendar month."""
    lr      = np.log(close / close.shift(1))
    ann_vol = lr.rolling(VOL_WINDOW).std().shift(1) * np.sqrt(TRADING_DAYS)
    ann_vol = ann_vol.replace(0.0, np.nan)

    pos = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    for month, grp in close.groupby(close.index.month):
        vt    = season_vol_target(month)
        if vt == 0.0:
            continue
        mask  = close.index.month == month
        sc    = (vt / ann_vol[mask]).clip(0.1, 2.0)
        pos[mask] = sc.fillna(0.0).values

    return pos


def compute_tsmom_signal(close: pd.DataFrame) -> pd.DataFrame:
    """TSMOM long-only positions for correlation comparison."""
    lr      = np.log(close / close.shift(1))
    cum     = lr.rolling(TSMOM_LB).sum().shift(1)
    signal  = (cum > 0).astype(float).fillna(0.0)
    ann_vol = lr.rolling(VOL_WINDOW).std().shift(1) * np.sqrt(TRADING_DAYS)
    ann_vol = ann_vol.replace(0.0, np.nan)
    scalar  = (0.15 / ann_vol).clip(0.1, 2.0)
    is_mon  = signal.index.dayofweek == 0
    pos     = (signal * scalar)
    pos[~is_mon] = np.nan
    pos = pos.ffill().fillna(0.0)
    return pos


# ── P&L ───────────────────────────────────────────────────────────────────────
def compute_pnl(close: pd.DataFrame, positions: pd.DataFrame) -> pd.Series:
    arith     = close.pct_change()
    held      = positions.shift(1).fillna(0.0)
    gross_pnl = (held * arith).sum(axis=1)

    # Monthly seasonality: rebalance on month-starts (change of signal)
    # Treat each calendar-month boundary as the turnover day
    pos_change = positions.diff().abs().sum(axis=1)
    costs      = pos_change * COST_PER_LEG
    return gross_pnl - costs


# ── Monthly return statistics ─────────────────────────────────────────────────
def monthly_return_stats(close: pd.DataFrame, start=START_LONG) -> pd.DataFrame:
    """
    For each calendar month (1-12): mean monthly log return, t-stat, std.
    Returns DataFrame indexed by month number.
    """
    close = close.loc[start:]
    lr    = np.log(close / close.shift(1))
    # Monthly log returns (sum of daily logs = log of monthly compounding)
    monthly = lr.resample("MS").sum()

    rows = []
    for m in range(1, 13):
        mask = monthly.index.month == m
        data = monthly[mask]
        for col in data.columns:
            s   = data[col].dropna()
            if len(s) < 2:
                continue
            mean, std = s.mean(), s.std()
            t, p = stats.ttest_1samp(s, 0)
            rows.append(dict(
                month=m, asset=col.replace("-USD",""),
                mean=mean, std=std, t_stat=t, p_val=p, n=len(s)
            ))
    return pd.DataFrame(rows)


# ── Yearly consistency ────────────────────────────────────────────────────────
def yearly_consistency(close: pd.DataFrame) -> pd.DataFrame:
    """
    For each year 2021-2025: compute mean strong-month return vs weak-month return.
    Returns DataFrame indexed by year.
    """
    lr      = np.log(close / close.shift(1))
    monthly = lr.resample("MS").sum()
    monthly = monthly.loc["2021":]

    rows = []
    for year, grp in monthly.groupby(monthly.index.year):
        strong = grp[grp.index.month.isin(STRONG_MONTHS)].mean(axis=1).mean()
        weak   = grp[grp.index.month.isin(WEAK_MONTHS)].mean(axis=1).mean()
        rows.append(dict(year=year, strong_avg=strong, weak_avg=weak,
                         edge=strong - weak, holds=strong > weak))
    return pd.DataFrame(rows).set_index("year")


# ── Metrics ───────────────────────────────────────────────────────────────────
def sharpe(r: pd.Series, ann: int = TRADING_DAYS) -> float:
    r = r.dropna()
    return float((r.mean() / r.std()) * np.sqrt(ann)) if r.std() > 0 else 0.0


def max_dd(r: pd.Series) -> float:
    eq = (1 + r.fillna(0)).cumprod()
    return float(((eq - eq.cummax()) / eq.cummax()).min())


def ann_ret(r: pd.Series) -> float:
    return float(r.dropna().mean() * TRADING_DAYS)


# ── Plotting ──────────────────────────────────────────────────────────────────
def plot_results(close, season_pnl, tm_pnl, month_stats, yearly):
    fig = plt.figure(figsize=(16, 11))
    gs  = gridspec.GridSpec(2, 3, figure=fig, hspace=0.50, wspace=0.38)

    ax1 = fig.add_subplot(gs[0, :2])  # equity curve (wide)
    ax2 = fig.add_subplot(gs[0, 2])   # yearly consistency
    ax3 = fig.add_subplot(gs[1, :])   # monthly mean returns (both assets)

    # ── Panel 1: Equity curves ───────────────────────────────────────────────
    cum_s  = (1 + season_pnl.fillna(0)).cumprod()
    cum_tm = (1 + tm_pnl.fillna(0)).cumprod()
    ax1.plot(cum_s.index, cum_s.values,  label=f"Seasonality (Sh={sharpe(season_pnl):.2f})", lw=1.8, color="steelblue")
    ax1.plot(cum_tm.index, cum_tm.values, label=f"TSMOM v2   (Sh={sharpe(tm_pnl):.2f})", lw=1.4, color="darkorange", alpha=0.8)
    ax1.axhline(1.0, color="grey", lw=0.5, ls="--")
    ax1.set_title("Crypto Seasonality vs TSMOM v2 — Equity Curve (2017–2026)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Cumulative return")
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # ── Panel 2: Yearly consistency ──────────────────────────────────────────
    years = yearly.index.astype(str)
    colors = ["green" if h else "red" for h in yearly["holds"]]
    ax2.bar(years, yearly["edge"] * 100, color=colors, alpha=0.8)
    ax2.axhline(0, color="grey", lw=0.8)
    ax2.set_title("Strong vs Weak Month Edge\nby Year (2021–2025)", fontsize=10, fontweight="bold")
    ax2.set_ylabel("Edge (% log return)")
    ax2.set_xlabel("Year")
    ax2.grid(True, alpha=0.3)

    # ── Panel 3: Monthly mean returns ────────────────────────────────────────
    x     = np.arange(1, 13)
    width = 0.35
    btc   = month_stats[month_stats["asset"] == "BTC"].set_index("month")
    eth   = month_stats[month_stats["asset"] == "ETH"].set_index("month")

    b1 = ax3.bar(x - width/2, btc["mean"].reindex(x).fillna(0)*100,
                 width, label="BTC", color="gold", alpha=0.85, edgecolor="white")
    b2 = ax3.bar(x + width/2, eth["mean"].reindex(x).fillna(0)*100,
                 width, label="ETH", color="steelblue", alpha=0.85, edgecolor="white")

    # Significance stars
    for i, m in enumerate(x):
        for data, offset in [(btc, -width/2), (eth, width/2)]:
            row = data.loc[m] if m in data.index else None
            if row is not None and abs(row["t_stat"]) > 1.5:
                h = row["mean"] * 100
                ax3.text(m + offset, h + (0.3 if h >= 0 else -0.8), "★",
                         ha="center", va="bottom", fontsize=9, color="darkred")

    ax3.axhline(0, color="grey", lw=0.8)
    # Shade strong/weak months
    for m in STRONG_MONTHS:
        ax3.axvspan(m - 0.5, m + 0.5, alpha=0.08, color="green")
    for m in WEAK_MONTHS:
        ax3.axvspan(m - 0.5, m + 0.5, alpha=0.08, color="red")
    ax3.set_xticks(x)
    ax3.set_xticklabels(MONTH_NAMES)
    ax3.set_title("Mean Monthly Log Return by Calendar Month (★ = t-stat > 1.5)", fontsize=10, fontweight="bold")
    ax3.set_ylabel("Mean log return (%)")
    ax3.legend(fontsize=9)
    ax3.grid(True, alpha=0.3)

    fig.suptitle("Crypto Monthly Seasonality — Feasibility", fontsize=13, fontweight="bold")
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    print(f"\nFigure saved → {OUT_PNG}")
    plt.close(fig)


# ── Verdict ───────────────────────────────────────────────────────────────────
def print_verdict(month_stats, yearly, sharpe_s, corr_tsmom, pct_in_market):
    # Count strong months with t-stat > 1.5 (pooled BTC+ETH)
    strong_sig = month_stats[
        month_stats["month"].isin(STRONG_MONTHS) & (month_stats["t_stat"] > 1.5)
    ]
    n_sig_strong = len(strong_sig)
    n_years_hold = int(yearly["holds"].sum())

    print("\n" + "═"*60)
    print("CRYPTO SEASONALITY — FEASIBILITY VERDICT")
    print("═"*60)
    print(f"  Strong months with t>1.5 : {n_sig_strong} / {len(STRONG_MONTHS)*len(ASSETS)}"
          f"  (asset×month pairs)")
    print(f"  Years pattern holds      : {n_years_hold}/5 (2021-2025)")
    print(f"  Equity Sharpe            : {sharpe_s:.2f}")
    print(f"  Corr with TSMOM          : {corr_tsmom:+.3f}")
    print(f"  % time in market         : {pct_in_market:.0%}")

    # Individual month stats
    print("\n  Monthly mean returns (BTC, log %, t-stat):")
    btc = month_stats[month_stats["asset"] == "BTC"].set_index("month")
    for m in range(1, 13):
        if m not in btc.index:
            continue
        row = btc.loc[m]
        tag = "STRONG" if m in STRONG_MONTHS else ("NEUTRAL" if m in NEUTRAL_MONTHS else "weak  ")
        star = "★" if abs(row["t_stat"]) > 1.5 else " "
        print(f"    {MONTH_NAMES[m-1]:3s} [{tag}]: mean={row['mean']*100:+.1f}%  t={row['t_stat']:+.2f}{star}")

    print("\n  Yearly edge (strong - weak avg monthly return):")
    for yr, row in yearly.iterrows():
        tick = "✓" if row["holds"] else "✗"
        print(f"    {yr}: {row['edge']*100:+.2f}%  {tick}")

    if n_sig_strong >= 3 and n_years_hold >= 3:
        verdict = "GO"
        reason  = f"{n_sig_strong} strong-month t>1.5 pairs AND pattern holds {n_years_hold}/5 years"
    elif n_years_hold < 3:
        verdict = "SKIP"
        reason  = f"Pattern holds only {n_years_hold}/5 post-2021 years — too unstable"
    elif n_sig_strong < 2:
        verdict = "SKIP"
        reason  = f"Only {n_sig_strong} significant strong months — no statistical basis"
    else:
        verdict = "WEAK"
        reason  = f"Borderline: {n_sig_strong} sig months, {n_years_hold}/5 years"

    print(f"\n  VERDICT: {verdict}")
    print(f"  Reason : {reason}")
    print("═"*60)
    return verdict


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("CRYPTO MONTHLY SEASONALITY — FEASIBILITY CHECK")
    print("=" * 60)

    close = download_data(start=START_LONG)

    print("Computing signals...")
    season_pos = compute_season_signal(close)
    tm_pos     = compute_tsmom_signal(close)

    print("Computing P&L...")
    season_pnl = compute_pnl(close, season_pos)
    tm_pnl     = compute_pnl(close, tm_pos)

    print("Computing monthly return statistics...")
    month_stats = monthly_return_stats(close, start=START_LONG)

    print("Computing yearly consistency (2021-2025)...")
    yearly = yearly_consistency(close)

    # OOS sub-period (2021-2026)
    season_oos = season_pnl.loc[START_OOS:]
    tm_oos     = tm_pnl.loc[START_OOS:]

    # % time in market
    pct_in = float((season_pos.sum(axis=1) > 0).mean())

    # Correlation with TSMOM (weekly aggregation)
    tm_wk  = (1 + tm_oos).resample("W-MON").prod() - 1
    s_wk   = (1 + season_oos).resample("W-MON").prod() - 1
    idx    = tm_wk.index.intersection(s_wk.index)
    corr   = float(tm_wk.loc[idx].corr(s_wk.loc[idx]))

    # IC-like metric: t-stat from pooled strong-month returns
    strong_mask   = close.index.month.isin(STRONG_MONTHS)
    lr_strong     = np.log(close / close.shift(1)).loc[strong_mask]
    fwd5_strong   = np.log(close / close.shift(1)).rolling(5).sum().shift(-5).loc[strong_mask]
    flat_s        = lr_strong.values.flatten()
    flat_f        = fwd5_strong.values.flatten()
    valid         = ~(np.isnan(flat_s) | np.isnan(flat_f))
    if valid.sum() > 10:
        from scipy.stats import spearmanr
        ic_pooled, _ = spearmanr(flat_s[valid], flat_f[valid])
        n_ic = valid.sum()
        t_ic = ic_pooled * np.sqrt(n_ic) / np.sqrt(max(1 - ic_pooled**2, 1e-9))
    else:
        ic_pooled, t_ic = 0.0, 0.0

    # ── Print results ─────────────────────────────────────────────────────────
    print("\n" + "─"*60)
    print("MONTHLY RETURN STATISTICS (BTC, 2017-2026)")
    print("─"*60)
    btc_stats = month_stats[month_stats["asset"] == "BTC"].set_index("month")
    for m in range(1, 13):
        if m not in btc_stats.index:
            continue
        row = btc_stats.loc[m]
        tag  = "STRONG" if m in STRONG_MONTHS else ("NEUTRAL" if m in NEUTRAL_MONTHS else "weak  ")
        star = "★" if abs(row["t_stat"]) > 1.5 else " "
        print(f"  {MONTH_NAMES[m-1]:3s} [{tag}]: mean={row['mean']*100:+.1f}%  t={row['t_stat']:+.2f}{star}  n={row['n']:.0f}")

    print("\n" + "─"*60)
    print("YEARLY CONSISTENCY (2021-2025)")
    print("─"*60)
    for yr, row in yearly.iterrows():
        tick = "✓ holds" if row["holds"] else "✗ fails"
        print(f"  {yr}: strong_avg={row['strong_avg']*100:+.2f}%  weak_avg={row['weak_avg']*100:+.2f}%  edge={row['edge']*100:+.2f}%  {tick}")

    print("\n" + "─"*60)
    print("EQUITY METRICS")
    print("─"*60)
    sh_s  = sharpe(season_pnl)
    sh_oos = sharpe(season_oos)
    sh_tm  = sharpe(tm_pnl.loc[START_LONG:])
    sh_tm_oos = sharpe(tm_oos)
    print(f"  Seasonality  — Full (2017-2026): Sharpe={sh_s:.2f}  MaxDD={max_dd(season_pnl):.1%}")
    print(f"  Seasonality  — OOS  (2021-2026): Sharpe={sh_oos:.2f}  MaxDD={max_dd(season_oos):.1%}")
    print(f"  TSMOM v2     — Full (2017-2026): Sharpe={sh_tm:.2f}")
    print(f"  TSMOM v2     — OOS  (2021-2026): Sharpe={sh_tm_oos:.2f}")
    print(f"  % time in market                : {pct_in:.0%}")
    print(f"  Weekly PnL corr w/ TSMOM (OOS) : {corr:+.3f}")
    print(f"  IC (strong-month daily returns) : {ic_pooled:+.4f}  t={t_ic:.2f}")

    plot_results(close, season_pnl, tm_pnl.loc[START_LONG:], month_stats, yearly)

    verdict = print_verdict(month_stats, yearly, sh_s, corr, pct_in)

    return dict(
        strategy="Seasonality",
        ic_tstat=t_ic,
        sharpe=sh_s,
        sharpe_oos=sh_oos,
        corr_tsmom=corr,
        disagreement=1 - pct_in,  # % of weeks with no position ≈ disagreement with always-long TM
        verdict=verdict,
    )


if __name__ == "__main__":
    main()
