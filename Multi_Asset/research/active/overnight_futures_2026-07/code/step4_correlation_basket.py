"""Step 4 (H6/P1) — mutual correlation of the four overnight sleeves, and whether a
defensible basket exists at EUR 13k.

Two matrices, both honest about their sample:
  (a) long CFD history, gap-excluded, exchange clock: GOLD / SILVER / WTI
      (SOYBEAN has no measurable window on the CFD - step 2b, N=13);
  (b) the 2024-2026 futures overlap, all four, on the real contracts.
Plus an effective-bets count and the pre-registered basket rule P1.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from common import (ACCOUNT_USD, CONTRACTS, NOTIONAL, OUT, REPO, cagr, hac_t, max_dd,
                    obs_per_year, sharpe, vol_target)

sys.path.insert(0, str(REPO / "yt_strategy_replications"))
from engine import stats as S  # noqa: E402

MICRO = {"GOLD": "MGC", "SILVER": "SIL", "WTI": "MCL", "SOYBEAN": "MZS"}
COST = {"GOLD": 0.66, "SILVER": 1.15, "WTI": 3.67, "SOYBEAN": 3.89}


def eff_bets(C: pd.DataFrame) -> float:
    lam = np.linalg.eigvalsh(C.to_numpy())
    lam = lam[lam > 0]
    return float(lam.sum() ** 2 / (lam ** 2).sum())


# ------------------------------------------------------------------ (a) CFD history
raw = pd.read_csv(OUT / "step3_sleeve_series.csv", index_col=0, parse_dates=True)
netA = {}
for c in raw.columns:
    w = raw[c].dropna()
    netA[c] = (vol_target(w) * w - vol_target(w).abs() * COST[c] * 1e-4).dropna()
A = pd.DataFrame(netA).dropna()
CA = A.corr()
print("=== (a) net sleeve correlation, long CFD history (gap-excluded, exchange clock) ===")
print(f"common days N={len(A)}  {A.index.min().date()} -> {A.index.max().date()}")
print(CA.round(3).to_string())
print(f"average pairwise corr = {CA.to_numpy()[np.triu_indices(len(CA), 1)].mean():.3f}")
print(f"effective bets = {eff_bets(CA):.2f} of {len(CA)}")
CA.to_csv(OUT / "step4_corr_cfd.csv")

# ------------------------------------------------------------- (b) futures overlap
fut = pd.read_csv(OUT / "step2_futures_daily.csv", index_col=0, parse_dates=True)
B = fut.pivot_table(index=fut.index, columns="sleeve", values="window_cap").dropna()
CB = B.corr()
print("\n=== (b) raw window correlation on the REAL contracts, 2024-2026 overlap ===")
print(f"common sessions N={len(B)}")
print(CB.round(3).to_string())
print(f"average pairwise corr = {CB.to_numpy()[np.triu_indices(len(CB), 1)].mean():.3f}")
print(f"effective bets = {eff_bets(CB):.2f} of {len(CB)}")
CB.to_csv(OUT / "step4_corr_futures.csv")

# --------------------------------------------------- seasonal check: January corr
jan = A[A.index.month == 1]
if len(jan) > 100:
    print(f"\n=== January-only correlation (N={len(jan)}) — the inventory's 0.86 claim ===")
    print(jan.corr().round(3).to_string())
    jan.corr().to_csv(OUT / "step4_corr_january.csv")

# ------------------------------------------------------- basket rule P1 evaluation
print("\n=== P1 basket rule ===")
print("P1 requires: >=2 sleeves individually PASS, mutual corr < 0.35, N_eff >= 2.0,")
print("             sum of margins <= 60% of account.")
perf = pd.read_csv(OUT / "step3_performance.csv")
base = perf[perf["cost_case"] == "net_base"].set_index("sleeve")
print(base[["SR", "t_hac", "DSR", "WF", "maxDD_pct"]].to_string())
passing = [s for s in base.index
           if base.loc[s, "SR"] >= 0.70 and base.loc[s, "t_hac"] >= 2.5
           and base.loc[s, "DSR"] >= 0.50]
print(f"\nsleeves clearing the statistical PASS thresholds at base cost: {passing}")
marg = {s: CONTRACTS[MICRO[s]]["margin"] for s in base.index}
print("margin at 1 contract:", {k: f'{v} ({100*v/ACCOUNT_USD:.1f}%)' for k, v in marg.items()})

# equal-risk 2-sleeve combination for reference (gold+silver), if both were tradable
if {"GOLD", "SILVER"}.issubset(A.columns):
    g, s = A["GOLD"], A["SILVER"]
    w = np.array([1 / g.std(), 1 / s.std()]); w = w / w.sum()
    comb = w[0] * g + w[1] * s
    print(f"\nreference equal-risk GOLD+SILVER (ignoring SILVER's step-0 rejection): "
          f"SR={sharpe(comb):.3f} vs GOLD alone {sharpe(g):.3f}, corr={g.corr(s):.3f}")

# ------------------------------------- GOLD detail: recent regime + no-winsor check
print("\n=== GOLD: sub-period stability at base cost (0.66 bps RT) ===")
g = A["GOLD"]
for lab, seg in (("2007-2013", g[g.index < "2014"]), ("2014-2019", g[(g.index >= "2014") & (g.index < "2020")]),
                 ("2020-2026", g[g.index >= "2020"]),
                 ("2024-03+ (futures overlap)", g[g.index >= "2024-03-07"])):
    if len(seg) < 100:
        continue
    mu, t = hac_t(seg)
    print(f"  {lab:28s} N={len(seg):5d}  SR={sharpe(seg):5.2f}  t={t:5.2f}  "
          f"mean={1e4*seg.mean():5.2f}bp  maxDD={100*max_dd(seg):6.1f}%")

print("\n=== GOLD: account-level outcome by contract count ($15,000) ===")
notional, marg = NOTIONAL["MGC"], CONTRACTS["MGC"]["margin"]
ppy = obs_per_year(g)
for n in (1, 2, 3):
    lev = n * notional / ACCOUNT_USD
    acct = g * lev
    print(f"  {n} MGC  lev={lev:5.2f}x  margin={100*n*marg/ACCOUNT_USD:5.1f}%  "
          f"vol={100*acct.std(ddof=1)*np.sqrt(ppy):5.1f}%  CAGR={100*cagr(acct):6.1f}%  "
          f"maxDD={100*max_dd(acct):6.1f}%  growth_SR2/2={100*sharpe(g)**2/2*(2*(lev/(sharpe(g)/ (g.std(ddof=1)*np.sqrt(ppy))))-(lev/(sharpe(g)/(g.std(ddof=1)*np.sqrt(ppy))))**2):.1f}%")
