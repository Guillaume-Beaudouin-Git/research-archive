"""
Vol-Spike Position Filter for TSMOM v2
=======================================
README §9 Research Priority #2: "Build a vol-spike detector that scales
down position regardless of regime."

HMM study (§6.15): intra-BULL vol spikes → 3% daily limit breaches on
Propr, not regime transitions. This overlay multiplies TSMOM v2 positions
by a spike_ratio-based multiplier, reducing size during elevated vol.

Multiplier rule (Monday-locked, per-asset):
  spike_ratio = vol5 / vol20   (5-day vs 20-day realized ann vol)
  T1 (base):  < 1.2→1.0   1.2–1.5→0.7   1.5–2.0→0.4   ≥2.0→0.2
  T2 (loose): < 1.3→1.0   1.3–1.8→0.6   1.8–2.5→0.3   ≥2.5→0.15
  T3 (tight): < 1.1→1.0   1.1–1.4→0.6   1.4–1.8→0.3   ≥1.8→0.15

Run: python -m strategies.tsmom_v2_propfirm.vol_spike_filter
"""
from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
import yfinance as yf

try:
    from strategies.tsmom_v2_propfirm.signal  import compute_signal, apply_weekly_rebalance
    from strategies.tsmom_v2_propfirm.sizing  import compute_vol_scalars, compute_positions
    from strategies.tsmom_v2_propfirm.config  import UNIVERSE, VOL_LOOKBACK_DAYS
except ImportError:
    # Inline fallbacks
    def compute_signal(prices, lookback=28):
        lr  = np.log(prices / prices.shift(1))
        cum = lr.rolling(lookback).sum().shift(1)
        sig = (cum > 0).astype(float)
        sig[cum.isna()] = np.nan
        return sig

    def apply_weekly_rebalance(signals, rebalance_weekday=0):
        mask = pd.Series(signals.index.dayofweek == rebalance_weekday, index=signals.index)
        return signals.where(mask).ffill()

    def compute_vol_scalars(lr, vol_target, vol_lookback=20):
        ann = lr.rolling(vol_lookback).std() * np.sqrt(365)
        return (vol_target / ann).shift(1).clip(0.1, 2.0)

    def compute_positions(signals, vol_scalars):
        return signals * vol_scalars

    UNIVERSE = [
        "BTC-USD","ETH-USD","SOL-USD","AVAX-USD","LINK-USD","ARB-USD",
        "MATIC-USD","OP-USD","DOGE-USD","ADA-USD","DOT-USD","UNI-USD",
        "LTC-USD","BCH-USD",
    ]
    VOL_LOOKBACK_DAYS = 20


# ── Constants ─────────────────────────────────────────────────────────────────
DATA_START   = "2021-01-01"
TRAIN_END    = "2023-12-31"
OOS_START    = "2024-01-01"
DATA_END     = "2026-05-14"
SIM_START    = "2025-01-06"
SIM_END      = "2025-11-03"

TRADING_DAYS = 365
VOL_TARGET   = 0.15
COST_PER_LEG = 0.00085   # one-way (0.17% RT)

INITIAL_EQ          = 5_000.0
PROFIT_TARGET_PCT   = 0.10
MAX_DD_PCT          = 0.06
DAILY_LIMIT_PCT     = 0.03
SIM_GROSS_CAP       = 0.90

# Walk-forward splits: (train_start, train_end, oos_start, oos_end)
WF_SPLITS = [
    ("2021-01-01", "2021-12-31", "2022-01-01", "2022-12-31"),
    ("2021-01-01", "2022-12-31", "2023-01-01", "2023-12-31"),
    ("2021-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),
    ("2021-01-01", "2024-12-31", "2025-01-01", "2025-12-31"),
]

THRESHOLD_CONFIGS = {
    "T1": [(1.2, 0.7), (1.5, 0.4), (2.0, 0.2)],   # base
    "T2": [(1.3, 0.6), (1.8, 0.3), (2.5, 0.15)],  # looser
    "T3": [(1.1, 0.6), (1.4, 0.3), (1.8, 0.15)],  # tighter
}

OUT_DIR = Path(__file__).parent
OUT_PNG = OUT_DIR / "vol_spike_results.png"


# ── Data ──────────────────────────────────────────────────────────────────────
def download_data() -> pd.DataFrame:
    print(f"Downloading {len(UNIVERSE)}-asset universe ({DATA_START} → {DATA_END})...")
    raw    = yf.download(UNIVERSE, start=DATA_START, end=DATA_END,
                         auto_adjust=True, progress=False)
    close  = raw["Close"].dropna(axis=1, how="all").ffill()
    if close.index.tz is not None:
        close.index = close.index.tz_convert(None)
    dropped = [t for t in UNIVERSE if t not in close.columns]
    print(f"  Available: {len(close.columns)} assets | Dropped: {dropped}")
    print(f"  Range    : {close.index[0].date()} → {close.index[-1].date()}"
          f"  ({len(close)} days)")
    return close


# ── Spike multiplier ──────────────────────────────────────────────────────────
def compute_spike_multiplier(log_ret: pd.DataFrame,
                              thresholds: list[tuple[float, float]]) -> pd.DataFrame:
    """
    Per-asset, Monday-locked spike multiplier.

    spike_ratio = vol5[t] / vol20[t]  (both shift(1) for no look-ahead)

    thresholds: [(ratio_1, mult_1), (ratio_2, mult_2), (ratio_3, mult_3)]
      Baseline (ratio < ratio_1) → 1.0
      ratio_1 ≤ ratio < ratio_2  → mult_1
      ratio_2 ≤ ratio < ratio_3  → mult_2
      ratio ≥ ratio_3             → mult_3
    """
    vol5  = log_ret.rolling(5).std().shift(1)  * np.sqrt(TRADING_DAYS)
    vol20 = log_ret.rolling(20).std().shift(1) * np.sqrt(TRADING_DAYS)
    spike_ratio = (vol5 / vol20.replace(0, np.nan)).fillna(1.0)

    mult = pd.DataFrame(1.0, index=log_ret.index, columns=log_ret.columns)
    for thresh, m in thresholds:
        mult[spike_ratio >= thresh] = m

    # Lock to Monday: evaluate multiplier only on rebalance day, hold for week
    is_mon = mult.index.dayofweek == 0
    locked = mult.copy()
    locked[~is_mon] = np.nan
    locked = locked.ffill().fillna(1.0)
    return locked


def spike_ratio_series(log_ret: pd.DataFrame) -> pd.Series:
    """Average spike ratio across all assets (for plotting)."""
    vol5  = log_ret.rolling(5).std().shift(1)  * np.sqrt(TRADING_DAYS)
    vol20 = log_ret.rolling(20).std().shift(1) * np.sqrt(TRADING_DAYS)
    return (vol5 / vol20.replace(0, np.nan)).mean(axis=1)


# ── Position building ─────────────────────────────────────────────────────────
def build_positions(close: pd.DataFrame,
                    thresholds: list[tuple[float, float]] | None = None
                    ) -> pd.DataFrame:
    """
    Build TSMOM v2 positions, optionally scaled by vol-spike multiplier.

    Returns DataFrame of position sizes (same shape as close).
    Values represent notional fraction of account equity per asset.
    Already Monday-locked and ffilled.
    """
    lr       = np.log(close / close.shift(1))
    signals  = compute_signal(close)
    scalars  = compute_vol_scalars(lr, VOL_TARGET, VOL_LOOKBACK_DAYS)
    raw_pos  = compute_positions(signals, scalars)
    weekly   = apply_weekly_rebalance(raw_pos)   # Monday-locked, ffilled

    if thresholds is not None:
        multiplier = compute_spike_multiplier(lr, thresholds)
        weekly     = weekly * multiplier          # both already Monday-locked

    return weekly.fillna(0.0)


# ── P&L ───────────────────────────────────────────────────────────────────────
def compute_portfolio_pnl(close: pd.DataFrame,
                           positions: pd.DataFrame) -> pd.Series:
    """
    Daily net portfolio return.
    Positions held = prior day's positions (shift(1) execution lag).
    Costs charged only on Monday (turnover × COST_PER_LEG one-way).
    """
    arith   = close.pct_change().fillna(0.0)
    held    = positions.shift(1).fillna(0.0)
    gross   = (held * arith).sum(axis=1)

    is_mon  = pd.Series(positions.index.dayofweek == 0,
                        index=positions.index).astype(float)
    turnover = positions.diff().abs().sum(axis=1)
    costs    = turnover * COST_PER_LEG * is_mon

    return gross - costs


# ── Metrics ───────────────────────────────────────────────────────────────────
def sharpe(r: pd.Series) -> float:
    r = r.dropna()
    return float((r.mean() / r.std()) * np.sqrt(TRADING_DAYS)) if r.std() > 0 else 0.0


def max_dd(r: pd.Series) -> float:
    eq = (1 + r.fillna(0)).cumprod()
    return float(((eq - eq.cummax()) / eq.cummax()).min())


def count_breach_days(r: pd.Series, threshold: float = DAILY_LIMIT_PCT) -> int:
    return int((r < -threshold).sum())


# ── Walk-forward ──────────────────────────────────────────────────────────────
def run_walk_forward(close: pd.DataFrame,
                      configs: dict[str, list]) -> pd.DataFrame:
    """
    4-fold expanding-window walk-forward.
    For each fold: compare base TSMOM vs each threshold config.
    Returns DataFrame with one row per (fold × config).
    """
    rows = []
    for fold_i, (tr_s, tr_e, oos_s, oos_e) in enumerate(WF_SPLITS, 1):
        # Build positions on full data (signal needs pre-OOS history)
        base_pos = build_positions(close)
        for cfg_name, thresholds in [("base", None)] + list(configs.items()):
            pos = build_positions(close, thresholds if cfg_name != "base" else None)
            pnl = compute_portfolio_pnl(close, pos)
            oos = pnl.loc[oos_s:oos_e]
            rows.append(dict(
                fold=fold_i,
                oos_period=f"{oos_s[:7]}–{oos_e[:7]}",
                config=cfg_name,
                sharpe=sharpe(oos),
                max_dd=max_dd(oos),
                breach_days=count_breach_days(oos),
                n_days=len(oos),
            ))
    return pd.DataFrame(rows)


# ── Propr challenge simulation ─────────────────────────────────────────────────
def _build_result(start: pd.Timestamp, end: pd.Timestamp,
                  outcome: str, fail_reason: str | None,
                  final_eq: float, eq_curve: list[float],
                  peak: float, trading_days: int) -> dict[str, Any]:
    arr = np.array(eq_curve)
    hwm = np.maximum.accumulate(arr)
    dd  = (arr - hwm) / hwm
    return {
        "start_date":       start,
        "end_date":         end,
        "outcome":          outcome,
        "fail_reason":      fail_reason,
        "final_equity":     round(final_eq, 2),
        "peak_equity":      round(peak, 2),
        "max_drawdown_pct": float(-dd.min()),
        "days_elapsed":     len(eq_curve) - 1,
        "trading_days":     trading_days,
        "equity_curve":     eq_curve,
    }


def simulate_challenge(
    start_date: pd.Timestamp,
    prices: pd.DataFrame,
    positions_df: pd.DataFrame,
) -> dict[str, Any]:
    """
    Simulate one Propr challenge attempt using pre-built positions.

    positions_df : DataFrame of position sizes (equity fraction per asset),
                   indexed by date, Monday-locked and ffilled.
    Rebalance    : Monday only — uses positions_df.loc[Monday] as target.
    Costs        : COST_PER_LEG × |Δnotional| on Monday only.
    HWM          : static at INITIAL_EQ (Propr static-drawdown rule).
    """
    equity:    float            = INITIAL_EQ
    hwm:       float            = INITIAL_EQ
    peak:      float            = INITIAL_EQ
    positions: dict[str, float] = {}   # {ticker: quantity}
    eq_curve:  list[float]      = [INITIAL_EQ]
    trading_days: int           = 0

    sim_dates = prices.index[prices.index >= start_date]

    for i, date in enumerate(sim_dates):
        eq_day_start = equity

        # ── 1. MTM on carried positions ───────────────────────────────────
        if i > 0 and positions:
            prev = sim_dates[i - 1]
            for ticker, qty in positions.items():
                if ticker not in prices.columns:
                    continue
                p_now  = prices.at[date, ticker]
                p_prev = prices.at[prev,  ticker]
                if not (pd.isna(p_now) or pd.isna(p_prev)):
                    equity += qty * (p_now - p_prev)

        # ── 2. Monday rebalance ───────────────────────────────────────────
        if date.dayofweek == 0 and date in positions_df.index:
            sizes_row = positions_df.loc[date]
            target: dict[str, float] = {}
            for ticker in prices.columns:
                if ticker not in sizes_row.index:
                    continue
                sz = sizes_row[ticker]
                px = prices.at[date, ticker]
                if not pd.isna(sz) and sz > 0 and not pd.isna(px) and px > 0:
                    target[ticker] = equity * float(sz)

            total_notional = sum(target.values())
            if total_notional > equity * SIM_GROSS_CAP:
                scale  = equity * SIM_GROSS_CAP / total_notional
                target = {k: v * scale for k, v in target.items()}

            for ticker in set(positions) | set(target):
                if ticker not in prices.columns:
                    continue
                px = prices.at[date, ticker]
                if pd.isna(px) or px <= 0:
                    continue
                old_n = positions.get(ticker, 0.0) * px
                new_n = target.get(ticker, 0.0)
                equity -= abs(new_n - old_n) * COST_PER_LEG

            positions = {t: n / prices.at[date, t]
                         for t, n in target.items()
                         if prices.at[date, t] > 0}
            trading_days += 1

        # ── 3. Daily loss limit ───────────────────────────────────────────
        if i > 0 and (equity - eq_day_start) / eq_day_start < -DAILY_LIMIT_PCT:
            eq_curve.append(equity)
            return _build_result(start_date, date, "FAIL", "daily_limit",
                                 equity, eq_curve, peak, trading_days)

        # ── 4. Total DD vs static HWM ─────────────────────────────────────
        if equity <= hwm * (1.0 - MAX_DD_PCT):
            eq_curve.append(equity)
            return _build_result(start_date, date, "FAIL", "total_drawdown",
                                 equity, eq_curve, peak, trading_days)

        # ── 5. Profit target ──────────────────────────────────────────────
        if equity >= hwm * (1.0 + PROFIT_TARGET_PCT):
            eq_curve.append(equity)
            return _build_result(start_date, date, "PASS", None,
                                 equity, eq_curve, peak, trading_days)

        if equity > peak:
            peak = equity
        eq_curve.append(equity)

    last = sim_dates[-1] if len(sim_dates) > 0 else start_date
    return _build_result(start_date, last, "INCOMPLETE", None,
                         equity, eq_curve, peak, trading_days)


def run_propr_sims(prices: pd.DataFrame,
                   positions_df: pd.DataFrame,
                   label: str = "",
                   verbose: bool = False) -> pd.DataFrame:
    """Run 44 weekly-start Propr challenge sims; return summary DataFrame."""
    start_dates = pd.date_range(start=SIM_START, end=SIM_END, freq="W-MON")
    results = []
    for sd in start_dates:
        if verbose:
            print(f"  [{label}] {sd.date()}", flush=True)
        r = simulate_challenge(sd, prices, positions_df)
        results.append({k: v for k, v in r.items() if k != "equity_curve"})
    return pd.DataFrame(results)


def sim_metrics(df: pd.DataFrame) -> dict[str, Any]:
    n          = len(df)
    pass_mask  = df["outcome"] == "PASS"
    pass_rate  = float(pass_mask.sum()) / n
    fail_daily = int((df["fail_reason"] == "daily_limit").sum())
    fail_total = int((df["fail_reason"] == "total_drawdown").sum())
    return dict(
        pass_rate=pass_rate,
        pass_count=int(pass_mask.sum()),
        fail_daily=fail_daily,
        fail_total=fail_total,
        median_max_dd=float(df["max_drawdown_pct"].median()),
    )


# ── Spike ratio bucket distribution ──────────────────────────────────────────
def spike_bucket_pct(log_ret: pd.DataFrame, thresholds: list) -> dict:
    """
    % of asset-days in each spike tier (Normal / Elevated / High / Extreme).
    """
    vol5  = log_ret.rolling(5).std().shift(1)  * np.sqrt(TRADING_DAYS)
    vol20 = log_ret.rolling(20).std().shift(1) * np.sqrt(TRADING_DAYS)
    ratio = (vol5 / vol20.replace(0, np.nan)).dropna(how="all")
    flat  = ratio.values.flatten()
    flat  = flat[~np.isnan(flat)]
    n     = len(flat)

    t1, _ = thresholds[0]
    t2, _ = thresholds[1]
    t3, _ = thresholds[2]

    return {
        "Normal":   float((flat < t1).sum()) / n,
        "Elevated": float(((flat >= t1) & (flat < t2)).sum()) / n,
        "High":     float(((flat >= t2) & (flat < t3)).sum()) / n,
        "Extreme":  float((flat >= t3).sum()) / n,
    }


# ── Plotting ──────────────────────────────────────────────────────────────────
def plot_results(
    close:      pd.DataFrame,
    base_pnl:   pd.Series,
    t1_pnl:     pd.Series,
    log_ret:    pd.DataFrame,
    base_sims:  pd.DataFrame,
    sim_results: dict[str, pd.DataFrame],
) -> None:
    fig = plt.figure(figsize=(16, 12))
    gs  = gridspec.GridSpec(2, 2, figure=fig, hspace=0.42, wspace=0.35)
    ax1 = fig.add_subplot(gs[0, 0])   # equity curve (OOS)
    ax2 = fig.add_subplot(gs[0, 1])   # spike ratio timeline
    ax3 = fig.add_subplot(gs[1, 0])   # daily return distribution
    ax4 = fig.add_subplot(gs[1, 1])   # Propr pass rate bar chart

    oos_base = base_pnl.loc[OOS_START:]
    oos_t1   = t1_pnl.loc[OOS_START:]

    # ── Panel 1: OOS equity curves ────────────────────────────────────────
    cum_base = (1 + oos_base.fillna(0)).cumprod()
    cum_t1   = (1 + oos_t1.fillna(0)).cumprod()
    ax1.plot(cum_base.index, cum_base.values,
             label=f"TSMOM base  (Sh={sharpe(oos_base):.2f})", lw=1.8, color="darkorange")
    ax1.plot(cum_t1.index,   cum_t1.values,
             label=f"+ Vol Filter T1 (Sh={sharpe(oos_t1):.2f})", lw=1.8, color="steelblue")
    ax1.axhline(1.0, color="grey", lw=0.5, ls="--")
    ax1.set_title("OOS Equity Curve (2024–2026)", fontsize=10, fontweight="bold")
    ax1.set_ylabel("Cumulative return")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    # ── Panel 2: Spike ratio timeline ────────────────────────────────────
    sratio = spike_ratio_series(log_ret)
    t1_cfg = THRESHOLD_CONFIGS["T1"]
    t1_r, _ = t1_cfg[0]; t2_r, _ = t1_cfg[1]; t3_r, _ = t1_cfg[2]

    ax2.plot(sratio.index, sratio.values, lw=0.8, color="grey", alpha=0.7)
    ax2.axhline(t1_r, color="gold",   lw=1.0, ls="--", label=f"Elevated >{t1_r}")
    ax2.axhline(t2_r, color="orange", lw=1.0, ls="--", label=f"High >{t2_r}")
    ax2.axhline(t3_r, color="red",    lw=1.0, ls="--", label=f"Extreme >{t3_r}")
    ax2.fill_between(sratio.index, t1_r, sratio.values.clip(min=t1_r),
                     alpha=0.15, color="gold")
    ax2.fill_between(sratio.index, t2_r, sratio.values.clip(min=t2_r),
                     alpha=0.20, color="orange")
    ax2.fill_between(sratio.index, t3_r, sratio.values.clip(min=t3_r),
                     alpha=0.25, color="red")
    ax2.set_title("Avg Spike Ratio (vol5/vol20) Over Time", fontsize=10, fontweight="bold")
    ax2.set_ylabel("Spike ratio")
    ax2.legend(fontsize=7)
    ax2.grid(True, alpha=0.3)

    # ── Panel 3: Daily return distribution (left tail zoom) ───────────────
    lim = 0.08
    bins = np.linspace(-lim, lim, 60)
    ax3.hist(base_pnl.loc[OOS_START:].clip(-lim, lim), bins=bins,
             color="darkorange", alpha=0.6, label="Base", density=True)
    ax3.hist(t1_pnl.loc[OOS_START:].clip(-lim, lim),   bins=bins,
             color="steelblue",  alpha=0.6, label="T1 filter", density=True)
    ax3.axvline(-DAILY_LIMIT_PCT, color="red", lw=1.5, ls="--",
                label=f"-{DAILY_LIMIT_PCT:.0%} Propr limit")
    ax3.set_xlim(-lim, lim)
    ax3.set_title("Daily Return Distribution — OOS (zoom)", fontsize=10, fontweight="bold")
    ax3.set_xlabel("Daily return")
    ax3.set_ylabel("Density")
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    # ── Panel 4: Propr pass rates ─────────────────────────────────────────
    labels     = ["Base"] + list(sim_results.keys())
    all_dfs    = [base_sims] + list(sim_results.values())
    pass_rates = [float((df["outcome"] == "PASS").sum()) / len(df) for df in all_dfs]
    colors     = ["darkorange", "steelblue", "seagreen", "mediumpurple"]
    bars = ax4.bar(labels, [r * 100 for r in pass_rates],
                   color=colors[:len(labels)], alpha=0.85, edgecolor="white")
    for bar, rate in zip(bars, pass_rates):
        ax4.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f"{rate:.0%}", ha="center", fontsize=9, fontweight="bold")
    ax4.axhline(50, color="red",    lw=1.2, ls="--", label="50% target")
    ax4.axhline(45, color="orange", lw=0.8, ls=":",  label="45% weak")
    ax4.set_ylim(0, 100)
    ax4.set_title("Propr Pass Rate — 44 sims from 2025-01-06", fontsize=10, fontweight="bold")
    ax4.set_ylabel("Pass rate (%)")
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.2)

    fig.suptitle("TSMOM v2 + Vol-Spike Filter — Feasibility", fontsize=13, fontweight="bold")
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    print(f"\nFigure saved → {OUT_PNG}")
    plt.close(fig)


# ── Verdict ───────────────────────────────────────────────────────────────────
def print_verdict(base_oos_sh, t1_oos_sh, base_br, t1_br, base_2025_br, t1_2025_br,
                  base_propr_m, best_config, best_propr_m, wf_df):
    pass_rate = best_propr_m["pass_rate"]
    sh_ratio  = t1_oos_sh / base_oos_sh if base_oos_sh != 0 else 0.0

    print("\n" + "═"*62)
    print("VOL-SPIKE FILTER — FEASIBILITY VERDICT")
    print("═"*62)
    print(f"  {'Metric':<28} {'TSMOM base':>12}  {'+ Vol Filter':>12}")
    print(f"  {'─'*28} {'─'*12}  {'─'*12}")
    print(f"  {'OOS Sharpe (2024-2026)':<28} {base_oos_sh:>12.2f}  {t1_oos_sh:>12.2f}")
    print(f"  {'Max DD (OOS)':<28} {max_dd(pd.Series()):.0%}  (see above)")
    print(f"  {'Days > 3% loss (OOS)':<28} {base_br:>12d}  {t1_br:>12d}")
    print(f"  {'Days > 3% loss (2025)':<28} {base_2025_br:>12d}  {t1_2025_br:>12d}")
    print(f"  {'Propr pass rate (44 sims)':<28} {base_propr_m['pass_rate']:>11.0%}  "
          f"{pass_rate:>11.0%}  [{best_config}]")
    print(f"  {'  daily_limit fails':<28} {base_propr_m['fail_daily']:>12d}  "
          f"{best_propr_m['fail_daily']:>12d}")
    print(f"  {'  total_dd fails':<28} {base_propr_m['fail_total']:>12d}  "
          f"{best_propr_m['fail_total']:>12d}")

    print(f"\n  Sharpe retention: {sh_ratio:.1%} of base  (need > 70% = no >30% degradation)")

    # Walk-forward consistency
    wf_base  = wf_df[wf_df["config"] == "base"]
    wf_best  = wf_df[wf_df["config"] == best_config]
    folds_better_sharpe  = int((wf_best["sharpe"].values  > wf_base["sharpe"].values).sum())
    folds_fewer_breaches = int((wf_best["breach_days"].values < wf_base["breach_days"].values).sum())
    print(f"\n  Walk-forward ({best_config} vs base):")
    print(f"    Folds with higher Sharpe  : {folds_better_sharpe}/4")
    print(f"    Folds with fewer breaches : {folds_fewer_breaches}/4")

    if pass_rate >= 0.50 and sh_ratio >= 0.70:
        verdict = "IMPLEMENT"
        reason  = (f"Pass rate {pass_rate:.0%} ≥ 50% AND Sharpe retention "
                   f"{sh_ratio:.0%} ≥ 70% [{best_config}]")
    elif pass_rate >= 0.45 and sh_ratio >= 0.70:
        verdict = "WEAK"
        reason  = f"Pass rate {pass_rate:.0%} (45–50%) borderline [{best_config}]"
    elif sh_ratio < 0.70:
        verdict = "SKIP"
        reason  = f"Sharpe degraded {1 - sh_ratio:.0%} > 30% — filter too aggressive"
    else:
        verdict = "SKIP"
        reason  = f"Pass rate {pass_rate:.0%} < 45% — filter does not help enough"

    print(f"\n  VERDICT: {verdict}")
    print(f"  Reason : {reason}")
    print("═"*62)
    return verdict, best_config


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 64)
    print("VOL-SPIKE FILTER — TSMOM v2")
    print("=" * 64)

    close   = download_data()
    log_ret = np.log(close / close.shift(1))

    # ── Build positions: base + T1/T2/T3 ──────────────────────────────────
    print("\nBuilding positions...")
    base_pos = build_positions(close)
    filt_pos = {name: build_positions(close, cfg)
                for name, cfg in THRESHOLD_CONFIGS.items()}

    # ── Portfolio P&L ──────────────────────────────────────────────────────
    print("Computing P&L...")
    base_pnl = compute_portfolio_pnl(close, base_pos)
    filt_pnl = {name: compute_portfolio_pnl(close, pos)
                for name, pos in filt_pos.items()}

    oos_base     = base_pnl.loc[OOS_START:]
    y2025_base   = base_pnl.loc["2025-01-01":"2025-12-31"]
    base_oos_sh  = sharpe(oos_base)
    base_br      = count_breach_days(oos_base)
    base_2025_br = count_breach_days(y2025_base)

    # ── Spike bucket distribution (T1) ────────────────────────────────────
    buckets = spike_bucket_pct(log_ret, THRESHOLD_CONFIGS["T1"])
    print(f"\nSpike ratio distribution (T1 thresholds, all assets 2021-2026):")
    for tier, pct in buckets.items():
        print(f"  {tier:<10}: {pct:.1%} of days")

    # ── OOS metrics per config ────────────────────────────────────────────
    print(f"\n{'─'*64}")
    print(f"OOS PERFORMANCE (2024-2026)")
    print(f"{'─'*64}")
    print(f"  {'Config':<8} {'Sharpe':>8} {'MaxDD':>8} {'Breach(OOS)':>12} "
          f"{'Breach(2025)':>13} {'Sh%base':>8}")
    print(f"  {'─'*8} {'─'*8} {'─'*8} {'─'*12} {'─'*13} {'─'*8}")
    print(f"  {'base':<8} {base_oos_sh:>8.2f} {max_dd(oos_base):>8.1%} "
          f"{base_br:>12d} {base_2025_br:>13d} {'—':>8}")

    for name, pnl in filt_pnl.items():
        oos_pnl  = pnl.loc[OOS_START:]
        y2025    = pnl.loc["2025-01-01":"2025-12-31"]
        sh       = sharpe(oos_pnl)
        br       = count_breach_days(oos_pnl)
        br25     = count_breach_days(y2025)
        sh_pct   = sh / base_oos_sh if base_oos_sh != 0 else 0.0
        print(f"  {name:<8} {sh:>8.2f} {max_dd(oos_pnl):>8.1%} "
              f"{br:>12d} {br25:>13d} {sh_pct:>7.0%}")

    # ── Walk-forward ──────────────────────────────────────────────────────
    print(f"\n{'─'*64}")
    print("WALK-FORWARD (4 expanding folds)")
    print(f"{'─'*64}")
    wf_df = run_walk_forward(close, THRESHOLD_CONFIGS)
    print(f"  {'Fold':>4} {'OOS Period':<14} {'Config':<8} "
          f"{'Sharpe':>8} {'MaxDD':>8} {'Breaches':>9}")
    print(f"  {'─'*4} {'─'*14} {'─'*8} {'─'*8} {'─'*8} {'─'*9}")
    for _, row in wf_df.iterrows():
        print(f"  {row['fold']:>4d} {row['oos_period']:<14} {row['config']:<8} "
              f"{row['sharpe']:>8.2f} {row['max_dd']:>8.1%} {row['breach_days']:>9d}")

    # ── Propr simulations ─────────────────────────────────────────────────
    print(f"\n{'─'*64}")
    print(f"PROPR SIMULATIONS (44 paths, {SIM_START} → {SIM_END})")
    print(f"{'─'*64}")
    prices_sim = close  # full history — sim logic slices by start_date

    print("  Running base...")
    base_sim_df = run_propr_sims(prices_sim, base_pos, label="base", verbose=True)
    base_propr_m = sim_metrics(base_sim_df)

    sim_dfs = {}
    for name, pos in filt_pos.items():
        print(f"  Running {name}...")
        df = run_propr_sims(prices_sim, pos, label=name, verbose=True)
        sim_dfs[name] = df

    print(f"\n  {'Config':<8} {'PassRate':>9} {'Passes':>7} {'DailyFail':>10} "
          f"{'TotalFail':>10} {'MedianDD':>9}")
    print(f"  {'─'*8} {'─'*9} {'─'*7} {'─'*10} {'─'*10} {'─'*9}")
    all_metrics = {"base": base_propr_m}
    for name, df in sim_dfs.items():
        m = sim_metrics(df)
        all_metrics[name] = m
        print(f"  {name:<8} {m['pass_rate']:>9.0%} {m['pass_count']:>7d} "
              f"{m['fail_daily']:>10d} {m['fail_total']:>10d} "
              f"{m['median_max_dd']:>8.1%}")

    print(f"  {'base':<8} {base_propr_m['pass_rate']:>9.0%} "
          f"{base_propr_m['pass_count']:>7d} "
          f"{base_propr_m['fail_daily']:>10d} {base_propr_m['fail_total']:>10d} "
          f"{base_propr_m['median_max_dd']:>8.1%}")

    # Best config by pass rate
    best_config = max(THRESHOLD_CONFIGS.keys(),
                      key=lambda n: all_metrics[n]["pass_rate"])
    best_m      = all_metrics[best_config]
    t1_pnl      = filt_pnl["T1"]
    t1_oos_sh   = sharpe(t1_pnl.loc[OOS_START:])
    t1_br       = count_breach_days(t1_pnl.loc[OOS_START:])
    t1_2025_br  = count_breach_days(t1_pnl.loc["2025-01-01":"2025-12-31"])

    # ── Figure ──────────────────────────────────────────────────────────
    plot_results(close, base_pnl, t1_pnl, log_ret,
                 base_sim_df, sim_dfs)

    # ── Verdict ──────────────────────────────────────────────────────────
    verdict, best_cfg = print_verdict(
        base_oos_sh, t1_oos_sh,
        base_br, t1_br, base_2025_br, t1_2025_br,
        base_propr_m, best_config, best_m, wf_df,
    )

    return verdict, best_cfg


if __name__ == "__main__":
    main()
