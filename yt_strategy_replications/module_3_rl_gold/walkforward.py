"""Walk-forward fold generation and the consistency gate (Module 3)."""
from __future__ import annotations

import numpy as np


def sliding_folds(n, n_folds=5, train=6000, val=1500, test=1500):
    """Fixed-size sliding window (the video's preferred scheme): train/val/test all
    move forward together so the model always learns from a recent, relevant slice."""
    block = train + val + test
    if block > n:
        raise ValueError(f"window {block} > sample {n}")
    starts = np.linspace(0, n - block, n_folds).astype(int)
    folds = []
    for s in starts:
        s = int(s)
        folds.append({"train": (s, s + train),
                      "val": (s + train, s + train + val),
                      "test": (s + train + val, s + train + val + test)})
    return folds


def anchored_folds(n, n_folds=5, val=1500, test=1500):
    """Anchored (expanding) window: train grows from 0, test slides forward."""
    test_total = n_folds * test
    folds = []
    for k in range(n_folds):
        test_hi = n - (n_folds - 1 - k) * test
        test_lo = test_hi - test
        val_hi = test_lo
        val_lo = val_hi - val
        folds.append({"train": (0, val_lo), "val": (val_lo, val_hi), "test": (test_lo, test_hi)})
    return folds


def consistency_gate(test_returns, min_frac=0.6):
    a = np.asarray(test_returns, float)
    k = len(a)
    pos = int((a > 0).sum())
    return {"pass": bool(k and pos / k >= min_frac), "n_pos": pos, "n": k,
            "frac": float(pos / k) if k else float("nan")}
