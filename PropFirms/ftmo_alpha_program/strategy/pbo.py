"""
pbo.py — Probability of Backtest Overfitting (Bailey, Borwein, López de Prado, Zhu 2014)
==========================================================================================

Reference
---------
Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2014).
"The probability of backtest overfitting." Journal of Computational Finance, 20(4).

What PBO measures
-----------------
Given a matrix `M` of returns shaped (T, N) with N strategy variants, PBO
estimates the probability that the variant selected as best in-sample
underperforms (is below the median) out-of-sample. PBO is computed via
combinatorial splits of the time axis into S equal slices (S even), with
each split assigning S/2 slices to IS and S/2 to OOS.

Algorithm (López de Prado AFML §11.4)
-------------------------------------
  1. Split rows of M into S contiguous slices C_1, …, C_S.
  2. Enumerate all C(S, S/2) combinations c of S/2 slices.
     For each c:
       a. J  = rows from slices in c       (IS)
       b. Jb = rows NOT in c               (OOS)
       c. R^j_n = Sharpe of column n on J,   R^jb_n = Sharpe of column n on Jb
       d. n*  = argmax_n R^j_n              (best IS)
       e. w   = OOS rank of n* / (N + 1)    (0 < w < 1)
       f. λ   = log( w / (1 - w) )          (logit)
     PBO = (1/|C|) * Σ 1[λ < 0]

Higher PBO ⇒ greater overfitting. Gate (CLAUDE.md L20-class): PBO < 0.5
required, ideally < 0.2 for a non-fragile selection.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np


def _sharpe(rets: np.ndarray) -> np.ndarray:
    """Per-column Sharpe (mean/std) on a 2-D array (axis=0 = time)."""
    mu = rets.mean(axis=0)
    sd = rets.std(axis=0, ddof=1)
    sd = np.where(sd <= 1e-12, np.nan, sd)
    return mu / sd


@dataclass
class PBOResult:
    pbo: float
    n_combinations: int
    n_variants: int
    n_slices: int
    logits: np.ndarray
    best_in_sample_indices: np.ndarray
    oos_ranks: np.ndarray


def probability_of_backtest_overfitting(M: np.ndarray, S: int = 16) -> PBOResult:
    """
    Compute PBO on a (T, N) returns matrix using S equal slices.

    Parameters
    ----------
    M : np.ndarray, shape (T, N)
        Per-period returns for N strategy variants over T periods.
    S : int
        Number of equal-time slices (must be even, ≥ 4). Default 16 ⇒ C(16,8)=12,870
        combinations — robust under arbitrary slice geometry.

    Returns
    -------
    PBOResult
        Fields: pbo, n_combinations, n_variants, n_slices, logits, ...
    """
    M = np.asarray(M, dtype=float)
    T, N = M.shape
    if N < 2:
        raise ValueError("PBO needs N ≥ 2 variants.")
    if S % 2 != 0 or S < 4:
        raise ValueError("S must be even and ≥ 4.")
    if T < S:
        raise ValueError(f"T={T} < S={S}; can't slice.")

    # Trim leading rows so T is divisible by S
    drop = T % S
    if drop:
        M = M[drop:, :]
        T = T - drop
    slice_len = T // S
    slices = [M[i * slice_len:(i + 1) * slice_len, :] for i in range(S)]

    combos = list(combinations(range(S), S // 2))
    logits = np.empty(len(combos), dtype=float)
    best = np.empty(len(combos), dtype=int)
    ranks = np.empty(len(combos), dtype=int)

    for k, c in enumerate(combos):
        c_set = set(c)
        J = np.vstack([slices[i] for i in c])
        Jb = np.vstack([slices[i] for i in range(S) if i not in c_set])
        sr_is = _sharpe(J)
        sr_oos = _sharpe(Jb)
        # NaN strategies are placed at the bottom of the IS ranking
        sr_is_filled = np.where(np.isnan(sr_is), -np.inf, sr_is)
        nstar = int(np.argmax(sr_is_filled))
        # OOS rank of n* among all variants (1 = worst, N = best)
        order = np.argsort(np.where(np.isnan(sr_oos), -np.inf, sr_oos), kind="mergesort")
        rank = int(np.where(order == nstar)[0][0]) + 1
        w = rank / (N + 1)
        w = min(max(w, 1e-6), 1.0 - 1e-6)
        logits[k] = np.log(w / (1.0 - w))
        best[k] = nstar
        ranks[k] = rank

    pbo = float((logits < 0).mean())
    return PBOResult(pbo=pbo, n_combinations=len(combos), n_variants=N,
                     n_slices=S, logits=logits,
                     best_in_sample_indices=best, oos_ranks=ranks)
