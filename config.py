"""
Configuration for the crypto trading system.
All hyperparameters in one place for reproducibility.
"""
from dataclasses import dataclass, field
from typing import List
import torch


@dataclass
class Config:
    # ── Data ────────────────────────────────────────────────────────────
    symbols: List[str] = field(
        default_factory=lambda: [
            "BTC-USD",   # reference asset
            "ETH-USD",   # smart contract platform
            "SOL-USD",   # high-throughput L1
            "ADA-USD",   # academic/PoS chain
            "AVAX-USD",  # subnet architecture
            "LINK-USD",  # oracle network (more utility-driven)
            "DOT-USD",   # cross-chain interoperability
        ]
    )
    interval: str = "1d"
    period: str = "max"         # full history (~11 years for BTC since 2014)

    # ── True out-of-sample cutoff ────────────────────────────────────────────
    # Everything before this date is training data.
    # Everything from this date onward is the untouched test set (~3 years).
    oos_start_date: str = "2023-01-01"

    # ── Labeling (Parente et al., 2024 — revised) ────────────────────────
    back_window: int = 5
    forward_window: int = 2
    alpha: float = 0.015        # FIX: lowered from 0.038 to 0.015 (1.5%)
                                # Less aggressive filtering → more labels,
                                # lower win rate, more realistic training
    beta: float = 0.15          # FIX: lowered from 0.264 to 0.15 (15%)
                                # Still filters black swans but less extreme
    fee: float = 0.00035        # Hyperliquid taker fee (0.035% per side)
                                # Previous value 0.002 was 5.7× too high
    use_trend_confirm: bool = False  # FIX: was implicitly True in old labeler
                                     # Removing EMA trend confirmation reduces
                                     # circular labeling bias

    # ── Model ────────────────────────────────────────────────────────────
    hidden_dims: List[int] = field(default_factory=lambda: [128, 64, 32])
    dropout: float = 0.2
    lr: float = 1e-3
    weight_decay: float = 1e-4
    batch_size: int = 256
    max_epochs: int = 80
    patience: int = 15

    # ── MC Dropout inference (Kalariya et al., 2022) ─────────────────────
    mc_samples: int = 30
    confidence_threshold: float = 0.50

    # ── Single split (main.py) ───────────────────────────────────────────
    train_frac: float = 0.70
    val_frac: float = 0.15

    # ── Walk-forward (walk_forward.py) ───────────────────────────────────
    wf_initial_train_years: int = 3
    wf_fold_size_days: int = 365
    wf_min_train_days: int = 500

    # ── Backtesting ──────────────────────────────────────────────────────
    initial_capital: float = 10_000.0
    position_size: float = 0.30     # FIX: invest 30% of capital per trade
                                    # Instead of 100% → kills astronomical compounding
    slippage: float = 0.001         # FIX: 0.1% market impact on entry and exit
    stop_loss: float = 0.05
    allow_short: bool = True
    auto_flip: bool = False         # FIX: when exiting long on Sell, go FLAT
                                    # instead of immediately opening short
                                    # Old behavior was always in position → inflated returns
    max_hold_bars: int = 30         # FIX: force exit after 30 bars
                                    # Prevents indefinitely holding losing positions

    # ── Misc ─────────────────────────────────────────────────────────────
    seed: int = 42
    device: str = field(
        default_factory=lambda: "cuda" if torch.cuda.is_available() else "cpu"
    )
    output_dir: str = "outputs"