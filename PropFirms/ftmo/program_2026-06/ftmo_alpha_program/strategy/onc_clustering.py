"""
onc_clustering.py — Optimal Number of Clusters on a correlation matrix
========================================================================

López de Prado (2019) "A Robust Estimator of the Efficient Frontier" §4.2,
implementing the simple hierarchical-clustering variant suitable for selecting
a representative subset of features whose pairwise correlation is below a
threshold (here 0.8) and whose silhouette is maximised.

Steps:
  1. Convert correlation to a metric distance D = sqrt(0.5 * (1 - corr))
     (Mantegna 1999; Lopez de Prado AFML eq. 14.4).
  2. Hierarchical clustering with average linkage (scipy).
  3. Sweep k from 2 to N-1 → for each k, compute mean silhouette score on D.
  4. Optimal k = arg max(silhouette).
  5. For each cluster, pick the **medoid** (smallest mean distance to cluster
     peers) as the representative.
  6. Hard rule: if two features have |corr| ≥ 0.8, force them into the same
     cluster regardless of the silhouette pick (post-processing step).

Returns a structure usable downstream by the ML sprint to set the honest
trial count for DSR and to feed the model with a non-redundant feature subset.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.metrics import silhouette_score


@dataclass
class ONCResult:
    n_clusters: int
    silhouette: float
    labels: np.ndarray            # cluster id per feature, len = N
    representatives: list[str]    # one feature name per cluster (medoid)
    members: dict[int, list[str]] # cluster id → list of feature names
    distance: np.ndarray          # N×N distance matrix (kept for downstream)
    linkage: np.ndarray           # scipy linkage matrix
    feature_names: list[str]
    hard_merged: list[tuple[str, str]]  # pairs forced together (corr ≥ threshold)


def correlation_to_distance(corr: np.ndarray) -> np.ndarray:
    """Mantegna metric: D_ij = sqrt(0.5*(1 - corr_ij)). 0 ⇒ identical, 1 ⇒ orth."""
    corr = np.clip(corr, -1.0, 1.0)
    return np.sqrt(0.5 * (1.0 - corr))


def _force_high_corr_merges(labels: np.ndarray, corr_abs: np.ndarray,
                            names: list[str], threshold: float
                            ) -> tuple[np.ndarray, list[tuple[str, str]]]:
    """Post-process: any |corr_ij| ≥ threshold forces i and j to share a cluster.

    Reassign by union-find. Documents the forced merges for the audit.
    """
    n = len(labels)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # seed unions from initial clustering
    for c in np.unique(labels):
        members = np.where(labels == c)[0].tolist()
        for i in members[1:]:
            union(members[0], i)

    # force merges for high-corr pairs
    forced: list[tuple[str, str]] = []
    for i in range(n):
        for j in range(i + 1, n):
            if corr_abs[i, j] >= threshold:
                if find(i) != find(j):
                    forced.append((names[i], names[j]))
                union(i, j)

    roots = [find(i) for i in range(n)]
    remap = {r: k + 1 for k, r in enumerate(sorted(set(roots)))}
    new_labels = np.array([remap[r] for r in roots], dtype=np.int64)
    return new_labels, forced


def _medoid(idx_in_cluster: np.ndarray, distance: np.ndarray) -> int:
    """Index of the feature with minimum mean distance to peers in cluster."""
    if len(idx_in_cluster) == 1:
        return int(idx_in_cluster[0])
    sub = distance[np.ix_(idx_in_cluster, idx_in_cluster)]
    mean_d = sub.mean(axis=1)
    return int(idx_in_cluster[np.argmin(mean_d)])


def onc(corr_df: pd.DataFrame, hard_merge_threshold: float = 0.8,
        max_k: int | None = None, min_k: int = 2,
        linkage_method: str = "average", random_state: int = 0) -> ONCResult:
    """Optimal Number of Clusters (silhouette sweep + high-|corr| forced merges).

    Parameters
    ----------
    corr_df : square correlation DataFrame (features as both index and columns).
    hard_merge_threshold : pairs with |corr| ≥ this share a cluster regardless.
    max_k : upper bound for the silhouette sweep (defaults to N-1).
    min_k : lower bound (≥ 2).
    linkage_method : scipy linkage method (default "average" per LdP).
    """
    names = list(corr_df.columns)
    corr = corr_df.values.astype(float)
    np.fill_diagonal(corr, 1.0)
    n = len(names)
    if n < 3:
        raise ValueError(f"Need ≥3 features for ONC; got {n}")

    dist = correlation_to_distance(corr)
    # symmetrise (numerical noise) and ensure non-negative
    dist = np.clip((dist + dist.T) / 2.0, 0.0, None)
    np.fill_diagonal(dist, 0.0)
    cond = squareform(dist, checks=False)
    Z = linkage(cond, method=linkage_method)

    if max_k is None:
        max_k = n - 1

    best_k, best_sil, best_labels = None, -np.inf, None
    sil_path: list[tuple[int, float]] = []
    for k in range(min_k, max_k + 1):
        labels_k = fcluster(Z, t=k, criterion="maxclust")
        if len(np.unique(labels_k)) < 2:
            continue
        try:
            sil = float(silhouette_score(dist, labels_k, metric="precomputed"))
        except Exception:
            continue
        sil_path.append((k, sil))
        if sil > best_sil:
            best_k, best_sil, best_labels = k, sil, labels_k

    if best_labels is None:
        # all singletons
        best_labels = np.arange(1, n + 1)
        best_k = n
        best_sil = 0.0

    # enforce high-correlation merges
    corr_abs = np.abs(corr)
    final_labels, forced = _force_high_corr_merges(
        best_labels, corr_abs, names, hard_merge_threshold)
    k_final = int(len(np.unique(final_labels)))

    members: dict[int, list[str]] = {}
    representatives: list[str] = []
    for c in sorted(np.unique(final_labels)):
        idx = np.where(final_labels == c)[0]
        members[int(c)] = [names[i] for i in idx]
        med = _medoid(idx, dist)
        representatives.append(names[med])

    return ONCResult(
        n_clusters=k_final,
        silhouette=float(best_sil),
        labels=final_labels,
        representatives=representatives,
        members=members,
        distance=dist,
        linkage=Z,
        feature_names=names,
        hard_merged=forced,
    )


def summarise_onc(result: ONCResult) -> str:
    """Pretty-print the ONC structure for the audit report."""
    lines = [f"ONC — N={result.n_clusters} clusters, silhouette={result.silhouette:.3f}"]
    for c, fs in result.members.items():
        rep = next(r for r in result.representatives
                   if r in fs)
        tag = " (medoid)" if len(fs) > 1 else ""
        lines.append(f"  cluster {c}: representative={rep}{tag} | members={fs}")
    if result.hard_merged:
        lines.append("  Forced merges (|corr| ≥ 0.8):")
        for a, b in result.hard_merged:
            lines.append(f"    - {a} ↔ {b}")
    return "\n".join(lines)
