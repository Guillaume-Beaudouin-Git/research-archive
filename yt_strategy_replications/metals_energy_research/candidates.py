"""
Candidate intraday edges for XAGUSD (silver) and USOIL (WTI) on FTMO.
Silver: transfer the gold overnight/Asian-drift (23:00-07:00 UTC, swap-free, VT).
WTI: search a NEW intraday edge (momentum into the US session, overnight, ORB-ish).
Returns are winsorised (0.5/99.5%) to neutralise bad ticks. Run: python candidates.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from engine import stats as S  # noqa: E402
spec = importlib.util.spec_from_file_location("iz", HERE.parent / "gold_research" / "intraday.py")
iz = importlib.util.module_from_spec(spec); spec.loader.exec_module(iz)
ANN = 252.0


def vt(w):
    rv = w.rolling(20, min_periods=20).std().shift(1)
    return (rv.expanding(min_periods=20).median() / rv).clip(upper=3.0).fillna(0.0)


def wins(s):
    lo, hi = s.quantile(0.005), s.quantile(0.995)
    return s.clip(lo, hi)


def sharpe(x):
    x = np.asarray(x); return float(x.mean() / x.std() * np.sqrt(ANN)) if x.std() > 0 else np.nan


def evalw(piv, hours, position=None, label="", spreads=(0, 3, 5, 7)):
    w = wins(iz.win_ret(piv, hours))
    pos = vt(w) if position is None else position.reindex(w.index).fillna(0.0) * vt(w)
    gross = (pos * w).dropna()
    rg = gross.to_numpy()
    oos = sharpe(gross[gross.index >= gross.index[int(0.6 * len(gross))]].to_numpy())
    out = dict(label=label, n=len(rg), gross_sharpe=round(sharpe(rg), 2),
               gross_bps=round(rg.mean() * 1e4, 2), hac_t=round(S.hac_tstat(rg)[1], 2),
               dsr=round(S.deflated_sharpe_ratio(rg, 25, periods_per_year=ANN)["dsr"], 2),
               oos=round(oos, 2))
    for sp in spreads:
        n = (pos * w - pos.abs() * sp * 1e-4).dropna()
        out[f"net{sp}"] = round(sharpe(n.to_numpy()), 2)
    return out


# ---------- SILVER: transfer the gold overnight edge + window check ----------
print("===== SILVER (XAGUSD) — overnight/Asian drift, swap-free (anchor 13) =====")
ag = iz.hourly_pivot("XAGUSD", anchor_hour=13)
rows = []
for start in [22, 23, 0]:
    for length in [6, 8, 10]:
        w = [(start + i) % 24 for i in range(length)]
        if start == 22:  # holds across rollover -> not swap-free; skip for deployable
            continue
        rows.append(evalw(ag, w, label=f"AG_{start}_{length}"))
df = pd.DataFrame(rows).sort_values("gross_sharpe", ascending=False)
print(df.to_string(index=False))

# ---------- WTI: new intraday edges ----------
print("\n===== WTI (USOIL) — new intraday edges =====")
oil0 = iz.hourly_pivot("USOIL", anchor_hour=0)
oil13 = iz.hourly_pivot("USOIL", anchor_hour=13)
US = list(range(13, 20))
def sgn(piv, hrs): return np.sign(wins(iz.win_ret(piv, hrs)))
rows2 = [
    evalw(oil13, [23, 0, 1, 2, 3, 4, 5, 6], label="OIL_overnight_23_8"),
    evalw(oil0, US, position=sgn(oil0, range(0, 13)), label="OIL_MOM_preUS->US"),
    evalw(oil0, US, position=sgn(oil0, range(6, 13)), label="OIL_MOM_EUR->US"),
    evalw(oil0, list(range(15, 20)), position=sgn(oil0, [13, 14]), label="OIL_MOM_open->close"),
    evalw(oil0, US, position=pd.Series(1.0, index=oil0.index), label="OIL_US_long"),
    evalw(oil0, US, position=pd.Series(-1.0, index=oil0.index), label="OIL_US_short"),
]
df2 = pd.DataFrame(rows2).sort_values("gross_sharpe", ascending=False)
print(df2.to_string(index=False))
print("\nbreakeven spread (RT) ~ gross_bps; viable on FTMO if realistic spread < breakeven.")
