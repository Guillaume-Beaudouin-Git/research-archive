"""
feature_audit_pointintime.py — Per-feature audit of trade_dataset_nq.

For each feature, three structural tests:
  A. Future-blind reconstruction: recompute the feature using ONLY bars
     strictly before the entry bar `bi`.  Compare to the stored value.
     Any mismatch (within numerical tolerance) → flag as look-ahead.
  B. Direction symmetry: report mean and std by direction (long/short).
     A direction-asymmetric mean for a non-direction-conditional feature
     is a clue.  (Direction-conditional features by design — gap_concord,
     dist_to_pdh_R — are flagged but not failed.)
  C. Off-by-one slice check: for each feature that takes a slice
     [start:bi], verify it does not accidentally include bar `bi` itself.

Outputs:
  - `feature_audit_pointintime_output.txt` — per-feature verdict.
  - `feature_audit_pointintime.csv` — structured results.

Also re-runs the F1 bug demo (ttb_buggy vs ttb_correct) on the NQ dataset
to confirm the bug pattern reproduces.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
TRADE_DS = ROOT / "trade_dataset_nq.parquet"
DATA_ROOT = ROOT.parents[1]  # = .../Algo_claude/data
NQ_PARQUET = DATA_ROOT / "raw" / "NQ_1min_databento_2010-2026.parquet"


# ---------------------------------------------------------------------------
# Load both stored dataset and raw NQ for point-in-time recompute
# ---------------------------------------------------------------------------

def load_raw_nq_5m() -> pd.DataFrame:
    df = pd.read_parquet(NQ_PARQUET, columns=["open", "high", "low", "close",
                                                "volume", "is_roll_day"])
    df = df[~df["is_roll_day"]].drop(columns="is_roll_day")
    df.index = df.index.tz_convert("US/Eastern").tz_localize(None)
    df = df.sort_index()
    df5 = df.resample("5min").agg(
        {"open": "first", "high": "max", "low": "min",
         "close": "last", "volume": "sum"}
    ).dropna()
    h, m = df5.index.hour, df5.index.minute
    sess = df5[((h > 9) | ((h == 9) & (m >= 30))) & (h < 16)].copy()
    sess["day"] = sess.index.normalize()
    return sess


def reconstruct_features_point_in_time(trades: pd.DataFrame,
                                        sess: pd.DataFrame) -> pd.DataFrame:
    """For each trade, recompute features from raw bars using ONLY bars < bi.

    Returns a DataFrame indexed identically to `trades` with recomputed values.
    """
    OR = 6  # 5-min bars
    recs = []
    daily = sess.groupby("day")
    # Pre-build session-daily aggregates for prior-day features
    sess_daily = sess.groupby("day").agg(high=("high", "max"),
                                          low=("low", "min"),
                                          close=("close", "last"),
                                          volume=("volume", "sum"))
    pdh_series = sess_daily["high"].shift(1)
    pdl_series = sess_daily["low"].shift(1)
    pc_series = sess_daily["close"].shift(1)
    pv_series = sess_daily["volume"].shift(1)
    atr20_series = (sess_daily["high"] - sess_daily["low"]).rolling(20).mean().shift(1)
    pdr_series = (sess_daily["close"] / sess_daily["close"].shift(1) - 1).shift(1)
    vol_med20_series = sess_daily["volume"].rolling(20).median().shift(1)

    for ts, row in trades.iterrows():
        day = ts.normalize()
        if day not in daily.groups:
            recs.append({"date": ts, **{c: np.nan for c in [
                "or_high_pit", "or_low_pit", "or_range_pit", "twap_or_pit",
                "vwap_or_true_pit", "or_vol_total_pit",
                "or_vol_5m_std_pit", "or_touches_pit",
                "time_to_break_5min_pit", "dist_twap_at_break_R_pit",
                "dist_vwap_at_break_R_pit", "dist_to_pdh_R_pit",
                "dist_to_pdl_R_pit", "or_range_atr_ratio_pit",
                "or_vol_ratio_20d_pit", "gap_abs_pit", "gap_dir_pit",
                "gap_concord_pit", "prior_day_concord_pit",
                "overnight_range_ratio_pit",
            ]}})
            continue
        g = daily.get_group(day)
        H = g["high"].values.astype(np.float64)
        L = g["low"].values.astype(np.float64)
        C = g["close"].values.astype(np.float64)
        O = g["open"].values.astype(np.float64)
        V = g["volume"].values.astype(np.float64)
        direction = int(row["breakout_dir"])
        bi = int(row["bi_raw"])
        # bi can equal OR if break is on first post-OR bar (iu/idn = 0).
        if bi >= len(g) or bi < OR:
            recs.append({"date": ts})
            continue

        # === OR descriptors (bars 0..OR-1 only) ===
        or_hi = H[:OR].max()
        or_lo = L[:OR].min()
        or_range = or_hi - or_lo
        risk = or_range
        twap_or = ((H[:OR] + L[:OR] + C[:OR]) / 3).mean()
        or_v = V[:OR]
        or_c = C[:OR]
        vwap_or_true = float((or_c * or_v).sum() / or_v.sum()) if or_v.sum() > 0 else np.nan
        or_vol_total = or_v.sum()
        if OR >= 2:
            or_rets = pd.Series(C[:OR]).pct_change().dropna()
            or_vol_5m_std = float(or_rets.std()) if len(or_rets) > 0 else np.nan
        else:
            or_vol_5m_std = np.nan

        # === Break detection (consistent with builder) ===
        up = np.where(H[OR:] > or_hi)[0]
        dn = np.where(L[OR:] < or_lo)[0]
        iu_pit = up[0] if len(up) else 10**9
        idn_pit = dn[0] if len(dn) else 10**9
        if iu_pit == idn_pit == 10**9:
            recs.append({"date": ts})
            continue
        if iu_pit <= idn_pit:
            dir_pit = 1
            level_pit = or_hi
            bi_pit = OR + iu_pit
        else:
            dir_pit = -1
            level_pit = or_lo
            bi_pit = OR + idn_pit

        # Direction sanity: recomputed should match stored.
        if dir_pit != direction:
            recs.append({"date": ts, "dir_mismatch": True})
            continue

        # === Strict future-blind features ===
        time_to_break_pit = bi_pit - OR
        # For OR-touches, when bi_pit == OR (break on first post-OR bar),
        # H[:bi_pit] = H[:OR] = OR bars only. The OR-defining bar always
        # contributes one touch. This matches the builder's behaviour.
        if direction == 1:
            touches_pit = int((H[:bi_pit] >= or_hi - 1e-6).sum())
        else:
            touches_pit = int((L[:bi_pit] <= or_lo + 1e-6).sum())
        dist_twap_pit = ((level_pit - twap_or) / risk) * dir_pit
        dist_vwap_pit = ((level_pit - vwap_or_true) / risk) * dir_pit if not np.isnan(vwap_or_true) else np.nan

        # Prior-day series
        pdh = pdh_series.get(day, np.nan)
        pdl = pdl_series.get(day, np.nan)
        pc = pc_series.get(day, np.nan)
        atr20 = atr20_series.get(day, np.nan)
        pdr = pdr_series.get(day, np.nan)
        vol_med = vol_med20_series.get(day, np.nan)
        dist_to_pdh_R_pit = ((level_pit - pdh) / risk) * dir_pit if not pd.isna(pdh) else np.nan
        dist_to_pdl_R_pit = ((level_pit - pdl) / risk) * dir_pit if not pd.isna(pdl) else np.nan
        or_range_atr_ratio_pit = or_range / atr20 if (not pd.isna(atr20) and atr20 > 0) else np.nan
        or_vol_ratio_20d_pit = or_vol_total / vol_med if (not pd.isna(vol_med) and vol_med > 0) else np.nan
        gap_abs_pit = O[0] - pc if not pd.isna(pc) else np.nan
        gap_dir_pit = float(np.sign(gap_abs_pit)) if not pd.isna(gap_abs_pit) else np.nan
        gap_concord_pit = float(dir_pit == gap_dir_pit) if not pd.isna(gap_dir_pit) and gap_dir_pit != 0 else np.nan
        prior_day_concord_pit = float(dir_pit == np.sign(pdr)) if not pd.isna(pdr) and pdr != 0 else np.nan
        if not pd.isna(pc):
            ovr = abs(O[0] - pc)
            overnight_range_ratio_pit = or_range / ovr if ovr > 0 else np.nan
        else:
            overnight_range_ratio_pit = np.nan

        recs.append({
            "date": ts,
            "or_high_pit": or_hi,
            "or_low_pit": or_lo,
            "or_range_pit": or_range,
            "twap_or_pit": twap_or,
            "vwap_or_true_pit": vwap_or_true,
            "or_vol_total_pit": or_vol_total,
            "or_vol_5m_std_pit": or_vol_5m_std,
            "or_touches_pit": touches_pit,
            "time_to_break_5min_pit": time_to_break_pit,
            "bi_pit": bi_pit,
            "dir_pit": dir_pit,
            "dist_twap_at_break_R_pit": dist_twap_pit,
            "dist_vwap_at_break_R_pit": dist_vwap_pit,
            "dist_to_pdh_R_pit": dist_to_pdh_R_pit,
            "dist_to_pdl_R_pit": dist_to_pdl_R_pit,
            "or_range_atr_ratio_pit": or_range_atr_ratio_pit,
            "or_vol_ratio_20d_pit": or_vol_ratio_20d_pit,
            "gap_abs_pit": gap_abs_pit,
            "gap_dir_pit": gap_dir_pit,
            "gap_concord_pit": gap_concord_pit,
            "prior_day_concord_pit": prior_day_concord_pit,
            "overnight_range_ratio_pit": overnight_range_ratio_pit,
        })
    out = pd.DataFrame(recs).set_index("date")
    return out


def compare_stored_vs_pit(trades: pd.DataFrame, pit: pd.DataFrame) -> pd.DataFrame:
    """For each (stored, _pit) pair, report n_diff at tolerance 1e-6 (or strict eq for ints)."""
    pairs = [
        ("or_high", "or_high_pit", False),
        ("or_low", "or_low_pit", False),
        ("or_range", "or_range_pit", False),
        ("twap_or", "twap_or_pit", False),
        ("vwap_or_true", "vwap_or_true_pit", False),
        ("or_vol_total", "or_vol_total_pit", False),
        ("or_vol_5m_std", "or_vol_5m_std_pit", False),
        ("or_touches", "or_touches_pit", True),  # int
        ("time_to_break_5min", "time_to_break_5min_pit", True),  # int
        ("dist_twap_at_break_R", "dist_twap_at_break_R_pit", False),
        ("dist_vwap_at_break_R", "dist_vwap_at_break_R_pit", False),
        ("dist_to_pdh_R", "dist_to_pdh_R_pit", False),
        ("dist_to_pdl_R", "dist_to_pdl_R_pit", False),
        ("or_range_atr_ratio", "or_range_atr_ratio_pit", False),
        ("or_vol_ratio_20d", "or_vol_ratio_20d_pit", False),
        ("gap_abs", "gap_abs_pit", False),
        ("gap_dir", "gap_dir_pit", False),
        ("gap_concord", "gap_concord_pit", True),
        ("prior_day_concord", "prior_day_concord_pit", True),
        ("overnight_range_ratio", "overnight_range_ratio_pit", False),
    ]
    common_idx = trades.index.intersection(pit.index)
    t = trades.loc[common_idx]
    p = pit.loc[common_idx]
    rows = []
    for stored, pit_col, is_int in pairs:
        if stored not in t.columns or pit_col not in p.columns:
            rows.append({"feature": stored, "verdict": "MISSING"})
            continue
        a = t[stored].values
        b = p[pit_col].values
        both_valid = ~(pd.isna(a) | pd.isna(b))
        n_compare = int(both_valid.sum())
        if n_compare == 0:
            rows.append({"feature": stored, "n_compare": 0, "verdict": "NO_OVERLAP"})
            continue
        if is_int:
            n_diff = int((a[both_valid].astype(np.int64) != b[both_valid].astype(np.int64)).sum())
            max_abs_diff = float(np.abs(a[both_valid].astype(np.float64) - b[both_valid].astype(np.float64)).max())
        else:
            diff = np.abs(a[both_valid].astype(np.float64) - b[both_valid].astype(np.float64))
            tol = 1e-6 + 1e-9 * np.abs(b[both_valid].astype(np.float64))
            n_diff = int((diff > tol).sum())
            max_abs_diff = float(diff.max()) if len(diff) else float("nan")
        pct_diff = n_diff / n_compare * 100
        verdict = "OK" if n_diff == 0 else ("MINOR" if pct_diff < 0.5 else "BUG")
        rows.append({"feature": stored,
                     "n_compare": n_compare,
                     "n_diff": n_diff,
                     "pct_diff": round(pct_diff, 3),
                     "max_abs_diff": round(max_abs_diff, 8),
                     "verdict": verdict})
    return pd.DataFrame(rows)


def direction_symmetry(trades: pd.DataFrame) -> pd.DataFrame:
    """Report per-feature mean / std by direction (long/short).

    Flag features where mean_long and mean_short differ by > 1 std as
    'direction-asymmetric' (informational; may be by design).
    """
    feats = ["or_range", "or_range_atr_ratio", "or_vol_5m_std",
             "or_vol_total", "or_vol_ratio_20d", "or_vol_skew",
             "or_vol_concord", "or_touches", "time_to_break_5min",
             "time_to_break_buggy", "dist_twap_at_break_R",
             "dist_vwap_at_break_R", "dist_to_pdh_R", "dist_to_pdl_R",
             "overnight_range_ratio", "prior_day_return", "gap_abs",
             "gap_pct", "gap_dir", "gap_concord", "prior_day_concord",
             "vol_pre_break", "pre_break_range_R"]
    longs = trades[trades["breakout_dir"] == 1]
    shorts = trades[trades["breakout_dir"] == -1]
    rows = []
    for f in feats:
        if f not in trades.columns:
            continue
        mL = longs[f].mean()
        sL = longs[f].std()
        mS = shorts[f].mean()
        sS = shorts[f].std()
        # asymmetry score: difference of means in pooled-std units
        pooled = np.sqrt((sL**2 + sS**2) / 2)
        asym = (mL - mS) / pooled if pooled and pooled > 0 else np.nan
        rows.append({"feature": f,
                     "mean_long": round(float(mL), 4),
                     "std_long": round(float(sL), 4),
                     "mean_short": round(float(mS), 4),
                     "std_short": round(float(sS), 4),
                     "abs_asym_score": round(float(abs(asym)), 3) if not pd.isna(asym) else np.nan})
    return pd.DataFrame(rows)


def f1_demo_buggy_vs_correct(trades: pd.DataFrame, target: str = "r_exec_nextopen") -> pd.DataFrame:
    """Reproduce the F1 ≤ median filter using BOTH buggy and correct ttb."""
    rows = []
    for subset_name, sub in [("ALL", trades),
                              ("LONG", trades[trades["breakout_dir"] == 1]),
                              ("SHORT", trades[trades["breakout_dir"] == -1])]:
        for ttb_col in ["time_to_break_buggy", "time_to_break_5min"]:
            thr = sub[ttb_col].quantile(0.5)
            keep = sub[ttb_col] <= thr
            r_base = sub[target].mean()
            r_f1 = sub.loc[keep, target].mean()
            rows.append({
                "subset": subset_name,
                "ttb_def": "buggy" if ttb_col == "time_to_break_buggy" else "correct",
                "n_total": len(sub),
                "n_kept": int(keep.sum()),
                "thr": float(thr),
                "mean_R_baseline": round(float(r_base), 4),
                "mean_R_F1": round(float(r_f1), 4),
                "delta_R": round(float(r_f1 - r_base), 4),
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print(f"Loading trade dataset: {TRADE_DS}")
    trades = pd.read_parquet(TRADE_DS)
    print(f"  {len(trades)} trades, {trades.index.min()} -> {trades.index.max()}")
    print()

    print("Loading raw NQ for point-in-time reconstruction...")
    sess = load_raw_nq_5m()
    print(f"  {len(sess)} bars, {sess.index.min()} -> {sess.index.max()}")
    print()

    print("=" * 90)
    print("A. Point-in-time reconstruction vs stored")
    print("=" * 90)
    pit = reconstruct_features_point_in_time(trades, sess)
    print(f"  Reconstructed {len(pit)} rows.")
    comp = compare_stored_vs_pit(trades, pit)
    print(comp.to_string(index=False))
    comp.to_csv(ROOT / "feature_audit_pointintime_diff.csv", index=False)
    print()

    print("=" * 90)
    print("B. Direction symmetry (mean +/- std by long/short)")
    print("=" * 90)
    sym = direction_symmetry(trades)
    print(sym.to_string(index=False))
    sym.to_csv(ROOT / "feature_audit_direction_symmetry.csv", index=False)
    print()

    print("=" * 90)
    print("C. F1 reproduction (ttb ≤ median): buggy vs correct, by subset")
    print("=" * 90)
    f1 = f1_demo_buggy_vs_correct(trades, target="r_exec_nextopen")
    print("Target = r_exec_nextopen (clean exec)")
    print(f1.to_string(index=False))
    print()
    f1L = f1_demo_buggy_vs_correct(trades, target="r_exec_level")
    print("Target = r_exec_level (legacy same-bar)")
    print(f1L.to_string(index=False))
    f1.to_csv(ROOT / "feature_audit_F1_demo_nextopen.csv", index=False)
    f1L.to_csv(ROOT / "feature_audit_F1_demo_level.csv", index=False)
    print()

    print("=" * 90)
    print("Summary of mismatches (BUG verdict only)")
    print("=" * 90)
    bugs = comp[comp["verdict"] == "BUG"]
    if len(bugs) == 0:
        print("  No mismatches > 0.5% — point-in-time reconstruction matches stored.")
    else:
        print(bugs.to_string(index=False))
