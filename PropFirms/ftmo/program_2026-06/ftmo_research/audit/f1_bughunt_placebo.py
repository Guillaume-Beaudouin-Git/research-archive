"""
f1_bughunt_placebo.py — Test décisif #2 : permutation placebo de time_to_break.

Si l'edge "ttb low → +R" est un VRAI signal point-in-time, alors permuter
time_to_break aléatoirement à travers les trades DEVRAIT donner edge ≈ 0.

Si l'edge persiste sous permutation → leak structurel dans le pipeline
(ttb encode quelque chose qui prédit R par construction, pas par causalité).

Test:
  1. Take the original trade dataset (3056 trades, EXEC_0 buggy model).
  2. Shuffle the time_to_break_5min column across trades (preserving R distribution).
  3. Apply F1 filter (ttb ≤ q0.5) on shuffled data.
  4. Repeat 1000 times.
  5. Compare distribution of "F1 mean R under permutation" vs the observed F1 mean R.

If observed F1 mean R is in the upper tail of permutation distribution → real edge.
If observed lies within the bulk → permutation makes the edge persist → LEAK.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats


def placebo_test(df: pd.DataFrame, n_permutations: int = 1000, seed: int = 42):
    rng = np.random.default_rng(seed)
    threshold = df["time_to_break_5min"].quantile(0.5)
    keep_orig = df["time_to_break_5min"] <= threshold
    observed_mean_R = df[keep_orig]["r_realised"].mean()
    observed_advantage = observed_mean_R - df["r_realised"].mean()

    perm_means = []
    perm_advantages = []
    for i in range(n_permutations):
        shuffled = df["time_to_break_5min"].sample(frac=1.0, random_state=int(rng.integers(0, 10**9))).values
        ttb_thr = np.quantile(shuffled, 0.5)
        keep = shuffled <= ttb_thr
        mean_R = df.loc[keep, "r_realised"].mean()
        perm_means.append(mean_R)
        perm_advantages.append(mean_R - df["r_realised"].mean())
    perm_arr = np.array(perm_means)
    perm_adv = np.array(perm_advantages)
    p_value = float((perm_arr >= observed_mean_R).mean())
    return {
        "observed_F1_mean_R": observed_mean_R,
        "observed_advantage": observed_advantage,
        "perm_mean_F1": perm_arr.mean(),
        "perm_std_F1": perm_arr.std(),
        "perm_q05": float(np.quantile(perm_arr, 0.05)),
        "perm_q95": float(np.quantile(perm_arr, 0.95)),
        "p_value_one_sided": p_value,
        "z_score": (observed_mean_R - perm_arr.mean()) / perm_arr.std() if perm_arr.std() > 0 else float("inf"),
    }


def placebo_test_clean_data(quantile: float = 0.5, n_perm: int = 1000):
    """Run placebo on the clean (EXEC_NEXT_OPEN) data, not just the buggy EXEC_0."""
    print("Running placebo on EXEC_NEXT_OPEN (clean execution)...")
    # Re-extract clean trades
    from f1_bughunt_delay import extract_all_exec
    df_clean = extract_all_exec("EXEC_NEXT_OPEN", lo="2022", hi="2025")
    df_clean = df_clean.rename(columns={"ttb_5min": "time_to_break_5min"})
    res = placebo_test(df_clean, n_permutations=n_perm)
    return res, df_clean


if __name__ == "__main__":
    df_buggy = pd.read_parquet("trade_dataset.parquet")
    print(f"Loaded buggy dataset: {len(df_buggy)} trades")
    print()

    print("=" * 90)
    print("PLACEBO #1 — Permute ttb on the BUGGY EXEC_0 dataset (n=1000 perms)")
    print("=" * 90)
    res = placebo_test(df_buggy, n_permutations=1000)
    for k, v in res.items():
        print(f"  {k:>25s} : {v}")
    print()
    print(f"  z-score (obs vs perm distribution) : {res['z_score']:.2f}")
    print(f"  one-sided p-value                  : {res['p_value_one_sided']:.4f}")
    if res["p_value_one_sided"] < 0.05:
        print(f"  -> observed F1 mean R is in the >95th percentile of placebo → REAL signal")
    elif res["p_value_one_sided"] < 0.50:
        print(f"  -> observed F1 mean R is in the upper half but not significantly so")
    else:
        print(f"  -> observed F1 mean R is in the bulk → SUSPICIOUS, possible leak")
    print()

    print("=" * 90)
    print("PLACEBO #2 — Permute ttb on CLEAN EXEC_NEXT_OPEN dataset (n=1000 perms)")
    print("=" * 90)
    res_clean, df_clean = placebo_test_clean_data(n_perm=1000)
    for k, v in res_clean.items():
        print(f"  {k:>25s} : {v}")
    print()
    print(f"  z-score : {res_clean['z_score']:.2f}, one-sided p-value : {res_clean['p_value_one_sided']:.4f}")
    if res_clean["p_value_one_sided"] < 0.05:
        print(f"  -> REAL signal under clean execution")
    else:
        print(f"  -> SUSPICIOUS — F1 effect may be artefactual under clean exec")
