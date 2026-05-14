#!/usr/bin/env python3
"""
strategies/combined_portfolio/feasibility.py

Combined Portfolio — TSMOM Long + Short-Only
============================================
Long leg  : BTC, ETH, AVAX, LINK, DOGE, ADA, DOT, LTC, BCH, OP
            (long when 28-day signal = +1)
Short leg : SOL, LINK, BCH, OP
            (short when 28-day signal = -1)
SOL       : short-only (never long)

Hypothesis: combining confirmed short signals (t > 2.0 OOS) with the
TSMOM v2 long leg should improve Sharpe via −0.37 correlation.

Run: python -m strategies.combined_portfolio.feasibility
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

warnings.filterwarnings("ignore")

# ── Constants ──────────────────────────────────────────────────────────────────

UNIVERSE: list[str] = [
    "BTC-USD", "ETH-USD", "AVAX-USD", "LINK-USD", "DOGE-USD",
    "ADA-USD", "DOT-USD", "LTC-USD", "BCH-USD", "OP-USD", "SOL-USD",
]
# Assets that can be SHORT when signal = -1
SHORT_CAPABLE: set[str] = {"SOL-USD", "LINK-USD", "BCH-USD", "OP-USD"}
# Assets that are never long (short-only)
SOL_ONLY_SHORT: set[str] = {"SOL-USD"}

DATA_START   = "2020-07-01"   # extra lookback for 2021 warm-up
TEST_START   = "2024-01-01"
TEST_END     = "2026-05-14"

LOOKBACK        = 28
VOL_WINDOW      = 20
COST_PER_LEG    = 0.00085   # 0.085% one-way (0.17% round trip)
GROSS_CAP       = 0.90
TRADING_DAYS    = 365        # crypto 24/7

# 5 allocation combos (vol_long, vol_short)
ALLOC_COMBOS: list[tuple[float, float]] = [
    (0.15, 0.05),  # W1: small short
    (0.15, 0.10),  # W2: medium short
    (0.15, 0.15),  # W3: equal vol
    (0.12, 0.12),  # W4: reduced both
    (0.10, 0.15),  # W5: short-heavy
]
COMBO_LABELS: list[str] = ["W1", "W2", "W3", "W4", "W5"]

# Walk-forward windows: (train_start, train_end, test_start, test_end)
WF_WINDOWS: list[tuple[str, str, str, str]] = [
    ("2021-01-01", "2022-12-31", "2023-01-01", "2023-12-31"),   # W1
    ("2021-01-01", "2023-12-31", "2024-01-01", "2024-12-31"),   # W2
    ("2021-01-01", "2023-06-30", "2023-07-01", "2024-06-30"),   # W3 rolling
    ("2021-01-01", "2024-12-31", "2025-01-01", "2026-05-14"),   # W4
]

# Propr challenge
PROPR_INITIAL      = 5_000.0
PROPR_TARGET_PCT   = 0.10
PROPR_TOTAL_DD_PCT = 0.06
PROPR_DAILY_DD_PCT = 0.03
SIM_START          = "2025-01-06"
SIM_END            = "2025-11-03"

OUT_DIR = Path(__file__).parent
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Data ───────────────────────────────────────────────────────────────────────

def download_data(start: str = DATA_START, end: str = TEST_END) -> pd.DataFrame:
    """Download daily adjusted close for all 11 assets."""
    print(f"Downloading {len(UNIVERSE)} assets ({start} → {end})...")
    raw = yf.download(
        UNIVERSE, start=start, end=end,
        auto_adjust=True, progress=False, interval="1d",
    )
    closes: pd.DataFrame
    if isinstance(raw.columns, pd.MultiIndex):
        closes = raw["Close"]
    else:
        closes = raw[["Close"]]

    if closes.index.tz is not None:
        closes.index = closes.index.tz_convert(None)

    # Forward-fill gaps (max 2 bars for OP-USD sparse early history)
    closes = closes.ffill(limit=2)
    # Drop columns that are almost entirely NaN
    closes = closes.dropna(axis=1, thresh=int(len(closes) * 0.60))

    dropped = [t for t in UNIVERSE if t not in closes.columns]
    print(f"  Available : {sorted(closes.columns.tolist())}")
    print(f"  Dropped   : {dropped}")
    print(f"  Range     : {closes.index[0].date()} → {closes.index[-1].date()}")
    return closes


# ── Signal and Position Helpers ────────────────────────────────────────────────

def build_positions(
    prices: pd.DataFrame,
    vol_long: float,
    vol_short: float,
    lookback: int = LOOKBACK,
    vol_window: int = VOL_WINDOW,
) -> pd.DataFrame:
    """
    Build daily signed position weights (+= long, -= short).
    Signal = sign(cumulative 28-day log return), shifted 1 day (no look-ahead).
    Weekly rebalance (Monday only, then ffill). Gross cap 90%.

    Parameters
    ----------
    prices    : daily close price DataFrame (index=date, columns=tickers)
    vol_long  : annualised vol target for long positions
    vol_short : annualised vol target for short positions
    lookback  : momentum lookback in days (28)
    vol_window: rolling window for realised vol (20)

    Returns
    -------
    DataFrame of signed daily position weights, same shape as prices.
    """
    lr = np.log(prices / prices.shift(1))

    # 28-day cum log return, shifted 1 day — no look-ahead
    cum28  = lr.rolling(lookback).sum().shift(1)
    signal = np.sign(cum28)  # +1, 0, -1  (NaN first ~29 days)

    # Realised vol, shifted 1 day
    ann_vol = lr.rolling(vol_window).std().shift(1) * np.sqrt(TRADING_DAYS)
    ann_vol = ann_vol.replace(0.0, np.nan)

    vs_long  = (vol_long  / ann_vol).clip(0.1, 2.0)
    vs_short = (vol_short / ann_vol).clip(0.1, 2.0)

    pos = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)

    for col in prices.columns:
        if col not in signal.columns:
            continue
        sig       = signal[col]
        can_long  = col not in SOL_ONLY_SHORT
        can_short = col in SHORT_CAPABLE

        col_pos = pd.Series(np.nan, index=prices.index, dtype=float)
        valid   = sig.notna()

        if can_long:
            lm = valid & (sig == 1.0)
            col_pos[lm] = (
                vs_long.loc[lm, col] if col in vs_long.columns else vol_long
            )

        if can_short:
            sm = valid & (sig == -1.0)
            col_pos[sm] = -(
                vs_short.loc[sm, col] if col in vs_short.columns else vol_short
            )

        # Flat: valid signal but neither long nor short
        flat_m = valid & ~(
            (can_long  & (sig == 1.0)) |
            (can_short & (sig == -1.0))
        )
        col_pos[flat_m] = 0.0

        pos[col] = col_pos

    # Weekly rebalance: keep Monday values, forward-fill through week
    is_monday = pos.index.dayofweek == 0
    pos_weekly = pos.copy()
    pos_weekly[~is_monday] = np.nan
    pos_weekly = pos_weekly.ffill()

    # Gross cap: scale each day so sum(|position|) ≤ 0.90
    gross = pos_weekly.abs().sum(axis=1)
    scale = (GROSS_CAP / gross).clip(upper=1.0).replace(
        [np.inf, -np.inf], 0.0
    )
    pos_capped = pos_weekly.multiply(scale, axis=0).fillna(0.0)
    return pos_capped


def build_tsmom_v2_positions(
    prices: pd.DataFrame,
    vol_long: float = 0.15,
) -> pd.DataFrame:
    """
    Replicate TSMOM v2 long-only baseline (10 assets, no SOL, no shorts).
    Uses same signal/sizing methodology for apples-to-apples comparison.
    """
    TSMOM_V2 = [
        "BTC-USD", "ETH-USD", "AVAX-USD", "LINK-USD", "DOGE-USD",
        "ADA-USD", "DOT-USD", "LTC-USD", "BCH-USD", "OP-USD",
    ]
    avail = [a for a in TSMOM_V2 if a in prices.columns]
    p     = prices[avail]
    lr    = np.log(p / p.shift(1))

    cum28   = lr.rolling(LOOKBACK).sum().shift(1)
    signal  = (cum28 > 0).astype(float)
    signal[cum28.isna()] = np.nan

    ann_vol = lr.rolling(VOL_WINDOW).std().shift(1) * np.sqrt(TRADING_DAYS)
    ann_vol = ann_vol.replace(0.0, np.nan)
    vs      = (vol_long / ann_vol).clip(0.1, 2.0)
    raw_pos = (signal * vs).fillna(0.0)

    is_monday = raw_pos.index.dayofweek == 0
    pos_w = raw_pos.copy()
    pos_w[~is_monday] = np.nan
    pos_w = pos_w.ffill().fillna(0.0)

    gross  = pos_w.abs().sum(axis=1)
    scale  = (GROSS_CAP / gross).clip(upper=1.0).replace([np.inf, -np.inf], 0.0)
    return pos_w.multiply(scale, axis=0).fillna(0.0)


# ── P&L Computation ────────────────────────────────────────────────────────────

def compute_pnl(
    prices: pd.DataFrame,
    positions: pd.DataFrame,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Daily net P&L decomposed into long and short legs.
    Short P&L: pnl = position × daily_return (position < 0 → profit when asset falls).
    Costs: COST_PER_LEG × |Δposition| per rebalance.

    Returns
    -------
    (pnl_long, pnl_short, pnl_total) — daily return series
    """
    arith_ret = prices.pct_change()

    # Position held during day = position set at prior close
    held      = positions.shift(1).fillna(0.0)
    gross_pnl = held * arith_ret

    # Costs on position changes (paid once per leg direction change)
    turnover = positions.diff().fillna(positions).abs()
    costs    = turnover * COST_PER_LEG

    net = gross_pnl - costs

    long_mask  = held > 0
    short_mask = held < 0

    pnl_long  = (net * long_mask).sum(axis=1)
    pnl_short = (net * short_mask).sum(axis=1)
    pnl_total = net.sum(axis=1)

    return pnl_long, pnl_short, pnl_total


def performance_metrics(
    rets: pd.Series,
    label: str = "",
) -> dict[str, Any]:
    """Standard annualised metrics from a daily return series."""
    r = rets.dropna()
    empty: dict[str, Any] = dict(
        label=label, sharpe=np.nan, ann_return=np.nan,
        max_dd=np.nan, win_rate=np.nan,
        max_daily_loss=np.nan, days_gt_3pct_loss=0,
    )
    if len(r) < 10 or r.std() == 0:
        return empty

    ann_ret   = float(r.mean() * TRADING_DAYS)
    sharpe    = float((r.mean() / r.std()) * np.sqrt(TRADING_DAYS))
    eq        = (1 + r).cumprod()
    hwm       = eq.cummax()
    max_dd    = float(((eq - hwm) / hwm).min())
    win_rate  = float((r > 0).mean())
    max_loss  = float(r.min())
    days_gt3  = int((r < -0.03).sum())

    return dict(
        label=label, sharpe=sharpe, ann_return=ann_ret,
        max_dd=max_dd, win_rate=win_rate,
        max_daily_loss=max_loss, days_gt_3pct_loss=days_gt3,
    )


# ── Allocation Sweep ───────────────────────────────────────────────────────────

def run_allocation_sweep(prices: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Test 5 (vol_long, vol_short) combos; evaluate OOS Sharpe on test set.

    Returns list of result dicts, one per combo.
    """
    print("\nAllocation sweep (5 combos):")
    results: list[dict[str, Any]] = []

    for (vl, vs), lbl in zip(ALLOC_COMBOS, COMBO_LABELS):
        print(f"  {lbl}: vol_long={vl:.2f}, vol_short={vs:.2f}...", end=" ", flush=True)
        pos   = build_positions(prices, vl, vs)
        pl, ps, pt = compute_pnl(prices, pos)

        oos_pnl = pt.loc[TEST_START:TEST_END].dropna()
        m       = performance_metrics(oos_pnl, lbl)

        results.append(dict(
            label=lbl, vol_long=vl, vol_short=vs,
            pnl_long=pl, pnl_short=ps, pnl_total=pt,
            positions=pos, metrics_oos=m,
        ))
        print(f"Sharpe={m['sharpe']:.2f}, MaxDD={m['max_dd']:.1%}")

    return results


# ── Walk-Forward ───────────────────────────────────────────────────────────────

def run_walk_forward(
    prices: pd.DataFrame,
    vol_long: float,
    vol_short: float,
) -> list[dict[str, Any]]:
    """
    4 specific OOS windows. Positions computed only on data ≤ test_end
    to prevent any look-ahead.

    Returns list of window dicts with oos_sharpe, oos_return, oos_maxdd.
    """
    wf_results: list[dict[str, Any]] = []

    for i, (tr_s, tr_e, te_s, te_e) in enumerate(WF_WINDOWS, 1):
        p_wf    = prices[prices.index <= te_e]
        pos     = build_positions(p_wf, vol_long, vol_short)
        _, _, pt = compute_pnl(p_wf, pos)

        oos = pt.loc[te_s:te_e].dropna()
        m   = performance_metrics(oos, f"WF-W{i}")

        wf_results.append(dict(
            window=i,
            train=f"{tr_s} → {tr_e}",
            test=f"{te_s} → {te_e}",
            oos_sharpe=m["sharpe"],
            oos_return=m["ann_return"],
            oos_maxdd=m["max_dd"],
            n_days=len(oos),
        ))

    return wf_results


# ── Decomposition Analysis ─────────────────────────────────────────────────────

def decomp_analysis(
    prices: pd.DataFrame,
    positions: pd.DataFrame,
    tsmom_v2_positions: pd.DataFrame,
) -> dict[str, Any]:
    """
    On the OOS test set:
    - Decompose P&L into long and short legs
    - Compute long/short correlation
    - Identify worst 10 TSMOM v2 days; measure short-leg performance on those days
    """
    pl, ps, pt = compute_pnl(prices, positions)
    _, _, tsmom_ret = compute_pnl(prices, tsmom_v2_positions)

    test_mask = (pt.index >= TEST_START) & (pt.index <= TEST_END)
    tl        = pl[test_mask].dropna()
    ts        = ps[test_mask].dropna()
    tt        = pt[test_mask].dropna()
    tv2       = tsmom_ret[test_mask].dropna()

    # Correlation: long vs short leg
    common      = tl.index.intersection(ts.index)
    long_short_corr = float(tl.loc[common].corr(ts.loc[common]))

    # Worst 10 TSMOM v2 days
    worst10_idx        = tv2.nsmallest(10).index
    worst10_tsmom      = tv2.loc[worst10_idx]
    worst10_combined   = tt.reindex(worst10_idx).fillna(0.0)
    worst10_short_leg  = ts.reindex(worst10_idx).fillna(0.0)

    return dict(
        pnl_long=tl,
        pnl_short=ts,
        pnl_total=tt,
        tsmom_oos=tv2,
        long_short_corr=long_short_corr,
        worst10_tsmom=worst10_tsmom,
        worst10_combined=worst10_combined,
        worst10_short_leg=worst10_short_leg,
    )


# ── Propr Challenge Simulation ─────────────────────────────────────────────────

def _build_sim_result(
    start: pd.Timestamp,
    end: pd.Timestamp,
    outcome: str,
    fail_reason: str | None,
    final_equity: float,
    equity_curve: list[float],
    peak: float,
) -> dict[str, Any]:
    arr     = np.array(equity_curve)
    hwm_arr = np.maximum.accumulate(arr)
    max_dd  = float(((arr - hwm_arr) / hwm_arr).min())
    return dict(
        start_date=start,
        end_date=end,
        outcome=outcome,
        fail_reason=fail_reason,
        final_equity=round(final_equity, 2),
        peak_equity=round(peak, 2),
        max_dd_pct=-max_dd,
        days_elapsed=len(equity_curve) - 1,
        equity_curve=equity_curve,
    )


def simulate_one_challenge(
    start_date: pd.Timestamp,
    prices: pd.DataFrame,
    positions: pd.DataFrame,
    initial_equity: float = PROPR_INITIAL,
) -> dict[str, Any]:
    """
    Simulate one Propr challenge using pre-computed signed positions.

    MTM: equity += signed_qty × (p_now - p_prev)
    Works correctly for longs (qty > 0) and shorts (qty < 0).
    HWM is static at initial_equity (Propr rule).

    Parameters
    ----------
    start_date  : Monday the challenge begins
    prices      : full daily close price DataFrame
    positions   : pre-computed weekly signed position weights
    initial_equity : starting capital

    Returns
    -------
    Result dict with outcome, fail_reason, equity_curve, etc.
    """
    equity      = initial_equity
    hwm         = initial_equity
    peak        = initial_equity
    equity_curve: list[float] = [initial_equity]
    pos_dict: dict[str, float] = {}   # ticker → signed quantity
    rebal_count = 0

    sim_dates = prices.index[prices.index >= start_date]

    for i, date in enumerate(sim_dates):
        eq_day_start = equity

        # 1. MTM on carried positions (signed qty × price change)
        if i > 0 and pos_dict:
            prev_date = sim_dates[i - 1]
            for ticker, qty in pos_dict.items():
                if ticker not in prices.columns:
                    continue
                p_now  = prices.at[date,      ticker]
                p_prev = prices.at[prev_date, ticker]
                if not (pd.isna(p_now) or pd.isna(p_prev)):
                    equity += qty * (p_now - p_prev)

        # 2. Weekly rebalance on Monday
        if date.dayofweek == 0 and date in positions.index:
            row = positions.loc[date]
            target_notional: dict[str, float] = {}

            for ticker in prices.columns:
                if ticker not in row.index:
                    continue
                sz = float(row[ticker])
                px = prices.at[date, ticker]
                if pd.isna(sz) or pd.isna(px) or px <= 0 or sz == 0.0:
                    continue
                target_notional[ticker] = equity * sz   # signed notional

            # Gross cap: sum(|notional|) ≤ equity × 0.90
            gross_n = sum(abs(n) for n in target_notional.values())
            if gross_n > equity * GROSS_CAP and gross_n > 0:
                scl = equity * GROSS_CAP / gross_n
                target_notional = {k: v * scl for k, v in target_notional.items()}

            # Costs: COST_PER_LEG × |Δnotional|
            for ticker in set(pos_dict) | set(target_notional):
                if ticker not in prices.columns:
                    continue
                px = prices.at[date, ticker]
                if pd.isna(px) or px <= 0:
                    continue
                old_n = pos_dict.get(ticker, 0.0) * px
                new_n = target_notional.get(ticker, 0.0)
                equity -= abs(new_n - old_n) * COST_PER_LEG

            # Convert signed notional to signed quantity
            pos_dict = {
                t: n / prices.at[date, t]
                for t, n in target_notional.items()
                if prices.at[date, t] > 0
            }
            rebal_count += 1

        # 3. Daily loss limit
        if i > 0 and eq_day_start > 0:
            daily_ret = (equity - eq_day_start) / eq_day_start
            if daily_ret < -PROPR_DAILY_DD_PCT:
                equity_curve.append(equity)
                return _build_sim_result(
                    start_date, date, "FAIL", "daily_limit",
                    equity, equity_curve, peak,
                )

        # 4. Total drawdown vs static HWM
        if equity <= hwm * (1.0 - PROPR_TOTAL_DD_PCT):
            equity_curve.append(equity)
            return _build_sim_result(
                start_date, date, "FAIL", "total_drawdown",
                equity, equity_curve, peak,
            )

        # 5. Profit target
        if equity >= hwm * (1.0 + PROPR_TARGET_PCT):
            equity_curve.append(equity)
            return _build_sim_result(
                start_date, date, "PASS", None,
                equity, equity_curve, peak,
            )

        peak = max(peak, equity)
        equity_curve.append(equity)

    last = sim_dates[-1] if len(sim_dates) > 0 else start_date
    return _build_sim_result(
        start_date, last, "INCOMPLETE", None,
        equity, equity_curve, peak,
    )


def run_propr_simulations(
    prices: pd.DataFrame,
    vol_long: float,
    vol_short: float,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """
    Run 44 Propr challenge simulations (every Monday 2025-01-06 → 2025-11-03).
    Positions are pre-computed on the full price history (no look-ahead).

    Returns
    -------
    (summary_df, full_results_list)
    """
    positions   = build_positions(prices, vol_long, vol_short)
    start_dates = pd.date_range(SIM_START, SIM_END, freq="W-MON")

    print(f"\nRunning {len(start_dates)} Propr simulations "
          f"(vol_long={vol_long:.2f}, vol_short={vol_short:.2f})...", flush=True)

    results: list[dict[str, Any]] = []
    for sd in start_dates:
        results.append(simulate_one_challenge(sd, prices, positions))

    rows = [{k: v for k, v in r.items() if k != "equity_curve"} for r in results]
    df   = pd.DataFrame(rows)
    return df, results


# ── Plotting ───────────────────────────────────────────────────────────────────

def plot_results(
    prices: pd.DataFrame,
    best: dict[str, Any],
    sweep_results: list[dict[str, Any]],
    tsmom_v2_positions: pd.DataFrame,
    decomp: dict[str, Any],
    propr_df: pd.DataFrame,
    save_path: Path,
) -> None:
    """
    5-subplot results figure:
    (1) Equity curves: combined vs TSMOM alone vs short-only
    (2) Allocation sweep: OOS Sharpe per combo
    (3) P&L decomposition: long vs short leg cumulative
    (4) Worst 10 TSMOM v2 days: combined portfolio vs baseline
    (5) Propr pass rates: combined vs prior strategies
    """
    fig = plt.figure(figsize=(20, 18))
    gs  = fig.add_gridspec(3, 2, hspace=0.40, wspace=0.32)

    # ── Panel 1: Equity curves ─────────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, :])

    tt_oos = best["pnl_total"].loc[TEST_START:TEST_END].dropna()
    ax1.plot(
        (1 + tt_oos).cumprod().index,
        (1 + tt_oos).cumprod().values,
        color="#2c3e50", lw=2.0,
        label=f"Combined (Sh={best['metrics_oos']['sharpe']:.2f})",
    )

    _, _, tsmom_rets = compute_pnl(prices, tsmom_v2_positions)
    tsmom_oos = tsmom_rets.loc[TEST_START:TEST_END].dropna()
    tsmom_m   = performance_metrics(tsmom_oos, "tsmom_v2")
    ax1.plot(
        (1 + tsmom_oos).cumprod().index,
        (1 + tsmom_oos).cumprod().values,
        color="#3498db", lw=1.5, linestyle="--",
        label=f"TSMOM v2 alone (Sh={tsmom_m['sharpe']:.2f})",
    )

    ts_oos = best["pnl_short"].loc[TEST_START:TEST_END].dropna()
    short_m = performance_metrics(ts_oos, "short_only")
    ax1.plot(
        (1 + ts_oos).cumprod().index,
        (1 + ts_oos).cumprod().values,
        color="#e74c3c", lw=1.2, linestyle=":",
        label=f"Short leg only (Sh={short_m['sharpe']:.2f})",
    )

    ax1.axhline(1.0, color="gray", lw=0.8, linestyle=":")
    ax1.set_title("Panel 1 — Equity Curves: OOS Test Set (2024–2026)", fontsize=11)
    ax1.set_ylabel("Cumulative Return")
    ax1.legend(fontsize=9)
    ax1.grid(alpha=0.3)

    # ── Panel 2: Allocation sweep ──────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[1, 0])

    sh_vals   = [r["metrics_oos"]["sharpe"] for r in sweep_results]
    labels_sw = [
        f"W{i+1}\nVL={r['vol_long']:.2f}\nVS={r['vol_short']:.2f}"
        for i, r in enumerate(sweep_results)
    ]
    best_sh = max(sh_vals)
    bar_clr = ["#27ae60" if abs(s - best_sh) < 1e-6 else "#95a5a6" for s in sh_vals]

    bars2 = ax2.bar(range(len(sh_vals)), sh_vals, color=bar_clr, edgecolor="white", width=0.6)
    ax2.axhline(0, color="black", lw=0.8)
    ax2.set_xticks(range(len(sh_vals)))
    ax2.set_xticklabels(labels_sw, fontsize=8)
    ax2.set_ylabel("OOS Sharpe")
    ax2.set_title("Panel 2 — Allocation Sweep: OOS Sharpe", fontsize=11)
    for bar, s in zip(bars2, sh_vals):
        yoff = 0.03 if s >= 0 else -0.10
        ax2.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + yoff,
            f"{s:.2f}", ha="center", va="bottom", fontsize=9, fontweight="bold",
        )
    ax2.grid(axis="y", alpha=0.3)

    # ── Panel 3: P&L decomposition ─────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 1])

    tl = decomp["pnl_long"].dropna()
    ts = decomp["pnl_short"].dropna()
    tt = decomp["pnl_total"].dropna()

    ax3.plot(
        (1 + tl).cumprod().index, (1 + tl).cumprod().values,
        color="#27ae60", lw=1.5, label=f"Long leg (Sh={performance_metrics(tl)['sharpe']:.2f})",
    )
    ax3.plot(
        (1 + ts).cumprod().index, (1 + ts).cumprod().values,
        color="#e74c3c", lw=1.5, label=f"Short leg (Sh={performance_metrics(ts)['sharpe']:.2f})",
    )
    ax3.plot(
        (1 + tt).cumprod().index, (1 + tt).cumprod().values,
        color="#2c3e50", lw=2.0, label=f"Combined (Sh={performance_metrics(tt)['sharpe']:.2f})",
    )
    ax3.axhline(1.0, color="gray", lw=0.8, linestyle=":")
    ax3.set_title("Panel 3 — P&L Decomposition (OOS 2024–2026)", fontsize=11)
    ax3.set_ylabel("Cumulative Return")
    ax3.legend(fontsize=9)
    ax3.grid(alpha=0.3)

    # ── Panel 4: Worst 10 TSMOM days ──────────────────────────────────────────
    ax4 = fig.add_subplot(gs[2, 0])

    w10_tsmom    = decomp["worst10_tsmom"].values * 100
    w10_combined = decomp["worst10_combined"].values * 100
    w10_short    = decomp["worst10_short_leg"].values * 100
    x_pos        = np.arange(len(w10_tsmom))
    w            = 0.27

    ax4.bar(x_pos - w, w10_tsmom,    width=w, color="#3498db",         label="TSMOM v2 alone")
    ax4.bar(x_pos,     w10_combined, width=w, color="#2c3e50",         label="Combined portfolio")
    ax4.bar(x_pos + w, w10_short,    width=w, color="#e74c3c", alpha=0.75, label="Short leg")
    ax4.axhline(0,   color="black",  lw=0.8)
    ax4.axhline(-3,  color="orange", lw=1.2, linestyle="--", label="-3% Propr daily limit")

    date_labels = [d.strftime("%Y-%m-%d") for d in decomp["worst10_tsmom"].index]
    ax4.set_xticks(x_pos)
    ax4.set_xticklabels(date_labels, rotation=42, ha="right", fontsize=7)
    ax4.set_ylabel("Daily Return (%)")
    ax4.set_title("Panel 4 — Worst 10 TSMOM Days:\nShort Leg as Hedge", fontsize=11)
    ax4.legend(fontsize=8)
    ax4.grid(axis="y", alpha=0.3)

    # ── Panel 5: Propr pass rates ──────────────────────────────────────────────
    ax5 = fig.add_subplot(gs[2, 1])

    combined_pass = float((propr_df["outcome"] == "PASS").mean()) * 100
    strat_names   = ["TSMOM\nv2 low\n(34%)", "TSMOM\nv2 high\n(45%)", "Short-only\n(34%)", "Combined"]
    pass_rates    = [34.0, 45.0, 34.0, combined_pass]
    bar_clr5      = [
        "#95a5a6", "#95a5a6", "#95a5a6",
        "#27ae60" if combined_pass >= 45 else ("#f39c12" if combined_pass >= 34 else "#e74c3c"),
    ]

    bars5 = ax5.bar(strat_names, pass_rates, color=bar_clr5, edgecolor="white", width=0.55)
    ax5.axhline(45, color="green", lw=1.2, linestyle="--", alpha=0.7, label="45% target")
    ax5.axhline(34, color="gray",  lw=1.0, linestyle=":",  alpha=0.7, label="34% baseline")
    for bar, pct in zip(bars5, pass_rates):
        ax5.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1.0,
            f"{pct:.0f}%", ha="center", va="bottom", fontsize=11, fontweight="bold",
        )
    ax5.set_ylabel("Pass Rate (%)")
    ax5.set_ylim(0, max(pass_rates) * 1.35)
    ax5.set_title("Panel 5 — Propr Pass Rates\nvs Prior Strategies", fontsize=11)
    ax5.legend(fontsize=9)
    ax5.grid(axis="y", alpha=0.3)

    fig.suptitle(
        f"Combined Portfolio — TSMOM Long + Short-Only  "
        f"(best: vol_long={best['vol_long']:.2f}, vol_short={best['vol_short']:.2f})",
        fontsize=13, fontweight="bold",
    )
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nFigure saved → {save_path}")


# ── Verdict ────────────────────────────────────────────────────────────────────

def print_verdict(
    best: dict[str, Any],
    wf_results: list[dict[str, Any]],
    propr_df: pd.DataFrame,
    decomp: dict[str, Any],
    tsmom_v2_metrics: dict[str, Any],
) -> None:
    """Print structured verdict block matching spec format."""
    m = best["metrics_oos"]

    combined_pass_rate  = float((propr_df["outcome"] == "PASS").mean())
    combined_daily_fail = int(
        ((propr_df["outcome"] == "FAIL") & (propr_df["fail_reason"] == "daily_limit")).sum()
    )
    combined_total_fail = int(
        ((propr_df["outcome"] == "FAIL") & (propr_df["fail_reason"] == "total_drawdown")).sum()
    )
    avg_days_to_pass: float | None = None
    pass_rows = propr_df[propr_df["outcome"] == "PASS"]
    if not pass_rows.empty:
        avg_days_to_pass = float(pass_rows["days_elapsed"].mean())

    wf_stable = sum(
        1 for w in wf_results
        if w["oos_sharpe"] is not None and not np.isnan(w["oos_sharpe"])
        and w["oos_sharpe"] > 0.5
    )
    wf_any_negative = any(
        w["oos_sharpe"] is not None and not np.isnan(w["oos_sharpe"])
        and w["oos_sharpe"] < 0
        for w in wf_results
    )

    ml = performance_metrics(decomp["pnl_long"],  "long_leg")
    ms = performance_metrics(decomp["pnl_short"], "short_leg")

    worst_short_avg = float(decomp["worst10_short_leg"].mean()) * 100
    hedge_label     = "hedge WORKS ✓" if worst_short_avg > 0 else "hedge FAILS ✗"

    print("\n" + "═" * 60)
    print("COMBINED PORTFOLIO — TSMOM LONG + SHORT-ONLY")
    print("═" * 60)
    print(f"Best allocation         : vol_long={best['vol_long']:.2f}, vol_short={best['vol_short']:.2f}")
    print()
    print("OOS Performance (2024-2026):")
    print(f"  Portfolio Sharpe      : {m['sharpe']:.2f}")
    print(f"  Long leg Sharpe       : {ml['sharpe']:.2f}")
    print(f"  Short leg Sharpe      : {ms['sharpe']:.2f}")
    print(f"  Max DD                : {m['max_dd']:.1%}")
    print(f"  Max daily loss        : {m['max_daily_loss']:.1%}")
    print(f"  Days > 3% loss        : {m['days_gt_3pct_loss']}")
    print()
    print(f"Walk-forward            : {wf_stable}/4 windows Sharpe > 0.5")
    for w in wf_results:
        sh   = w["oos_sharpe"]
        flag = " ★" if sh > 0.5 else (" ✗ UNSTABLE" if sh < 0 else "")
        print(f"  W{w['window']} ({w['test']}): Sharpe={sh:.2f}{flag}")
    if wf_any_negative:
        print("  ⚠ At least one window is UNSTABLE (Sharpe < 0)")
    print()
    print(f"Propr pass rate         : {combined_pass_rate:.0%} (vs TSMOM alone: 34-45%)")
    print(f"Daily limit fails       : {combined_daily_fail}/44 (vs 23-26/44)")
    print(f"Total DD fails          : {combined_total_fail}/44")
    adp_str = f"{avg_days_to_pass:.0f}" if avg_days_to_pass else "n/a"
    print(f"Avg days to pass        : {adp_str}")
    print()
    print("Correlation decomp:")
    print(f"  Long/short corr       : {decomp['long_short_corr']:.2f}")
    print(f"  On worst TSMOM days   : short leg avg = {worst_short_avg:+.1f}%  ({hedge_label})")
    print()

    # ── Verdict logic ──────────────────────────────────────────────────────────
    if (
        m["sharpe"] >= 1.5
        and combined_pass_rate >= 0.45
        and wf_stable >= 3
    ):
        verdict = "DEPLOY"
    elif m["sharpe"] >= 1.0 or combined_pass_rate >= 0.40:
        verdict = "PROMISING"
    elif (
        not np.isnan(tsmom_v2_metrics["sharpe"])
        and m["sharpe"] >= tsmom_v2_metrics["sharpe"]
    ):
        verdict = "WEAK"
    else:
        verdict = "SKIP"

    print(f"VERDICT: {verdict}")
    print()

    if verdict == "DEPLOY":
        print('Action: "Implement combined portfolio in execution layer.')
        print("Add short positions for SOL/LINK/BCH/OP when signal=-1.")
        print(f'Expected portfolio Sharpe: {m["sharpe"]:.2f}"')
    elif verdict == "PROMISING":
        print('Action: "Add HMM regime filter: only activate short leg')
        print("in BEAR/RANGE regime (when shorts are most likely to profit).")
        print('In BULL regime: long-only like current v2."')
    elif verdict == "WEAK":
        print('Action: "Short signals are real but not large enough to')
        print("overcome costs at portfolio level. Accept TSMOM v2 long-only.")
        print(f'TSMOM v2 baseline Sharpe: {tsmom_v2_metrics["sharpe"]:.2f}"')
    else:
        print('Action: "The short leg hurts more than it helps. Skip.')
        print(f"Combined Sharpe ({m['sharpe']:.2f}) < TSMOM v2 alone "
              f"({tsmom_v2_metrics['sharpe']:.2f}). Stick with long-only v2.")

    print("═" * 60)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:  # noqa: PLR0914
    prices = download_data()

    # TSMOM v2 baseline (long-only, 10 assets)
    print("\nBuilding TSMOM v2 baseline (long-only)...")
    tsmom_v2_pos  = build_tsmom_v2_positions(prices)
    _, _, tv2_ret = compute_pnl(prices, tsmom_v2_pos)
    tv2_oos       = tv2_ret.loc[TEST_START:TEST_END].dropna()
    tsmom_v2_m    = performance_metrics(tv2_oos, "TSMOM_v2")
    print(f"  TSMOM v2 OOS Sharpe: {tsmom_v2_m['sharpe']:.2f}")

    # Allocation sweep
    sweep_results = run_allocation_sweep(prices)

    # Best combo by OOS Sharpe
    best = max(sweep_results, key=lambda r: r["metrics_oos"]["sharpe"])
    vl, vs = best["vol_long"], best["vol_short"]
    print(f"\nBest combo: vol_long={vl:.2f}, vol_short={vs:.2f} "
          f"→ OOS Sharpe={best['metrics_oos']['sharpe']:.2f}")

    # Walk-forward (4 windows)
    print("\nWalk-forward validation (4 windows):")
    wf_results = run_walk_forward(prices, vl, vs)
    for w in wf_results:
        sh   = w["oos_sharpe"]
        flag = " ✗ UNSTABLE" if sh < 0 else (" ★" if sh > 0.5 else "")
        print(f"  W{w['window']} test {w['test']}: Sharpe={sh:.2f}{flag}")

    # P&L decomposition
    print("\nP&L decomposition analysis...")
    best_pos = build_positions(prices, vl, vs)
    decomp   = decomp_analysis(prices, best_pos, tsmom_v2_pos)
    long_short_corr = decomp["long_short_corr"]
    print(f"  Long/short corr: {long_short_corr:.2f}")
    print(f"  Worst-10 TSMOM days — short leg avg: "
          f"{decomp['worst10_short_leg'].mean()*100:+.1f}%")

    # Propr challenge (44 simulations)
    propr_df, _ = run_propr_simulations(prices, vl, vs)
    n_pass        = int((propr_df["outcome"] == "PASS").sum())
    n_daily_fail  = int(
        ((propr_df["outcome"] == "FAIL") & (propr_df["fail_reason"] == "daily_limit")).sum()
    )
    print(f"  PASS: {n_pass}/44  |  daily_limit fails: {n_daily_fail}/44")

    # Plot
    plot_results(
        prices, best, sweep_results, tsmom_v2_pos,
        decomp, propr_df,
        OUT_DIR / "feasibility_results.png",
    )

    # Final verdict
    print_verdict(best, wf_results, propr_df, decomp, tsmom_v2_m)


if __name__ == "__main__":
    main()
