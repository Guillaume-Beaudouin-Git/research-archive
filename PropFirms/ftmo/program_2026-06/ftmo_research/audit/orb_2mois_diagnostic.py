"""ORB V2+E7 — 2-month verdict + diagnostic. Cost = 0.4 bps RT fixed.

PART 1: hard-cap 8-week MC. For each sizing in {1.0, 1.5, 2.5, 3.0, 4.0}%:
  - % PASSED  (target P1+P2 hit ≤ 40 trades total)
  - % BUST    (floor or daily breach ≤ 40 trades total)
  - % NEITHER (still trading at 40 trades = FAIL by hard cap)

PART 2: Descriptive diagnostic — NO MINING (L10/L19). Read the structure,
do NOT tune. Any candidate signal noted is flagged "OOS hypothesis only".

Reuses engine from orb_ppass_grid_v2.py (verbatim functions).
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm

LEDGER = "<HOME>/Desktop/Algo_claude/data/ftmo_research/audit/nq_v2_trades.parquet"
DAILY_RTH = "<HOME>/Desktop/Algo_claude/data/overnight_research/nq_rth_daily.parquet"
VIX_PATH = "<HOME>/Desktop/Algo_claude/data/panels/vix.csv"

E7_LIFT_R = 0.015
ACCOUNT_INIT = 10000.0
DLL_PCT = 0.05
MAX_TOTAL_PCT = 0.10
TARGET_P1 = 0.10
TARGET_P2 = 0.05
BLOCK_SIZE = 21
N_PATHS = 12000
MIN_TRADES_PHASE = 4
RNG_SEED = 17
COST_BPS = 0.4
TRADES_PER_WEEK = 5
HARD_CAP_WEEKS = 8
HARD_CAP_TRADES = HARD_CAP_WEEKS * TRADES_PER_WEEK   # 40 trades total cap

SIZINGS = [0.010, 0.015, 0.025, 0.030, 0.040]


# ----- engine (verbatim from orb_ppass_grid_v2.py) -----
def generate_bootstrap(samples, n_paths, max_steps, block_size, rng):
    L = len(samples)
    n_blocks = (max_steps + block_size - 1) // block_size
    starts = rng.integers(0, L - block_size + 1, size=(n_paths, n_blocks))
    out = np.empty((n_paths, n_blocks * block_size), dtype=np.float64)
    for k in range(block_size):
        out[:, k::block_size] = samples[starts + k]
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
    return passed, pass_first + 1, bust_first + 1   # 1-indexed; >max_steps means "did not happen"


# ----- load ledger & build per-trade R @ 0.4 bps V2+E7 -----
df = pd.read_parquet(LEDGER).reset_index()
r_2 = df["r_2 bps RT (median)"].astype(float).values
r_1 = df["r_1 bps RT (aggressive)"].astype(float).values
cost_unit = r_1 - r_2
r_v2e7 = r_2 + (2.0 - COST_BPS) * cost_unit + E7_LIFT_R
df["r"] = r_v2e7
df["year"] = pd.to_datetime(df["date"]).dt.year
df["weekday"] = pd.to_datetime(df["date"]).dt.weekday   # 0=Mon
df["date_d"] = pd.to_datetime(df["date"]).dt.normalize()

print("=" * 80)
print("ORB V2+E7 @ 0.4 bps RT — n_trades=", len(df), " mean_R=", round(r_v2e7.mean(), 4))
print("=" * 80)


# =====================================================================
# PART 1 — Hard-cap 8-week verdict
# =====================================================================
print("\n\n" + "█" * 80)
print("PART 1 — HARD CAP 8 SEMAINES (=40 trades total P1+P2)")
print("█" * 80)
print(f"{'Sizing':>8s}{'% PASSED ≤8w':>15s}{'% BUST ≤8w':>13s}{'% NI-NI ≤8w':>14s}")
print("-" * 50)


def run_hardcap_8w(samples, sizing_pct, cap_total_trades=HARD_CAP_TRADES, seed_offset=0):
    """A path is PASSED iff (target1 hit before bust1 AND p1_step ≤ cap)
                            AND (target2 hit before bust2 in remaining trades).
       A path is BUSTED iff bust happened (in P1 or P2) within window AND target was NOT yet hit.
       Else NEITHER (neither bust nor pass within cap)."""
    rng = np.random.default_rng(RNG_SEED + seed_offset)
    boot1 = generate_bootstrap(samples, N_PATHS, cap_total_trades, BLOCK_SIZE, rng)
    p1_pass, p1_pass_step, p1_bust_step = simulate_phase(boot1, sizing_pct, TARGET_P1)
    # p1_pass is True iff target hit BEFORE bust. p1_pass_step / p1_bust_step are independent indices.
    p1_pass_in_window = p1_pass & (p1_pass_step <= cap_total_trades)
    # Bust in window = (~p1_pass means bust came first) AND p1_bust_step ≤ cap
    p1_bust_in_window = (~p1_pass) & (p1_bust_step <= cap_total_trades)
    # P2 only runs for paths that passed P1 in window
    if p1_pass_in_window.any():
        rem_trades = cap_total_trades - p1_pass_step[p1_pass_in_window]
        boot2 = generate_bootstrap(samples, int(p1_pass_in_window.sum()), cap_total_trades, BLOCK_SIZE, rng)
        p2_pass, p2_pass_step, p2_bust_step = simulate_phase(boot2, sizing_pct, TARGET_P2)
        funded_in_window = p2_pass & (p2_pass_step <= rem_trades)
        bust_in_window_p2 = (~p2_pass) & (p2_bust_step <= rem_trades)
    else:
        funded_in_window = np.array([], dtype=bool)
        bust_in_window_p2 = np.array([], dtype=bool)
    p_pass = funded_in_window.sum() / N_PATHS
    p_bust_p1 = p1_bust_in_window.sum() / N_PATHS
    p_bust_p2_joint = bust_in_window_p2.sum() / N_PATHS    # already / N_PATHS denominator
    p_bust_total = p_bust_p1 + p_bust_p2_joint
    p_neither = 1.0 - p_pass - p_bust_total
    return {"passed": p_pass, "busted": p_bust_total, "neither": p_neither,
            "p_bust_p1": p_bust_p1, "p_bust_p2_joint": p_bust_p2_joint}


hardcap_results = []
for sz in SIZINGS:
    res = run_hardcap_8w(r_v2e7, sz, seed_offset=int(sz * 1000))
    sanity = res['passed'] + res['busted'] + res['neither']
    print(f"{sz:>7.1%}{res['passed']*100:>14.2f}%{res['busted']*100:>12.2f}%{res['neither']*100:>13.2f}%  "
          f"(check sum={sanity*100:.2f}%, bust_P1={res['p_bust_p1']*100:.2f}% bust_P2={res['p_bust_p2_joint']*100:.2f}%)")
    hardcap_results.append({"sizing": sz, **res})

pd.DataFrame(hardcap_results).to_csv(
    "<HOME>/Desktop/Algo_claude/data/ftmo_research/audit/orb_2mois_hardcap8w.csv", index=False
)


# =====================================================================
# PART 2 — Diagnostic (descriptive ONLY)
# =====================================================================
print("\n\n" + "█" * 80)
print("PART 2 — DIAGNOSTIC DESCRIPTIF (no mining, no tuning)")
print("█" * 80)

# ----- 2.1 Distribution R + top 5% contrib P&L -----
print("\n--- 2.1 Distribution R par trade ---")
r = r_v2e7
print(f"  n={len(r)}  mean={r.mean():+.4f}  std={r.std():.3f}  median={np.median(r):+.4f}")
print(f"  skew={pd.Series(r).skew():+.3f}  kurt(excess)={pd.Series(r).kurt():+.2f}")
print(f"  hit_rate={(r>0).mean():.2%}")
for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
    print(f"  p{p:>2d} = {np.percentile(r, p):+.3f} R")
print(f"  Max win:  {r.max():+.3f} R  ({(r == r.max()).sum()} trade)")
print(f"  Max loss: {r.min():+.3f} R")

# Top 5% trades contribution
sorted_r = np.sort(r)
n5 = int(0.05 * len(r))
top5_winners_sum = sorted_r[-n5:].sum()
total_sum = sorted_r.sum()
print(f"\n  Total P&L (in R): {total_sum:+.1f} R sur {len(r)} trades")
print(f"  Top 5% trades (winners by R, n={n5}): contrib = {top5_winners_sum:+.1f} R  "
      f"= {100*top5_winners_sum/total_sum:.0f}% du P&L total")
print(f"  Top 1% (n={int(0.01*len(r))}): contrib = {sorted_r[-int(0.01*len(r)):].sum():+.1f} R  "
      f"= {100*sorted_r[-int(0.01*len(r)):].sum()/total_sum:.0f}% du P&L total")
print(f"  Bottom 5% (losers by R): contrib = {sorted_r[:n5].sum():+.1f} R")
# Without top winners
print(f"\n  P&L SANS le top 5% winners: {(total_sum - top5_winners_sum):+.1f} R "
      f"= mean {(total_sum - top5_winners_sum)/(len(r)-n5):+.4f} R/trade")
print(f"  P&L SANS le top 1% winners: {(total_sum - sorted_r[-int(0.01*len(r)):].sum()):+.1f} R "
      f"= mean {(total_sum - sorted_r[-int(0.01*len(r)):].sum())/(len(r)-int(0.01*len(r))):+.4f} R/trade")


# ----- 2.2 Bust mechanism (from MC bust paths @ sizing 2.5%, the 'typical' challenge size) -----
print("\n--- 2.2 Mécanisme de bust (MC paths busted ≤ 8 sem @ sizing 2.5%) ---")
sz_b = 0.025
rng = np.random.default_rng(RNG_SEED + int(sz_b * 1000))
boot = generate_bootstrap(r_v2e7, N_PATHS, HARD_CAP_TRADES, BLOCK_SIZE, rng)
p1_pass, p1_pass_step, p1_bust_step = simulate_phase(boot, sz_b, TARGET_P1)
bust_mask = (p1_bust_step <= HARD_CAP_TRADES) & (~p1_pass)
print(f"  Sizing {sz_b:.1%} → bust paths: {bust_mask.sum()} sur {N_PATHS} ({bust_mask.mean():.1%})")

if bust_mask.sum() > 0:
    bust_boot = boot[bust_mask]
    bust_step = p1_bust_step[bust_mask]
    # Per bust path: trade R that triggered bust, last N R's, max DD prior, etc.
    trigger_R = []
    cumsum_at_bust = []
    consec_losses_before_bust = []
    max_single_loss_within = []
    for i in range(len(bust_boot)):
        b_step_idx = bust_step[i] - 1  # 0-indexed
        path_R = bust_boot[i, :b_step_idx + 1]
        trigger_R.append(path_R[-1])
        cumsum_at_bust.append(path_R.sum())
        # consecutive losses just before bust
        n_consec = 0
        for j in range(len(path_R) - 1, -1, -1):
            if path_R[j] < 0:
                n_consec += 1
            else:
                break
        consec_losses_before_bust.append(n_consec)
        max_single_loss_within.append(path_R.min())

    trigger_R = np.array(trigger_R)
    cumsum_at_bust = np.array(cumsum_at_bust)
    consec_losses_before_bust = np.array(consec_losses_before_bust)
    max_single_loss_within = np.array(max_single_loss_within)

    print(f"\n  Trade trigger (last R before bust):")
    print(f"    mean={trigger_R.mean():+.3f}  median={np.median(trigger_R):+.3f}  "
          f"min={trigger_R.min():+.3f}  max={trigger_R.max():+.3f}")
    print(f"    P(trigger ≤ -1R) = {(trigger_R <= -1).mean():.1%}  "
          f"(c'est un stop normal {sz_b:.1%}×1R={sz_b*100:.1f}% loss/account → no single-trade DLL breach possible @ this sizing since DLL=5%, 1R={sz_b*100:.1f}%)")
    print(f"    P(trigger ≤ -1.5R) = {(trigger_R <= -1.5).mean():.1%}  (gap fail beyond stop)")
    print(f"    P(trigger ≤ -2R) = {(trigger_R <= -2).mean():.1%}  (extreme gap)")

    print(f"\n  Consecutive losses just before bust (run length):")
    for n in [1, 2, 3, 5, 8]:
        print(f"    P(≥ {n} consec losses just before bust) = {(consec_losses_before_bust >= n).mean():.1%}")
    print(f"    mean={consec_losses_before_bust.mean():.1f}  median={np.median(consec_losses_before_bust):.0f}")

    print(f"\n  Cumulative R at bust (= total drawdown in R):")
    print(f"    mean={cumsum_at_bust.mean():+.2f} R  median={np.median(cumsum_at_bust):+.2f} R  "
          f"min={cumsum_at_bust.min():+.2f}")
    print(f"    At sizing {sz_b:.1%}, cumsum -3.33R triggers 10% MaxDD bust (one possible mechanism).")
    print(f"    P(bust via accumulation, cumsum ≤ -3R) = {(cumsum_at_bust <= -3).mean():.1%}")

    print(f"\n  Mechanism breakdown:")
    is_single_big = trigger_R <= -1.5    # gap beyond stop, single trade
    is_accumulation = (~is_single_big) & (cumsum_at_bust <= -2.5)   # not single big, but accumulated DD
    is_neither = ~is_single_big & ~is_accumulation
    print(f"    Single-trade trigger (R ≤ -1.5):       {is_single_big.mean():.1%}")
    print(f"    Accumulation (cumsum ≤ -2.5R only):    {is_accumulation.mean():.1%}")
    print(f"    Mixed / other:                          {is_neither.mean():.1%}")


# ----- 2.3 Correlation descriptive: R vs observable BEFORE entry -----
print("\n--- 2.3 Corrélations descriptives R vs variables observables avant entrée ---")
# Build join with daily RTH and VIX
try:
    daily = pd.read_parquet(DAILY_RTH).reset_index()
    daily.columns = ["date", "o", "c", "pc", "ov_bps", "in_bps", "wd", "yr"]
    daily["date"] = pd.to_datetime(daily["date"]).dt.normalize()
    # gap_overnight = (open[t] / close[t-1] - 1) — already as ov_bps
    daily["gap_overnight_bps"] = daily["ov_bps"]
    df_j = df.merge(daily[["date", "gap_overnight_bps"]], left_on="date_d", right_on="date", how="left")
except Exception as e:
    print(f"  ! daily merge fail: {e}")
    df_j = df.copy()
    df_j["gap_overnight_bps"] = np.nan

try:
    vix = pd.read_csv(VIX_PATH)
    vix.columns = ["date", "vix", "vvix"]
    vix["date"] = pd.to_datetime(vix["date"]).dt.normalize()
    vix["vix_prev"] = vix["vix"].shift(1)   # VIX of previous day, observable before today's ORB entry
    df_j = df_j.merge(vix[["date", "vix_prev"]], left_on="date_d", right_on="date", how="left", suffixes=("", "_v"))
except Exception as e:
    print(f"  ! VIX merge fail: {e}")
    df_j["vix_prev"] = np.nan

# Variables to correlate
# OR width (in bps of underlying)
df_j["or_range_bps"] = df_j["or_range"] / df_j["level"] * 1e4
# bi = break index after OR close (in 1-min bars)
# weekday
features = {
    "or_range_bps": df_j["or_range_bps"].values,
    "bi (mins after OR close)": df_j["bi"].values,
    "ttb_5min": df_j["ttb_5min"].values,
    "gap_overnight_bps": df_j["gap_overnight_bps"].values,
    "weekday (0=Mon..4=Fri)": df_j["weekday"].values,
    "VIX_prev": df_j["vix_prev"].values,
    "direction (1=long,-1=short)": df_j["direction"].values,
}

def hac_corr(y, x, lag=6):
    """Correlation + HAC t-stat for null β=0 in y = α + βx."""
    mask = ~(np.isnan(y) | np.isnan(x))
    y, x = y[mask], x[mask]
    if len(y) < 30:
        return np.nan, np.nan, len(y)
    if x.std() == 0:
        return 0.0, 0.0, len(y)
    corr = np.corrcoef(y, x)[0, 1]
    X = sm.add_constant(x)
    res = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    t = float(res.tvalues[1])
    return corr, t, len(y)


print(f"\n{'Variable':35s}{'corr(R,X)':>11s}{'t_HAC6':>9s}{'n':>7s}{'  flag':>10s}")
corr_rows = []
for name, x in features.items():
    corr, t, n = hac_corr(r_v2e7, x)
    flag = "**STRONG**" if abs(t) >= 2.5 else ("weak" if abs(t) >= 1.65 else "")
    print(f"{name:35s}{corr:>+11.3f}{t:>+9.2f}{n:>7d}{flag:>10s}")
    corr_rows.append({"variable": name, "corr": corr, "t_HAC6": t, "n": n, "flag": flag})
pd.DataFrame(corr_rows).to_csv(
    "<HOME>/Desktop/Algo_claude/data/ftmo_research/audit/orb_2mois_correlations.csv", index=False)


# ----- 2.4 3 pires années vs 3 meilleures -----
print("\n--- 2.4 Structure des 3 pires années (2010, 2013, 2015) vs 3 meilleures (2022, 2023, 2024) ---")
df_j["or_range_pts"] = df_j["or_range"]
df_j["abs_R"] = np.abs(df_j["r"])
year_stats = df_j.groupby("year").agg(
    n=("r", "size"),
    mean_R=("r", "mean"),
    hit=("r", lambda x: (x > 0).mean()),
    skew=("r", lambda x: pd.Series(x).skew()),
    p95_R=("r", lambda x: np.percentile(x, 95)),
    p99_R=("r", lambda x: np.percentile(x, 99)),
    or_range_med=("or_range", "median"),
    or_range_p90=("or_range", lambda x: np.percentile(x, 90)),
    or_range_bps_med=("or_range_bps", "median"),
    ttb_5min_med=("ttb_5min", "median"),
    gap_overnight_bps_med=("gap_overnight_bps", lambda x: np.nanmedian(x)),
    vix_med=("vix_prev", lambda x: np.nanmedian(x)),
).round(3)
year_stats["mean_R"] = year_stats["mean_R"].round(4)
print(year_stats.to_string())

worst = [2010, 2013, 2015]
best = [2022, 2023, 2024]
print(f"\n  Means structurelles:")
print(f"  Variable             worst(2010,2013,2015)    best(2022,2023,2024)   Δ (best - worst)")
for col in ["mean_R", "hit", "skew", "p95_R", "or_range_med", "or_range_bps_med", "ttb_5min_med", "vix_med"]:
    w = year_stats.loc[worst, col].mean()
    b = year_stats.loc[best, col].mean()
    print(f"    {col:22s} {w:>14.3f}      {b:>14.3f}    {b-w:>+14.3f}")
