"""
phase2_filter_hypotheses.py — Pre-registered 2-condition filters with full
honesty checks.

Hypotheses (pre-registered before observing in-sample results — built from
Phase 1 univariate scan + theory, not from in-sample optimization):

  H0  Long-only baseline check
       Filter: breakout_dir == 1
       Theory: dropping shorts may already help (positive drift bias).

  H1  Trend-aligned long momentum
       Filter: dir==1  AND  gap_pct > 0  AND  dist_to_pdh_R > 0
       Theory: classic momentum confluence — long ORB break with positive
       gap and above prior-day high.  Two conditions OR'd with the long
       direction restriction (the direction itself is "free" since it's
       the trade's structural attribute, not a derived feature).

  H2  Decisive opening range
       Filter: or_vol_5m_std < median(s)  AND  pre_break_range_R < median(s)
       Theory: low intra-OR realised vol + short pre-break consolidation
       = high-conviction structural break, less noise.

  H3  Volume-confirmed momentum
       Filter: or_vol_total > median  AND  dist_twap_at_break_R > median
       Theory: above-typical volume during OR + break far from TWAP
       (signed) = institutional / directional conviction.

  H4  Symmetric trend-aligned (long + short)
       Filter: gap_concord == 1  AND  dist_to_pdh_R*dir < median  [long]
           OR  gap_concord == 1  AND  dist_to_pdl_R*dir < median  [short]
       Theory: dir matches gap AND break level is on the "favourable"
       side of prior-day extreme.  Direction-symmetric version of H1.

For each hypothesis:
  - Baseline mean_R + std_R + Sharpe (sqrt(252))
  - Filter: kept n + filtered mean_R + delta + skew + top-decile R
  - L19 ablation: drop one condition at a time
  - Regime decomposition (5 buckets 2010-12, 2013-15, 2016-18, 2019-21, 2022-26)
  - Block-bootstrap CI on delta_R (block=20 days)
  - Honest top-decile preservation: % top-decile R captured in filter set
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats as scstats

ROOT = Path(__file__).resolve().parent
DS = ROOT / "trade_dataset_clean.parquet"
TARGET = "r_exec_nextopen"

REGIMES = [
    ("2010-2012", "2010", "2012"),
    ("2013-2015", "2013", "2015"),
    ("2016-2018", "2016", "2018"),
    ("2019-2021", "2019", "2021"),
    ("2022-2026", "2022", "2026"),
]


def summary(name: str, sub: pd.DataFrame, target: str = TARGET) -> dict:
    """Per-set diagnostics: mean R, std, daily Sharpe, skew, top-decile mean R."""
    y = sub[target].dropna().values
    n = len(y)
    if n == 0:
        return {"set": name, "n": 0}
    mean_R = float(np.mean(y))
    std_R = float(np.std(y, ddof=1))
    sharpe_daily = mean_R / std_R if std_R > 0 else np.nan
    sharpe_ann = sharpe_daily * np.sqrt(252) if not np.isnan(sharpe_daily) else np.nan
    skew = float(scstats.skew(y))
    kurt = float(scstats.kurtosis(y))
    # Top-decile R: 90th percentile and mean above
    top_dec_thresh = np.quantile(y, 0.90)
    top_dec_mean = float(np.mean(y[y >= top_dec_thresh]))
    hit_rate = float((y > 0).mean()) * 100
    return {
        "set": name,
        "n": n,
        "mean_R": round(mean_R, 4),
        "std_R": round(std_R, 4),
        "sharpe_daily_ann": round(sharpe_ann, 3),
        "skew": round(skew, 3),
        "kurt": round(kurt, 3),
        "hit_rate_pct": round(hit_rate, 2),
        "top_dec_thresh": round(float(top_dec_thresh), 4),
        "top_dec_meanR": round(top_dec_mean, 4),
    }


def topdec_capture(full: pd.DataFrame, filt: pd.DataFrame, target: str = TARGET) -> float:
    """% of top-decile R trades (in full sample) that survive the filter."""
    y_full = full[target].dropna().values
    if len(y_full) == 0:
        return float("nan")
    thr = np.quantile(y_full, 0.90)
    top_in_full = full[full[target] >= thr]
    if len(top_in_full) == 0:
        return float("nan")
    top_in_filt = filt[filt[target] >= thr]
    return float(len(top_in_filt) / len(top_in_full) * 100)


def regime_table(name: str, full: pd.DataFrame, filt: pd.DataFrame,
                  target: str = TARGET) -> pd.DataFrame:
    rows = []
    for reg_name, lo, hi in REGIMES:
        f_full = full.loc[lo:hi]
        f_filt = filt.loc[lo:hi]
        y_full = f_full[target].dropna().values
        y_filt = f_filt[target].dropna().values
        if len(y_full) == 0:
            rows.append({"hypothesis": name, "regime": reg_name,
                          "n_full": 0, "n_filt": 0})
            continue
        mean_full = float(np.mean(y_full))
        mean_filt = float(np.mean(y_filt)) if len(y_filt) else np.nan
        delta = (mean_filt - mean_full) if not np.isnan(mean_filt) else np.nan
        # Top-decile capture in this regime
        if len(y_full) >= 10:
            thr = np.quantile(y_full, 0.90)
            tot_top = (y_full >= thr).sum()
            kept_top = (y_filt >= thr).sum() if len(y_filt) else 0
            topdec = kept_top / tot_top * 100 if tot_top > 0 else float("nan")
        else:
            topdec = float("nan")
        rows.append({
            "hypothesis": name,
            "regime": reg_name,
            "n_full": int(len(y_full)),
            "n_filt": int(len(y_filt)),
            "kept_pct": round(len(y_filt) / len(y_full) * 100, 1) if len(y_full) > 0 else float("nan"),
            "mean_R_full": round(mean_full, 4),
            "mean_R_filt": round(mean_filt, 4) if not np.isnan(mean_filt) else np.nan,
            "delta_R": round(delta, 4) if not np.isnan(delta) else np.nan,
            "topdec_capture_pct": round(topdec, 1) if not np.isnan(topdec) else np.nan,
        })
    return pd.DataFrame(rows)


def block_bootstrap_delta_R(full: pd.DataFrame, filt: pd.DataFrame,
                              target: str = TARGET, n_boot: int = 1000,
                              block_days: int = 20, seed: int = 0) -> dict:
    """Block bootstrap of (mean_R_filt - mean_R_full), VECTORIZED.

    Strategy: NQ has ~1 trade/day, so we can treat each row as a "block element"
    if block_days ≈ block_trades.  For each bootstrap iteration, pick
    n_blocks * block_days indices (circular) and compute means on numpy arrays.
    """
    rng = np.random.default_rng(seed)
    full_sorted = full.sort_index()
    y_full = full_sorted[target].values
    n = len(y_full)
    if n < block_days * 2:
        return {"ci_lo": np.nan, "ci_hi": np.nan, "p_boot": np.nan}
    # Mark which rows belong to filter (boolean)
    in_filt = full_sorted.index.isin(filt.index)
    n_blocks = int(np.ceil(n / block_days))
    obs_delta = float(filt[target].mean() - full[target].mean())
    # Block-start index for each row in flattened bootstrap sample
    boots = np.empty(n_boot, dtype=np.float64)
    for b in range(n_boot):
        starts = rng.integers(0, n, size=n_blocks)
        # Build index list: for each start, take block_days consecutive
        offsets = np.arange(block_days)
        idx = ((starts[:, None] + offsets[None, :]) % n).ravel()
        y_b = y_full[idx]
        m_b = in_filt[idx]
        full_mean = y_b.mean()
        filt_mean = y_b[m_b].mean() if m_b.any() else np.nan
        boots[b] = filt_mean - full_mean if not np.isnan(filt_mean) else np.nan
    boots = boots[~np.isnan(boots)]
    if len(boots) < 100:
        return {"ci_lo": np.nan, "ci_hi": np.nan, "p_boot": np.nan, "obs_delta": obs_delta}
    ci_lo, ci_hi = np.percentile(boots, [2.5, 97.5])
    p = float(np.mean(np.abs(boots - boots.mean()) >= abs(obs_delta - boots.mean())))
    return {"ci_lo": round(float(ci_lo), 4),
            "ci_hi": round(float(ci_hi), 4),
            "p_boot": round(p, 3),
            "obs_delta": round(obs_delta, 4)}


# ---------------------------------------------------------------------------
# Hypothesis filters
# ---------------------------------------------------------------------------

def filt_H0(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["breakout_dir"] == 1]


def filt_H1(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["breakout_dir"] == 1) &
              (df["gap_pct"] > 0) &
              (df["dist_to_pdh_R"] > 0)]


def filt_H1_drop_gap(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["breakout_dir"] == 1) & (df["dist_to_pdh_R"] > 0)]


def filt_H1_drop_pdh(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df["breakout_dir"] == 1) & (df["gap_pct"] > 0)]


def filt_H2(df: pd.DataFrame) -> pd.DataFrame:
    med_v = df["or_vol_5m_std"].median()
    med_p = df["pre_break_range_R"].median()
    return df[(df["or_vol_5m_std"] < med_v) &
              (df["pre_break_range_R"] < med_p)]


def filt_H2_drop_vol(df):
    med_p = df["pre_break_range_R"].median()
    return df[df["pre_break_range_R"] < med_p]


def filt_H2_drop_range(df):
    med_v = df["or_vol_5m_std"].median()
    return df[df["or_vol_5m_std"] < med_v]


def filt_H3(df: pd.DataFrame) -> pd.DataFrame:
    med_vol = df["or_vol_total"].median()
    med_dist = df["dist_twap_at_break_R"].median()
    return df[(df["or_vol_total"] > med_vol) &
              (df["dist_twap_at_break_R"] > med_dist)]


def filt_H3_drop_vol(df):
    med_dist = df["dist_twap_at_break_R"].median()
    return df[df["dist_twap_at_break_R"] > med_dist]


def filt_H3_drop_dist(df):
    med_vol = df["or_vol_total"].median()
    return df[df["or_vol_total"] > med_vol]


def filt_H4(df: pd.DataFrame) -> pd.DataFrame:
    # Symmetric trend-aligned: gap_concord == 1 AND break level on
    # "favourable" side relative to prior day extreme.
    # For long: dist_to_pdh_R > 0  (above PDH)
    # For short: dist_to_pdl_R > 0  (formula already direction-aware → "above PDL"
    #    in long-projection, which for shorts means break level (or_lo) BELOW PDL)
    long_m = (df["breakout_dir"] == 1) & (df["gap_concord"] == 1) & (df["dist_to_pdh_R"] > 0)
    short_m = (df["breakout_dir"] == -1) & (df["gap_concord"] == 1) & (df["dist_to_pdl_R"] > 0)
    return df[long_m | short_m]


HYPS = [
    ("H0_long_only", filt_H0,
        "Drop short trades only."),
    ("H1_long_momentum", filt_H1,
        "LONG AND gap_pct>0 AND dist_to_pdh_R>0 — long break with positive gap above PDH."),
    ("H1_ablate_no_gap", filt_H1_drop_gap,
        "L19: drop gap_pct condition."),
    ("H1_ablate_no_pdh", filt_H1_drop_pdh,
        "L19: drop dist_to_pdh_R condition."),
    ("H2_decisive_OR", filt_H2,
        "or_vol_5m_std<med AND pre_break_range_R<med — decisive OR + decisive break."),
    ("H2_ablate_no_vol", filt_H2_drop_vol,
        "L19: drop or_vol_5m_std condition."),
    ("H2_ablate_no_range", filt_H2_drop_range,
        "L19: drop pre_break_range_R condition."),
    ("H3_vol_directional", filt_H3,
        "or_vol_total>med AND dist_twap_at_break_R>med — high vol + far from TWAP."),
    ("H3_ablate_no_vol", filt_H3_drop_vol,
        "L19: drop or_vol_total condition."),
    ("H3_ablate_no_dist", filt_H3_drop_dist,
        "L19: drop dist_twap_at_break_R condition."),
    ("H4_sym_trend_aligned", filt_H4,
        "(LONG with gap_concord & dist_to_pdh_R>0) OR (SHORT with gap_concord & dist_to_pdl_R>0)."),
]


if __name__ == "__main__":
    print(f"Loading clean dataset: {DS}")
    df = pd.read_parquet(DS).dropna(subset=[TARGET])
    print(f"  {len(df)} trades, target = {TARGET}")
    print()

    base_summary = summary("BASELINE", df)
    print("BASELINE diagnostics:")
    print("  " + ", ".join(f"{k}={v}" for k, v in base_summary.items()))
    print()

    print("=" * 110)
    print("HYPOTHESES — summary table")
    print("=" * 110)
    rows = []
    boot_results = {}
    regime_results = {}
    for name, fn, doc in HYPS:
        sub = fn(df)
        s = summary(name, sub)
        s["kept_pct"] = round(len(sub) / len(df) * 100, 1)
        s["delta_meanR"] = round(s["mean_R"] - base_summary["mean_R"], 4) if "mean_R" in s else float("nan")
        s["topdec_capt_pct"] = round(topdec_capture(df, sub), 1)
        # Block bootstrap
        bs = block_bootstrap_delta_R(df, sub, n_boot=500)
        s.update({"boot_ci_lo": bs["ci_lo"], "boot_ci_hi": bs["ci_hi"],
                   "boot_p": bs.get("p_boot", float("nan"))})
        rows.append(s)
        boot_results[name] = bs
        regime_results[name] = regime_table(name, df, sub)
    out = pd.DataFrame(rows)
    cols_order = ["set", "n", "kept_pct", "mean_R", "delta_meanR", "std_R",
                   "sharpe_daily_ann", "skew", "kurt", "hit_rate_pct",
                   "top_dec_meanR", "topdec_capt_pct",
                   "boot_ci_lo", "boot_ci_hi", "boot_p"]
    cols_order = [c for c in cols_order if c in out.columns]
    print(out[cols_order].to_string(index=False))
    out.to_csv(ROOT / "phase2_hypotheses_summary.csv", index=False)
    print()

    print("=" * 110)
    print("HYPOTHESES — descriptions")
    print("=" * 110)
    for name, _, doc in HYPS:
        print(f"  {name:30s}  {doc}")
    print()

    print("=" * 110)
    print("REGIME DECOMPOSITION — main hypotheses + ablations")
    print("=" * 110)
    rd_all = pd.concat(list(regime_results.values()), ignore_index=True)
    print(rd_all.to_string(index=False))
    rd_all.to_csv(ROOT / "phase2_hypotheses_regime.csv", index=False)
    print()

    print("=" * 110)
    print("L19 ABLATION ANALYSIS — does each condition add value?")
    print("=" * 110)
    for base in ["H1_long_momentum", "H2_decisive_OR", "H3_vol_directional"]:
        h_row = next(r for r in rows if r["set"] == base)
        print(f"\n{base}: n={h_row['n']}, ΔR={h_row['delta_meanR']}")
        for ablate in [r for r in rows if r["set"].startswith(base.split('_')[0] + "_ablate")]:
            print(f"  {ablate['set']:35s}: n={ablate['n']}, ΔR={ablate['delta_meanR']}, "
                   f"topdec_capt={ablate['topdec_capt_pct']}%")
