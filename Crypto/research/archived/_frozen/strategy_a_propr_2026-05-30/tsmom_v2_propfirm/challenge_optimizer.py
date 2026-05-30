"""
Challenge Optimizer — Propr pass rate maximization for TSMOM v2
================================================================
The Propr challenge is an asymmetric game:
  Win  : equity ≥ 110% of start (profit target)
  Lose : equity ≤ 94% of start (6% total DD) OR any day loss > 3%
  Payout: binary — maximise P(pass), not Sharpe.

There is an optimal vol target that maximises P(pass). Lower is NOT
always safer: it reduces daily loss exposure but also reduces expected
gain, so the profit target takes longer (more draws from a negative-
drift period → higher cumulative ruin probability).

Three-part study:
  Part 1 — Vol target sweep: P(pass) across [0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20]
  Part 2 — Equity-adaptive sizing: scale up near profit target, scale down near DD limit
  Part 3 — Combined: best fixed vol + adaptive + T3 vol-spike filter

Run: python -m strategies.tsmom_v2_propfirm.challenge_optimizer
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
    from strategies.tsmom_v2_propfirm.vol_spike_filter import (
        compute_spike_multiplier, THRESHOLD_CONFIGS,
    )
except ImportError:
    def compute_signal(prices, lookback=28):
        lr  = np.log(prices / prices.shift(1))
        cum = lr.rolling(lookback).sum().shift(1)
        sig = (cum > 0).astype(float); sig[cum.isna()] = np.nan; return sig

    def apply_weekly_rebalance(signals, rebalance_weekday=0):
        mask = pd.Series(signals.index.dayofweek == rebalance_weekday, index=signals.index)
        return signals.where(mask).ffill()

    def compute_vol_scalars(lr, vol_target, vol_lookback=20):
        ann = lr.rolling(vol_lookback).std() * np.sqrt(365)
        return (vol_target / ann).shift(1).clip(0.1, 2.0)

    def compute_positions(signals, vol_scalars): return signals * vol_scalars

    UNIVERSE = [
        "BTC-USD","ETH-USD","SOL-USD","AVAX-USD","LINK-USD","ARB-USD",
        "MATIC-USD","OP-USD","DOGE-USD","ADA-USD","DOT-USD","UNI-USD","LTC-USD","BCH-USD",
    ]
    VOL_LOOKBACK_DAYS = 20

    def compute_spike_multiplier(log_ret, thresholds):
        vol5  = log_ret.rolling(5).std().shift(1)  * np.sqrt(365)
        vol20 = log_ret.rolling(20).std().shift(1) * np.sqrt(365)
        spike_ratio = (vol5 / vol20.replace(0, np.nan)).fillna(1.0)
        mult = pd.DataFrame(1.0, index=log_ret.index, columns=log_ret.columns)
        for thresh, m in thresholds: mult[spike_ratio >= thresh] = m
        is_mon = mult.index.dayofweek == 0
        locked = mult.copy(); locked[~is_mon] = np.nan
        return locked.ffill().fillna(1.0)

    THRESHOLD_CONFIGS = {"T3": [(1.1, 0.6), (1.4, 0.3), (1.8, 0.15)]}


# ── Constants ─────────────────────────────────────────────────────────────────
DATA_START  = "2021-01-01"
DATA_END    = "2026-05-14"
SIM_START   = "2025-01-06"
SIM_END     = "2025-11-03"

TRADING_DAYS  = 365
COST_PER_LEG  = 0.00085
INITIAL_EQ    = 5_000.0
PROFIT_TARGET = 0.10
MAX_DD_PCT    = 0.06
DAILY_LIMIT   = 0.03
GROSS_CAP     = 0.90

VOL_TARGETS = [0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20]

# Adaptive scale thresholds (per spec)
PROFIT_BOOST_THRESHOLD = 0.07   # within 3% of target → scale up
DD_FLOOR_1             = 0.02   # within 2% of DD limit → 0.30×
DD_FLOOR_2             = 0.03   # within 3% of DD limit → 0.50×
PROFIT_BOOST_SCALE     = 1.50
DD_FLOOR_1_SCALE       = 0.30
DD_FLOOR_2_SCALE       = 0.50

OUT_DIR = Path(__file__).parent
OUT_PNG = OUT_DIR / "challenge_optimizer_results.png"


# ── Data ──────────────────────────────────────────────────────────────────────
def download_data() -> pd.DataFrame:
    print(f"Downloading {len(UNIVERSE)}-asset universe ({DATA_START} → {DATA_END})...")
    raw   = yf.download(UNIVERSE, start=DATA_START, end=DATA_END,
                        auto_adjust=True, progress=False)
    close = raw["Close"].dropna(axis=1, how="all").ffill()
    if close.index.tz is not None:
        close.index = close.index.tz_convert(None)
    dropped = [t for t in UNIVERSE if t not in close.columns]
    print(f"  Available: {len(close.columns)} assets | Dropped: {dropped}")
    print(f"  Range    : {close.index[0].date()} → {close.index[-1].date()}"
          f"  ({len(close)} days)")
    return close


# ── Position building ─────────────────────────────────────────────────────────
def build_base_positions(close: pd.DataFrame,
                          vol_target: float) -> pd.DataFrame:
    """TSMOM v2 positions at a given vol target — no adaptive scaling."""
    lr      = np.log(close / close.shift(1))
    signals = compute_signal(close)
    scalars = compute_vol_scalars(lr, vol_target, VOL_LOOKBACK_DAYS)
    raw_pos = compute_positions(signals, scalars)
    return apply_weekly_rebalance(raw_pos).fillna(0.0)


def build_t3_positions(close: pd.DataFrame,
                        vol_target: float) -> pd.DataFrame:
    """TSMOM v2 with T3 vol-spike filter applied."""
    lr         = np.log(close / close.shift(1))
    base       = build_base_positions(close, vol_target)
    multiplier = compute_spike_multiplier(lr, THRESHOLD_CONFIGS["T3"])
    return (base * multiplier).fillna(0.0)


# ── Adaptive scale function ───────────────────────────────────────────────────
def get_adaptive_scale(equity: float, initial_equity: float) -> float:
    """
    Returns a position scale multiplier based on the challenge state.

    profit_buffer = how much profit has been made (as fraction of initial)
    dd_buffer     = distance from the 6% total-DD floor (as fraction of initial)

    Rule (per spec):
      profit > 7% → 1.5×   (3% away from target, go for the win)
      dd < 2%     → 0.3×   (within 2% of DD limit, protect aggressively)
      dd < 3%     → 0.5×   (within 3% of DD limit, reduce)
      else        → 1.0×
    """
    profit_buffer = (equity - initial_equity) / initial_equity
    min_equity    = initial_equity * (1.0 - MAX_DD_PCT)
    dd_buffer     = (equity - min_equity) / initial_equity

    if profit_buffer > PROFIT_BOOST_THRESHOLD:
        return PROFIT_BOOST_SCALE
    elif dd_buffer < DD_FLOOR_1:
        return DD_FLOOR_1_SCALE
    elif dd_buffer < DD_FLOOR_2:
        return DD_FLOOR_2_SCALE
    else:
        return 1.0


# ── Challenge simulation ───────────────────────────────────────────────────────
def _build_result(start, end, outcome, fail_reason, final_eq,
                  eq_curve, peak, trading_days):
    arr = np.array(eq_curve)
    hwm = np.maximum.accumulate(arr)
    dd  = (arr - hwm) / hwm
    return {
        "start_date":       start,
        "end_date":         end,
        "outcome":          outcome,
        "fail_reason":      fail_reason,
        "final_equity":     round(final_eq, 2),
        "max_drawdown_pct": float(-dd.min()),
        "days_elapsed":     len(eq_curve) - 1,
        "trading_days":     trading_days,
        "eq_at_fail":       round(final_eq, 2) if outcome == "FAIL" else np.nan,
        "equity_curve":     eq_curve,
        "scale_history":    [],    # filled only for adaptive sims
    }


def simulate_challenge(
    start_date:   pd.Timestamp,
    prices:       pd.DataFrame,
    positions_df: pd.DataFrame,
    adaptive:     bool = False,
) -> dict[str, Any]:
    """
    Simulate one Propr challenge attempt.

    positions_df : Monday-locked, ffilled position sizes (fraction of equity).
    adaptive     : if True, multiply Monday target sizes by get_adaptive_scale().
    """
    equity:    float            = INITIAL_EQ
    positions: dict[str, float] = {}
    eq_curve:  list[float]      = [INITIAL_EQ]
    scale_hist: list[tuple]     = []
    peak:      float            = INITIAL_EQ
    trading_days: int           = 0

    sim_dates = prices.index[prices.index >= start_date]

    for i, date in enumerate(sim_dates):
        eq_day_start = equity

        # 1. MTM
        if i > 0 and positions:
            prev = sim_dates[i - 1]
            for ticker, qty in positions.items():
                if ticker not in prices.columns: continue
                p_now  = prices.at[date, ticker]
                p_prev = prices.at[prev,  ticker]
                if not (pd.isna(p_now) or pd.isna(p_prev)):
                    equity += qty * (p_now - p_prev)

        # 2. Monday rebalance
        if date.dayofweek == 0 and date in positions_df.index:
            sizes_row = positions_df.loc[date]
            adapt_scale = get_adaptive_scale(equity, INITIAL_EQ) if adaptive else 1.0
            if adaptive:
                scale_hist.append((date, adapt_scale, equity))

            target: dict[str, float] = {}
            for ticker in prices.columns:
                if ticker not in sizes_row.index: continue
                sz = sizes_row[ticker]
                px = prices.at[date, ticker]
                if not pd.isna(sz) and sz > 0 and not pd.isna(px) and px > 0:
                    target[ticker] = equity * float(sz) * adapt_scale

            total_notional = sum(target.values())
            if total_notional > equity * GROSS_CAP:
                scale  = equity * GROSS_CAP / total_notional
                target = {k: v * scale for k, v in target.items()}

            for ticker in set(positions) | set(target):
                if ticker not in prices.columns: continue
                px = prices.at[date, ticker]
                if pd.isna(px) or px <= 0: continue
                old_n = positions.get(ticker, 0.0) * px
                new_n = target.get(ticker, 0.0)
                equity -= abs(new_n - old_n) * COST_PER_LEG

            positions = {t: n / prices.at[date, t]
                         for t, n in target.items()
                         if prices.at[date, t] > 0}
            trading_days += 1

        # 3. Daily loss limit
        if i > 0 and (equity - eq_day_start) / eq_day_start < -DAILY_LIMIT:
            eq_curve.append(equity)
            r = _build_result(start_date, date, "FAIL", "daily_limit",
                              equity, eq_curve, peak, trading_days)
            r["scale_history"] = scale_hist
            return r

        # 4. Total DD
        if equity <= INITIAL_EQ * (1.0 - MAX_DD_PCT):
            eq_curve.append(equity)
            r = _build_result(start_date, date, "FAIL", "total_drawdown",
                              equity, eq_curve, peak, trading_days)
            r["scale_history"] = scale_hist
            return r

        # 5. Profit target
        if equity >= INITIAL_EQ * (1.0 + PROFIT_TARGET):
            eq_curve.append(equity)
            r = _build_result(start_date, date, "PASS", None,
                              equity, eq_curve, peak, trading_days)
            r["scale_history"] = scale_hist
            return r

        if equity > peak: peak = equity
        eq_curve.append(equity)

    last = sim_dates[-1] if len(sim_dates) > 0 else start_date
    r = _build_result(start_date, last, "INCOMPLETE", None,
                      equity, eq_curve, peak, trading_days)
    r["scale_history"] = scale_hist
    return r


def run_propr_sims(prices, positions_df, adaptive=False,
                   label="", verbose=False):
    """Run 44 weekly-start Propr sims; return (summary_df, results_list)."""
    start_dates = pd.date_range(start=SIM_START, end=SIM_END, freq="W-MON")
    results = []
    for sd in start_dates:
        if verbose: print(f"  [{label}] {sd.date()}", flush=True)
        results.append(simulate_challenge(sd, prices, positions_df, adaptive=adaptive))
    rows = [{k: v for k, v in r.items() if k not in ("equity_curve", "scale_history")}
            for r in results]
    return pd.DataFrame(rows), results


def sim_metrics(df: pd.DataFrame) -> dict[str, Any]:
    n = len(df)
    pass_m  = df["outcome"] == "PASS"
    pass_r  = float(pass_m.sum()) / n
    fail_d  = int((df["fail_reason"] == "daily_limit").sum())
    fail_t  = int((df["fail_reason"] == "total_drawdown").sum())
    avg_days_pass = float(df.loc[pass_m, "days_elapsed"].mean()) if pass_m.any() else np.nan
    return dict(
        pass_rate=pass_r,
        pass_count=int(pass_m.sum()),
        fail_daily=fail_d,
        fail_total=fail_t,
        avg_days_pass=avg_days_pass,
        median_max_dd=float(df["max_drawdown_pct"].median()),
        score=pass_r / avg_days_pass if (pass_r > 0 and not np.isnan(avg_days_pass)) else 0.0,
    )


# ── Plotting ──────────────────────────────────────────────────────────────────
def plot_results(vol_sweep_metrics, fixed_df, adaptive_df, combined_df,
                 all_results_fixed, all_results_adaptive, close):
    fig = plt.figure(figsize=(16, 12))
    gs  = gridspec.GridSpec(2, 2, figure=fig, hspace=0.42, wspace=0.38)
    ax1 = fig.add_subplot(gs[0, 0])   # pass rate vs vol target
    ax2 = fig.add_subplot(gs[0, 1])   # fail mode breakdown
    ax3 = fig.add_subplot(gs[1, 0])   # sample equity paths
    ax4 = fig.add_subplot(gs[1, 1])   # adaptive scale over example run

    vts        = [m["vol_target"]   for m in vol_sweep_metrics]
    pass_rates = [m["pass_rate"]*100 for m in vol_sweep_metrics]
    scores     = [m["score"]*1000   for m in vol_sweep_metrics]

    # ── Panel 1: Pass rate vs vol target ─────────────────────────────────
    ax1.plot(vts, pass_rates, "o-", lw=2, color="steelblue", label="Pass rate %")
    ax1.axhline(50, color="red",    ls="--", lw=1, label="50% target")
    ax1.axhline(45, color="orange", ls=":",  lw=1, label="45% weak")
    ax1b = ax1.twinx()
    ax1b.plot(vts, scores, "s--", lw=1.2, color="green", alpha=0.7, label="Score×1000")
    ax1b.set_ylabel("Score (pass/day×1000)", color="green", fontsize=8)
    ax1.set_title("Pass Rate vs Vol Target", fontsize=10, fontweight="bold")
    ax1.set_xlabel("Vol target (annualized)")
    ax1.set_ylabel("Pass rate (%)")
    lines1, _ = ax1.get_legend_handles_labels()
    lines2, _ = ax1b.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, [l.get_label() for l in lines1 + lines2], fontsize=8)
    ax1.grid(True, alpha=0.3)

    # ── Panel 2: Fail mode breakdown ─────────────────────────────────────
    x     = np.arange(len(vts))
    width = 0.25
    daily = [m["fail_daily"]  for m in vol_sweep_metrics]
    total = [m["fail_total"]  for m in vol_sweep_metrics]
    passes = [m["pass_count"] for m in vol_sweep_metrics]
    ax2.bar(x - width, passes, width, label="Pass",       color="steelblue", alpha=0.85)
    ax2.bar(x,         daily,  width, label="Daily limit", color="tomato",    alpha=0.85)
    ax2.bar(x + width, total,  width, label="Total DD",    color="darkorange", alpha=0.85)
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{v:.0%}" for v in vts], fontsize=8)
    ax2.set_title("Fail Mode Breakdown (44 sims each)", fontsize=10, fontweight="bold")
    ax2.set_xlabel("Vol target")
    ax2.set_ylabel("Count")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.2)

    # ── Panel 3: 10 sample equity paths ──────────────────────────────────
    n_paths = min(10, len(all_results_fixed))
    colors_f = plt.cm.Blues(np.linspace(0.4, 0.9, n_paths))
    colors_a = plt.cm.Greens(np.linspace(0.4, 0.9, n_paths))
    for i, (rf, ra) in enumerate(zip(all_results_fixed[:n_paths],
                                      all_results_adaptive[:n_paths])):
        ec_f = np.array(rf["equity_curve"]) / INITIAL_EQ
        ec_a = np.array(ra["equity_curve"]) / INITIAL_EQ
        label_f = "Fixed" if i == 0 else None
        label_a = "Adaptive" if i == 0 else None
        ax3.plot(ec_f, color=colors_f[i], lw=0.9, alpha=0.8, label=label_f)
        ax3.plot(ec_a, color=colors_a[i], lw=0.9, alpha=0.8, label=label_a, ls="--")
    ax3.axhline(1.10, color="green", lw=1.2, ls="--", label="Profit target +10%")
    ax3.axhline(0.94, color="red",   lw=1.2, ls="--", label="DD limit -6%")
    ax3.set_title("Sample Equity Paths (10 paths: fixed vs adaptive)", fontsize=10, fontweight="bold")
    ax3.set_xlabel("Days elapsed")
    ax3.set_ylabel("Equity / Initial")
    ax3.legend(fontsize=8, ncol=2)
    ax3.grid(True, alpha=0.3)

    # ── Panel 4: Adaptive scale over an example run ───────────────────────
    # Find the example with the most scale changes
    best_example = max(all_results_adaptive,
                       key=lambda r: len(r.get("scale_history", [])))
    sh = best_example.get("scale_history", [])
    if sh:
        dates    = [s[0] for s in sh]
        scales   = [s[1] for s in sh]
        equities = [s[2] for s in sh]
        ax4b = ax4.twinx()
        ax4.step(range(len(scales)), scales, where="post",
                 color="steelblue", lw=1.8, label="Scale factor")
        ax4b.plot(range(len(equities)), equities, color="darkorange",
                  lw=1, alpha=0.7, label="Equity")
        ax4b.axhline(INITIAL_EQ * 1.07, color="green", ls="--", lw=0.8)
        ax4b.axhline(INITIAL_EQ * 0.97, color="orange", ls="--", lw=0.8)
        ax4b.axhline(INITIAL_EQ * 0.96, color="red", ls="--", lw=0.8)
        ax4.axhline(PROFIT_BOOST_SCALE, color="green",  ls=":", lw=0.8)
        ax4.axhline(DD_FLOOR_2_SCALE,   color="orange", ls=":", lw=0.8)
        ax4.axhline(DD_FLOOR_1_SCALE,   color="red",    ls=":", lw=0.8)
        ax4.set_title("Adaptive Scale Factor — Example Challenge Run", fontsize=10, fontweight="bold")
        ax4.set_xlabel("Monday rebalances")
        ax4.set_ylabel("Position scale", color="steelblue")
        ax4b.set_ylabel("Equity ($)", color="darkorange")
        lines1, _ = ax4.get_legend_handles_labels()
        lines2, _ = ax4b.get_legend_handles_labels()
        ax4.legend(lines1 + lines2, [l.get_label() for l in lines1 + lines2], fontsize=8)
    else:
        ax4.text(0.5, 0.5, "No adaptive scale changes\nin this sim window",
                 ha="center", va="center", transform=ax4.transAxes, fontsize=10)
    ax4.grid(True, alpha=0.3)

    fig.suptitle("Challenge Optimizer — Vol Target Sweep + Adaptive Kelly Sizing",
                 fontsize=13, fontweight="bold")
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    print(f"\nFigure saved → {OUT_PNG}")
    plt.close(fig)


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 68)
    print("CHALLENGE OPTIMIZER — TSMOM v2 PROPR PASS RATE MAXIMIZATION")
    print("=" * 68)

    close = download_data()
    lr    = np.log(close / close.shift(1))

    # ══════════════════════════════════════════════════════════════
    # PART 1 — Vol target sweep
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'═'*68}")
    print("PART 1 — VOL TARGET SWEEP")
    print(f"{'═'*68}")

    vol_sweep = []
    all_positions = {}

    for vt in VOL_TARGETS:
        print(f"  vol_target={vt:.2f}: building positions & running 44 sims...", flush=True)
        pos = build_base_positions(close, vt)
        all_positions[vt] = pos
        df, _ = run_propr_sims(close, pos, label=f"{vt:.2f}")
        m = sim_metrics(df)
        m["vol_target"] = vt
        vol_sweep.append(m)
        print(f"    Pass: {m['pass_rate']:.0%}  DailyFails: {m['fail_daily']}  "
              f"TotalDD: {m['fail_total']}  AvgDaysPass: {m['avg_days_pass']:.0f}d  "
              f"Score: {m['score']:.5f}", flush=True)

    # Print vol sweep table
    print(f"\n{'─'*68}")
    hdr = (f"  {'VT':>5} | {'Pass%':>6} | {'DailyF':>7} | {'TotalF':>7} | "
           f"{'AvgDays|Pass':>13} | {'MedianDD':>9} | {'Score':>8}")
    print(hdr)
    print(f"  {'─'*5}─{'─'*6}─{'─'*7}─{'─'*7}─{'─'*13}─{'─'*9}─{'─'*8}")
    for m in vol_sweep:
        adp = f"{m['avg_days_pass']:.0f}d" if not np.isnan(m.get('avg_days_pass', np.nan)) else "—"
        print(f"  {m['vol_target']:>5.2f} | {m['pass_rate']:>6.0%} | "
              f"{m['fail_daily']:>7d} | {m['fail_total']:>7d} | "
              f"{adp:>13} | {m['median_max_dd']:>8.1%} | {m['score']:>8.5f}")

    best_vt_idx = max(range(len(vol_sweep)), key=lambda i: vol_sweep[i]["pass_rate"])
    best_vt     = vol_sweep[best_vt_idx]["vol_target"]
    best_m      = vol_sweep[best_vt_idx]
    print(f"\n  Best vol target by pass rate: {best_vt:.2f}  "
          f"({best_m['pass_rate']:.0%} pass, {best_m['fail_daily']} daily fails)")

    # ══════════════════════════════════════════════════════════════
    # PART 2 — Equity-adaptive sizing
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'═'*68}")
    print(f"PART 2 — EQUITY-ADAPTIVE SIZING (base vol = {best_vt:.2f})")
    print(f"{'═'*68}")
    print(f"  Rule: profit>7% → ×{PROFIT_BOOST_SCALE}  |  "
          f"dd<3% → ×{DD_FLOOR_2_SCALE}  |  dd<2% → ×{DD_FLOOR_1_SCALE}")

    pos_best = all_positions[best_vt]
    print(f"  Running fixed {best_vt:.2f} (baseline for comparison)...", flush=True)
    df_fixed,    results_fixed    = run_propr_sims(close, pos_best, adaptive=False,
                                                    label=f"fixed_{best_vt:.2f}", verbose=True)
    m_fixed = sim_metrics(df_fixed)

    print(f"  Running adaptive {best_vt:.2f}...", flush=True)
    df_adaptive, results_adaptive = run_propr_sims(close, pos_best, adaptive=True,
                                                    label=f"adaptive_{best_vt:.2f}", verbose=True)
    m_adaptive = sim_metrics(df_adaptive)

    print(f"\n  {'Config':<20} {'Pass%':>6} {'DailyF':>8} {'TotalF':>8} "
          f"{'AvgDays|P':>10} {'Score':>8}")
    print(f"  {'─'*20} {'─'*6} {'─'*8} {'─'*8} {'─'*10} {'─'*8}")
    for label, m in [(f"Fixed {best_vt:.2f}", m_fixed), (f"Adaptive {best_vt:.2f}", m_adaptive)]:
        adp = f"{m['avg_days_pass']:.0f}d" if not np.isnan(m.get('avg_days_pass', np.nan)) else "—"
        print(f"  {label:<20} {m['pass_rate']:>6.0%} {m['fail_daily']:>8d} "
              f"{m['fail_total']:>8d} {adp:>10} {m['score']:>8.5f}")

    # ══════════════════════════════════════════════════════════════
    # PART 3 — Combined: best vol + adaptive + T3 filter
    # ══════════════════════════════════════════════════════════════
    print(f"\n{'═'*68}")
    print(f"PART 3 — COMBINED (vol={best_vt:.2f} + adaptive + T3 filter)")
    print(f"{'═'*68}")

    pos_t3 = build_t3_positions(close, best_vt)
    print(f"  Running T3-filtered positions (non-adaptive)...", flush=True)
    df_t3only, _ = run_propr_sims(close, pos_t3, adaptive=False,
                                   label="T3_fixed", verbose=True)
    m_t3only = sim_metrics(df_t3only)

    print(f"  Running T3-filtered + adaptive...", flush=True)
    df_combined, results_combined = run_propr_sims(close, pos_t3, adaptive=True,
                                                    label="T3_adaptive", verbose=True)
    m_combined = sim_metrics(df_combined)

    # ── Final comparison table ──────────────────────────────────────────
    print(f"\n{'═'*68}")
    print("FINAL COMPARISON")
    print(f"{'═'*68}")
    print(f"  {'Config':<28} {'Pass%':>6} {'DailyF':>8} {'TotalF':>8} "
          f"{'AvgDays|P':>10} {'Score':>8}")
    print(f"  {'─'*28} {'─'*6} {'─'*8} {'─'*8} {'─'*10} {'─'*8}")
    baseline_15 = vol_sweep[VOL_TARGETS.index(0.15)] if 0.15 in VOL_TARGETS else None
    configs_to_print = []
    if baseline_15:
        configs_to_print.append((f"Base 15% (original)", baseline_15))
    configs_to_print += [
        (f"Best fixed {best_vt:.2f}",  m_fixed),
        (f"Adaptive {best_vt:.2f}",    m_adaptive),
        (f"T3 only {best_vt:.2f}",     m_t3only),
        (f"Combined (best)",           m_combined),
    ]
    for label, m in configs_to_print:
        adp = f"{m['avg_days_pass']:.0f}d" if not np.isnan(m.get('avg_days_pass', np.nan)) else "—"
        print(f"  {label:<28} {m['pass_rate']:>6.0%} {m['fail_daily']:>8d} "
              f"{m['fail_total']:>8d} {adp:>10} {m['score']:>8.5f}")

    # ── Verdict ──────────────────────────────────────────────────────────
    best_combined_rate = m_combined["pass_rate"]
    best_fixed_rate    = m_fixed["pass_rate"]
    print(f"\n{'═'*68}")
    print("VERDICT")
    print(f"{'═'*68}")
    print(f"  Best fixed vol target  : {best_vt:.2f}  ({best_fixed_rate:.0%} pass rate)")
    print(f"  Adaptive improvement   : {m_adaptive['pass_rate'] - m_fixed['pass_rate']:+.0%}"
          f"  ({m_adaptive['pass_rate']:.0%} adaptive vs {m_fixed['pass_rate']:.0%} fixed)")
    print(f"  T3 filter improvement  : {m_t3only['pass_rate'] - m_fixed['pass_rate']:+.0%}")
    print(f"  Combined pass rate     : {best_combined_rate:.0%}")

    if best_combined_rate >= 0.50:
        verdict = "IMPLEMENT"
        reason  = (f"Combined pass rate {best_combined_rate:.0%} ≥ 50% — "
                   f"optimal_vol={best_vt:.2f} + adaptive + T3")
    elif best_combined_rate >= 0.45:
        verdict = "WEAK"
        reason  = f"Combined pass rate {best_combined_rate:.0%} (45–50%) borderline"
    else:
        verdict = "SKIP"
        reason  = (f"Best combined pass rate {best_combined_rate:.0%} < 45% — "
                   "strategy return distribution fundamentally incompatible with "
                   f"3% daily limit at any vol target in {VOL_TARGETS}")

    print(f"\n  VERDICT: {verdict}")
    print(f"  Reason : {reason}")
    print(f"{'═'*68}")

    # ── Figure ──────────────────────────────────────────────────────────
    print("\nGenerating figure...")
    plot_results(vol_sweep, df_fixed, df_adaptive, df_combined,
                 results_fixed, results_adaptive, close)

    return verdict, best_vt, m_combined


if __name__ == "__main__":
    main()
