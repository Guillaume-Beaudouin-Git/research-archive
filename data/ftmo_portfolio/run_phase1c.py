"""Phase 1c — final composition tests (archive-grounded variants, then FREEZE).

1. gold-only vs metals (G1 validated on gold; does XAG dilute?)
2. energy LONG-ONLY trend (structural: long swap = credit +3/+4 bps/night,
   short = -14/-19 -> two-sided was cost-doomed; long-only never archive-tested)
3. J1 exact: USDJPY TSMOM 12-1 long-only, vol-target 10% (archive spec, real swap)
4. crypto by-year (decay check)
"""
import numpy as np
import pandas as pd
import config as C
from sleeves import trend_book, perf_stats, realized_vol

pd.set_option("display.width", 200)
px = pd.read_parquet(C.CACHE / "panel_px.parquet")
rets = pd.read_parquet(C.CACHE / "panel_rets.parquet")
swap_L = pd.read_parquet(C.CACHE / "panel_swapL.parquet")
swap_S = pd.read_parquet(C.CACHE / "panel_swapS.parquet")
mult = pd.read_parquet(C.CACHE / "panel_mult.parquet")
rt = pd.read_csv(C.OUT / "phase0_rt_cost_bps.csv", index_col=0).iloc[:, 0]


def show(tag, net):
    f, r = perf_stats(net), perf_stats(net.loc["2019-01-01":])
    print(f"{tag:28s} SR={f['sharpe']:+.2f} ann={f['ann']*100:+.1f}% dd={f['maxdd']*100:.0f}% "
          f"skew={f['skew']:+.2f} t={f['t']:+.2f} | SR19+={r['sharpe']:+.2f}")
    return net


# 1) gold only vs metals
for tag, syms in {"gold_only": ["XAUUSD"], "metals_pair": ["XAUUSD", "XAGUSD"]}.items():
    out = trend_book(rets, px, swap_L, swap_S, mult, rt, {"m": syms}, {"m": 1.0}, carry_adj=True)
    show(tag, out["net"].loc["2008-01-01":])

# 2) energy long-only (positions clipped >=0, cost-consistent rerun)
out = trend_book(rets, px, swap_L, swap_S, mult, rt,
                 {"e": ["UKOIL", "USOIL"]}, {"e": 1.0}, carry_adj=True)
posL = out["pos"].clip(lower=0.0)
syms = ["UKOIL", "USOIL"]
gross = (posL * rets[syms]).sum(axis=1)
tc = (posL.diff().abs() * (rt[syms] / 2 / 1e4)).sum(axis=1)
sw = pd.DataFrame({s: posL[s].abs() * np.where(posL[s] > 0, swap_L[s], 0.0) / 1e4 * mult[s]
                   for s in syms}).sum(axis=1)
show("energy_long_only", (gross - tc + sw).loc["2008-01-01":])

# 3) J1 exact: USDJPY 12-1 LO (sign of ret[t-252 -> t-21] > 0), vol target 10%
p = px["USDJPY"].dropna()
mom = p.shift(21) / p.shift(252) - 1.0
sig = (mom > 0).astype(float)
rv = realized_vol(rets["USDJPY"]).clip(lower=1e-4)
w = (0.10 / rv).clip(upper=5.0)
pos = (sig * w).shift(1).reindex(rets.index).fillna(0.0)
grossj = pos * rets["USDJPY"]
tcj = pos.diff().abs() * (rt["USDJPY"] / 2 / 1e4)
swj = pos.abs() * np.where(pos > 0, swap_L["USDJPY"], 0.0) / 1e4 * mult["USDJPY"]
j1 = (grossj - tcj + swj).loc["2008-01-01":]
show("J1_usdjpy_12-1_LO", j1)
# swap contribution check
print(f"   J1 swap contribution: {swj.loc['2008-01-01':].sum()*100:.1f}% cum, "
      f"gross {grossj.loc['2008-01-01':].sum()*100:.1f}%")

# 4) crypto by-year
out = trend_book(rets, px, swap_L, swap_S, mult, rt,
                 {"c": ["BTCUSD", "ETHUSD"]}, {"c": 1.0}, carry_adj=True)
cn = out["net"].loc["2015-01-01":]
yr = cn.groupby(cn.index.year).apply(lambda x: (1 + x).prod() - 1)
print("crypto by-year %:", (yr * 100).round(0).astype(int).to_dict())

# save chosen sleeves for Phase 2
keep = {}
out_g = trend_book(rets, px, swap_L, swap_S, mult, rt, {"m": ["XAUUSD"]}, {"m": 1.0}, carry_adj=True)
keep["gold"] = out_g["net"]
keep["energy_LO"] = (gross - tc + sw)
keep["J1"] = (grossj - tcj + swj)
out_c = trend_book(rets, px, swap_L, swap_S, mult, rt, {"c": ["BTCUSD", "ETHUSD"]}, {"c": 1.0}, carry_adj=True)
keep["crypto"] = out_c["net"]
keep["metals_pair"] = trend_book(rets, px, swap_L, swap_S, mult, rt,
                                 {"m": ["XAUUSD", "XAGUSD"]}, {"m": 1.0}, carry_adj=True)["net"]
b = pd.read_parquet(C.CACHE / "phase1b_buckets.parquet")
keep["overnight"] = b["overnight_net"]
pd.DataFrame(keep).to_parquet(C.CACHE / "phase1c_sleeves.parquet")
print("saved phase1c_sleeves.parquet")
