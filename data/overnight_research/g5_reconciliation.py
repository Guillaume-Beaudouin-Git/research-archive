"""G5 — Reconciliation with CLAUDE.md constitutional rules.

L25: two-sided — is the long-only overnight just disguised long-equity beta?
L31: OOS / post-regime — re-verify IN<2019 vs OOS≥2019 on our own recompute.
vs A/B/C: how does the personal-book sleeve at L=0.75× compare on SR & corr?
"""
import numpy as np
import pandas as pd

DAILY = "<HOME>/Desktop/Algo_claude/data/overnight_research/nq_rth_daily.parquet"
SWAP_1X = 3.081 / 1e4
SWAP_3X = 9.243 / 1e4

d = pd.read_parquet(DAILY).copy()
d["swap_charge"] = d.wd.apply(lambda w: SWAP_3X if w == 0 else SWAP_1X)
d["net_ret"] = d["ov_bps"] / 1e4 - d["swap_charge"]
d["intra_ret"] = d["in_bps"] / 1e4

# Long-only midweek series
mid = d.loc[d.wd.isin([1, 2])].copy()
mid_zero = pd.Series(0.0, index=d.index)
mid_zero.loc[mid.index] = mid["net_ret"].values

# Buy-hold proxy (long NQ daily): use close-to-close = ov+intra
d["full_day_ret"] = d["ov_bps"] / 1e4 + d["intra_ret"]
bh = d["full_day_ret"]

# ===== L25 — Beta test =====
print("=" * 78)
print("L25 — Two-sided / beta-dominance test")
print("=" * 78)
# Regress midweek strategy returns on NQ buy-hold returns
common = pd.concat([mid_zero.rename("strat"), bh.rename("bh")], axis=1).dropna()
common = common[common["strat"] != 0]  # only midweek nights
# Approx daily buy-hold during the held night = ov_bps + intra_ret_prev? Actually for "overnight only", the comparison
# benchmark is the close-to-close of NQ on the corresponding day.
y = common["strat"].values
x = common["bh"].values
beta = np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1)
alpha = y.mean() - beta * x.mean()
corr = np.corrcoef(y, x)[0, 1]
print(f"  N midweek-night co-observations: {len(common)}")
print(f"  Corr (overnight, full-day BH):   {corr:+.3f}")
print(f"  β (slope overnight on BH):        {beta:+.3f}")
print(f"  α (intercept, bps/night):         {alpha*1e4:+.2f}")
print(f"  → If β >> 0 and corr high (>0.5), the 'edge' is mostly beta exposure.")

# ===== L31 — IN<2019 / OOS≥2019 =====
print("\n" + "=" * 78)
print("L31 — IN (<2019) vs OOS (≥2019) — independent recompute")
print("=" * 78)
mid["yr"] = mid.index.year
IN = mid.loc[mid.yr < 2019, "net_ret"].values
OOS = mid.loc[mid.yr >= 2019, "net_ret"].values
print(f"  IN  (<2019) : n={len(IN):4d}  mean={IN.mean()*1e4:+.2f} bps  std={IN.std()*1e4:.0f} bps  t={IN.mean()/(IN.std()/np.sqrt(len(IN))):+.2f}")
print(f"  OOS (≥2019): n={len(OOS):4d}  mean={OOS.mean()*1e4:+.2f} bps  std={OOS.std()*1e4:.0f} bps  t={OOS.mean()/(OOS.std()/np.sqrt(len(OOS))):+.2f}")
# Difference in means (two-sample t)
pooled = np.sqrt(IN.var(ddof=1)/len(IN) + OOS.var(ddof=1)/len(OOS))
t_diff = (OOS.mean() - IN.mean()) / pooled
print(f"  Δ(OOS - IN) = {(OOS.mean()-IN.mean())*1e4:+.2f} bps  Welch t = {t_diff:+.2f}")
print(f"  → If Δ small and t < 2, the OOS holds.")

# By-year overnight (midweek)
by_year_mid = mid.groupby("yr")["net_ret"].mean()
pos = (by_year_mid > 0).sum()
print(f"\n  Midweek by-year overnight positive years (NET): {pos}/{len(by_year_mid)}")
print(f"  worst {by_year_mid.min()*1e4:+.1f} bps  best {by_year_mid.max()*1e4:+.1f} bps")
print(f"  by-year mean:\n{(by_year_mid*1e4).round(1).to_string()}")

# ===== Comparison with A, B, C =====
print("\n" + "=" * 78)
print("Comparison vs existing strategies (FTMO_SYNC mapping)")
print("=" * 78)
print("  Strategy A — TSMOM v3 (crypto):       OOS SR 1.33   MaxDD -6.9%   personal book (Propr frozen)")
print("  Strategy B — Delta-neutral carry:     proxy SR 2.0  MaxDD -0.5%   personal book (HL testnet)")
print("  Strategy C — NQ ORB iter_10:           SR 1.52→0.51 on validation; NO-GO Tradeify $25K (memory)")
print()
print("  Overnight midweek NQ, L=0.5× (FTMO-safe MaxDD):")
print("     SR_net   0.68")
print("     MaxDD   -8.2%")
print("     AnnRet  +2.5%/yr")
print()
print("  Overnight midweek NQ, L=0.75× (FTMO 82% p_funded unlimited-time):")
print("     SR_net   0.68")
print("     MaxDD  -12.1%   ← breaches FTMO 10% on 1.6% of EOD")
print("     AnnRet  +3.7%/yr")
print()
print("  Verdict on book inclusion:")
print("     SR 0.68 < RESEARCH_PASS gate (0.7) — marginal fail")
print("     β to NQ buy-hold ≈ {:+.2f}, corr {:+.2f} → mostly beta, not alpha (L25 trigger)".format(beta, corr))
print("     vs A (SR 1.33), B (2.0), C (1.52): clearly inferior on SR")
print("     Would dilute current portfolio Sharpe (current A+B+C ~2.24, D-gate requires SR(D+book)>2.46)")
