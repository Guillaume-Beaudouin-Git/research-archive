"""
Walk-Forward Validation — industry standard for strategy evaluation.

Instead of one fixed train/test split, the training window expands
and a fresh out-of-sample test window is evaluated at each fold.
This covers multiple market regimes (bull, bear, flat) and gives
a realistic distribution of strategy performance.

Usage:
    python walk_forward.py
"""

import logging
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.metrics import classification_report

from backtest import Backtester
from config   import Config
from features import extract_features
from labeler  import compute_labels
from trainer  import SingleSplitTrainer

warnings.filterwarnings("ignore")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Configuration ──────────────────────────────────────────────────────────────
SYMBOL     = "BTC-USD"
OUTPUT_DIR = Path("outputs/walk_forward")


def load_full_history(symbol: str, cfg: Config) -> tuple:
    """Download max available history and build X, y, prices."""
    logger.info(f"Downloading {symbol} — full history")
    df = yf.download(symbol, period="max", interval="1d",
                     auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open","High","Low","Close","Volume"]].dropna()
    logger.info(f"  {len(df)} bars  ({df.index[0].date()} -> {df.index[-1].date()})")

    feat   = extract_features(df)
    labels = compute_labels(df, cfg)
    valid  = feat.dropna().index.intersection(labels.index)

    X      = feat.loc[valid].values.astype("float32")
    y      = labels.loc[valid].values.astype("int64")
    prices = df.loc[valid, ["Open","Close"]]
    dates  = valid

    return X, y, prices, dates


def run_walk_forward(symbol: str = SYMBOL) -> pd.DataFrame:
    # Single config used for both training and backtesting — no dual-config drift.
    # Use 90/10 split within each fold's training data for validation (no test leak).
    cfg = Config()
    cfg.train_frac            = 0.90
    cfg.val_frac              = 0.10

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    X, y, prices, dates = load_full_history(symbol, cfg)
    n = len(X)

    # Build fold boundaries using config params
    first_test_start = cfg.wf_initial_train_years * 365

    folds = []
    test_start = first_test_start
    while test_start + cfg.wf_fold_size_days <= n:
        test_end = min(test_start + cfg.wf_fold_size_days, n)
        folds.append((test_start, test_end))
        test_start = test_end   # expanding window: train grows each fold

    logger.info(f"\n{len(folds)} folds over "
                f"{dates[first_test_start].date()} → {dates[-1].date()}")

    # ── Run each fold ──────────────────────────────────────────────────────────
    all_equity   = []
    fold_metrics = []
    bt           = Backtester(cfg)

    for fold_idx, (ts, te) in enumerate(folds):
        train_X = X[:ts]
        train_y = y[:ts]
        test_X  = X[ts:te]
        test_y  = y[ts:te]
        test_prices = prices.iloc[ts:te]
        test_dates  = dates[ts:te]

        if len(train_X) < cfg.wf_min_train_days or len(test_X) < 30:
            logger.info(f"Fold {fold_idx+1}: skipped (insufficient data)")
            continue

        start_d = test_dates[0].date()
        end_d   = test_dates[-1].date()
        logger.info(f"\nFold {fold_idx+1}/{len(folds)} | "
                    f"Train: {len(train_X)} bars | "
                    f"Test: {start_d} → {end_d} ({len(test_X)} bars)")

        trainer = SingleSplitTrainer(cfg)
        trainer.fit(train_X, train_y)

        preds  = trainer.predict(test_X)
        equity, trades = bt.run(test_prices, preds)
        metrics = bt.compute_metrics(equity, trades, freq="1d")
        bh_ret  = test_prices["Close"].iloc[-1] / test_prices["Close"].iloc[0] - 1

        logger.info(f"  Total Return: {metrics['total_return']:+.2%}  "
                    f"Sharpe: {metrics['sharpe']:.3f}  "
                    f"MDD: {metrics['max_drawdown']:.2%}  "
                    f"B&H: {bh_ret:+.2%}  "
                    f"Trades: {metrics.get('n_trades', 0)}")

        # Tag equity with fold info
        equity["fold"]    = fold_idx + 1
        equity["bh"]      = cfg.initial_capital * (
            test_prices["Close"] / test_prices["Close"].iloc[0]
        ).values

        all_equity.append(equity)
        fold_metrics.append({
            "fold":         fold_idx + 1,
            "start":        str(start_d),
            "end":          str(end_d),
            "train_bars":   len(train_X),
            "test_bars":    len(test_X),
            "total_return": metrics["total_return"],
            "sharpe":       metrics["sharpe"],
            "sortino":      metrics["sortino"],
            "max_drawdown": metrics["max_drawdown"],
            "calmar":       metrics["calmar"],
            "win_rate":     metrics.get("win_rate", np.nan),
            "n_trades":     metrics.get("n_trades", 0),
            "bh_return":    bh_ret,
            "beat_bh":      metrics["total_return"] > bh_ret,
        })

    if not fold_metrics:
        logger.error("No folds completed.")
        return pd.DataFrame()

    results_df = pd.DataFrame(fold_metrics)

    # ── Aggregate summary ──────────────────────────────────────────────────────
    print_summary(results_df)

    # ── Concatenated equity curve ──────────────────────────────────────────────
    plot_walk_forward(all_equity, results_df, symbol)

    results_df.to_csv(OUTPUT_DIR / "fold_results.csv", index=False)
    logger.info(f"\nResults saved → {OUTPUT_DIR}/fold_results.csv")

    return results_df


def print_summary(df: pd.DataFrame) -> None:
    print(f"\n{'='*65}")
    print("WALK-FORWARD SUMMARY")
    print(f"{'='*65}")

    # Per-fold table
    display_cols = ["fold","start","end","total_return","sharpe",
                    "max_drawdown","n_trades","bh_return","beat_bh"]
    fmt = df[display_cols].copy()
    fmt["total_return"] = fmt["total_return"].map("{:+.2%}".format)
    fmt["bh_return"]    = fmt["bh_return"].map("{:+.2%}".format)
    fmt["max_drawdown"] = fmt["max_drawdown"].map("{:.2%}".format)
    fmt["sharpe"]       = fmt["sharpe"].map("{:.3f}".format)
    print(fmt.to_string(index=False))

    print(f"\n{'─'*65}")
    print(f"  Folds:                  {len(df)}")
    print(f"  Beat B&H:               {df['beat_bh'].sum()}/{len(df)} folds")
    print(f"  Median Total Return:    {df['total_return'].median():+.2%}")
    print(f"  Mean Sharpe:            {df['sharpe'].mean():.3f}  "
          f"(std={df['sharpe'].std():.3f})")
    print(f"  Worst Sharpe:           {df['sharpe'].min():.3f}")
    print(f"  Best  Sharpe:           {df['sharpe'].max():.3f}")
    print(f"  Mean Max Drawdown:      {df['max_drawdown'].mean():.2%}")
    print(f"  Total trades (all):     {df['n_trades'].sum()}")
    print(f"  Mean trades/fold:       {df['n_trades'].mean():.0f}")
    print(f"  Mean win rate:          {df['win_rate'].mean():.1%}")
    print(f"{'='*65}\n")

    # Red flags
    flags = []
    if df["sharpe"].mean() > 3.0:
        flags.append(f"Mean Sharpe {df['sharpe'].mean():.2f} > 3 — verify no data leakage")
    if df["n_trades"].mean() < 20:
        flags.append(f"Only {df['n_trades'].mean():.0f} trades/fold avg — lower confidence_threshold")
    if df["sharpe"].std() > 2.0:
        flags.append(f"High Sharpe std ({df['sharpe'].std():.2f}) — unstable across regimes")
    if df["beat_bh"].mean() < 0.5:
        flags.append("Strategy beats B&H in <50% of folds — no consistent edge")

    if flags:
        print("RED FLAGS:")
        for f in flags:
            print(f"  ! {f}")
    else:
        print("No red flags detected.")


def plot_walk_forward(all_equity: list, results_df: pd.DataFrame,
                      symbol: str) -> None:
    if not all_equity:
        return

    fig, axes = plt.subplots(3, 1, figsize=(15, 13))
    fig.suptitle(f"{symbol} — Walk-Forward Backtest", fontsize=14, fontweight="bold")

    colors = plt.cm.tab10.colors

    # ── Per-fold equity curves ─────────────────────────────────────────────────
    ax = axes[0]
    for i, eq in enumerate(all_equity):
        c = colors[i % len(colors)]
        # Normalise each fold to start at 100
        norm   = eq["equity"] / eq["equity"].iloc[0] * 100
        norm_bh= eq["bh"]    / eq["bh"].iloc[0]    * 100
        ax.plot(eq.index, norm,    color=c, lw=1.5, label=f"Fold {i+1}")
        ax.plot(eq.index, norm_bh, color=c, lw=0.8, linestyle="--", alpha=0.5)
    ax.axhline(100, color="black", lw=0.5, linestyle=":")
    ax.set_title("Per-fold equity (solid=strategy, dashed=B&H, normalised to 100)")
    ax.set_ylabel("Indexed return")
    ax.legend(fontsize=7, ncol=4)
    ax.grid(alpha=0.3)

    # ── Sharpe per fold ────────────────────────────────────────────────────────
    ax = axes[1]
    folds  = results_df["fold"].values
    sharpe = results_df["sharpe"].values
    colors_bar = ["steelblue" if s > 0 else "tomato" for s in sharpe]
    ax.bar(folds, sharpe, color=colors_bar)
    ax.axhline(0,   color="black", lw=0.8)
    ax.axhline(1.0, color="green", lw=0.8, linestyle="--", label="Sharpe=1")
    ax.set_title("Sharpe Ratio per fold")
    ax.set_xlabel("Fold")
    ax.set_ylabel("Sharpe")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    for i, (f, s) in enumerate(zip(folds, sharpe)):
        ax.text(f, s + 0.05 * np.sign(s), f"{s:.2f}", ha="center", fontsize=8)

    # ── Return vs B&H per fold ─────────────────────────────────────────────────
    ax = axes[2]
    x    = np.arange(len(folds))
    w    = 0.35
    strat_ret = results_df["total_return"].values * 100
    bh_ret    = results_df["bh_return"].values    * 100
    ax.bar(x - w/2, strat_ret, w, label="Strategy", color="steelblue")
    ax.bar(x + w/2, bh_ret,    w, label="Buy & Hold", color="lightcoral")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_title("Total Return per fold: Strategy vs Buy & Hold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"F{f}\n{s}" for f, s in
                        zip(folds, results_df["start"].str[:7])])
    ax.set_ylabel("Return (%)")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")

    plt.tight_layout()
    path = OUTPUT_DIR / "walk_forward.png"
    plt.savefig(path, dpi=150)
    plt.close()
    logger.info(f"Plot saved → {path}")


if __name__ == "__main__":
    # Run walk-forward on every symbol in config.
    # Pass a single symbol as argument to run just one:
    #   python walk_forward.py BTC-USD
    import sys
    cfg_symbols = Config().symbols
    targets = sys.argv[1:] if len(sys.argv) > 1 else cfg_symbols
    all_results = {}
    for sym in targets:
        logger.info(f"\n{'█'*60}\n  Walk-Forward: {sym}\n{'█'*60}")
        all_results[sym] = run_walk_forward(sym)