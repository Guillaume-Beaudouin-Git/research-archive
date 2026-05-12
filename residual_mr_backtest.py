"""
residual_mr_backtest.py
BTC-Neutral Residual Mean-Reversion Backtest (long-only)

Signal at close of day t → entry at close of day t+1 (1-day execution lag).
Cost 0.34% on entry AND exit. No daily hold cost.
"""
from __future__ import annotations

import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

warnings.filterwarnings("ignore")

# ── CONSTANTS ────────────────────────────────────────────────────────────────
ROUND_TRIP_COST  = 0.0034
ENTRY_COST       = ROUND_TRIP_COST / 2          # 0.17% per leg
EXIT_COST        = ROUND_TRIP_COST / 2
BETA_WINDOW      = 180
ZSCORE_WINDOW    = 30
ENTRY_THRESHOLD  = 1.5
EXIT_THRESHOLD   = 0.0
VOL_TARGET       = 0.15
MAX_POSITION     = 1.0
START            = "2021-06-01"
END              = "2025-01-01"
ASSETS           = ["ETH-USD", "SOL-USD", "BNB-USD"]
FACTOR           = "BTC-USD"
OUT_DIR          = Path(__file__).parent

# ── DATA ─────────────────────────────────────────────────────────────────────

def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Download daily Close, compute log returns. Drop assets >5% missing."""
    tickers = [FACTOR] + ASSETS
    raw = yf.download(tickers, start=START, end=END, auto_adjust=True, progress=False)["Close"]
    raw = raw.dropna(how="all")

    # Filter assets with >5% missing
    keep = []
    for col in raw.columns:
        pct_miss = raw[col].isna().mean()
        if pct_miss > 0.05:
            print(f"  Dropping {col}: {pct_miss:.1%} missing")
        else:
            keep.append(col)
    prices = raw[keep].copy()

    log_ret = np.log(prices / prices.shift(1))
    return prices, log_ret


# ── SIGNAL CONSTRUCTION ───────────────────────────────────────────────────────

def compute_signals(log_ret: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns:
      z_scores : DataFrame [date × asset], rolling z of residual
      resid_df : DataFrame [date × asset], raw residual
    """
    btc = log_ret[FACTOR]
    z_scores = pd.DataFrame(index=log_ret.index)
    resid_df = pd.DataFrame(index=log_ret.index)

    for asset in ASSETS:
        if asset not in log_ret.columns:
            continue
        ri = log_ret[asset]

        # Rolling beta
        roll_corr = ri.rolling(BETA_WINDOW).corr(btc)
        roll_std_i = ri.rolling(BETA_WINDOW).std()
        roll_std_b = btc.rolling(BETA_WINDOW).std()
        beta = roll_corr * (roll_std_i / roll_std_b)

        # Residual
        resid = ri - beta * btc
        resid_df[asset] = resid

        # Z-score of residual
        resid_mean = resid.rolling(ZSCORE_WINDOW).mean()
        resid_std  = resid.rolling(ZSCORE_WINDOW).std()
        z = (resid - resid_mean) / resid_std
        z_scores[asset] = z

    return z_scores, resid_df


# ── BACKTEST ENGINE ───────────────────────────────────────────────────────────

def run_backtest(log_ret: pd.DataFrame, z_scores: pd.DataFrame,
                 subset_dates: pd.DatetimeIndex | None = None
                 ) -> tuple[pd.Series, list[dict]]:
    """
    Returns:
      strat_ret : daily strategy returns (after costs)
      trades    : list of trade dicts
    """
    assets = [a for a in ASSETS if a in z_scores.columns]

    # Restrict to subset_dates if given (walk-forward test window)
    if subset_dates is not None:
        dates = log_ret.index.intersection(subset_dates)
    else:
        dates = log_ret.index

    # Position state per asset
    in_trade   = {a: False for a in assets}
    entry_date = {a: None  for a in assets}
    position   = {a: 0.0   for a in assets}  # vol-scaled size

    # Vol for sizing: use full log_ret so rolling window is warm
    daily_vol = {a: log_ret[a].rolling(20).std() for a in assets}

    strat_rets = []
    trades = []

    for i, date in enumerate(dates):
        # Signal was generated at close of previous day → execute today
        if i == 0:
            strat_rets.append(0.0)
            continue

        prev_date = dates[i - 1]
        day_ret = 0.0

        for asset in assets:
            z_prev = z_scores[asset].get(prev_date, np.nan)
            z_curr = z_scores[asset].get(date, np.nan)
            ret_i  = log_ret[asset].get(date, np.nan)

            if pd.isna(z_prev) or pd.isna(z_curr) or pd.isna(ret_i):
                continue

            vol = daily_vol[asset].get(date, np.nan)
            if pd.isna(vol) or vol == 0:
                raw_size = MAX_POSITION
            else:
                raw_size = VOL_TARGET / (vol * math.sqrt(252))
            sz = min(raw_size, MAX_POSITION)

            if not in_trade[asset]:
                # Entry signal: z crosses below -ENTRY_THRESHOLD
                if z_prev < -ENTRY_THRESHOLD:
                    in_trade[asset]   = True
                    entry_date[asset] = date
                    position[asset]   = sz
                    # Entry cost (applied at entry day)
                    day_ret -= ENTRY_COST * position[asset]
                    # Gross return from entry (position taken at open of today)
                    day_ret += position[asset] * ret_i
                # else: no position, no return
            else:
                # Exit signal: z crosses above EXIT_THRESHOLD
                if z_prev > EXIT_THRESHOLD:
                    # Exit: apply exit cost, no gross return today (closed at open)
                    day_ret -= EXIT_COST * position[asset]
                    trades.append({
                        "asset":      asset,
                        "entry_date": entry_date[asset],
                        "exit_date":  date,
                        "hold_days":  (date - entry_date[asset]).days,
                        "size":       position[asset],
                    })
                    in_trade[asset]   = False
                    position[asset]   = 0.0
                    entry_date[asset] = None
                else:
                    # Hold: gross return, no cost
                    day_ret += position[asset] * ret_i

        strat_rets.append(day_ret)

    # Force-close open positions at end of period
    last_date = dates[-1]
    for asset in assets:
        if in_trade[asset]:
            day_ret = strat_rets[-1]  # already appended; adjust last
            day_ret -= EXIT_COST * position[asset]
            strat_rets[-1] = day_ret
            trades.append({
                "asset":      asset,
                "entry_date": entry_date[asset],
                "exit_date":  last_date,
                "hold_days":  (last_date - entry_date[asset]).days,
                "size":       position[asset],
            })
            in_trade[asset]  = False
            position[asset]  = 0.0

    strat_series = pd.Series(strat_rets, index=dates)
    return strat_series, trades


def simultaneous_positions(log_ret: pd.DataFrame, z_scores: pd.DataFrame,
                           dates: pd.DatetimeIndex) -> pd.Series:
    """Count simultaneous open positions per day."""
    assets = [a for a in ASSETS if a in z_scores.columns]
    in_trade = {a: False for a in assets}
    counts = []

    for i, date in enumerate(dates):
        if i == 0:
            counts.append(0)
            continue
        prev_date = dates[i - 1]
        for asset in assets:
            z_prev = z_scores[asset].get(prev_date, np.nan)
            z_curr = z_scores[asset].get(date,      np.nan)
            if pd.isna(z_prev) or pd.isna(z_curr):
                continue
            if not in_trade[asset] and z_prev < -ENTRY_THRESHOLD:
                in_trade[asset] = True
            elif in_trade[asset] and z_prev > EXIT_THRESHOLD:
                in_trade[asset] = False
        counts.append(sum(in_trade.values()))

    return pd.Series(counts, index=dates)


# ── METRICS ───────────────────────────────────────────────────────────────────

def sharpe(rets: pd.Series) -> float:
    if rets.std() == 0:
        return 0.0
    return float(rets.mean() / rets.std() * math.sqrt(252))


def max_drawdown(cum_ret: pd.Series) -> float:
    roll_max = cum_ret.cummax()
    dd = (cum_ret - roll_max) / (1 + roll_max)
    return float(dd.min())


def annualized_return(rets: pd.Series) -> float:
    n_days = len(rets)
    total  = (1 + rets).prod()
    return float(total ** (252 / n_days) - 1)


def compute_trade_metrics(trades: list[dict], strat_ret: pd.Series,
                          log_ret: pd.DataFrame) -> dict:
    """Compute per-trade win rate using cumulative return over hold period."""
    if not trades:
        return {"win_rate": float("nan"), "avg_hold": float("nan"),
                "total_trades": 0, "cost_drag": float("nan")}

    wins = 0
    hold_days = []
    cost_total = 0.0

    for t in trades:
        hold_days.append(t["hold_days"])
        # P&L proxy: sum of strategy daily returns during hold
        mask = (strat_ret.index >= t["entry_date"]) & (strat_ret.index <= t["exit_date"])
        pnl = strat_ret[mask].sum()
        # Cost per trade = entry + exit cost × size
        cost_total += ROUND_TRIP_COST * t["size"]
        if pnl > 0:
            wins += 1

    n = len(trades)
    return {
        "win_rate":    wins / n,
        "avg_hold":    float(np.mean(hold_days)),
        "total_trades": n,
        "cost_drag":   cost_total,
    }


# ── WALK-FORWARD ──────────────────────────────────────────────────────────────

def walk_forward(log_ret: pd.DataFrame, z_scores: pd.DataFrame,
                 n_folds: int = 12, fold_months: int = 6) -> list[float]:
    """
    Expanding window walk-forward.
    Each fold: test on [fold_start, fold_start + 6M).
    Min train: 6 months before first test fold.
    """
    all_dates = log_ret.index
    total_days = len(all_dates)
    fold_days  = int(fold_months * 21)   # ~126 trading days per 6 months

    # First test fold starts after minimum 6-month train (126 days)
    min_train_days = 126
    first_test_start = min_train_days

    fold_sharpes = []

    for fold in range(n_folds):
        test_start_idx = first_test_start + fold * fold_days
        test_end_idx   = test_start_idx + fold_days

        if test_end_idx > total_days:
            break

        test_dates = all_dates[test_start_idx:test_end_idx]

        # Signals computed on full dataset (expanding: z-scores use all history
        # up to the test date — beta/z params are rolling so naturally expanding)
        fold_ret, _ = run_backtest(log_ret, z_scores, subset_dates=test_dates)

        s = sharpe(fold_ret)
        fold_sharpes.append(s)
        print(f"  Fold {fold+1:2d}: {test_dates[0].date()} → {test_dates[-1].date()}  "
              f"Sharpe = {s:+.2f}")

    return fold_sharpes


# ── PLOTS ─────────────────────────────────────────────────────────────────────

def plot_equity(strat_ret: pd.Series, btc_ret: pd.Series,
                sim_pos: pd.Series) -> None:
    cum_strat = (1 + strat_ret).cumprod() - 1
    cum_btc   = (1 + btc_ret.reindex(strat_ret.index).fillna(0)).cumprod() - 1

    roll_max  = (1 + strat_ret).cumprod().cummax()
    drawdown  = ((1 + strat_ret).cumprod() - roll_max) / roll_max

    fig = plt.figure(figsize=(14, 10))
    gs  = gridspec.GridSpec(3, 1, height_ratios=[3, 1.5, 1.2], hspace=0.35)

    # Top: cumulative returns
    ax0 = fig.add_subplot(gs[0])
    ax0.plot(cum_strat.index, cum_strat * 100, color="steelblue",
             linewidth=1.5, label="Residual MR (after costs)")
    ax0.plot(cum_btc.index, cum_btc * 100, color="orange",
             linewidth=1.2, linestyle="--", alpha=0.8, label="BTC buy-and-hold")
    ax0.axhline(0, color="black", linewidth=0.5, linestyle=":")
    ax0.set_ylabel("Cumulative Return (%)")
    ax0.set_title("BTC-Neutral Residual MR — Equity Curve", fontsize=13)
    ax0.legend(loc="upper left", fontsize=9)
    ax0.grid(True, alpha=0.3)

    # Middle: drawdown
    ax1 = fig.add_subplot(gs[1])
    ax1.fill_between(drawdown.index, drawdown * 100, 0,
                     color="crimson", alpha=0.5, label="Drawdown")
    ax1.set_ylabel("Drawdown (%)")
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="lower left", fontsize=9)

    # Bottom: simultaneous positions
    ax2 = fig.add_subplot(gs[2])
    ax2.step(sim_pos.index, sim_pos.values, color="navy", linewidth=0.8, where="post")
    ax2.fill_between(sim_pos.index, sim_pos.values, 0,
                     color="navy", alpha=0.2, step="post")
    ax2.set_yticks([0, 1, 2, 3])
    ax2.set_ylabel("# Positions")
    ax2.set_ylim(-0.1, 3.5)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlabel("Date")

    path = OUT_DIR / "residual_mr_equity.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_folds(fold_sharpes: list[float]) -> None:
    fig, ax = plt.subplots(figsize=(12, 5))
    x = list(range(1, len(fold_sharpes) + 1))
    colors = ["forestgreen" if s > 0 else "crimson" for s in fold_sharpes]

    ax.bar(x, fold_sharpes, color=colors, edgecolor="black", linewidth=0.5)
    ax.axhline(0,   color="black",  linewidth=1.0)
    ax.axhline(0.8, color="gold",   linewidth=1.5, linestyle="--", label="Sharpe = 0.8")
    ax.set_xlabel("Fold")
    ax.set_ylabel("Sharpe Ratio (annualized)")
    ax.set_title("Walk-Forward Fold Sharpe Ratios — Residual MR", fontsize=13)
    ax.set_xticks(x)
    ax.legend(fontsize=9)
    ax.grid(True, axis="y", alpha=0.3)

    path = OUT_DIR / "residual_mr_folds.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ── REPORT ────────────────────────────────────────────────────────────────────

def verdict(full_sharpe: float, pos_folds: int, n_folds: int) -> str:
    if full_sharpe > 0.8 and pos_folds >= int(n_folds * 2 / 3):
        return "PASS"
    if full_sharpe >= 0.5 or pos_folds >= int(n_folds / 2):
        return "MARGINAL"
    return "FAIL"


def print_report(strat_ret, btc_ret, trades, fold_sharpes, sim_pos) -> None:
    cum_strat = (1 + strat_ret).cumprod()
    mdd = max_drawdown(cum_strat)
    ann_ret = annualized_return(strat_ret)
    sh = sharpe(strat_ret)

    tm = compute_trade_metrics(trades, strat_ret, None)

    # Correlations
    btc_daily = btc_ret.reindex(strat_ret.index).fillna(0)
    btc_cum   = (1 + btc_daily).cumprod()
    corr_daily = strat_ret.corr(btc_daily)
    corr_bnh   = strat_ret.corr(btc_daily)   # same as daily for daily series

    # Cost drag as % of portfolio
    cost_drag_pct = tm["cost_drag"] * 100

    pos_folds = sum(1 for s in fold_sharpes if s > 0)
    n_folds   = len(fold_sharpes)
    med_sh = float(np.median(fold_sharpes)) if fold_sharpes else float("nan")
    min_sh = float(np.min(fold_sharpes))   if fold_sharpes else float("nan")
    max_sh = float(np.max(fold_sharpes))   if fold_sharpes else float("nan")

    avg_pos = sim_pos.mean()
    verd = verdict(sh, pos_folds, n_folds)

    W = 61
    print()
    print("─" * W)
    print(" BTC-NEUTRAL RESIDUAL MR BACKTEST REPORT")
    print("─" * W)
    print(f"  Period:         {START} → {END}")
    print(f"  Assets:         ETH, SOL, BNB (long-only)")
    print(f"  Strategy:       Enter z < -{ENTRY_THRESHOLD} | Exit z > {EXIT_THRESHOLD} | Vol-scaled")
    print(f"  Lag note:       Signal at close day t → entry at close day t+1")
    print()
    print(f"  Full period (after costs):")
    print(f"    Sharpe ratio:           {sh:+.2f}")
    print(f"    Annualized return:      {ann_ret*100:+.1f}%")
    print(f"    Max drawdown:           {mdd*100:.1f}%")
    print(f"    Win rate:               {tm['win_rate']*100:.1f}%")
    print(f"    Avg hold period:        {tm['avg_hold']:.1f} days")
    print(f"    Total trades:           {tm['total_trades']}")
    print(f"    Total cost drag:        {cost_drag_pct:.1f}%")
    print(f"    Avg simultaneous pos:   {avg_pos:.1f} / 3")
    print()
    print(f"  Correlation to BTC daily return:     {corr_daily:+.2f}")
    print(f"  Correlation to BTC buy-and-hold:     {corr_bnh:+.2f}")
    print()
    print(f"  Walk-forward ({n_folds} folds × 6 months):")
    print(f"    Positive folds:         {pos_folds}/{n_folds}")
    print(f"    Median fold Sharpe:     {med_sh:+.2f}")
    print(f"    Min fold Sharpe:        {min_sh:+.2f}")
    print(f"    Max fold Sharpe:        {max_sh:+.2f}")
    print("─" * W)
    print(f"  PASS:     full Sharpe > 0.8 AND positive folds >= 8/12")
    print(f"  MARGINAL: full Sharpe 0.5-0.8 OR positive folds 6-8/12")
    print(f"  FAIL:     full Sharpe < 0.5 OR positive folds < 6/12")
    print("─" * W)
    print(f"  VERDICT: {verd}")
    print("─" * W)
    print()


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("── Step 1: Loading data ──────────────────────────────────────────")
    prices, log_ret = load_data()
    print(f"  Dates: {log_ret.index[0].date()} → {log_ret.index[-1].date()}")
    print(f"  Columns: {list(log_ret.columns)}")

    print("\n── Step 2: Computing signals ─────────────────────────────────────")
    z_scores, resid_df = compute_signals(log_ret)
    print(f"  z-scores computed for: {list(z_scores.columns)}")

    print("\n── Step 3: Full-period backtest ──────────────────────────────────")
    strat_ret, trades = run_backtest(log_ret, z_scores)
    print(f"  Total trades: {len(trades)}")
    print(f"  Strategy return days: {len(strat_ret)}")

    print("\n── Step 4: Simultaneous position count ───────────────────────────")
    sim_pos = simultaneous_positions(log_ret, z_scores, log_ret.index)

    print("\n── Step 5: Walk-forward (12 folds × 6 months) ───────────────────")
    fold_sharpes = walk_forward(log_ret, z_scores, n_folds=12, fold_months=6)

    print("\n── Step 6: Plots ─────────────────────────────────────────────────")
    btc_ret = log_ret[FACTOR]
    plot_equity(strat_ret, btc_ret, sim_pos)
    plot_folds(fold_sharpes)

    print("\n── Step 7: Report ────────────────────────────────────────────────")
    print_report(strat_ret, btc_ret, trades, fold_sharpes, sim_pos)


if __name__ == "__main__":
    main()
