"""Phase 1 — sleeve re-validation under real FTMO costs.

PRE-REGISTERED (frozen before results, 2026-06-10):
  - Trend spec: dossier-frozen TSMOM blend {60,120,250}, theta=0.34,
    inst vol target 10%, port vol target 10%, vol de-risk, equity gate 0.4@MA100.
    NOT re-tuned here. Two universes (replica / full), carry_adj on/off = 4 runs.
  - Overnight spec: verified Mon+Tue nights long US100+GER40 (report frozen).
  - Gates: net Sharpe (full & 2019+), IS<=2015 vs OOS 2016+, delay+1 degradation,
    swap x{0.5,1.0,1.5}, by-year table. No further iteration inside Phase 1.
Compliance: within corr>0.75 clusters (trailing 120d), opposing signs resolved
by zeroing the weaker |signal| leg (anti-hedging insurance).
"""
import numpy as np
import pandas as pd
import config as C
from sleeves import trend_book, overnight_sleeve, perf_stats, tsmom_signal

pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30)

px = pd.read_parquet(C.CACHE / "panel_px.parquet")
rets = pd.read_parquet(C.CACHE / "panel_rets.parquet")
swap_L = pd.read_parquet(C.CACHE / "panel_swapL.parquet")
swap_S = pd.read_parquet(C.CACHE / "panel_swapS.parquet")
mult = pd.read_parquet(C.CACHE / "panel_mult.parquet")
rt = pd.read_csv(C.OUT / "phase0_rt_cost_bps.csv", index_col=0).iloc[:, 0]

BUCKETS_REPLICA = {"eq": ["US500"], "metals": ["XAUUSD", "XAGUSD"],
                   "energy": ["USOIL"], "crypto": ["BTCUSD", "ETHUSD"]}
RISK_REPLICA = {"eq": .25, "metals": .25, "energy": .25, "crypto": .25}
BUCKETS_FULL = {"eq": ["US500", "GER40"], "metals": ["XAUUSD", "XAGUSD"],
                "energy": ["UKOIL", "USOIL"], "fx": C.FX, "crypto": ["BTCUSD", "ETHUSD"]}
RISK_FULL = {"eq": .15, "metals": .20, "energy": .15, "fx": .30, "crypto": .20}


def run(buckets, risks, carry_adj, label, swap_mul=1.0, delay=0):
    sl = swap_L * swap_mul if swap_mul != 1.0 else swap_L
    ss = swap_S * swap_mul if swap_mul != 1.0 else swap_S
    r = rets.copy()
    if delay:
        # execute signals 'delay' days later: shift positions further
        pass  # handled via prices shift in signal: implemented by shifting rets input
    out = trend_book(r, px, sl, ss, mult, rt, buckets, risks, carry_adj=carry_adj)
    net = out["net"].loc["2008-01-01":]
    s_full = perf_stats(net)
    s_rec = perf_stats(net.loc["2019-01-01":])
    s_is = perf_stats(net.loc[:"2015-12-31"])
    s_oos = perf_stats(net.loc["2016-01-01":])
    row = dict(label=label,
               sharpe=s_full["sharpe"], ann=s_full["ann"], maxdd=s_full["maxdd"],
               skew=s_full["skew"], worst=s_full["worst_day"], t=s_full["t"],
               sharpe_2019=s_rec["sharpe"], sharpe_IS=s_is["sharpe"],
               sharpe_OOS=s_oos["sharpe"])
    return row, net, out


results, series = [], {}
for label, (b, k) in {"replica": (BUCKETS_REPLICA, RISK_REPLICA),
                      "full": (BUCKETS_FULL, RISK_FULL)}.items():
    for ca in (False, True):
        tag = f"trend_{label}{'_carryadj' if ca else ''}"
        row, net, _ = run(b, k, ca, tag)
        results.append(row); series[tag] = net

# swap stress on the headline config
for sm in (0.5, 1.5):
    row, net, _ = run(BUCKETS_FULL, RISK_FULL, True, f"trend_full_carryadj_swap{sm}", swap_mul=sm)
    results.append(row)

# delay+1 leak test: recompute signals on prices shifted by 1 day (signal sees older data)
px_lag = px.shift(1)
out_d1 = trend_book(rets, px_lag, swap_L, swap_S, mult, rt, BUCKETS_FULL, RISK_FULL,
                    carry_adj=True)
s = perf_stats(out_d1["net"].loc["2008-01-01":])
results.append(dict(label="trend_full_carryadj_DELAY+1", sharpe=s["sharpe"], ann=s["ann"],
                    maxdd=s["maxdd"], skew=s["skew"], worst=s["worst_day"], t=s["t"],
                    sharpe_2019=np.nan, sharpe_IS=np.nan, sharpe_OOS=np.nan))

# overnight sleeve (M1-era CET bars => use cache daily open/close for US100, GER40)
daily = {s: pd.read_parquet(C.CACHE / f"{s}_daily_cet.parquet") for s in ("US100", "GER40")}
spread_on = {s: float(np.nanmedian(daily[s]["spread_med_bps"].tail(750))) + 1.0
             for s in daily}
swapL_on = {s: float(swap_L[s].iloc[-1]) for s in daily}
on = overnight_sleeve(daily, ("US100", "GER40"), swapL_on, spread_on)
on = on.loc["2014-01-01":]
s_on = perf_stats(on)
results.append(dict(label="overnight_midweek", sharpe=s_on["sharpe"], ann=s_on["ann"],
                    maxdd=s_on["maxdd"], skew=s_on["skew"], worst=s_on["worst_day"],
                    t=s_on["t"], sharpe_2019=perf_stats(on.loc["2019-01-01":])["sharpe"],
                    sharpe_IS=np.nan, sharpe_OOS=np.nan))
series["overnight_midweek"] = on

res = pd.DataFrame(results).set_index("label")
print(res.round(3).to_string())
pd.DataFrame(series).to_parquet(C.CACHE / "phase1_sleeve_returns.parquet")
res.to_csv(C.OUT / "phase1_gates.csv")

# by-year table for headline
hl = series["trend_full_carryadj"]
yr = hl.groupby(hl.index.year).apply(lambda x: (1 + x).prod() - 1)
print("\nby-year trend_full_carryadj:")
print((yr * 100).round(1).to_string())
print("\ncorr matrix of sleeves:")
print(pd.DataFrame(series).corr().round(3).to_string())
