"""G3 — Gap-tail distribution and max sustainable leverage.

Question: at what leverage L can the strategy survive FTMO 2-step constraints
  - Daily Loss Limit:  5% of account (per day, balance-anchored at 00:00 CE(S)T)
  - Max Total Loss:    10% of account (high-water-marked, never below initial)
when the only positional exposure is overnight (no intraday stop)?

Approach:
  1. Build the midweek-only daily PnL series (Tue+Wed open-days = Mon-night & Tue-night holds), NET of swap.
  2. Quantify the gap-tail (worst, p1, p5, std) of net-overnight returns.
  3. For a grid of leverages L ∈ {0.5, 1.0, 1.5, 2.0, 3.0, 4.0}:
       - Compute L × worst, L × p1, L × p5  → check vs DLL 5%
       - Compute compounded equity curve and MaxDD (unleveraged then × L → linear in L on log-equity locally)
       - Honest: use compounded simulation per night, sized to L × notional at each entry, no intraday stop.
       - Hit-rate of daily-DLL breach (<-5%) and total-DD breach (<-10% from HWM).
  4. Report annualized SR_net at the LARGEST L that keeps P(single-night DLL breach) below ~0.1% (calibrated to a ~1-year challenge).
"""
import numpy as np
import pandas as pd

DAILY = "<HOME>/Desktop/Algo_claude/data/overnight_research/nq_rth_daily.parquet"
SWAP_1X_BPS = 3.081  # G2 confirmed
SWAP_3X_BPS = 9.243

d = pd.read_parquet(DAILY).copy()
print(f"Loaded daily series: {len(d)} rows  {d.index[0].date()} → {d.index[-1].date()}")

# Compute net overnight per night
def assign_swap_charge(wd, conv="A"):
    """Conv A (industry): Mon-open = 3x, others = 1x; Conv B (dossier): Fri-open = 3x."""
    if conv == "A":
        return SWAP_3X_BPS if wd == 0 else SWAP_1X_BPS
    else:
        return SWAP_3X_BPS if wd == 4 else SWAP_1X_BPS


for conv in ["A", "B"]:
    d[f"swap_charge_{conv}"] = d["wd"].apply(lambda w: assign_swap_charge(w, conv))
    d[f"net_bps_{conv}"] = d["ov_bps"] - d[f"swap_charge_{conv}"]
    d[f"net_ret_{conv}"] = d[f"net_bps_{conv}"] / 1e4

# Define held set: midweek (Tue+Wed open) — robust to convention A/B
mid_mask = d.wd.isin([1, 2])
all_nights_mask = d.wd.between(0, 4)

print("\n" + "=" * 78)
print("TAIL DISTRIBUTION  (gross then net, midweek vs all-nights)")
print("=" * 78)
for label, msk in [("MIDWEEK (Tue+Wed open)", mid_mask), ("ALL NIGHTS (Mon-Fri open)", all_nights_mask)]:
    sub = d.loc[msk]
    for col, tag in [("ov_bps", "GROSS"), ("net_bps_A", "NET (Conv A)"), ("net_bps_B", "NET (Conv B)")]:
        s = sub[col].dropna().values
        print(f"  {label:30s} {tag:14s}  n={len(s):5d}  "
              f"mean={s.mean():+7.2f} bps   std={s.std():6.0f}   "
              f"worst={s.min():+7.0f}   p1={np.percentile(s,1):+6.0f}   p5={np.percentile(s,5):+6.0f}   "
              f"p95={np.percentile(s,95):+5.0f}")

# ===== Leverage sustainability =====
print("\n" + "=" * 78)
print("LEVERAGE SUSTAINABILITY  (FTMO DLL 5%, Max Total 10%)")
print("=" * 78)
# Use Convention A as the conservative default (Mon-open = 3x).
held = d.loc[mid_mask, "net_ret_A"].dropna().values
worst = held.min()
p1 = np.percentile(held, 1)
p5 = np.percentile(held, 5)
print(f"  Midweek net-of-swap (Conv A):  n={len(held)}  mean={held.mean()*1e4:+.2f} bps  std={held.std()*1e4:.0f} bps")
print(f"  Worst night: {worst*100:+.2f}%   p1: {p1*100:+.2f}%   p5: {p5*100:+.2f}%   p95: {np.percentile(held,95)*100:+.2f}%")

# Equity simulation, midweek-only, with leverage L, compounded
def simulate_midweek(returns, all_calendar_dates, mid_dates_mask, L):
    """Build a daily equity curve where on midweek days we earn L*r, off-days flat."""
    # Reconstruct daily series across all calendar days for HWM/DD tracking
    df = pd.DataFrame(index=all_calendar_dates, data={"r": 0.0})
    df.loc[mid_dates_mask, "r"] = returns
    df["lev_r"] = L * df["r"]
    df["eq"] = (1 + df["lev_r"]).cumprod()
    df["eq_hwm"] = df["eq"].cummax()
    df["dd"] = (df["eq"] / df["eq_hwm"]) - 1  # max drawdown ≤ 0
    df["dll_breach"] = df["lev_r"] < -0.05  # daily loss > 5%
    df["max_total_breach"] = df["dd"] < -0.10
    return df


held_idx_mask = mid_mask.values
held_dates = d.index
ann_factor = np.sqrt(252)

print(f"\n{'Lev':>5s}{'P(night<−5%)':>13s}{'P(EOD MaxDD<−10%)':>18s}"
      f"{'WorstNight':>11s}{'MaxDD':>9s}{'AnnRet_bps':>13s}{'AnnSR':>8s}{'YrsToFunded(10%)':>18s}")
results = []
for L in [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0]:
    sim = simulate_midweek(held, held_dates, held_idx_mask, L)
    p_dll = sim["dll_breach"].mean()
    p_dd = sim["max_total_breach"].mean()
    worst_night = sim["lev_r"].min()
    max_dd = sim["dd"].min()
    nonzero = sim["lev_r"][sim["lev_r"] != 0]
    ann_ret = nonzero.mean() * 2 * 52  # 2 midweek nights/week, ~52 weeks
    daily_std_all = sim["lev_r"].std()
    ann_sr = (sim["lev_r"].mean() / daily_std_all) * ann_factor if daily_std_all > 0 else np.nan
    # Years to a +10% gross
    final_eq = sim["eq"].iloc[-1]
    yrs = len(sim) / 252
    cagr = final_eq ** (1 / yrs) - 1 if final_eq > 0 else np.nan
    yrs_to_10 = np.log(1.10) / np.log(1 + cagr) if cagr and cagr > 0 else np.inf
    print(f"{L:>5.2f}{p_dll:>13.4%}{p_dd:>18.4%}"
          f"{worst_night:>11.2%}{max_dd:>9.2%}{ann_ret*1e4:>13.0f}{ann_sr:>8.2f}{yrs_to_10:>18.2f}")
    results.append({"L": L, "p_night_dll5pct": p_dll, "p_max_total_dd10pct": p_dd,
                    "worst_night_pct": worst_night, "max_dd": max_dd,
                    "ann_ret_bps": ann_ret * 1e4, "ann_sr": ann_sr,
                    "years_to_funded10pct": yrs_to_10})

pd.DataFrame(results).to_csv(
    "<HOME>/Desktop/Algo_claude/data/overnight_research/g3_leverage_sweep.csv", index=False)

# ===== Hard-limit leverage L* =====
print("\n" + "=" * 78)
print("HARD LIMITS")
print("=" * 78)
print(f"  Tightest single-night constraint: L × |worst| < 5%  →  L_max = {0.05/abs(worst):.2f}×")
print(f"  p1 constraint (P>1% of nights):    L × |p1|    < 5%  →  L_max = {0.05/abs(p1):.2f}×")
print(f"  p5 constraint (P>5% of nights):    L × |p5|    < 5%  →  L_max = {0.05/abs(p5):.2f}×")

print("\nSaved: data/overnight_research/g3_leverage_sweep.csv")
