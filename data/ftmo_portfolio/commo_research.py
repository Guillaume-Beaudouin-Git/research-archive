"""Commodity sleeve research — Phase A: variant table (iterations 1-12).
Frozen trend spec (blend {60,120,250}, theta 0.34, carry-adj via signed swap).
Costs: per-instrument measured RT bps (own M1 spreads + slip + 0 comm) at
x1.0 (worst) and x0.5 (FTMO-optimistic, demo-conditional). Swap from specs;
SUGAR/COTTON = softs-median markup; NGAS = USOIL-like (flagged, stress wide).
Weekly variants rebalance Fridays only. LO = positions clipped >= 0.
Outputs: net SR full/2019+, corr to existing challenge book, ann turnover.
"""
import numpy as np
import pandas as pd
import config as C
from sleeves import tsmom_signal, realized_vol

px = pd.read_parquet(C.CACHE / "panel_px.parquet")
rets = pd.read_parquet(C.CACHE / "panel_rets.parquet")
swap_L = pd.read_parquet(C.CACHE / "panel_swapL.parquet")
swap_S = pd.read_parquet(C.CACHE / "panel_swapS.parquet")
mult = pd.read_parquet(C.CACHE / "panel_mult.parquet")
rt = pd.read_csv(C.OUT / "phase0_rt_cost_bps.csv", index_col=0).iloc[:, 0]

# add NGAS from cache
ng = pd.read_parquet(C.CACHE / "NGAS_daily_cet.parquet")
ng = ng[ng["n_bars"] > 100]
px["NGAS"] = ng["close"].reindex(px.index)
rets["NGAS"] = px["NGAS"].pct_change(fill_method=None).clip(-0.3, 0.3)
rt["NGAS"] = float(np.nanmedian(ng["spread_med_bps"].tail(750))) + 2.0
swap_L["NGAS"] = swap_L["USOIL"]; swap_S["NGAS"] = swap_S["USOIL"]
mult["NGAS"] = mult["USOIL"]

# existing challenge book proxy (for corr)
sl = pd.read_parquet(C.CACHE / "phase1c_sleeves.parquet")
orb = pd.read_parquet(C.CACHE / "orb_e7_Rera.parquet")["R"]
book = (0.5 * sl["gold"].fillna(0) + 0.5 * sl["J1"].fillna(0)
        + 0.6 * sl["overnight"].fillna(0)
        + 0.0025 * orb.reindex(sl.index).fillna(0.0))

SOFTS = ["COCOA", "COFFEE", "SUGAR", "COTTON", "SOYBEAN"]
ENERGY = ["UKOIL", "USOIL"]


def sleeve(syms, lo=False, weekly=False, cost_mul=1.0, theta=0.34, start="2018-06-01"):
    pos = pd.DataFrame(0.0, index=rets.index, columns=syms)
    for s in syms:
        carry = swap_L[s]
        sig = tsmom_signal(px[s].dropna(), theta=theta, carry_daily_bps=carry).reindex(rets.index)
        rv = realized_vol(rets[s]).clip(lower=1e-4)
        pos[s] = sig * (0.10 / rv).clip(upper=5.0)
    pos = pos / max(len(syms), 1)
    if lo:
        pos = pos.clip(lower=0.0)
    pos = pos.shift(1)
    if weekly:
        wk = pd.Series(pos.index.dayofweek == 4, index=pos.index)
        pos = pos.where(wk, np.nan).ffill()
    raw = (pos * rets[syms]).sum(axis=1)
    bvol = raw.rolling(60).std().shift(1) * np.sqrt(252)
    scale = (0.10 / bvol.clip(lower=1e-4)).clip(upper=10.0)
    pos = pos.mul(scale, axis=0).clip(lower=-1.5, upper=1.5)
    gross = (pos * rets[syms]).sum(axis=1)
    turn = pos.diff().abs()
    tc = (turn * (rt[syms] * cost_mul / 2 / 1e4)).sum(axis=1)
    sw = pd.DataFrame({s: pos[s].abs() * np.where(pos[s] > 0, swap_L[s],
                       np.where(pos[s] < 0, swap_S[s], 0)) / 1e4 * mult[s]
                       for s in syms}).sum(axis=1)
    net = (gross - tc + sw).loc[start:]
    ann_turn = turn.sum(axis=1).loc[start:].mean() * 252
    return net, ann_turn


def stats(net, ann_turn, tag):
    r = net.dropna()
    sr = r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else np.nan
    r19 = r.loc["2019-01-01":]
    sr19 = r19.mean() / r19.std() * np.sqrt(252) if r19.std() > 0 else np.nan
    co = r.corr(book.reindex(r.index))
    print(f"{tag:42s} SR={sr:+.2f} SR19+={sr19:+.2f} corr_book={co:+.2f} turn={ann_turn:.0f}x/an")
    return sr


if __name__ == "__main__":
    n = 0
    variants = [
        ("It1  softs 2-sided daily", SOFTS, False, False),
        ("It2  softs LO daily", SOFTS, True, False),
        ("It3  softs 2-sided weekly", SOFTS, False, True),
        ("It4  softs LO weekly", SOFTS, True, True),
        ("It5  energy 2-sided weekly", ENERGY, False, True),
        ("It6  energy LO weekly", ENERGY, True, True),
        ("It7  NGAS 2-sided weekly", ["NGAS"], False, True),
        ("It8  NGAS LO weekly", ["NGAS"], True, True),
        ("It9  XAG 2-sided daily", ["XAGUSD"], False, False),
        ("It10 all-commo 2-sided weekly", SOFTS + ENERGY + ["NGAS", "XAGUSD"], False, True),
    ]
    for tag, syms, lo, wk in variants:
        n += 1
        for cm in (1.0, 0.5):
            net, t = sleeve(syms, lo, wk, cost_mul=cm)
            stats(net, t, f"{tag} cost x{cm}")
    print(f"\n[itérations consommées: {n}]")
