"""
Dig the one non-overnight signal with a pulse: intraday REVERSION of a large US-open
move, on gold & silver. Condition on the size of the first-30-min move; measure the
fade over (a) the last 30-min and (b) the rest of the session. GROSS, HAC t, decile
monotonicity. Run: python conditional_reversion.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from engine import stats as S
DEEP = Path("/sessions/elegant-intelligent-lovelace/mnt/Algo_claude/data/deep_history_utc")
ANN = 252.0


def build_30(sym):
    f = HERE.parent / "data_cache" / "gold" / f"{sym}_30min_close.parquet"
    if f.exists():
        return pd.read_parquet(f)
    df = pd.read_csv(DEEP / f"{sym}_M1.csv", usecols=["timestamp_utc", "open", "high", "low", "close"])
    df.index = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    agg = df.resample("30min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    agg.to_parquet(f); return agg


def shp(x):
    x = np.asarray(x); x = x[~np.isnan(x)]; return float(x.mean() / x.std() * np.sqrt(ANN)) if len(x) > 20 and x.std() > 0 else np.nan


def wins(s):
    return s.clip(s.quantile(0.005), s.quantile(0.995))


def run(sym, lo=None):
    g = build_30(sym); g["t"] = g.index.strftime("%H:%M"); g["d"] = g.index.normalize()
    piv = g.pivot_table(index="d", columns="t", values="close", aggfunc="last")
    if lo:
        piv = piv.loc[lo:]
    for c in ["13:00", "13:30", "19:30", "20:00"]:
        piv = piv[piv[c].notna()] if c in piv.columns else piv
    first30 = wins(np.log(piv["13:30"] / piv["13:00"]))
    last30 = wins(np.log(piv["20:00"] / piv["19:30"]))
    rest = wins(np.log(piv["20:00"] / piv["13:30"]))
    df = pd.concat([first30.rename("f"), last30.rename("l"), rest.rename("r")], axis=1).dropna()
    az = df["f"].abs()
    print(f"\n=== {sym} (n={len(df)}{', '+lo+'+' if lo else ''}) — fade the open ===")
    for thr, name in [(0.0, "all"), (az.quantile(0.5), ">median"), (az.quantile(0.75), ">75pct"), (az.quantile(0.9), ">90pct")]:
        m = az > thr
        revL = (-np.sign(df["f"]) * df["l"])[m]
        revR = (-np.sign(df["f"]) * df["r"])[m]
        print(f"  |open|{name:8s} n={int(m.sum()):5d} | REV->last30 SR {shp(revL):+.2f} t {S.hac_tstat(revL.to_numpy())[1]:+.2f} "
              f"| REV->rest SR {shp(revR):+.2f} t {S.hac_tstat(revR.to_numpy())[1]:+.2f}")
    # decile monotonicity of last30 reversion vs open size
    df["dec"] = pd.qcut(df["f"], 5, labels=False, duplicates="drop")
    mono = df.groupby("dec").apply(lambda x: (x["l"].mean()) * 1e4)
    print(f"  last30 mean(bps) by first30 quintile (Q0=most down .. Q4=most up): {[round(v,1) for v in mono.values]}")


for sym, lo in [("XAUUSD", None), ("XAGUSD", "2014")]:
    run(sym, lo)
