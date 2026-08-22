"""
oof_framework.py — Walk-forward expanding OOF utilities for ORB push-pass.

Method:
  Expanding-window WF with initial training 2010-2013 (4 years), then 1-year
  test folds 2014, 2015, ..., 2026.

For each fold F:
  - Training start set = days in [data_start, F_start)
  - Test start set     = days in [F_start, F_end)

For each candidate config K (exit variant, sizing rule, etc.):
  - In-sample p(pass) on training = simulator with start_indices ∈ training
  - Apply to test                  = simulator with start_indices ∈ test
  - "Best K on training" is selected from a candidate set

OOF aggregate:
  - For each test fold, the simulator runs with the BEST-ON-TRAINING config,
    measures p_funded over starts in that fold.
  - The OOF p_funded reported = pooled fraction of FUNDED outcomes over
    all test starts.

Comparing in-sample (full-data simulator on the same config) vs OOF
(walk-forward) gives the overfit gap.

Selection criterion: training p_funded. Tie-break: training p_phase1.

NOTE: each simulator path can extend AFTER the test fold end (the challenge
walks forward through later data). This is correct — at decision time
(start of test fold), the config was fixed; the unrolled challenge uses
future data which is "future" to the decision.
"""
from __future__ import annotations
from pathlib import Path
import sys
import logging
from dataclasses import dataclass
from typing import Callable
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from nq_sim import simulate_2step_uncapped

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# Default WF setup
INITIAL_TRAIN_END = "2014-01-01"
WF_FOLD_END_DATES = [
    "2014-01-01", "2015-01-01", "2016-01-01", "2017-01-01",
    "2018-01-01", "2019-01-01", "2020-01-01", "2021-01-01",
    "2022-01-01", "2023-01-01", "2024-01-01", "2025-01-01",
    "2026-01-01", "2027-01-01",  # last test fold = 2026 partial year
]


def build_fold_boundaries(daily_R: pd.Series,
                            fold_ends: list[str] = WF_FOLD_END_DATES) -> list[tuple[int, int, int]]:
    """Return [(train_end_idx, test_start_idx, test_end_idx), ...] index triples."""
    idx = daily_R.index
    if not isinstance(idx, pd.DatetimeIndex):
        idx = pd.DatetimeIndex(idx)
    boundaries = []
    for i in range(len(fold_ends) - 1):
        train_end = pd.Timestamp(fold_ends[i])
        test_end = pd.Timestamp(fold_ends[i + 1])
        # Train indices = all rows < train_end
        train_end_idx = int((idx < train_end).sum())
        test_start_idx = train_end_idx
        test_end_idx = int((idx < test_end).sum())
        if test_end_idx <= test_start_idx + 30:
            continue
        boundaries.append((train_end_idx, test_start_idx, test_end_idx,
                            str(train_end.date()), str(test_end.date())))
    return boundaries


def evaluate_config_pfunded(daily_R: pd.Series, start_indices: np.ndarray,
                              block_cap_pct: float = 0.005) -> dict:
    """Run FTMO 2-step sim with restricted start indices. Returns dict with p_funded."""
    if len(start_indices) == 0:
        return {"p_funded_pct": float("nan"), "p_phase1_pct": float("nan"),
                "n_resolved": 0, "n_funded": 0, "n_total": 0}
    out = simulate_2step_uncapped(daily_R, block_cap_pct=block_cap_pct,
                                    start_indices=start_indices.tolist())
    # Compute counts
    p_funded_frac = out.get("p_funded", float("nan"))
    if pd.isna(p_funded_frac):
        n_funded = 0
    else:
        n_funded = int(round(p_funded_frac * out["n_resolved"]))
    return {
        "p_funded_pct": out.get("p_funded_pct", float("nan")),
        "p_phase1_pct": out.get("p_phase1", 0.0) * 100 if not pd.isna(out.get("p_phase1", float("nan"))) else float("nan"),
        "n_resolved": out["n_resolved"],
        "n_funded": n_funded,
        "n_total": out["n_total"],
        "censored_pct": out["censored_pct"],
    }


def walk_forward_select_apply(daily_R_per_config: dict[str, pd.Series],
                                 fold_boundaries: list[tuple],
                                 block_cap_pct: float = 0.005,
                                 min_train_n_resolved: int = 100) -> dict:
    """For each fold:
       1. Compute training p_funded for each candidate.
       2. Pick best (max training p_funded, with min n_resolved gate).
       3. Apply best to test fold; record test p_funded.

    Returns dict with per-fold selections and aggregated OOF stats.
    """
    fold_records = []
    total_test_resolved = 0
    total_test_funded = 0
    total_test_starts = 0

    for fold_idx, (train_end_idx, test_start_idx, test_end_idx,
                    train_end_date, test_end_date) in enumerate(fold_boundaries):
        # 1. Compute training p_funded for each candidate
        train_results = {}
        for name, daily_R in daily_R_per_config.items():
            train_starts = np.arange(0, train_end_idx)
            train_eval = evaluate_config_pfunded(daily_R, train_starts, block_cap_pct)
            train_results[name] = train_eval

        # 2. Pick best (gate by min training n_resolved)
        ranked = sorted(
            train_results.items(),
            key=lambda kv: (
                kv[1].get("p_funded_pct", -1) if kv[1].get("n_resolved", 0) >= min_train_n_resolved else -100,
                kv[1].get("p_phase1_pct", -1),
            ),
            reverse=True,
        )
        best_name = ranked[0][0]
        best_train = ranked[0][1]

        # 3. Apply to test fold
        test_starts = np.arange(test_start_idx, test_end_idx)
        test_R = daily_R_per_config[best_name]
        test_eval = evaluate_config_pfunded(test_R, test_starts, block_cap_pct)

        fold_records.append({
            "fold_idx": fold_idx,
            "train_end": train_end_date,
            "test_end": test_end_date,
            "best_config": best_name,
            "train_p_funded_pct": round(best_train.get("p_funded_pct", float("nan")), 2),
            "train_p_phase1_pct": round(best_train.get("p_phase1_pct", float("nan")), 2),
            "train_n_resolved": best_train.get("n_resolved", 0),
            "test_p_funded_pct": round(test_eval.get("p_funded_pct", float("nan")), 2),
            "test_p_phase1_pct": round(test_eval.get("p_phase1_pct", float("nan")), 2),
            "test_n_resolved": test_eval.get("n_resolved", 0),
            "test_n_funded": test_eval.get("n_funded", 0),
            "test_n_total": test_eval.get("n_total", 0),
            "test_censored_pct": round(test_eval.get("censored_pct", float("nan")), 1),
        })

        total_test_resolved += test_eval.get("n_resolved", 0)
        total_test_funded += test_eval.get("n_funded", 0)
        total_test_starts += test_eval.get("n_total", 0)

    oof_p_funded = (total_test_funded / total_test_resolved * 100) if total_test_resolved > 0 else float("nan")
    return {
        "fold_records": fold_records,
        "oof_total_starts": total_test_starts,
        "oof_total_resolved": total_test_resolved,
        "oof_total_funded": total_test_funded,
        "oof_p_funded_pct": round(oof_p_funded, 2),
    }


def full_sample_pfunded(daily_R: pd.Series, block_cap_pct: float = 0.005) -> float:
    """In-sample p_funded across all start dates."""
    all_starts = np.arange(0, len(daily_R))
    res = evaluate_config_pfunded(daily_R, all_starts, block_cap_pct)
    return res.get("p_funded_pct", float("nan"))
