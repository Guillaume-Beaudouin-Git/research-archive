"""
MLP classifier for crypto trading.

Architecture (Parente et al., 2024):
    Input → [Linear → BatchNorm → LeakyReLU → Dropout] x n_layers → Linear(3)

MC Dropout (Kalariya et al., 2022):
    Keep dropout active at inference time and average over N stochastic passes.
    Gives calibrated class probabilities + implicit uncertainty estimate.
    Only trade when max(p) > confidence_threshold.
"""

from typing import List

import torch
import torch.nn as nn


class TradingMLP(nn.Module):
    """
    Buy / Hold / Sell classifier with MC Dropout support.

    Args:
        input_dim:   Number of input features.
        hidden_dims: Widths of hidden layers (default: [128, 64, 32]).
        n_classes:   Number of output classes (3: Sell/Hold/Buy).
        dropout:     Dropout probability applied after every hidden layer.
    """

    def __init__(
        self,
        input_dim: int,
        hidden_dims: List[int] = (128, 64, 32),
        n_classes: int = 3,
        dropout: float = 0.2,
    ):
        super().__init__()
        layers: list = []
        in_dim = input_dim
        for h in hidden_dims:
            layers += [
                nn.Linear(in_dim, h),
                nn.BatchNorm1d(h),
                nn.LeakyReLU(negative_slope=0.1, inplace=True),
                nn.Dropout(p=dropout),
            ]
            in_dim = h
        layers.append(nn.Linear(in_dim, n_classes))
        self.net = nn.Sequential(*layers)
        self._init_weights()

    def _init_weights(self) -> None:
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight, nonlinearity="leaky_relu")
                nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm1d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Standard forward pass → raw logits."""
        return self.net(x)

    @torch.no_grad()
    def predict_proba(
        self, x: torch.Tensor, n_samples: int = 30
    ) -> torch.Tensor:
        """
        MC Dropout inference: keep Dropout enabled, average N forward passes.

        BatchNorm layers are kept in eval mode (frozen running stats).
        Only Dropout layers are set to train mode to inject stochastic noise.

        Returns:
            mean_proba: Tensor of shape (batch, n_classes), sum=1 along dim=1.
        """
        self.eval()   # freeze BatchNorm running stats
        for m in self.modules():
            if isinstance(m, nn.Dropout):
                m.train()   # enable stochastic dropout only
        probs = torch.stack(
            [torch.softmax(self.forward(x), dim=-1) for _ in range(n_samples)]
        )   # (n_samples, batch, n_classes)
        self.eval()
        return probs.mean(dim=0)   # (batch, n_classes)

    @torch.no_grad()
    def predict(
        self, x: torch.Tensor, n_samples: int = 30, confidence_threshold: float = 0.0
    ) -> torch.Tensor:
        """
        Predict class labels.  If confidence_threshold > 0, samples where
        max(proba) < threshold are forced to Hold (class 1).
        """
        proba = self.predict_proba(x, n_samples)
        preds = proba.argmax(dim=-1)
        if confidence_threshold > 0.0:
            low_conf = proba.max(dim=-1).values < confidence_threshold
            preds[low_conf] = 1   # Hold
        return preds
        