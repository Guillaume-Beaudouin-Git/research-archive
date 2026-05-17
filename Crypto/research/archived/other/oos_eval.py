"""
True Out-of-Sample Evaluation — multi-asset.

Methodology:
    Hard training cutoff: config.oos_start_date (default 2023-01-01).
    Train on ALL data before that date.
    Test on ALL data from that date to present (~3 years as of 2026).
    A fresh model is trained per asset. No data after the cutoff is
    ever seen during training or hyperparameter selection.

    Assets are taken from config.symbols — 7 diverse chains with
    different tech stacks and partially different investor bases.
    They were listed before running the evaluation, not selected
    after seeing the results.

    This directly addresses two known weaknesses of the walk-forward
    results:
        1. Single-asset evaluation (BTC only) — solved by multi-asset
        2. Short test windows per fold — solved by 3-year hard cutoff

Usage:
    python oos_eval.py
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
from config import Config
from features import extract_features
from labeler import compute_labels, label_distribution
from trainer import SingleSplitTrainer

warnings.filterwarnings("ignore")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("outputs/oos_eval")


# ── Data loading ───────────────────────────────────────────────────────────────

def load_and_split(symbol: str, cfg: Config):
    """
    Download full history, build features/labels, split at oos_start_date.

    Returns:
        X_train, y_train, X_test, y_test, prices_train, prices_test
    """
    logger.info(f"Downloading {symbol}")
    df = yf.download(symbol, period="max", interval="1d",
                     auto_adjust=True, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()

    feat   = extract_features(df)
    labels = compute_labels(df, cfg)
    valid  = feat.dropna().index.intersection(labels.index)

    X      = feat.loc[valid].values.astype("float32")
    y      = labels.loc[valid].values.astype("int64")
    prices = df.loc[valid, ["Open", "Close"]]
    dates  = valid

    cutoff     = pd.Timestamp(cfg.oos_start_date)
    train_mask = dates < cutoff
    test_mask  = dates >= cutoff

    n_train = int(train_mask.sum())
    n_test  = int(test_mask.sum())

    if n_train < cfg.wf_min_train_days:
        raise ValueError(
            f"{symbol}: only {n_train} training bars before {cfg.oos_start_date} "
            f"(minimum required: {cfg.wf_min_train_days})"
        )
    if n_test < 60:
        raise ValueError(
            f"{symbol}: only {n_test} test bars after {cfg.oos_start_date} — "
            f"not enough for meaningful evaluation"
        )

    train_start = dates[train_mask][0].date()
    train_end   = dates[train_mask][-1].date()
    test_start  = dates[test_mask][0].date()
    test_end    = dates[test_mask][-1].date()

    logger.info(
        f"  Total: {len(df)} bars | "
        f"Train: {n_train} ({train_start} – {train_end}) | "
        f"Test:  {n_test}  ({test_start} – {test_end})"
    )
    logger.info(f"  Train labels: {label_distribution(y[train_mask])}")
    logger.info(f"  Test  labels: {label_distribution(y[test_mask])}")

    return (
        X[train_mask], y[train_mask],
        X[test_mask],  y[test_mask],
        prices[train_mask], prices[test_mask],
    )


# ── Per-asset runner ───────────────────────────────────────────────────────────

def run_asset(symbol: str, cfg: Config, bt: Backtester) -> dict | None:
    try:
        X_train, y_train, X_test, y_test, prices_train, prices_test = (
            load_and_split(symbol, cfg)
        )
    except ValueError as e:
        logger.warning(str(e))
        return None

    trainer = SingleSplitTrainer(cfg)
    trainer.fit(X_train, y_train)

    preds  = trainer.predict(X_test)
    probas = trainer.predict_proba(X_test)

    logger.info("\nClassification Report (OOS test set):")
    logger.info(
        "\n" + classification_report(y_test, preds,
                                     target_names=["Sell", "Hold", "Buy"],
                                     zero_division=0)
    )

    equity, trades = bt.run(prices_test, preds)
    metrics  = bt.compute_metrics(equity, trades, freq="1d")
    bh_ret   = prices_test["Close"].iloc[-1] / prices_test["Close"].iloc[0] - 1
    n_years  = len(prices_test) / 365

    logger.info(
        f"  {prices_test.index[0].date()} → {prices_test.index[-1].date()} "
        f"({n_years:.1f} years OOS)"
    )
    logger.info(f"  Return: {metrics['total_return']:+.2%}  B&H: {bh_ret:+.2%}")
    logger.info(
        f"  Sharpe: {metrics['sharpe']:.3f}  "
        f"Sortino: {metrics['sortino']:.3f}  "
        f"MDD: {metrics['max_drawdown']:.2%}  "
        f"Trades: {metrics.get('n_trades', 0)}"
    )

    # Save per-asset equity curve
    out = OUTPUT_DIR / symbol.replace("-", "_")
    out.mkdir(parents=True, exist_ok=True)
    equity.to_csv(out / "equity.csv")
    if len(trades):
        trades.to_csv(out / "trades.csv", index=False)
    _plot_asset(symbol, equity, bt.buy_and_hold(prices_test, cfg.initial_capital), out)

    return {
        "symbol":       symbol,
        "test_start":   str(prices_test.index[0].date()),
        "test_end":     str(prices_test.index[-1].date()),
        "test_years":   round(n_years, 1),
        "total_return": metrics["total_return"],
        "ann_return":   metrics["ann_return"],
        "sharpe":       metrics["sharpe"],
        "sortino":      metrics["sortino"],
        "max_drawdown": metrics["max_drawdown"],
        "calmar":       metrics["calmar"],
        "win_rate":     metrics.get("win_rate", np.nan),
        "n_trades":     metrics.get("n_trades", 0),
        "bh_return":    bh_ret,
        "beat_bh":      metrics["total_return"] > bh_ret,
    }


# ── Main entry ─────────────────────────────────────────────────────────────────

def run_oos_eval() -> pd.DataFrame:
    # 90/10 internal split so the last 10% of training data is used for
    # early stopping validation. The OOS test set is provided externally.
    cfg = Config()
    cfg.train_frac = 0.90
    cfg.val_frac   = 0.10

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    bt = Backtester(cfg)

    logger.info(
        f"\nTrue OOS evaluation | cutoff: {cfg.oos_start_date} | "
        f"assets: {cfg.symbols}"
    )

    results = []
    for symbol in cfg.symbols:
        logger.info(f"\n{'═'*60}\n  {symbol}\n{'═'*60}")
        row = run_asset(symbol, cfg, bt)
        if row:
            results.append(row)

    if not results:
        logger.error("No assets completed successfully.")
        return pd.DataFrame()

    df = pd.DataFrame(results)
    _print_summary(df, cfg.oos_start_date)
    _plot_summary(df, cfg.oos_start_date)
    df.to_csv(OUTPUT_DIR / "oos_results.csv", index=False)
    logger.info(f"\nResults saved → {OUTPUT_DIR}/oos_results.csv")
    return df


# ── Reporting ──────────────────────────────────────────────────────────────────

def _print_summary(df: pd.DataFrame, cutoff: str) -> None:
    sep = "=" * 75
    print(f"\n{sep}")
    print("TRUE OUT-OF-SAMPLE EVALUATION — MULTI-ASSET SUMMARY")
    print(f"Training cutoff: {cutoff}  |  Assets evaluated: {len(df)}")
    print(sep)

    fmt = df[[
        "symbol", "test_years", "total_return", "ann_return",
        "sharpe", "max_drawdown", "n_trades", "win_rate", "bh_return", "beat_bh"
    ]].copy()
    fmt["total_return"] = fmt["total_return"].map("{:+.1%}".format)
    fmt["ann_return"]   = fmt["ann_return"].map("{:+.1%}".format)
    fmt["bh_return"]    = fmt["bh_return"].map("{:+.1%}".format)
    fmt["max_drawdown"] = fmt["max_drawdown"].map("{:.1%}".format)
    fmt["sharpe"]       = fmt["sharpe"].map("{:.2f}".format)
    fmt["win_rate"]     = fmt["win_rate"].map(
        lambda x: f"{x:.1%}" if pd.notna(x) else "N/A"
    )
    print(fmt.to_string(index=False))

    print(f"\n{'─'*75}")
    beat = df["beat_bh"].sum()
    print(f"  Beat B&H:              {beat}/{len(df)} assets")
    print(f"  Median total return:   {df['total_return'].median():+.1%}")
    print(f"  Mean Sharpe:           {df['sharpe'].mean():.2f}  "
          f"(std={df['sharpe'].std():.2f})")
    print(f"  Worst Sharpe:          {df['sharpe'].min():.2f}  "
          f"({df.loc[df['sharpe'].idxmin(), 'symbol']})")
    print(f"  Best  Sharpe:          {df['sharpe'].max():.2f}  "
          f"({df.loc[df['sharpe'].idxmax(), 'symbol']})")
    print(f"  Mean max drawdown:     {df['max_drawdown'].mean():.1%}")
    print(f"  Mean trades / asset:   {df['n_trades'].mean():.0f}")
    print(f"  Mean win rate:         {df['win_rate'].mean():.1%}")
    print(f"{sep}\n")

    # ── Red flags ─────────────────────────────────────────────────────────────
    flags = []
    if df["sharpe"].mean() > 3.0:
        flags.append(
            f"Mean Sharpe {df['sharpe'].mean():.2f} > 3 on OOS data — "
            f"verify no leakage around the {cutoff} boundary"
        )
    if df["n_trades"].mean() < 15:
        flags.append(
            f"Only {df['n_trades'].mean():.0f} avg trades — too few for statistical inference. "
            f"Lower confidence_threshold."
        )
    if df["sharpe"].std() > 1.5:
        flags.append(
            f"Sharpe std {df['sharpe'].std():.2f} — signal varies widely across assets"
        )
    if beat / len(df) < 0.5:
        flags.append(
            f"Strategy beats B&H on only {beat}/{len(df)} assets — "
            f"no consistent cross-asset edge"
        )
    negative = df[df["sharpe"] < 0]["symbol"].tolist()
    if negative:
        flags.append(f"Negative Sharpe on: {', '.join(negative)}")

    if flags:
        print("RED FLAGS:")
        for f in flags:
            print(f"  ! {f}")
        print()
    else:
        print("No red flags detected.\n")


def _plot_summary(df: pd.DataFrame, cutoff: str) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(
        f"True OOS Evaluation ({len(df)} assets, cutoff {cutoff})",
        fontsize=13, fontweight="bold",
    )

    labels = df["symbol"].str.replace("-USD", "")
    x = np.arange(len(df))
    w = 0.35

    # ── Total return: strategy vs B&H ─────────────────────────────────────────
    ax = axes[0]
    strat = df["total_return"].values * 100
    bh    = df["bh_return"].values    * 100
    bars_s = ax.bar(x - w / 2, strat, w, label="Strategy",    color="steelblue")
    bars_b = ax.bar(x + w / 2, bh,    w, label="Buy & Hold",  color="lightcoral")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Total Return (%)")
    ax.set_title("Total Return per Asset (OOS)")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")

    # ── Sharpe per asset ──────────────────────────────────────────────────────
    ax = axes[1]
    colors = ["steelblue" if s > 0 else "tomato" for s in df["sharpe"]]
    ax.bar(labels, df["sharpe"], color=colors)
    ax.axhline(0,   color="black", lw=0.8)
    ax.axhline(1.0, color="green", lw=0.8, linestyle="--", label="Sharpe = 1")
    ax.set_ylabel("Sharpe Ratio")
    ax.set_title("Sharpe Ratio per Asset (OOS)")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    for i, s in enumerate(df["sharpe"]):
        ax.text(i, s + 0.04 * np.sign(s), f"{s:.2f}", ha="center", fontsize=9)

    plt.tight_layout()
    path = OUTPUT_DIR / "oos_summary.png"
    plt.savefig(path, dpi=150)
    plt.close()
    logger.info(f"Summary plot saved → {path}")


def _plot_asset(symbol: str, equity: pd.DataFrame,
                bh: pd.Series, out: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    fig.suptitle(f"{symbol} — True OOS", fontsize=12, fontweight="bold")

    ax = axes[0]
    ax.plot(equity.index, equity["equity"], label="Strategy", lw=1.5)
    ax.plot(bh.index, bh.values, label="Buy & Hold", lw=1.5,
            alpha=0.7, linestyle="--")
    ax.set_ylabel("Portfolio Value ($)")
    ax.set_title("Equity Curve")
    ax.legend()
    ax.grid(alpha=0.3)

    ax = axes[1]
    cummax = equity["equity"].cummax()
    dd = (equity["equity"] - cummax) / (cummax + 1e-9) * 100
    ax.fill_between(equity.index, dd, 0, color="crimson", alpha=0.45)
    ax.set_ylabel("Drawdown (%)")
    ax.set_title("Drawdown")
    ax.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(out / "equity.png", dpi=150)
    plt.close()


if __name__ == "__main__":
    run_oos_eval()
