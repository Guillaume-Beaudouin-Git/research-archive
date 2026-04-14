"""
train_and_save.py

Train the model on full history and save it to disk so live_trader.py
can load it without retraining on every cron run.

Usage:
    python train_and_save.py --symbol BTC-USD
    python train_and_save.py --symbol SOL-USD --epochs 100
"""
import argparse
import json
import logging
import pickle
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yfinance as yf

from config import Config
from features import extract_features
from labeler import compute_labels
from trainer import SingleSplitTrainer

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def train_and_save(symbol: str, output_dir: str = "model_store",
                   epochs: int | None = None) -> None:
    cfg = Config()
    cfg.train_frac = 0.90
    cfg.val_frac = 0.10
    if epochs:
        cfg.max_epochs = epochs

    out = Path(output_dir)
    out.mkdir(exist_ok=True)

    logger.info(f"Downloading {symbol} full history...")
    df = yf.download(symbol, period="max", interval="1d",
                     auto_adjust=True, progress=False)
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    logger.info(f"  {len(df)} bars ({df.index[0].date()} -> {df.index[-1].date()})")

    feat = extract_features(df)
    labels = compute_labels(df, cfg)
    valid = feat.dropna().index.intersection(labels.index)
    X = feat.loc[valid].values.astype("float32")
    y = labels.loc[valid].values.astype("int64")

    trainer = SingleSplitTrainer(cfg)
    trainer.fit(X, y)

    symbol_clean = symbol.replace("-", "_")
    model_path = out / f"{symbol_clean}_model.pt"
    scaler_path = out / f"{symbol_clean}_scaler.pkl"
    meta_path = out / f"{symbol_clean}_meta.json"

    import torch
    torch.save(trainer.model.state_dict(), model_path)
    with open(scaler_path, "wb") as f:
        pickle.dump(trainer.scaler, f)

    meta = {
        "symbol": symbol,
        "trained_until": df.index[-1].strftime("%Y-%m-%d"),
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "n_samples": len(X),
        "input_dim": X.shape[1],
        "hidden_dims": cfg.hidden_dims,
        "dropout": cfg.dropout,
        "feature_names": list(feat.columns),
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    logger.info(f"Saved model to {model_path}")
    logger.info(f"Saved scaler to {scaler_path}")
    logger.info(f"Saved meta to {meta_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTC-USD")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--output-dir", default="model_store")
    args = parser.parse_args()
    train_and_save(args.symbol, args.output_dir, args.epochs)
