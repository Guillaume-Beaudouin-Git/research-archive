"""
Main training and evaluation pipeline.

Usage:
    python main.py

Requirements:
    pip install torch yfinance pandas numpy scikit-learn matplotlib shap
"""

import logging
import os
from pathlib import Path
from typing import Dict

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Data loading ───────────────────────────────────────────────────────────────

def load_ohlcv(symbol: str, cfg: Config) -> pd.DataFrame:
    """
    Download OHLCV data from Yahoo Finance.

    Note on intervals:
        "1d"  → up to 10 years, recommended for sufficient training data
        "1h"  → last 730 days only (yfinance limitation)
        "4h"  → not natively supported; use ccxt + Binance for intraday research
    """
    logger.info(f"Downloading {symbol}  interval={cfg.interval}  period={cfg.period}")
    df = yf.download(
        symbol,
        period=cfg.period,
        interval=cfg.interval,
        progress=False,
        auto_adjust=True,
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    logger.info(f"  → {len(df)} bars  ({df.index[0].date()} – {df.index[-1].date()})")
    return df


# ── Dataset builder ────────────────────────────────────────────────────────────

def build_dataset(df: pd.DataFrame, cfg: Config):
    """
    Extract features and labels, align indices, drop NaN rows.

    Returns:
        X      : float32 array (T, n_features)
        y      : int64 array   (T,)   {0: Sell, 1: Hold, 2: Buy}
        prices : DataFrame     (T,)   with Open, Close for backtesting
        index  : DatetimeIndex
    """
    feat   = extract_features(df)
    labels = compute_labels(df, cfg)

    valid  = feat.dropna().index.intersection(labels.index)
    X      = feat.loc[valid].values.astype(np.float32)
    y      = labels.loc[valid].values.astype(np.int64)
    prices = df.loc[valid, ["Open", "Close"]]

    logger.info(f"  Dataset: {len(X)} samples × {X.shape[1]} features")
    logger.info(f"  Labels : {label_distribution(y)}")
    return X, y, prices, valid


# ── Per-symbol pipeline ────────────────────────────────────────────────────────

def run_symbol(symbol: str, cfg: Config) -> Dict:
    logger.info(f"\n{'═'*55}\n  {symbol}\n{'═'*55}")

    # 1. Load & build dataset
    df           = load_ohlcv(symbol, cfg)
    X, y, prices, _ = build_dataset(df, cfg)

    # 2. Train
    trainer = SingleSplitTrainer(cfg)
    history = trainer.fit(X, y)

    # 3. Evaluate on held-out test split
    X_test, y_test  = trainer.get_test_split(X, y)
    n_test_start    = len(X) - len(X_test)
    prices_test     = prices.iloc[n_test_start:]

    predictions     = trainer.predict(X_test)
    probas          = trainer.predict_proba(X_test)

    logger.info("\nClassification Report (test set):")
    logger.info(
        "\n" + classification_report(y_test, predictions,
                                     target_names=["Sell", "Hold", "Buy"])
    )

    # 4. Backtest
    bt         = Backtester(cfg)
    equity_df, trade_df = bt.run(prices_test, predictions)
    metrics    = bt.compute_metrics(equity_df, trade_df, freq=cfg.interval)
    bh_equity  = bt.buy_and_hold(prices_test, cfg.initial_capital)
    bh_total   = bh_equity.iloc[-1] / cfg.initial_capital - 1

    _print_metrics(symbol, metrics, bh_total)

    # 5. Save results
    out = Path(cfg.output_dir) / symbol.replace("-", "_")
    out.mkdir(parents=True, exist_ok=True)
    plot_results(symbol, equity_df, bh_equity, prices_test, history, out)

    if len(trade_df):
        trade_df.to_csv(out / "trades.csv", index=False)

    return {"symbol": symbol, "metrics": metrics, "bh_return": bh_total}


def _print_metrics(symbol: str, m: Dict, bh: float) -> None:
    sep = "─" * 40
    logger.info(f"\n{sep}\n  Backtest — {symbol}\n{sep}")
    logger.info(f"  Total Return     : {m['total_return']:>+8.2%}")
    logger.info(f"  Ann. Return      : {m['ann_return']:>+8.2%}")
    logger.info(f"  Sharpe Ratio     : {m['sharpe']:>8.3f}")
    logger.info(f"  Sortino Ratio    : {m['sortino']:>8.3f}")
    logger.info(f"  Max Drawdown     : {m['max_drawdown']:>8.2%}")
    logger.info(f"  Calmar Ratio     : {m['calmar']:>8.3f}")
    logger.info(f"  Final Capital    : ${m['final_capital']:>,.2f}")
    if "n_trades" in m:
        logger.info(f"  # Trades         : {m['n_trades']}")
        logger.info(f"  Win Rate         : {m['win_rate']:>8.2%}")
        logger.info(f"  Profit Factor    : {m['profit_factor']:>8.3f}")
    logger.info(f"  B&H Return       : {bh:>+8.2%}")
    logger.info(sep)


# ── Plotting ───────────────────────────────────────────────────────────────────

def plot_results(
    symbol: str,
    equity_df: pd.DataFrame,
    bh_equity: pd.Series,
    prices: pd.DataFrame,
    history: Dict,
    out_dir: Path,
) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    fig.suptitle(symbol, fontsize=14, fontweight="bold")

    # ── Equity curve ──────────────────────────────────────────────────────
    ax = axes[0]
    ax.plot(equity_df.index, equity_df["equity"], label="Strategy", lw=1.5)
    ax.plot(bh_equity.index, bh_equity.values, label="Buy & Hold",
            lw=1.5, alpha=0.7, linestyle="--")
    ax.set_ylabel("Portfolio Value ($)")
    ax.set_title("Equity Curve")
    ax.legend()
    ax.grid(alpha=0.3)

    # ── Drawdown ──────────────────────────────────────────────────────────
    ax = axes[1]
    cummax = equity_df["equity"].cummax()
    dd = (equity_df["equity"] - cummax) / (cummax + 1e-9)
    ax.fill_between(equity_df.index, dd * 100, 0, color="crimson", alpha=0.45)
    ax.set_ylabel("Drawdown (%)")
    ax.set_title("Drawdown")
    ax.grid(alpha=0.3)

    # ── Training loss ─────────────────────────────────────────────────────
    ax = axes[2]
    epochs = range(1, len(history["train_loss"]) + 1)
    ax.plot(epochs, history["train_loss"], label="Train Loss", lw=1.2)
    ax.plot(epochs, history["val_loss"],   label="Val Loss",   lw=1.2)
    ax2 = ax.twinx()
    ax2.plot(epochs, history["val_acc"], color="green", lw=1.0,
             linestyle=":", label="Val Acc", alpha=0.7)
    ax2.set_ylabel("Val Accuracy")
    ax.set_ylabel("Loss")
    ax.set_title("Training History")
    ax.legend(loc="upper left")
    ax2.legend(loc="upper right")
    ax.grid(alpha=0.3)

    plt.tight_layout()
    path = out_dir / "results.png"
    plt.savefig(path, dpi=150)
    plt.close()
    logger.info(f"Plot saved → {path}")


# ── Optional: SHAP feature importance ────────────────────────────────────────

def shap_analysis(trainer: SingleSplitTrainer, X_test: np.ndarray, feature_names: list) -> None:
    """
    SHAP feature importance (Parente et al., 2024 — Section 6).
    Requires:  pip install shap
    """
    try:
        import shap
        import torch

        logger.info("Computing SHAP values...")
        X_bg = trainer.transform(X_test[:200])   # background samples
        X_ex = trainer.transform(X_test[:100])   # samples to explain

        def model_fn(x: np.ndarray) -> np.ndarray:
            t = torch.FloatTensor(x).to(trainer.cfg.device)
            return trainer.model.predict_proba(t).cpu().numpy()

        explainer  = shap.KernelExplainer(model_fn, X_bg)
        shap_vals  = explainer.shap_values(X_ex, nsamples=100)
        # shap_vals: list of 3 arrays (one per class), shape (n_samples, n_features)

        mean_abs   = np.mean([np.abs(sv).mean(axis=0) for sv in shap_vals], axis=0)
        importance = pd.Series(mean_abs, index=feature_names).sort_values(ascending=False)

        plt.figure(figsize=(10, 6))
        importance.head(12).plot(kind="barh")
        plt.xlabel("Mean |SHAP value|")
        plt.title("Feature Importance (SHAP)")
        plt.gca().invert_yaxis()
        plt.tight_layout()
        plt.savefig("outputs/shap_importance.png", dpi=150)
        plt.close()
        logger.info("SHAP plot saved → outputs/shap_importance.png")
    except ImportError:
        logger.warning("shap not installed. Run: pip install shap")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    cfg = Config()
    Path(cfg.output_dir).mkdir(exist_ok=True)

    all_results = []
    for symbol in cfg.symbols:
        try:
            result = run_symbol(symbol, cfg)
            all_results.append(result)
        except Exception as e:
            logger.error(f"Failed on {symbol}: {e}", exc_info=True)

    # ── Summary table ─────────────────────────────────────────────────────
    if all_results:
        rows = []
        for r in all_results:
            m = r["metrics"]
            rows.append({
                "Symbol":       r["symbol"],
                "Ann Return":   f"{m['ann_return']:+.2%}",
                "Sharpe":       f"{m['sharpe']:.3f}",
                "Max DD":       f"{m['max_drawdown']:.2%}",
                "Calmar":       f"{m['calmar']:.3f}",
                "B&H Return":   f"{r['bh_return']:+.2%}",
                "Win Rate":     f"{m.get('win_rate', 0):.2%}",
            })
        summary = pd.DataFrame(rows).set_index("Symbol")
        logger.info(f"\n{'═'*55}\n  SUMMARY\n{'═'*55}\n{summary.to_string()}\n")
        summary.to_csv(f"{cfg.output_dir}/summary.csv")


if __name__ == "__main__":
    main()