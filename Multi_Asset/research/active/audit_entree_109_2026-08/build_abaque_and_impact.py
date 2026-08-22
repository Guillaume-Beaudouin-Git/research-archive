"""
Chantier B/C -- convert the entry-ambiguity bias to bps, build the abaque (bias vs
stretch/ATR and day-range/ATR), and quantify pooled per-trade impact for each of the
8 exposed strategies (to compare against their already-known Gate-1 fill-artefact
verdict swing).
"""
import glob, os
import numpy as np, pandas as pd

STUDY_DIR = os.path.dirname(os.path.abspath(__file__))
FILES = {
    "S001_crabel_nr_orb": ("S001", 3841, 564),
    "S002_crabel_nr_setupexit": ("S002", 4366, 666),
    "S037_gsv": ("S037", 12548, 2116),
    "S055_narrow_range": ("S055", 4242, 684),
    "S056_nr7": ("S056", 7504, 1105),
    "S061_orb": ("S061", 13272, 2774),
    "S096_wide_range": ("S096", 4434, 1217),
}

impact_rows = []
all_diag = []
for name, (code, n_trades_total, n_both_real) in FILES.items():
    d = pd.read_csv(os.path.join(STUDY_DIR, f"diag_{name}.csv"))
    d["strategy"] = name
    d["bias_R"] = d["assumed_R"] - d["unbiased_R"]
    d["bias_bps"] = d["bias_R"] * d["risk0"] / d["price"] * 1e4
    all_diag.append(d)
    n_amb = len(d)  # diagnostic count (matches real engine for all but S002, see caveat)
    mean_bias_R = d["bias_R"].mean()
    se_bias_R = d["bias_R"].std(ddof=1) / np.sqrt(n_amb)
    t_stat = mean_bias_R / se_bias_R
    mean_bias_bps = d["bias_bps"].mean()
    # pooled-per-trade impact: only the ambiguous fraction carries the bias, rest = 0
    frac_both_real = n_both_real / n_trades_total
    pooled_bias_R = mean_bias_R * frac_both_real
    pooled_bias_bps = mean_bias_bps * frac_both_real
    impact_rows.append(dict(
        strategy=name, code=code, n_trades_total=n_trades_total, n_both_real=n_both_real,
        frac_both_real=frac_both_real, n_ambiguous_diagnosed=n_amb,
        mean_assumed_R=d["assumed_R"].mean(), mean_unbiased_R=d["unbiased_R"].mean(),
        mean_bias_R_per_ambiguous_trade=mean_bias_R, t_stat_ambiguous_subset=t_stat,
        mean_bias_bps_per_ambiguous_trade=mean_bias_bps,
        pooled_bias_R_per_trade_all=pooled_bias_R,
        pooled_bias_bps_per_trade_all=pooled_bias_bps,
        note=("S002 diagnostic uses an approximated exit tail (no Stretch-band exit) "
              "-> n_ambiguous_diagnosed(564) != real engine n_both(666); bias magnitude "
              "still representative (same setup/stretch construction as S001)."
              if name == "S002_crabel_nr_setupexit" else "")
    ))

impact = pd.DataFrame(impact_rows)
impact.to_csv(os.path.join(STUDY_DIR, "impact_by_strategy.csv"), index=False)
print(impact[["strategy","n_trades_total","frac_both_real","mean_bias_R_per_ambiguous_trade",
              "t_stat_ambiguous_subset","mean_bias_bps_per_ambiguous_trade",
              "pooled_bias_R_per_trade_all","pooled_bias_bps_per_trade_all"]].round(4).to_string())

# ---------------- Abaque: bias vs stretch/ATR x day_range/ATR --------------------
pooled = pd.concat(all_diag, ignore_index=True)
pooled.to_csv(os.path.join(STUDY_DIR, "pooled_ambiguous_trades_all_strategies.csv"), index=False)

stretch_bins = [0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50, np.inf]
range_bins   = [0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0, np.inf]
pooled["stretch_bin"] = pd.cut(pooled["stretch_over_atr"], stretch_bins)
pooled["range_bin"] = pd.cut(pooled["day_range_over_atr"], range_bins)

abaque = pooled.groupby(["stretch_bin", "range_bin"], observed=True).agg(
    n=("bias_R", "size"), mean_bias_R=("bias_R", "mean"), mean_bias_bps=("bias_bps", "mean"),
    mean_assumed_R=("assumed_R", "mean"), mean_unbiased_R=("unbiased_R", "mean"),
).reset_index()
abaque = abaque[abaque["n"] >= 5]
abaque.to_csv(os.path.join(STUDY_DIR, "abaque_biais_entree.csv"), index=False)
print("\n=== ABAQUE (stretch/ATR x day_range/ATR) ===")
print(abaque.round(4).to_string())

# Marginal by stretch/ATR alone (cleaner headline table)
marg_stretch = pooled.groupby("stretch_bin", observed=True).agg(
    n=("bias_R","size"), mean_bias_R=("bias_R","mean"), mean_bias_bps=("bias_bps","mean")).reset_index()
marg_stretch.to_csv(os.path.join(STUDY_DIR, "abaque_biais_entree_marginal_stretch.csv"), index=False)
print("\n=== marginal by stretch/ATR ===")
print(marg_stretch.round(4).to_string())

marg_range = pooled.groupby("range_bin", observed=True).agg(
    n=("bias_R","size"), mean_bias_R=("bias_R","mean"), mean_bias_bps=("bias_bps","mean")).reset_index()
marg_range.to_csv(os.path.join(STUDY_DIR, "abaque_biais_entree_marginal_range.csv"), index=False)
print("\n=== marginal by day_range/ATR ===")
print(marg_range.round(4).to_string())

print(f"\nPooled N ambiguous (all 7 strategies, diagnostic counts): {len(pooled)}")
print(f"Overall mean bias_R: {pooled['bias_R'].mean():+.4f}  mean bias_bps: {pooled['bias_bps'].mean():+.3f}  "
      f"t={pooled['bias_R'].mean()/(pooled['bias_R'].std(ddof=1)/np.sqrt(len(pooled))):.2f}")
