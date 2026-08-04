"""Q1 — L38 orthogonality: is J1 anything other than long USDJPY beta?
Q2 — edge of the 12-1 signal: SR, t_HAC(6), DSR, walk-forward by era.
Q3 — the disjoint SHORT leg at ZERO cost (L25).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, "<HOME>/Desktop/Algo_claude")
from j1_lib import (load_panels, j1_weights, sleeve_returns, sharpe, t_hac,
                    hac_reg, block_bootstrap_ci, RT_BPS_USDJPY_ALLIN)
from dsr import deflated_sharpe_ratio, estimate_std_sr_trials, sampling_noise_floor_sr

px, rets, sL, sS, mu, rt = load_panels()
START = "2013-10-01"     # engine.load_market default start

g_l, n_l, w_l = sleeve_returns(px, rets, sL, sS, mu, "long", RT_BPS_USDJPY_ALLIN)
g_u, n_u, w_u = sleeve_returns(px, rets, sL, sS, mu, "uncond", RT_BPS_USDJPY_ALLIN)
g_s, n_s, w_s = sleeve_returns(px, rets, sL, sS, mu, "short", RT_BPS_USDJPY_ALLIN)
g0_s, _, _ = sleeve_returns(px, rets, sL, sS, mu, "short", 0.0, swaps=False)
g0_l, _, _ = sleeve_returns(px, rets, sL, sS, mu, "long", 0.0, swaps=False)

sl = slice(START, None)
mask = w_l.reindex(px.index).notna() & px["USDJPY"].notna()
idx = px.loc[sl].index
idx = idx[px["USDJPY"].loc[sl].notna()]

R = pd.DataFrame({"j1_gross": g_l, "j1_net": n_l, "bh_gross": g_u, "bh_net": n_u,
                  "short_gross0": g0_s, "long_gross0": g0_l,
                  "w_long": w_l, "w_uncond": w_u, "w_short": w_s}).loc[idx]
R = R.dropna(subset=["j1_gross"])

print("=" * 78)
print("SAMPLE:", R.index[0].date(), "->", R.index[-1].date(), " N =", len(R))
print("=" * 78)

# ---------------------------------------------------------------- Q1 : L38
print("\n### Q1 — L38 ORTHOGONALITY REGRESSION (HAC lag 6)")
for tag, y, x in [("GROSS", R["j1_gross"], R["bh_gross"]),
                  ("NET(all-in 1.86bps + swaps)", R["j1_net"], R["bh_net"])]:
    m, cols, d = hac_reg(y, x.to_frame("bh"))
    a, b = m.params
    print(f"\n{tag}: N={int(m.nobs)}")
    print(f"  alpha = {a*252*100:+.3f} %/yr   t_HAC = {m.tvalues[0]:+.2f}   p = {m.pvalues[0]:.3f}")
    print(f"  beta  = {b:.4f}              t_HAC = {m.tvalues[1]:+.2f}")
    print(f"  R^2   = {m.rsquared*100:.1f} %   -> {'NOT orthogonal (>30%)' if m.rsquared>0.30 else 'orthogonal'}")

# duty cycle / signal agreement
on = (R["w_long"] > 0)
print(f"\n  duty cycle (days long)     : {on.mean()*100:.1f} %")
print(f"  sign(sleeve w) == sign(bh w): {(R['w_long'].gt(0) == R['w_uncond'].gt(0)).mean()*100:.1f} %")

# ---------------------------------------------------------------- Q2 : edge
print("\n### Q2 — EDGE OF THE 12-1 SIGNAL")
def line(tag, r, ppy=252):
    r = pd.Series(r).dropna()
    lo, hi = block_bootstrap_ci(r, lambda x: x.mean()/x.std(ddof=1)*np.sqrt(ppy), n=1500)
    print(f"  {tag:<34} SR {sharpe(r):+.3f}  t_HAC {t_hac(r):+.2f}  "
          f"boot95 [{lo:+.2f},{hi:+.2f}]  ann {r.mean()*252*100:+.2f}%/yr")
    return sharpe(r)

sr_g = line("J1 GROSS (cost 0)", R["long_gross0"])
sr_n = line("J1 NET (1.86bps + swap)", R["j1_net"])
line("BH vol-targeted long (gross)", R["bh_gross"])
line("BH vol-targeted long (net)", R["bh_net"])
line("SPREAD J1 - BH (gross)", R["j1_gross"] - R["bh_gross"])

# --- eras (L31: JPY carry regime + 2022-24 unwind)
print("\n  ERAS (net):")
eras = {"pre-2021 (2013-10..2020-12)": ("2013-10-01", "2020-12-31"),
        "post-2021 (2021-01..)":       ("2021-01-01", None),
        "2022-2024 unwind window":     ("2022-01-01", "2024-12-31"),
        "EX 2022-2024":                None}
for k, v in eras.items():
    if v is None:
        r = R["j1_net"][~R.index.to_series().between("2022-01-01", "2024-12-31")]
        rb = R["bh_net"][~R.index.to_series().between("2022-01-01", "2024-12-31")]
    else:
        r = R["j1_net"].loc[v[0]:v[1]]
        rb = R["bh_net"].loc[v[0]:v[1]]
    print(f"    {k:<30} N={len(r):>4}  SR {sharpe(r):+.3f}  t_HAC {t_hac(r):+.2f}"
          f"   | BH SR {sharpe(rb):+.3f}")

# --- walk-forward: 5 expanding folds, sign of OOS SR
print("\n  WALK-FORWARD (5 expanding folds, OOS net SR):")
n = len(R)
cuts = [int(n * f) for f in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)]
pos = 0
for i in range(5):
    oos = R["j1_net"].iloc[cuts[i]:cuts[i+1]]
    b = R["bh_net"].iloc[cuts[i]:cuts[i+1]]
    s = sharpe(oos)
    pos += s > 0
    print(f"    fold {i+1} {oos.index[0].date()}..{oos.index[-1].date()} "
          f"N={len(oos):>3}  SR {s:+.3f}  | BH {sharpe(b):+.3f}")
print(f"    -> WF hit rate = {pos}/5 = {pos/5*100:.0f} %   (gate: >60% PROPFIRM_PASS)")

# --- DSR
print("\n  DSR (rf=0, orthogonal to WF):")
fam = [sr_g, sr_n, sharpe(R["bh_net"]), sharpe(R["short_gross0"])]
for ntr in (4, 30, 321):
    sd = estimate_std_sr_trials(fam, periods_per_year=252, n_obs=len(R))
    out = deflated_sharpe_ratio(R["j1_net"].values, n_trials=ntr, periods_per_year=252,
                                std_sr_trials=sd, rf=0.0)
    print(f"    n_trials={ntr:>4}  std_sr_trials={sd:.3f}  SR={out['sharpe']:+.3f} "
          f" bench={out['sr_benchmark']:.3f}  DSR={out['dsr']:.4f}  "
          f"skew={out['skewness']:+.2f} exkurt={out['excess_kurtosis']:.2f} pass={out['passed']}")
og = deflated_sharpe_ratio(R["long_gross0"].values, n_trials=321, periods_per_year=252,
                           std_sr_trials=sd, rf=0.0)
print(f"    GROSS (cost 0), n_trials=321: DSR={og['dsr']:.4f}")
print(f"    sampling noise floor SR = "
      f"{sampling_noise_floor_sr(n_obs=len(R), periods_per_year=252):.3f}")

# ---------------------------------------------------------------- Q3 : short
print("\n### Q3 — DISJOINT SHORT LEG at ZERO COST (L25)")
sdays = R["w_short"] < 0
ldays = R["w_long"] > 0
print(f"  long days {ldays.sum()} | short days {sdays.sum()} | "
      f"overlap {int((sdays & ldays).sum())} (must be 0)")
for tag, r in [("SHORT leg gross, cost 0, swap 0", R["short_gross0"]),
               ("LONG  leg gross, cost 0, swap 0", R["long_gross0"])]:
    r2 = pd.Series(r).dropna()
    print(f"  {tag:<34} SR {sharpe(r2):+.3f}  t_HAC {t_hac(r2):+.2f}  "
          f"ann {r2.mean()*252*100:+.2f}%/yr  N_active {(r2!=0).sum()}")
# conditional mean of USDJPY return on short days vs long days
rj = rets["USDJPY"].reindex(R.index)
print(f"  E[USDJPY ret | mom>0] = {rj[ldays].mean()*1e4:+.2f} bps/d  (N={ldays.sum()})")
print(f"  E[USDJPY ret | mom<0] = {rj[sdays].mean()*1e4:+.2f} bps/d  (N={sdays.sum()})")
print(f"  E[USDJPY ret] uncond  = {rj.mean()*1e4:+.2f} bps/d  <- L58 baseline")

R.to_parquet("<SCRATCH>"
             "908bf995-6a3c-4956-9bcd-f38fe0bb9fb3/scratchpad/j1cache/j1_returns.parquet")
print("\n[cached -> scratchpad/j1cache/j1_returns.parquet]")
