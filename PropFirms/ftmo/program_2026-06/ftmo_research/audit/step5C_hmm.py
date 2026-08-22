"""
step5C_hmm.py — Walk-forward HMM with filtered (online) probabilities + L19 ablation.

Implementation notes:
  - hmmlearn GaussianHMM (Student-t not directly available; we approximate fat
    tails by augmenting features with abs(returns) which captures vol clustering)
  - WALK-FORWARD: refit every 60 trading days using only data <= J-1
  - FILTERED (online): use score_samples step-by-step via forward algorithm,
    NOT Viterbi/smoothed (which uses future info)
  - Map states to "good"/"bad" by mean ORB R conditional on state (training only)
  - L19 ablation: HMM-gate vs simple threshold-gate (vr5 low tercile), head-to-head

Caveat: hmmlearn doesn't expose filtered probabilities directly — we compute them
by running predict_proba on each prefix and taking the last column.
"""
from __future__ import annotations
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from orb_core import build_3sleeve_matrix, _load_m5, block_capped_pnl
from ftmo_engine import simulate
from step5_regime import (
    underlying_daily_log_returns, rolling_features, tag_terciles_expanding
)


def build_hmm_features(lo: str = "2020", hi: str = "2026") -> pd.DataFrame:
    """
    Daily features for HMM: [log_return_z, abs_return_z, rv5_z]
    Standardised expanding (so no leak).
    """
    r_us = underlying_daily_log_returns("US100", lo, hi)
    r_ger = underlying_daily_log_returns("GER40", lo, hi)
    # Combine: portfolio of US100 + GER40
    r = ((r_us + r_ger) / 2).dropna()
    df = pd.DataFrame({"r": r})
    df["absr"] = r.abs()
    df["rv5"] = r.rolling(5).std()
    df = df.dropna()
    # Expanding z-score (online, no future leak)
    def expanding_z(s):
        mean = s.expanding(60).mean()
        std = s.expanding(60).std()
        return (s - mean) / std
    feats = pd.DataFrame({
        "r_z": expanding_z(df["r"]),
        "absr_z": expanding_z(df["absr"]),
        "rv5_z": expanding_z(df["rv5"]),
    }).dropna()
    return feats


def walk_forward_hmm(feats: pd.DataFrame, n_states: int = 2,
                     refit_every: int = 60, min_train: int = 252,
                     seed: int = 0) -> pd.DataFrame:
    """
    Walk-forward HMM with filtered (online) state probabilities.
    Returns a DataFrame index=date with columns:
      prob_state_0 .. prob_state_n-1  (filtered, using info <= t)
      state_pred   (argmax)
    """
    out_probs = []
    out_states = []
    dates = []
    X = feats.values
    last_model = None
    last_means_ordered = None
    state_order = None
    for i in range(min_train, len(X)):
        if (i - min_train) % refit_every == 0:
            # Refit on data up to i-1
            try:
                hmm = GaussianHMM(n_components=n_states,
                                  covariance_type="full",
                                  n_iter=50, random_state=seed,
                                  tol=1e-3)
                hmm.fit(X[:i])
                # Sort states by mean of feature 0 (return) so state 0 = "low return"
                # i.e. "bad" state
                m = hmm.means_[:, 0]
                state_order = np.argsort(m)
                last_model = hmm
            except Exception:
                if last_model is None:
                    continue
        if last_model is None:
            continue
        # Filter on data <= i (inclusive of t=i for the obs at t=i)
        # Filtered probability = P(state_t | obs_0..t)
        try:
            probs_all = last_model.predict_proba(X[:i+1])
            p_t = probs_all[-1]  # last = filtered
            # Reorder by state_order
            p_ordered = p_t[state_order]
            out_probs.append(p_ordered)
            out_states.append(int(np.argmax(p_ordered)))
            dates.append(feats.index[i])
        except Exception:
            continue
    arr = np.array(out_probs)
    df = pd.DataFrame(arr, index=dates,
                      columns=[f"prob_state{i}" for i in range(n_states)])
    df["state"] = out_states
    return df


def state_to_edge_map(hmm_df: pd.DataFrame, M_full: pd.DataFrame,
                      train_end: str) -> dict:
    """
    On TRAINING data only, compute the mean ORB R conditional on state.
    Returns {state: mean_R} so we can label 'good' state = argmax.
    """
    pnl = block_capped_pnl(M_full).fillna(0.0)
    train_states = hmm_df.loc[:train_end, "state"]
    train_pnl = pnl.reindex(train_states.index).fillna(0.0)
    return {s: float(train_pnl[train_states == s].mean()) for s in train_states.unique()}


def step_5C_hmm(M_full: pd.DataFrame, n_states: int = 2):
    print("=" * 80)
    print("5-C — Walk-forward HMM (filtered probabilities, ablation L19)")
    print("=" * 80)
    feats = build_hmm_features("2020", "2026")
    print(f"  HMM features: {feats.shape}")
    hmm_df = walk_forward_hmm(feats, n_states=n_states, refit_every=60, min_train=252)
    print(f"  Walk-forward HMM output: {hmm_df.shape}")
    print()
    # Map states to ORB edge using training period
    edge = state_to_edge_map(hmm_df, M_full, train_end="2022-12-31")
    good_state = max(edge, key=edge.get)
    bad_state = min(edge, key=edge.get)
    print(f"  Training-period (≤2022) edge per state: {edge}")
    print(f"  -> good state = {good_state} (mean PnL/day = {edge[good_state]*100:.3f}%)")
    print(f"  -> bad  state = {bad_state} (mean PnL/day = {edge[bad_state]*100:.3f}%)")
    print()

    # Conditional on state at start, what's the pass rate?
    out = simulate(M_full, mode="real_path", max_days=40)
    starts = out["start_indices"]
    status = out["status"]
    start_dates = M_full.index[starts]
    # State (filtered) at start day
    states_at_start = hmm_df["state"].reindex(start_dates).values
    # also probability of being in good state at start
    p_good_at_start = hmm_df[f"prob_state{good_state}"].reindex(start_dates).values

    print("--- Pass rate conditional on filtered HMM state at start (info ≤ J-1) ---")
    for s in sorted(set(int(x) for x in states_at_start if not np.isnan(x))):
        mask = (states_at_start == s)
        n = mask.sum()
        if n == 0:
            continue
        ps = float((status[mask] == 1).mean())
        bust_t = float((status[mask] == 3).mean())
        label = "good" if s == good_state else "bad"
        print(f"  state={s} ({label:>4}): n={n}, pass={ps*100:.1f}%, bust_total={bust_t*100:.1f}%")
    print()

    print("--- Pass rate conditional on P(good_state) >= 0.5 / 0.7 / 0.9 (FILTERED) ---")
    print(f"  {'threshold':>10} | {'n_selected':>10} | {'pass%':>6} | {'bust%':>6}")
    for thr in [0.0, 0.3, 0.5, 0.7, 0.9]:
        mask = p_good_at_start >= thr
        if mask.sum() == 0:
            continue
        ps = float((status[mask] == 1).mean())
        bust_t = float((status[mask] == 3).mean())
        print(f"  {thr:>10.2f} | {int(mask.sum()):>10d} | {ps*100:5.1f}% | {bust_t*100:5.1f}%")
    print()

    # L19 ABLATION: HMM-gate (top X% by P_good) vs threshold-gate (vr5 low tercile)
    # head-to-head, SAME number selected
    print("=" * 80)
    print("L19 ABLATION — HMM-gate vs Threshold-gate (same selection count)")
    print("=" * 80)
    # threshold gate: vr5 low tercile
    r_us = underlying_daily_log_returns("US100", "2020", "2026")
    r_ger = underlying_daily_log_returns("GER40", "2020", "2026")
    feat_us = rolling_features(r_us)
    feat_ger = rolling_features(r_ger)
    feat_avg = (feat_us.reindex(M_full.index) + feat_ger.reindex(M_full.index)) / 2
    vr5_series = feat_avg["vr5"].loc[start_dates]
    vr5_tercile = tag_terciles_expanding(vr5_series)
    threshold_mask = (vr5_tercile == 0).values  # low VR_5 = "favourable" per 5-A

    n_thr = threshold_mask.sum()
    # HMM-gate: top n_thr by P_good
    p_good_safe = np.where(np.isnan(p_good_at_start), -1, p_good_at_start)
    rank = np.argsort(-p_good_safe)  # descending
    hmm_mask = np.zeros(len(starts), dtype=bool)
    hmm_mask[rank[:n_thr]] = True

    print(f"  Both gates select n={n_thr} challenge starts")
    print()
    print(f"  {'gate':>10} | {'pass%':>6} | {'bust%':>6} | {'median TTP':>10}")
    for label, mask in [("Threshold", threshold_mask), ("HMM filt", hmm_mask)]:
        if mask.sum() == 0:
            continue
        sub = status[mask]
        p = float((sub == 1).mean())
        bt = float((sub == 3).mean())
        print(f"  {label:>10} | {p*100:5.1f}% | {bt*100:5.1f}% |   (TTP not tracked here)")
    # Overlap
    overlap = (threshold_mask & hmm_mask).sum()
    print(f"\n  Overlap between gates: {overlap}/{n_thr} = {overlap/n_thr*100:.0f}%")
    print()

    # HMM transition matrix on training data
    print("--- HMM transition matrix (training ≤2022) — episode persistence ---")
    from collections import Counter
    states_train = hmm_df.loc[:"2022-12-31", "state"].values
    transitions = Counter()
    for i in range(len(states_train) - 1):
        transitions[(states_train[i], states_train[i+1])] += 1
    total_per_state = {s: sum(c for (a,_), c in transitions.items() if a == s)
                       for s in set(int(x) for x in states_train)}
    for from_s in sorted(set(int(x) for x in states_train)):
        for to_s in sorted(set(int(x) for x in states_train)):
            c = transitions.get((from_s, to_s), 0)
            tot = total_per_state[from_s]
            p = c / tot if tot else 0
            print(f"  P(state={to_s} | prev={from_s}) = {p:.3f}  (n={c}/{tot})")
    print()
    # Expected dwell time in good state
    p_stay_good = transitions.get((good_state, good_state), 0) / max(total_per_state.get(good_state, 1), 1)
    if p_stay_good > 0 and p_stay_good < 1:
        exp_dwell = 1 / (1 - p_stay_good)
        # P(stay good for >= 14 days)
        p_dwell_14 = p_stay_good ** 14
        p_dwell_40 = p_stay_good ** 40
        print(f"  Expected dwell in good state = {exp_dwell:.1f} days")
        print(f"  P(stay good ≥14 consecutive days) = {p_dwell_14:.3f}")
        print(f"  P(stay good ≥40 consecutive days) = {p_dwell_40:.3f}")
    return hmm_df


if __name__ == "__main__":
    M_full = build_3sleeve_matrix(lo="2022", hi="2025")
    step_5C_hmm(M_full, n_states=2)
    print()
    print("=" * 80)
    print("Running n_states=3 for comparison...")
    print("=" * 80)
    step_5C_hmm(M_full, n_states=3)
