"""Phase 1b — per-bucket decomposition + FX swap-gate variant + overnight net sleeve.

PRE-REGISTERED choices (a priori, not swept):
  - FX swap gate: hold FX position only if its direction's swap > -0.75 bps/night.
    (Rationale: refuse to pay > ~2.7%/yr carry to hold an FX trend; J1 logic.)
  - Overnight sleeve: long US100+GER40, Mon&Tue nights (Tue/Wed open-days),
    net of time-varying swap + RT spread each night. No leverage here (unit=1).
Diagnostics only otherwise; risk weights remain pre-registered.
"""
import numpy as np
import pandas as pd
import config as C
from sleeves import trend_book, perf_stats

pd.set_option("display.width", 220); pd.set_option("display.max_columns", 30)

px = pd.read_parquet(C.CACHE / "panel_px.parquet")
rets = pd.read_parquet(C.CACHE / "panel_rets.parquet")
swap_L = pd.read_parquet(C.CACHE / "panel_swapL.parquet")
swap_S = pd.read_parquet(C.CACHE / "panel_swapS.parquet")
mult = pd.read_parquet(C.CACHE / "panel_mult.parquet")
rt = pd.read_csv(C.OUT / "phase0_rt_cost_bps.csv", index_col=0).iloc[:, 0]

BUCKETS = {"eq": ["US500", "GER40"], "metals": ["XAUUSD", "XAGUSD"],
           "energy": ["UKOIL", "USOIL"], "fx": C.FX, "crypto": ["BTCUSD", "ETHUSD"]}

# --- FX swap gate: censor rets info? No: gate positions by zeroing signal via swap mask
GATE_BPS = -0.75
fx_maskL = swap_L[C.FX] > GATE_BPS     # allowed to be long
fx_maskS = swap_S[C.FX] > GATE_BPS     # allowed to be short


def run_bucket(name, syms, carry_adj=True, fx_gate=False):
    out = trend_book(rets, px, swap_L, swap_S, mult, rt,
                     {name: syms}, {name: 1.0}, carry_adj=carry_adj)
    net, pos = out["net"], out["pos"]
    if fx_gate and name == "fx":
        # post-hoc consistent re-run: zero disallowed directions then recompute costs
        posg = pos.copy()
        for s in syms:
            posg[s] = pos[s].where(~((pos[s] > 0) & ~fx_maskL[s]), 0.0)
            posg[s] = posg[s].where(~((posg[s] < 0) & ~fx_maskS[s]), 0.0)
        gross = (posg * rets[syms]).sum(axis=1)
        tc = (posg.diff().abs() * (rt[syms] / 2 / 1e4)).sum(axis=1)
        sw = pd.DataFrame({s: posg[s].abs() * np.where(posg[s] > 0, swap_L[s],
                          np.where(posg[s] < 0, swap_S[s], 0)) / 1e4 * mult[s]
                          for s in syms}).sum(axis=1)
        net = gross - tc + sw
    return net.loc["2008-01-01":]


rows, nets = [], {}
for name, syms in BUCKETS.items():
    for ca in (True, False):
        for fg in ((True, False) if name == "fx" else (False,)):
            tag = f"{name}{'_ca' if ca else ''}{'_gate' if fg else ''}"
            net = run_bucket(name, syms, ca, fg)
            st = perf_stats(net)
            st_r = perf_stats(net.loc["2019-01-01":])
            rows.append(dict(bucket=tag, sharpe=st["sharpe"], ann=st["ann"],
                             maxdd=st["maxdd"], skew=st["skew"], t=st["t"],
                             sharpe_2019=st_r["sharpe"]))
            nets[tag] = net

print(pd.DataFrame(rows).set_index("bucket").round(3).to_string())

# --- overnight net sleeve (time-varying swap, both indices, Mon+Tue nights)
ov_parts = []
for sym in ("US100", "GER40"):
    ov = pd.read_parquet(C.CACHE / f"{sym}_overnight_bps.parquet")["ov_bps"]
    ov = ov[ov.abs() < 800] / 1e4
    take = pd.Series(ov.index.dayofweek, index=ov.index).isin([1, 2])
    spr = float(np.nanmedian(pd.read_parquet(C.CACHE / f"{sym}_daily_cet.parquet")
                             ["spread_med_bps"].tail(750))) + 1.0
    swl = swap_L[sym].reindex(ov.index).ffill()
    net = (ov - (spr / 1e4) + swl / 1e4).where(take, 0.0)
    ov_parts.append(net)
on_net = pd.concat(ov_parts, axis=1).mean(axis=1).dropna()
nets["overnight_net"] = on_net
for w, lab in ((on_net, "overnight_net_full"), (on_net.loc["2019-01-01":], "overnight_net_2019+")):
    st = perf_stats(w)
    print(f"{lab}: sharpe={st['sharpe']:.2f} ann={st['ann']*100:.1f}% maxdd={st['maxdd']*100:.1f}% "
          f"skew={st['skew']:.2f} worst={st['worst_day']*100:.2f}% t={st['t']:.2f}")

co = pd.DataFrame(nets)
print("\nbucket correlations:")
print(co.corr().round(2).to_string())
co.to_parquet(C.CACHE / "phase1b_buckets.parquet")
print("\nsaved phase1b_buckets.parquet")
