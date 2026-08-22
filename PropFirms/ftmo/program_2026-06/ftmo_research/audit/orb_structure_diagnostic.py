"""ORB V2+E7 @ 0.4 bps RT — Structure diagnostic (Angles A & B).

ANGLE A: anatomy of right tail (top 1% trades = 40 trades, 93% of P&L).
  - Compare distribution of observable-ex-ante variables top1% vs rest.
  - KS test + Welch t-stat for each variable.
  - Verdict: are jackpots ex-ante targetable?

ANGLE B: bust cluster mechanism.
  - Autocorrelation of R (lag 1..10) + Ljung-Box test.
  - Run-length distribution (observed vs iid expectation).
  - DECISIVE TEST: for the 40 jackpots, how many arrive within 1-3 trades AFTER a ≥2-loss cluster?
    If many → anti-cluster overlay would destroy the edge.

NO MINING. NO FILTER. Description only. N=40 → flag fragility throughout.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox

LEDGER = "<HOME>/Desktop/Algo_claude/data/ftmo_research/audit/nq_v2_trades.parquet"
DAILY_RTH = "<HOME>/Desktop/Algo_claude/data/overnight_research/nq_rth_daily.parquet"
VIX_PATH = "<HOME>/Desktop/Algo_claude/data/panels/vix.csv"

E7_LIFT_R = 0.015
COST_BPS = 0.4
TOP_PCT = 0.01

# ----- Load & build features -----
df = pd.read_parquet(LEDGER).reset_index()
r_2 = df["r_2 bps RT (median)"].astype(float).values
r_1 = df["r_1 bps RT (aggressive)"].astype(float).values
cost_unit = r_1 - r_2
df["r"] = r_2 + (2.0 - COST_BPS) * cost_unit + E7_LIFT_R
df["date_d"] = pd.to_datetime(df["date"]).dt.normalize()
df["year"] = pd.to_datetime(df["date"]).dt.year
df["weekday"] = pd.to_datetime(df["date"]).dt.weekday
df["or_range_bps"] = df["or_range"] / df["level"] * 1e4

# Merge daily gap + VIX
try:
    daily = pd.read_parquet(DAILY_RTH).reset_index()
    daily.columns = ["date", "o", "c", "pc", "ov_bps", "in_bps", "wd", "yr"]
    daily["date"] = pd.to_datetime(daily["date"]).dt.normalize()
    df = df.merge(daily[["date", "ov_bps"]].rename(columns={"ov_bps": "gap_overnight_bps", "date": "date_dd"}),
                  left_on="date_d", right_on="date_dd", how="left").drop(columns=["date_dd"])
except Exception as e:
    df["gap_overnight_bps"] = np.nan

try:
    vix = pd.read_csv(VIX_PATH)
    vix.columns = ["date", "vix", "vvix"]
    vix["date"] = pd.to_datetime(vix["date"]).dt.normalize()
    vix["vix_prev"] = vix["vix"].shift(1)
    df = df.merge(vix[["date", "vix_prev"]].rename(columns={"date": "date_v"}),
                  left_on="date_d", right_on="date_v", how="left").drop(columns=["date_v"])
except Exception as e:
    df["vix_prev"] = np.nan

print("=" * 80)
print(f"ORB V2+E7 @ {COST_BPS} bps — n_trades={len(df)}  mean_R={df.r.mean():+.4f}  "
      f"std={df.r.std():.3f}  hit={(df.r>0).mean():.2%}")
print("=" * 80)

# Identify top 1% (jackpots) and rest
N = len(df)
n_top = int(N * TOP_PCT)
threshold = df["r"].sort_values(ascending=False).iloc[n_top - 1]
df["is_top1pct"] = df["r"] >= threshold
top = df[df.is_top1pct]
rest = df[~df.is_top1pct]
print(f"\nTop 1%: n={len(top)}  threshold R≥{threshold:+.3f}  "
      f"contrib_R={top.r.sum():+.1f}  ({100*top.r.sum()/df.r.sum():.0f}% of total P&L)")
print(f"Rest:    n={len(rest)}  contrib_R={rest.r.sum():+.1f}  mean_R={rest.r.mean():+.4f}")

# =====================================================================
# ANGLE A — ex-ante signature of jackpots
# =====================================================================
print("\n\n" + "█" * 80)
print("ANGLE A — anatomy of TOP 1% (40 jackpots) vs rest (3973)")
print("█" * 80)


def compare_dist(var_name, x_top, x_rest, is_categorical=False):
    """Returns: top_summary, rest_summary, KS stat, KS p, Welch t, Welch p."""
    x_top = np.asarray(x_top, dtype=float)
    x_rest = np.asarray(x_rest, dtype=float)
    x_top = x_top[~np.isnan(x_top)]
    x_rest = x_rest[~np.isnan(x_rest)]
    if len(x_top) < 5 or len(x_rest) < 30:
        return None
    if not is_categorical:
        ks_stat, ks_p = stats.ks_2samp(x_top, x_rest)
        t_stat, t_p = stats.ttest_ind(x_top, x_rest, equal_var=False)
    else:
        ks_stat = ks_p = np.nan
        t_stat = t_p = np.nan
    return {
        "var": var_name,
        "n_top": len(x_top), "n_rest": len(x_rest),
        "top_mean": x_top.mean(), "rest_mean": x_rest.mean(),
        "top_med": np.median(x_top), "rest_med": np.median(x_rest),
        "top_std": x_top.std(), "rest_std": x_rest.std(),
        "ks_stat": ks_stat, "ks_p": ks_p,
        "welch_t": t_stat, "welch_p": t_p,
    }


variables = [
    ("weekday (0=Mon..4=Fri)", "weekday", False),
    ("bi (mins after OR close)", "bi", False),
    ("ttb_5min", "ttb_5min", False),
    ("or_range_bps", "or_range_bps", False),
    ("or_range_pts", "or_range", False),
    ("gap_overnight_bps", "gap_overnight_bps", False),
    ("VIX_prev", "vix_prev", False),
    ("direction (1=long,-1=short)", "direction", False),
    ("year", "year", False),
]

print(f"\n{'Variable':32s}{'top_mean':>11s}{'rest_mean':>11s}{'Δ':>8s}{'KS_stat':>10s}{'KS_p':>9s}{'Welch_t':>10s}{'Welch_p':>10s}{'flag':>12s}")
results_A = []
for label, col, cat in variables:
    if col not in df.columns:
        continue
    res = compare_dist(label, top[col], rest[col], is_categorical=cat)
    if res is None:
        continue
    flag = "**SIGN**" if (res["ks_p"] < 0.01 or res["welch_p"] < 0.01) else (
        "weak" if (res["ks_p"] < 0.05 or res["welch_p"] < 0.05) else "")
    delta = res["top_mean"] - res["rest_mean"]
    print(f"{label:32s}{res['top_mean']:>+11.3f}{res['rest_mean']:>+11.3f}"
          f"{delta:>+8.3f}{res['ks_stat']:>10.3f}{res['ks_p']:>9.3f}"
          f"{res['welch_t']:>+10.2f}{res['welch_p']:>10.4f}{flag:>12s}")
    results_A.append(res | {"flag": flag, "delta_mean": delta})

# Year breakdown of top 1%
print("\n\nYear breakdown of top 1% (40 trades):")
yr_top = top["year"].value_counts().sort_index()
yr_all = df["year"].value_counts().sort_index()
yr_share = (yr_top / yr_all * 100).fillna(0).round(2)
print(f"{'Year':>6s}{'n_top1%':>10s}{'n_total':>10s}{'share_top1%':>13s}{'expected_iid(%)':>17s}")
for yr in sorted(yr_all.index):
    obs_share = yr_share.get(yr, 0)
    exp_share = 100 * yr_all[yr] / N
    print(f"{yr:>6d}{yr_top.get(yr,0):>10d}{yr_all[yr]:>10d}{obs_share:>12.2f}%{exp_share:>16.2f}%")
print(f"(expected_iid = if jackpots distributed uniformly, share = n_year / n_total)")

# Weekday breakdown of top 1%
print("\nWeekday breakdown of top 1%:")
wd_top = top["weekday"].value_counts().sort_index()
wd_all = df["weekday"].value_counts().sort_index()
print(f"{'wd':>4s}{'name':>5s}{'n_top':>7s}{'n_all':>8s}{'share_top(%)':>14s}{'exp_iid(%)':>13s}")
for wd in range(5):
    print(f"{wd:>4d}{['Mon','Tue','Wed','Thu','Fri'][wd]:>5s}"
          f"{wd_top.get(wd,0):>7d}{wd_all[wd]:>8d}"
          f"{100*wd_top.get(wd,0)/wd_all[wd]:>13.2f}%{100*wd_all[wd]/N:>12.2f}%")

# Direction breakdown
dir_top = top["direction"].value_counts().sort_index()
dir_all = df["direction"].value_counts().sort_index()
print("\nDirection breakdown of top 1%:")
for d in [-1, 1]:
    print(f"  dir={d:+d}: top={dir_top.get(d,0):>3d}/{dir_all[d]:>4d} = {100*dir_top.get(d,0)/dir_all[d]:.2f}%  "
          f"(iid baseline {TOP_PCT*100:.0f}%)")

# OR range quintiles
print("\nOR range bps quintiles:")
df["or_q"] = pd.qcut(df["or_range_bps"], q=5, labels=False)
for q in range(5):
    sub = df[df.or_q == q]
    n_top_q = sub.is_top1pct.sum()
    print(f"  Quintile {q+1} (or_range_bps {sub.or_range_bps.min():.0f}..{sub.or_range_bps.max():.0f}): "
          f"top1%={n_top_q:>3d}/{len(sub):>4d} = {100*n_top_q/len(sub):.2f}%  (iid 1%)")

# Hour-bucket: bi ∈ [0, 5] = first 30 min vs rest
print("\nBreak time bucket (bi = minutes after OR close):")
df["bi_bucket"] = pd.cut(df["bi"], bins=[-1, 5, 15, 30, 60, 9999],
                         labels=["[0-5]", "[6-15]", "[16-30]", "[31-60]", "[61+]"])
for b in df["bi_bucket"].cat.categories:
    sub = df[df.bi_bucket == b]
    n_top_b = sub.is_top1pct.sum()
    if len(sub) > 0:
        print(f"  bi={b}: top1%={n_top_b:>3d}/{len(sub):>4d} = {100*n_top_b/len(sub):.2f}%")

pd.DataFrame(results_A).to_csv(
    "<HOME>/Desktop/Algo_claude/data/ftmo_research/audit/orb_structure_angle_A_top1pct.csv", index=False)


# =====================================================================
# ANGLE B — Cluster mechanism
# =====================================================================
print("\n\n" + "█" * 80)
print("ANGLE B — Cluster mechanism (autocorr, runs obs vs iid, jackpots post-cluster)")
print("█" * 80)

# Sort chronologically (ledger should already be by date)
df_sorted = df.sort_values(["date", "bi"]).reset_index(drop=True)
r = df_sorted["r"].values
loss = (r < 0).astype(int)
hit = (r > 0).astype(int)
p_loss = loss.mean()
p_win = hit.mean()
print(f"\nP(loss) = {p_loss:.4f}  ({loss.sum()} losses on {len(r)} trades)")
print(f"P(win)  = {p_win:.4f}")

# ----- B.1 Autocorrelation -----
print("\n--- B.1 Autocorrélation des R ---")
print(f"{'lag':>5s}{'corr(R_t, R_{t-k})':>22s}{'t-stat (HAC6)':>16s}")
ac_rows = []
for lag in [1, 2, 3, 5, 10]:
    y = r[lag:]
    x = r[:-lag]
    corr = np.corrcoef(y, x)[0, 1]
    X = sm.add_constant(x)
    res = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    t = float(res.tvalues[1])
    print(f"{lag:>5d}{corr:>+22.4f}{t:>+16.2f}")
    ac_rows.append({"lag": lag, "corr": corr, "t_HAC6": t})

# Ljung-Box on R
lb_r = acorr_ljungbox(r, lags=[5, 10, 20], return_df=True)
print(f"\nLjung-Box on R (H0 = no autocorr):")
print(lb_r.round(4).to_string())

# Ljung-Box on loss indicator
lb_l = acorr_ljungbox(loss, lags=[5, 10, 20], return_df=True)
print(f"\nLjung-Box on loss indicator (1 if R<0):")
print(lb_l.round(4).to_string())

# ----- B.2 Run-length distribution observed vs iid -----
print("\n--- B.2 Run-length distribution: observed vs iid (p_loss compound) ---")
# Compute observed run-lengths of consecutive losses
runs = []
cur = 0
for x in loss:
    if x == 1:
        cur += 1
    else:
        if cur > 0:
            runs.append(cur)
        cur = 0
if cur > 0:
    runs.append(cur)
runs = np.array(runs)
print(f"  Total of {len(runs)} loss-runs in {len(r)} trades.")
print(f"  Run lengths: max={runs.max()}, mean={runs.mean():.2f}, median={int(np.median(runs))}")

# Expected under iid: in a sequence of N trades with P(loss)=p, the expected NUMBER of runs
# of exactly length k (followed by a win or end) is N × p^k × (1-p)
print(f"\n{'len(k)':>8s}{'observed':>11s}{'iid_expected':>15s}{'ratio_obs/iid':>17s}")
print("  (iid expected = N × p^k × (1-p) ; assumes independent trades with constant p_loss)")
for k in [1, 2, 3, 4, 5, 6, 7, 8, 10]:
    n_obs = (runs == k).sum() if k < runs.max() else (runs >= k).sum() if k == runs.max() else 0
    # exactly length k = followed by a win (or end). Approximation: count "≥k consecutive losses then break"
    iid_exp = len(r) * (p_loss ** k) * (1 - p_loss)
    ratio = n_obs / iid_exp if iid_exp > 0 else np.nan
    print(f"{k:>8d}{n_obs:>11d}{iid_exp:>15.1f}{ratio:>+17.2f}x")

# Specifically: P(≥4 consec losses anywhere in sequence)
def count_consec_at_least_k(seq, k):
    """Count positions where seq[i..i+k-1] are all 1 (= a run of ≥k ones starting at i, possibly longer)."""
    n = 0
    for i in range(len(seq) - k + 1):
        if np.all(seq[i:i+k] == 1):
            n += 1
    return n

print(f"\n  P(4 consec losses anywhere):")
for k in [2, 3, 4, 5, 6]:
    obs = count_consec_at_least_k(loss, k)
    iid = (len(r) - k + 1) * (p_loss ** k)  # # positions starting a run of ≥k under iid
    print(f"    ≥{k} consec : observed positions = {obs:>5d}  ;  iid expected = {iid:>8.1f}  ;  ratio = {obs/iid:.2f}x")

# ----- B.3 DECISIVE TEST: jackpots post-cluster -----
print("\n--- B.3 DECISIVE TEST: do jackpots arrive after loss clusters? ---")
# For each top 1% jackpot at position t, check trades [t-3, t-2, t-1] for ≥2 consecutive losses
top_positions = df_sorted.index[df_sorted.is_top1pct].tolist()
print(f"  Top 1% jackpots: n={len(top_positions)}")

def has_consec_loss_in_window(loss_arr, end_pos, window_size, k=2):
    """Check if any ≥k consecutive losses exist in loss_arr[end_pos-window_size : end_pos]."""
    start = max(0, end_pos - window_size)
    sub = loss_arr[start:end_pos]
    if len(sub) < k:
        return False
    # Look for at least k consecutive 1s
    cur = 0
    for x in sub:
        if x == 1:
            cur += 1
            if cur >= k:
                return True
        else:
            cur = 0
    return False

# DECISIVE: for each jackpot, is there a ≥2 consec losses in the 1-3 preceding trades?
print(f"\n  TEST: jackpot at position t — preceded (in trades t-3, t-2, t-1) by a ≥2 consec losses cluster?")
counts = {}
for window in [1, 2, 3, 5]:
    flagged = 0
    for t in top_positions:
        if has_consec_loss_in_window(loss, t, window, k=2):
            flagged += 1
    counts[window] = flagged
    iid_baseline = 1 - (1 - p_loss**2)**(max(window - 1, 1))   # rough iid baseline
    print(f"    window {window} trades before jackpot:  "
          f"{flagged:>3d}/{len(top_positions)} jackpots ({100*flagged/len(top_positions):.1f}%)  "
          f"(rough iid expected if random: {iid_baseline*100:.1f}%)")

# Also: jackpots immediately preceded by a loss (any loss, not cluster)
n_top_after_loss = 0
n_top_after_win = 0
n_top_first = 0
for t in top_positions:
    if t == 0:
        n_top_first += 1
    elif loss[t-1] == 1:
        n_top_after_loss += 1
    else:
        n_top_after_win += 1
print(f"\n  Single-trade view:")
print(f"    Jackpot immediately after a loss (t-1 < 0): {n_top_after_loss}/{len(top_positions)} "
      f"({100*n_top_after_loss/(len(top_positions)-n_top_first):.1f}%)")
print(f"    Jackpot immediately after a win   (t-1 > 0): {n_top_after_win}/{len(top_positions)} "
      f"({100*n_top_after_win/(len(top_positions)-n_top_first):.1f}%)")
print(f"  iid baseline: P(loss prev) = {p_loss:.2%}  — so any jackpot bias toward post-win/loss is informative.")

# What fraction of TOTAL R sum is in jackpots arriving after ≥2 consec losses ?
print(f"\n  P&L SPLIT — jackpot R-sum by precedence pattern:")
total_jackpot_r = df_sorted.loc[top_positions, "r"].sum()
for window in [1, 2, 3]:
    flag_pos = [t for t in top_positions if has_consec_loss_in_window(loss, t, window, k=2)]
    r_post_cluster = df_sorted.loc[flag_pos, "r"].sum()
    print(f"    Window {window}: jackpots after ≥2-consec cluster contribute {r_post_cluster:+.1f} R  "
          f"({100*r_post_cluster/total_jackpot_r:.1f}% of jackpot R-sum)")

# Save
pd.DataFrame(ac_rows).to_csv(
    "<HOME>/Desktop/Algo_claude/data/ftmo_research/audit/orb_structure_angle_B_autocorr.csv", index=False)
