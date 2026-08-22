"""ORB V2+E7 @ 0.4 bps RT — Regime nowcast + forward-predictive falsification.

Stage 1: WHERE ARE WE (descriptive)?
  - mean_R per month 2010-2026
  - regime classification: favorable (>+0.08) / neutral / unfavorable (<0)
  - position of last 3/6/12 months
  - p(funded) MC conditional on bootstrap from current-regime months only

Stage 2: FORWARD PREDICTABILITY (falsification, prior fortement négatif)
  Test if end-of-month M variables predict mean_R(M+1) and mean_R(M+2):
    - VIX level (close last day of M)
    - VIX/VIX3M term-structure slope (contango/backwardation)
    - NQ realized vol 20d
    - NQ trend (close vs MA200, binary + continuous distance)
    - auto-persistence: mean_R_ORB(M) → mean_R_ORB(M+1)
  Gate: t-HAC>2.5 AND holds OOS (train<2019/test≥2019) AND R² economically non-trivial.
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm

LEDGER = "<HOME>/Desktop/Algo_claude/data/ftmo_research/audit/nq_v2_trades.parquet"
DAILY_RTH = "<HOME>/Desktop/Algo_claude/data/overnight_research/nq_rth_daily.parquet"
VIX_PATH = "<HOME>/Desktop/Algo_claude/data/panels/vix.csv"
VIX_TS_PATH = "<HOME>/Desktop/Algo_claude/data/panels/vix_term_structure.csv"

E7_LIFT_R = 0.015
COST_BPS = 0.4
ACCOUNT_INIT = 10000.0
DLL_PCT = 0.05
MAX_TOTAL_PCT = 0.10
TARGET_P1 = 0.10
TARGET_P2 = 0.05
BLOCK_SIZE = 21
N_PATHS = 12000
MAX_STEPS = 252 * 5
MIN_TRADES_PHASE = 4
RNG_SEED = 17

# ----- Load ledger & build per-trade R + monthly aggregation -----
df = pd.read_parquet(LEDGER).reset_index()
r_2 = df["r_2 bps RT (median)"].astype(float).values
r_1 = df["r_1 bps RT (aggressive)"].astype(float).values
cost_unit = r_1 - r_2
df["r"] = r_2 + (2.0 - COST_BPS) * cost_unit + E7_LIFT_R
df["date"] = pd.to_datetime(df["date"])
df["month"] = df["date"].dt.to_period("M")
df["year_month"] = df["month"].dt.to_timestamp()

print("=" * 80)
print(f"ORB V2+E7 @ {COST_BPS} bps RT — n_trades={len(df)} from {df.date.min().date()} to {df.date.max().date()}")
print("=" * 80)

# Monthly aggregation
monthly = df.groupby("year_month").agg(
    n_trades=("r", "size"),
    mean_R=("r", "mean"),
    median_R=("r", "median"),
    sum_R=("r", "sum"),
    hit=("r", lambda x: (x > 0).mean()),
).reset_index()
monthly = monthly[monthly.n_trades >= 5].copy()  # drop very thin months
print(f"\nMonths in ledger (with ≥5 trades): {len(monthly)} months from {monthly.year_month.min().date()} to {monthly.year_month.max().date()}")

# Regime classification
def classify(mr):
    if mr >= 0.08:
        return "favorable"
    elif mr >= 0:
        return "neutral"
    else:
        return "unfavorable"
monthly["regime"] = monthly["mean_R"].apply(classify)
print("\nRegime distribution (monthly):")
print(monthly.regime.value_counts())

# =====================================================================
# STAGE 1 — Nowcast
# =====================================================================
print("\n" + "█" * 80)
print("STAGE 1 — NOWCAST")
print("█" * 80)

# Distribution stats
print(f"\nMonthly mean_R distribution (full sample n={len(monthly)} months):")
for p in [5, 10, 25, 50, 75, 90, 95]:
    print(f"  p{p:>2d} = {np.percentile(monthly.mean_R, p):+.4f}")
print(f"  mean  = {monthly.mean_R.mean():+.4f}")
print(f"  std   = {monthly.mean_R.std():.4f}")

# Last 3/6/12 months
monthly_sorted = monthly.sort_values("year_month").reset_index(drop=True)
n_total = len(monthly_sorted)
for w in [3, 6, 12]:
    sub = monthly_sorted.tail(w)
    mean_R_recent = sub.mean_R.mean()
    weighted_mean_R = (sub.mean_R * sub.n_trades).sum() / sub.n_trades.sum()
    n_trades_recent = sub.n_trades.sum()
    # percentile: how many months had mean_R <= this recent average?
    pct = (monthly.mean_R <= mean_R_recent).mean()
    regime = classify(mean_R_recent)
    print(f"\n  Last {w} months ({sub.year_month.min().strftime('%Y-%m')} → {sub.year_month.max().strftime('%Y-%m')}):")
    print(f"    n_trades = {n_trades_recent}  unweighted mean_R per month = {mean_R_recent:+.4f}")
    print(f"    weighted (per-trade) mean_R = {weighted_mean_R:+.4f}")
    print(f"    Position in historical distribution: {pct*100:.0f}e percentile")
    print(f"    Regime: **{regime.upper()}**")

# Last 12 months breakdown
print("\nLast 12 months — month-by-month:")
print(monthly_sorted.tail(12)[["year_month", "n_trades", "mean_R", "hit", "regime"]].to_string(index=False))

# p(funded) conditional on current regime
print("\n--- p(funded) FTMO 2-step MC conditional on CURRENT regime (last 6 months) ---")

def generate_bootstrap(samples, n_paths, max_steps, block_size, rng):
    L = len(samples)
    n_blocks = (max_steps + block_size - 1) // block_size
    starts = rng.integers(0, max(1, L - block_size + 1), size=(n_paths, n_blocks))
    out = np.empty((n_paths, n_blocks * block_size), dtype=np.float64)
    for k in range(block_size):
        # Make sure we don't go out of bounds
        idx = starts + k
        idx = np.clip(idx, 0, L - 1)
        out[:, k::block_size] = samples[idx]
    return out[:, :max_steps]


def simulate_phase(boot, sizing_pct, target_pct, account_init=ACCOUNT_INIT,
                   dll_pct=DLL_PCT, max_total_pct=MAX_TOTAL_PCT,
                   min_trades=MIN_TRADES_PHASE):
    n_paths, max_steps = boot.shape
    risk_dollar = account_init * sizing_pct
    pnl = boot * risk_dollar
    eq = account_init + np.cumsum(pnl, axis=1)
    midnight = np.concatenate([np.full((n_paths, 1), account_init), eq[:, :-1]], axis=1)
    dll_breach = pnl <= -dll_pct * midnight
    floor = account_init * (1 - max_total_pct)
    target = account_init * (1 + target_pct)
    floor_breach = eq <= floor
    target_hit = eq >= target
    target_hit[:, :min_trades - 1] = False
    bust_step = np.where(dll_breach | floor_breach, np.arange(max_steps), max_steps + 1)
    bust_first = bust_step.min(axis=1)
    pass_step = np.where(target_hit, np.arange(max_steps), max_steps + 1)
    pass_first = pass_step.min(axis=1)
    passed = pass_first < bust_first
    return passed, pass_first + 1, bust_first + 1


def p_funded_mc(samples, sizing, seed_offset, block_size=BLOCK_SIZE, n_paths=N_PATHS):
    rng = np.random.default_rng(RNG_SEED + seed_offset)
    boot1 = generate_bootstrap(samples, n_paths, MAX_STEPS, block_size, rng)
    p1_pass, p1_pass_step, _ = simulate_phase(boot1, sizing, TARGET_P1)
    n_p1_pass = int(p1_pass.sum())
    if n_p1_pass == 0:
        return 0.0, 0.0
    boot2 = generate_bootstrap(samples, n_p1_pass, MAX_STEPS, block_size, rng)
    p2_pass, _, _ = simulate_phase(boot2, sizing, TARGET_P2)
    p_funded = (n_p1_pass / n_paths) * (p2_pass.mean())
    return p_funded, p1_pass.mean()

# Bootstrap from last 6mo
last_6mo_cutoff = monthly_sorted.year_month.max() - pd.DateOffset(months=6)
mask_6mo = df.date >= last_6mo_cutoff
r_recent6 = df.loc[mask_6mo, "r"].values
last_12mo_cutoff = monthly_sorted.year_month.max() - pd.DateOffset(months=12)
mask_12mo = df.date >= last_12mo_cutoff
r_recent12 = df.loc[mask_12mo, "r"].values

# Full sample for comparison
r_full = df["r"].values

print(f"\n  Sample sizes:")
print(f"    Last 6mo trades: {len(r_recent6)}  mean_R={r_recent6.mean():+.4f}  std={r_recent6.std():.3f}")
print(f"    Last 12mo trades: {len(r_recent12)}  mean_R={r_recent12.mean():+.4f}  std={r_recent12.std():.3f}")
print(f"    Full 16y trades: {len(r_full)}  mean_R={r_full.mean():+.4f}  std={r_full.std():.3f}")

# Use smaller block_size for short samples to avoid block too large
block_recent = min(BLOCK_SIZE, max(5, len(r_recent6) // 5))
print(f"  (Using block_size={block_recent} for recent-regime bootstrap, vs {BLOCK_SIZE} for full)")

print(f"\n  p(funded) MC by sample (12000 paths, no time limit):")
print(f"  {'Sample':>16s}{'sizing 1.0%':>14s}{'sizing 1.5%':>14s}{'sizing 2.5%':>14s}")
ppass_rows = []
for label, samples, block in [
    ("Full 16y", r_full, BLOCK_SIZE),
    ("Last 12mo", r_recent12, block_recent),
    ("Last 6mo", r_recent6, block_recent),
]:
    row_cells = []
    for sz in [0.010, 0.015, 0.025]:
        pf, p1p = p_funded_mc(samples, sz, seed_offset=int(sz * 1000) + hash(label) % 10000, block_size=block)
        row_cells.append(pf)
        ppass_rows.append({"sample": label, "sizing": sz, "p_funded": pf, "p1_pass": p1p, "n_trades": len(samples)})
    print(f"  {label:>16s}{row_cells[0]*100:>13.1f}%{row_cells[1]*100:>13.1f}%{row_cells[2]*100:>13.1f}%")

pd.DataFrame(ppass_rows).to_csv(
    "<HOME>/Desktop/Algo_claude/data/ftmo_research/audit/orb_regime_ppass_conditional.csv", index=False)

# =====================================================================
# STAGE 2 — Forward predictability
# =====================================================================
print("\n" + "█" * 80)
print("STAGE 2 — FORWARD PREDICTABILITY (falsification, prior ≪0)")
print("█" * 80)

# Build end-of-month features
# VIX EOM (level + 1mo change)
vix = pd.read_csv(VIX_PATH)
vix.columns = ["date", "vix", "vvix"]
vix["date"] = pd.to_datetime(vix["date"])
vix["month"] = vix["date"].dt.to_period("M").dt.to_timestamp()
vix_eom = vix.sort_values("date").groupby("month").tail(1)[["month", "vix"]].rename(columns={"vix": "vix_eom"})

# VIX term structure (VIX/VIX3M)
vts = pd.read_csv(VIX_TS_PATH)
vts.columns = ["date", "vix_ts", "vix3m"]
vts["date"] = pd.to_datetime(vts["date"])
vts["month"] = vts["date"].dt.to_period("M").dt.to_timestamp()
vts["vix_term_slope"] = vts["vix_ts"] / vts["vix3m"]  # <1 = contango (calm); >1 = backwardation (stress)
vts_eom = vts.dropna(subset=["vix_term_slope"]).sort_values("date").groupby("month").tail(1)[["month", "vix_term_slope"]]

# NQ daily for vol & MA200
daily = pd.read_parquet(DAILY_RTH).reset_index()
daily.columns = ["date", "o", "c", "pc", "ov_bps", "in_bps", "wd", "yr"]
daily["date"] = pd.to_datetime(daily["date"])
daily["ret"] = daily["c"] / daily["c"].shift(1) - 1
daily["vol_20d"] = daily["ret"].rolling(20).std() * np.sqrt(252)
daily["ma200"] = daily["c"].rolling(200).mean()
daily["dist_ma200"] = (daily["c"] - daily["ma200"]) / daily["ma200"]
daily["above_ma200"] = (daily["c"] > daily["ma200"]).astype(int)
daily["month"] = daily["date"].dt.to_period("M").dt.to_timestamp()
daily_eom = daily.dropna(subset=["vol_20d", "dist_ma200"]).sort_values("date").groupby("month").tail(1)[
    ["month", "vol_20d", "dist_ma200", "above_ma200"]]

# Merge all on month
feat = monthly[["year_month", "mean_R", "n_trades"]].rename(columns={"year_month": "month", "mean_R": "orb_mean_R_M"})
feat = feat.merge(vix_eom, on="month", how="left").merge(vts_eom, on="month", how="left").merge(daily_eom, on="month", how="left")
feat = feat.sort_values("month").reset_index(drop=True)
# Add forward targets
feat["orb_mean_R_M1"] = feat["orb_mean_R_M"].shift(-1)
feat["orb_mean_R_M2"] = feat["orb_mean_R_M"].shift(-2)
print(f"\nFeature panel: {len(feat)} months ; complete features for {feat.dropna().shape[0]} rows (after lead)")
print(f"Sample period: {feat.month.min().date()} → {feat.month.max().date()}")

# Define predictors
predictors = [
    ("VIX_eom", "vix_eom"),
    ("VIX_term_slope (VIX/VIX3M)", "vix_term_slope"),
    ("NQ_vol_20d", "vol_20d"),
    ("NQ_dist_MA200", "dist_ma200"),
    ("NQ_above_MA200 (binary)", "above_ma200"),
    ("ORB_mean_R_M (auto-persistence)", "orb_mean_R_M"),
]

def reg_predict(y, x, label):
    """Return mean, t-HAC6, R² for OLS y ~ const + x."""
    mask = ~(np.isnan(y) | np.isnan(x))
    y, x = y[mask], x[mask]
    if len(y) < 30 or x.std() == 0:
        return None
    X = sm.add_constant(x)
    res = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    return {
        "label": label,
        "n": len(y),
        "beta": float(res.params[1]),
        "t_HAC6": float(res.tvalues[1]),
        "r2": float(res.rsquared),
    }

print(f"\n--- Forward regression: mean_R(M+1) ~ feature(M) ---")
print(f"{'Predictor':35s}{'beta':>12s}{'t_HAC6':>10s}{'R²':>9s}{'n':>6s}{'flag':>10s}")
results_M1 = []
for label, col in predictors:
    y = feat["orb_mean_R_M1"].values
    x = feat[col].values
    res = reg_predict(y, x, label)
    if res is None:
        continue
    flag = "**PASS**" if (abs(res["t_HAC6"]) >= 2.5 and res["r2"] > 0.02) else (
        "weak" if abs(res["t_HAC6"]) >= 1.65 else "")
    print(f"{label:35s}{res['beta']:>+12.5f}{res['t_HAC6']:>+10.2f}{res['r2']:>9.4f}{res['n']:>6d}{flag:>10s}")
    res["target"] = "M+1"
    results_M1.append(res)

print(f"\n--- Forward regression: mean_R(M+2) ~ feature(M) ---")
print(f"{'Predictor':35s}{'beta':>12s}{'t_HAC6':>10s}{'R²':>9s}{'n':>6s}{'flag':>10s}")
results_M2 = []
for label, col in predictors:
    y = feat["orb_mean_R_M2"].values
    x = feat[col].values
    res = reg_predict(y, x, label)
    if res is None:
        continue
    flag = "**PASS**" if (abs(res["t_HAC6"]) >= 2.5 and res["r2"] > 0.02) else (
        "weak" if abs(res["t_HAC6"]) >= 1.65 else "")
    print(f"{label:35s}{res['beta']:>+12.5f}{res['t_HAC6']:>+10.2f}{res['r2']:>9.4f}{res['n']:>6d}{flag:>10s}")
    res["target"] = "M+2"
    results_M2.append(res)

# OOS split: train<2019, test≥2019
print(f"\n--- OOS split — train month <2019, test ≥2019 (M+1 only) ---")
feat["year"] = feat.month.dt.year
print(f"{'Predictor':35s}{'beta_IS':>10s}{'t_IS':>8s}{'R²_IS':>8s}{'beta_OOS':>11s}{'t_OOS':>9s}{'R²_OOS':>9s}{'hold':>8s}")
for label, col in predictors:
    train = feat[(feat.year < 2019)].copy()
    test = feat[(feat.year >= 2019)].copy()
    res_is = reg_predict(train["orb_mean_R_M1"].values, train[col].values, label + "_IS")
    res_oos = reg_predict(test["orb_mean_R_M1"].values, test[col].values, label + "_OOS")
    if res_is is None or res_oos is None:
        continue
    same_sign = (np.sign(res_is["beta"]) == np.sign(res_oos["beta"]))
    hold = "✓" if (same_sign and abs(res_oos["t_HAC6"]) >= 1.65) else ""
    print(f"{label:35s}{res_is['beta']:>+10.5f}{res_is['t_HAC6']:>+8.2f}{res_is['r2']:>8.3f}"
          f"{res_oos['beta']:>+11.5f}{res_oos['t_HAC6']:>+9.2f}{res_oos['r2']:>9.3f}{hold:>8s}")

pd.DataFrame(results_M1 + results_M2).to_csv(
    "<HOME>/Desktop/Algo_claude/data/ftmo_research/audit/orb_regime_forward_predictors.csv", index=False)
print("\nSaved -> orb_regime_ppass_conditional.csv + orb_regime_forward_predictors.csv")
