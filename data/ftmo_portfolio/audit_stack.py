"""Audited data stack loader — single source of truth post-audit.
Repaired M5 (NQ-proxy 2018-21 US100), GER40 hole masked, era-costed ORB.
"""
import pandas as pd
import numpy as np
import config as C
import simulator as S


def load_audited(swap_mul=1.0, spread_mul=1.0):
    m5 = pd.read_parquet(C.CACHE / "sim_m5_repaired.parquet")
    raw = pd.read_parquet(C.CACHE / "sim_m5.parquet")["GER40"]
    w = raw.loc["2018":"2021"].dropna()
    cnt = w.groupby(w.index.date).size()
    holes = set(d.date() for d in pd.bdate_range("2018-01-01", "2021-12-31")
                if cnt.get(d.date(), 0) < 50)
    mask = pd.DataFrame(False, index=m5.index, columns=m5.columns)
    mask["GER40"] = [d in holes for d in m5.index.date]
    sL = pd.read_parquet(C.CACHE / "panel_swapL.parquet") * swap_mul
    sS = pd.read_parquet(C.CACHE / "panel_swapS.parquet") * swap_mul
    mu = pd.read_parquet(C.CACHE / "panel_mult.parquet")
    rt = pd.read_csv(C.OUT / "phase0_rt_cost_bps.csv", index_col=0).iloc[:, 0] * spread_mul
    D = S.build_days(m5, sL, sS, mu, rt, nan_mask=mask)
    orb = pd.read_parquet(C.CACHE / "orb_e7_Rera.parquet")["R"]
    idx = pd.DatetimeIndex(D.dates)
    D.orb_R = orb.reindex(idx).fillna(0.0).to_numpy(float)
    return D


def cohorts(D, lo, hi, step=5):
    idx = pd.DatetimeIndex(D.dates)
    sel = np.where((idx >= lo) & (idx <= hi))[0]
    return sel[::step]
