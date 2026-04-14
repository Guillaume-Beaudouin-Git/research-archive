"""
Single chronological split training pipeline.

Critical: data is split CHRONOLOGICALLY (no shuffling across the full set).
This is the single most common backtesting mistake in the literature.

Pipeline:
    1. Chronological train / val / test split
    2. Undersample Hold on train only
    3. StandardScaler fitted on train, applied to val/test
    4. AdamW + CosineAnnealing + gradient clipping
    5. Early stopping on val loss (restore best weights)

For multi-fold walk-forward evaluation, see walk_forward.py.
"""

import logging
from typing import Dict, Tuple

import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

from config import Config
from labeler import undersample_hold
from model import TradingMLP

logger = logging.getLogger(__name__)


class SingleSplitTrainer:
    def __init__(self, config: Config):
        self.cfg = config
        self.scaler = StandardScaler()
        self.model: TradingMLP | None = None
        torch.manual_seed(config.seed)
        np.random.seed(config.seed)

    # ── Split ──────────────────────────────────────────────────────────────────

    def chronological_split(
        self, X: np.ndarray, y: np.ndarray
    ) -> Tuple[Tuple, Tuple, Tuple]:
        """Strict chronological split — NO random shuffling."""
        n = len(X)
        t1 = int(n * self.cfg.train_frac)
        t2 = int(n * (self.cfg.train_frac + self.cfg.val_frac))
        return (X[:t1], y[:t1]), (X[t1:t2], y[t1:t2]), (X[t2:], y[t2:])

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _loader(self, X: np.ndarray, y: np.ndarray, shuffle: bool) -> DataLoader:
        ds = TensorDataset(torch.FloatTensor(X), torch.LongTensor(y))
        return DataLoader(ds, batch_size=self.cfg.batch_size, shuffle=shuffle,
                          pin_memory=(self.cfg.device == "cuda"), num_workers=0)

    def _class_weights(self, y: np.ndarray) -> torch.Tensor:
        """Inverse-frequency weights for imbalanced labels."""
        counts = np.bincount(y, minlength=3).astype(float) + 1.0
        w = 1.0 / counts
        w = w / w.sum() * 3          # normalise so weights sum to n_classes
        return torch.FloatTensor(w).to(self.cfg.device)

    # ── Main fit ───────────────────────────────────────────────────────────────

    def fit(self, X: np.ndarray, y: np.ndarray) -> Dict[str, list]:
        """
        Train on X, y using chronological walk-forward split.

        Returns:
            history dict with train_loss, val_loss, val_acc per epoch.
        """
        cfg = self.cfg
        (X_tr, y_tr), (X_val, y_val), _ = self.chronological_split(X, y)

        # Undersample Hold majority class in train only
        X_tr, y_tr = undersample_hold(X_tr, y_tr, seed=cfg.seed)

        logger.info(
            f"Split sizes — train: {len(X_tr)}, val: {len(X_val)}"
        )

        # Scale: fit on train, transform val
        X_tr_s  = self.scaler.fit_transform(X_tr).astype(np.float32)
        X_val_s = self.scaler.transform(X_val).astype(np.float32)

        # Build model
        self.model = TradingMLP(
            input_dim=X.shape[1],
            hidden_dims=cfg.hidden_dims,
            dropout=cfg.dropout,
        ).to(cfg.device)

        optimizer = torch.optim.AdamW(
            self.model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay
        )
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=cfg.max_epochs, eta_min=cfg.lr * 0.01
        )
        criterion = nn.CrossEntropyLoss(weight=self._class_weights(y_tr))

        train_loader = self._loader(X_tr_s, y_tr, shuffle=True)
        X_val_t = torch.FloatTensor(X_val_s).to(cfg.device)
        y_val_t = torch.LongTensor(y_val).to(cfg.device)

        best_val_loss   = float("inf")
        patience_count  = 0
        best_state_dict = None
        history: Dict[str, list] = {"train_loss": [], "val_loss": [], "val_acc": []}

        for epoch in range(cfg.max_epochs):
            # ── Train ────────────────────────────────────────────────────
            self.model.train()
            running_loss = 0.0
            for X_b, y_b in train_loader:
                X_b, y_b = X_b.to(cfg.device), y_b.to(cfg.device)
                optimizer.zero_grad(set_to_none=True)
                loss = criterion(self.model(X_b), y_b)
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                optimizer.step()
                running_loss += loss.item() * len(X_b)

            scheduler.step()
            epoch_loss = running_loss / len(X_tr)

            # ── Validate ─────────────────────────────────────────────────
            self.model.eval()
            with torch.no_grad():
                val_logits = self.model(X_val_t)
                val_loss   = criterion(val_logits, y_val_t).item()
                val_preds  = val_logits.argmax(dim=1)
                val_acc    = (val_preds == y_val_t).float().mean().item()

            history["train_loss"].append(epoch_loss)
            history["val_loss"].append(val_loss)
            history["val_acc"].append(val_acc)

            if epoch % 10 == 0:
                logger.info(
                    f"Epoch {epoch:3d} | train_loss={epoch_loss:.4f} "
                    f"val_loss={val_loss:.4f} val_acc={val_acc:.3f}"
                )

            # ── Early stopping ───────────────────────────────────────────
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_count = 0
                best_state_dict = {
                    k: v.cpu().clone() for k, v in self.model.state_dict().items()
                }
            else:
                patience_count += 1
                if patience_count >= cfg.patience:
                    logger.info(f"Early stop at epoch {epoch}")
                    break

        if best_state_dict:
            self.model.load_state_dict(best_state_dict)

        logger.info(f"Best val loss: {best_val_loss:.4f}")
        return history

    # ── Inference ──────────────────────────────────────────────────────────────

    def predict(self, X: np.ndarray) -> np.ndarray:
        """MC Dropout prediction with confidence filtering."""
        assert self.model is not None, "Call fit() first."
        X_s = self.scaler.transform(X).astype(np.float32)
        X_t = torch.FloatTensor(X_s).to(self.cfg.device)
        self.model.eval()
        preds = self.model.predict(
            X_t,
            n_samples=self.cfg.mc_samples,
            confidence_threshold=self.cfg.confidence_threshold,
        )
        return preds.cpu().numpy()

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        assert self.model is not None, "Call fit() first."
        X_s = self.scaler.transform(X).astype(np.float32)
        X_t = torch.FloatTensor(X_s).to(self.cfg.device)
        proba = self.model.predict_proba(X_t, n_samples=self.cfg.mc_samples)
        return proba.cpu().numpy()

    def get_test_split(self, X: np.ndarray, y: np.ndarray):
        """Return the held-out test portion (raw, unscaled)."""
        _, _, (X_test, y_test) = self.chronological_split(X, y)
        return X_test, y_test

    def transform(self, X: np.ndarray) -> np.ndarray:
        return self.scaler.transform(X).astype(np.float32)