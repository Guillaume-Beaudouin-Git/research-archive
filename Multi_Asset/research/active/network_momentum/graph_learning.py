"""
graph_learning.py — Laplacian-based graph learning for Network Momentum (Strategy E)
======================================================================================
Solves the convex graph learning problem from Pu et al. (2023) equations 3-5:

    minimize_A   tr(F^T L F) / (N*K) + alpha * ||A||_F^2 - beta * sum(log(d))

    subject to:  A symmetric, A_ii = 0, A_ij >= 0

Where:
  - F = features matrix (N × K), K=8 features
  - L = D - A (graph Laplacian, D = diag(A @ 1))
  - d = diagonal of D (degree vector)
  - alpha = smoothness penalty (higher = sparser graph)
  - beta = log-barrier ensuring connectivity (higher = denser graph)

Uses CVXPY with CLARABEL solver (bundled with cvxpy 1.7+).
Multi-lookback: learn 5 graphs at lookbacks {252, 504, 756, 1008, 1260} and average.

Usage:
    from Multi_Asset.research.active.network_momentum.graph_learning import learn_graph
    A = learn_graph(F_window, alpha=0.1, beta=0.1)
    A_ensemble = learn_graph_ensemble(F_history, t_idx, alpha=0.1, beta=0.1)
"""
from __future__ import annotations

import logging
import warnings
from typing import List, Optional

import cvxpy as cp
import numpy as np

log = logging.getLogger(__name__)

LOOKBACKS        = [252, 504, 756, 1008, 1260]
DEFAULT_ALPHA    = 0.1
DEFAULT_BETA     = 0.1
MAX_SOLVE_SECS   = 60
SOLVER_TOL       = 1e-5


# ─────────────────────────────────────────────────────────────────────────────
# Core graph learning
# ─────────────────────────────────────────────────────────────────────────────

def learn_graph(
    F_window: np.ndarray,        # shape (T_window, N, 8) or (N, K) already averaged
    alpha:    float = DEFAULT_ALPHA,
    beta:     float  = DEFAULT_BETA,
    verbose:  bool   = False,
) -> Optional[np.ndarray]:
    """
    Learn an N×N adjacency matrix from a feature window.

    If F_window is 3D (T, N, K), computes column-means across T.
    If 2D (N, K), uses directly.

    Returns N×N symmetric non-negative adjacency matrix (zeros on diagonal),
    or None if solver fails.
    """
    if F_window.ndim == 3:
        # Average features across time window, ignoring NaN rows
        F = np.nanmean(F_window, axis=0)  # (N, K)
    else:
        F = F_window                       # already (N, K)

    # Replace remaining NaN with 0 (missing data → zero feature)
    F = np.nan_to_num(F, nan=0.0)

    N, K = F.shape
    if N < 4:
        log.warning(f"learn_graph: N={N} too small, returning identity-zero")
        return np.zeros((N, N))

    # Upper-triangle variables (excludes diagonal, symmetric constraint)
    n_edges = N * (N - 1) // 2

    # Build CVXPY problem
    # A_vec: flattened upper-triangle edge weights >= 0
    A_vec = cp.Variable(n_edges, nonneg=True)

    # Build full symmetric A from upper-triangle vector
    # Upper-triangle indices
    tri_i, tri_j = np.triu_indices(N, k=1)

    # A_full[i,j] = A_full[j,i] = A_vec via indexing
    # We build L = D - A directly
    # L_ij = -A_ij for i != j, L_ii = sum_j A_ij
    # L = diag(A @ 1) - A

    # Build linear maps: A_full and degree vector d from A_vec
    # A_full = E @ A_vec + E.T @ A_vec (excluding diagonal)
    # We express the Laplacian in terms of A_vec

    # Degree of node i = sum of row i edges = sum over j!=i of A[i,j]
    # Build degree matrix from A_vec
    # d[i] = sum_{j: j>i} A_vec[edge(i,j)] + sum_{j: j<i} A_vec[edge(j,i)]

    # Edge-to-node incidence: B[i, e] = 1 if node i is endpoint of edge e
    B = np.zeros((N, n_edges))
    for e, (i, j) in enumerate(zip(tri_i, tri_j)):
        B[i, e] = 1.0
        B[j, e] = 1.0

    d = B @ A_vec  # degree vector (N,)

    # Laplacian diagonal = d, off-diagonal L[i,j] = -A[i,j]
    # tr(F^T L F) = sum_i d[i] * ||F[i]||^2 - sum_{i<j} A[i,j] * 2 * F[i].F[j]
    # = sum_e A_vec[e] * (||F[i]||^2 + ||F[j]||^2 - 2 F[i].F[j])
    # = sum_e A_vec[e] * ||F[i] - F[j]||^2

    # Compute ||F[i] - F[j]||^2 for each edge
    diff_sq = np.array([
        np.sum((F[i] - F[j]) ** 2)
        for i, j in zip(tri_i, tri_j)
    ])  # (n_edges,)

    smoothness_term = (A_vec @ diff_sq) / (N * K)  # scalar, normalized

    # Frobenius norm: ||A||_F^2 = 2 * sum A_vec^2 (since A symmetric, each edge counted twice)
    frob_term = alpha * 2.0 * cp.sum_squares(A_vec)

    # Log-barrier: -beta * sum(log(d[i])) to prevent disconnected nodes
    # Use cp.sum(cp.log(d)) — concave, so negating makes it convex in the minimize
    log_barrier = -beta * cp.sum(cp.log(d + 1e-8))

    objective = cp.Minimize(smoothness_term + frob_term + log_barrier)

    # Connectivity constraint: minimum degree > 0 is handled by log barrier
    # Add explicit lower bound to prevent numerical issues
    constraints = [d >= 1e-6]

    problem = cp.Problem(objective, constraints)

    # Try solvers in order: CLARABEL → SCS → ECOS
    solved = False
    for solver_name, solver_kwargs in [
        (cp.CLARABEL, {"verbose": verbose, "max_iter": 10000}),
        (cp.SCS,      {"verbose": verbose, "max_iters": 10000, "eps": SOLVER_TOL}),
        (cp.ECOS,     {"verbose": verbose, "max_iters": 10000}),
    ]:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                problem.solve(solver=solver_name, **solver_kwargs)
            if problem.status in ("optimal", "optimal_inaccurate") and A_vec.value is not None:
                solved = True
                break
        except Exception as exc:
            log.debug(f"Solver {solver_name} failed: {exc}")
            continue

    if not solved:
        log.error(f"All solvers failed (N={N}, alpha={alpha}, beta={beta})")
        return None

    # Reconstruct full N×N symmetric adjacency matrix
    a_vals = np.maximum(A_vec.value, 0.0)  # clip negatives from numerical noise
    A_full = np.zeros((N, N))
    for e, (i, j) in enumerate(zip(tri_i, tri_j)):
        A_full[i, j] = a_vals[e]
        A_full[j, i] = a_vals[e]

    return A_full


# ─────────────────────────────────────────────────────────────────────────────
# Multi-lookback ensemble
# ─────────────────────────────────────────────────────────────────────────────

def learn_graph_ensemble(
    F_history: np.ndarray,          # shape (T_total, N, 8) — full history up to time t
    lookbacks: List[int] = LOOKBACKS,
    alpha: float = DEFAULT_ALPHA,
    beta:  float = DEFAULT_BETA,
) -> Optional[np.ndarray]:
    """
    Learn 5 graphs at different lookbacks and return their simple average.

    Uses the most recent [lookback] rows of F_history for each lookback.
    Skips lookbacks where insufficient history exists.

    Returns averaged N×N adjacency matrix (non-negative, symmetric, zero diagonal).
    """
    T = F_history.shape[0]
    graphs = []

    for lb in lookbacks:
        if T < lb:
            log.debug(f"Lookback {lb}: insufficient history ({T} < {lb}), skipping")
            continue
        F_window = F_history[-lb:]        # most recent lb rows
        A = learn_graph(F_window, alpha=alpha, beta=beta)
        if A is not None:
            graphs.append(A)
        else:
            log.warning(f"Graph learning failed at lookback={lb}")

    if not graphs:
        log.error("All lookbacks failed — returning None")
        return None

    # Simple average across successful lookbacks
    A_ens = np.mean(graphs, axis=0)
    return A_ens


# ─────────────────────────────────────────────────────────────────────────────
# Graph analysis utilities
# ─────────────────────────────────────────────────────────────────────────────

def graph_stats(A: np.ndarray, asset_names: list) -> dict:
    """Compute summary statistics for a learned adjacency matrix."""
    N = A.shape[0]
    n_edges = (N * (N - 1)) // 2

    # Edge density (fraction of possible edges with nonzero weight)
    edge_mask = A[np.triu_indices(N, k=1)] > 1e-6
    density = edge_mask.mean()

    # Top 5 strongest edges
    tri_i, tri_j = np.triu_indices(N, k=1)
    weights = A[tri_i, tri_j]
    top5_idx = np.argsort(weights)[-5:][::-1]
    top5 = [
        (asset_names[tri_i[k]], asset_names[tri_j[k]], round(float(weights[k]), 4))
        for k in top5_idx
    ]

    # Degree per node
    degrees = A.sum(axis=1)

    return {
        "n_assets":      N,
        "edge_density":  round(float(density), 3),
        "n_active_edges":int(edge_mask.sum()),
        "top5_edges":    top5,
        "mean_degree":   round(float(degrees.mean()), 4),
        "min_degree":    round(float(degrees.min()), 6),
    }


def jaccard_stability(A1: np.ndarray, A2: np.ndarray, threshold: float = 1e-6) -> float:
    """
    Jaccard similarity between two binary edge sets.
    Measures graph structure stability across rebalance dates.
    """
    N = A1.shape[0]
    tri_i, tri_j = np.triu_indices(N, k=1)
    e1 = A1[tri_i, tri_j] > threshold
    e2 = A2[tri_i, tri_j] > threshold
    intersection = (e1 & e2).sum()
    union        = (e1 | e2).sum()
    return float(intersection / union) if union > 0 else 0.0


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    # Quick smoke test with random features
    np.random.seed(42)
    N, K, T = 10, 8, 300
    F_rand = np.random.randn(T, N, K).astype(np.float32)

    print("Testing single graph learning...")
    A = learn_graph(F_rand, alpha=0.1, beta=0.1)
    if A is not None:
        names = [f"A{i}" for i in range(N)]
        stats = graph_stats(A, names)
        print(f"  Edge density: {stats['edge_density']:.3f}")
        print(f"  Top 5 edges: {stats['top5_edges']}")
        print(f"  Mean degree: {stats['mean_degree']:.4f}")
    else:
        print("  FAILED")

    print("\nTesting ensemble (3 lookbacks for speed)...")
    A_ens = learn_graph_ensemble(F_rand, lookbacks=[100, 200, 300], alpha=0.1, beta=0.1)
    if A_ens is not None:
        stats_ens = graph_stats(A_ens, names)
        print(f"  Ensemble edge density: {stats_ens['edge_density']:.3f}")
    else:
        print("  FAILED")
