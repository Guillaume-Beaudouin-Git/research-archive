"""
Proper 30-minute intraday tests on gold (and oil) — the canonical Gao-Han-Li-Zhou
'market intraday momentum' (first 30-min -> last 30-min), plus opening-range
breakout and conditional reversion, on the US session. GROSS, winsorised, HAC t.
Run: python intraday_30min.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from engine import data, stats as S
ANN = 252.0
DEEP = Path("/sessions/elegant-intelligent-lovelace/mnt/Algo_claude/data/deep_history_utc")


def build_30(sym):
    f = HERE.parent / "data_cache" / "gold" / f"{sym}_30min_close.parquet"
    if f.exists():
        return pd.read_parquet(f)
    df = pd.read_csv(DEEP / f"{sym}_M1.csv", usecols=["timestamp_utc", "open", "high", "low", "close"])
    df.index = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    agg = df.resample("30min").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    agg.to_parquet(f)
    return agg


def shp(x):
    x = np.asarray(x); x = x[~np.isnan(x)]; return float(x.mean() / x.std() * np.sqrt(ANN)) if len(x) > 20 and x.std() > 0 else np.nan


def wins(s):
    return s.clip(s.quantile(0.005), s.quantile(0.995))


def cl(piv, hhmm):
    return piv[hhmm] if hhmm in piv.columns else pd.Series(dtype=float)


def analyse(sym, sess_open="13:00", first_end="13:30", last_start="19:30", sess_close="20:00"):
    g = build_30(sym)
    g["t"] = g.index.strftime("%H:%M"); g["d"] = g.index.normalize()
    piv = g.pivot_table(index="d", columns="t", values="close", aggfunc="last")
    need = [sess_open, first_end, last_start, sess_close]
    piv = piv.dropna(subset=[c for c in need if c in piv.columns])
    first30 = wins(np.log(cl(piv, first_end) / cl(piv, sess_open)))
    last30 = wins(np.log(cl(piv, sess_close) / cl(piv, last_start)))
    rest = wins(np.log(cl(piv, sess_close) / cl(piv, first_end)))
    df = pd.concat([first30.rename("f"), last30.rename("l"), rest.rename("r")], axis=1).dropna()
    print(f"\n=== {sym}  (session {sess_open}-{sess_close} UTC, n={len(df)}) ===")
    # Gao: first30 predicts last30
    mom_last = np.sign(df["f"]) * df["l"]
    print(f"  Gao MOM first30->last30 : grossSR {shp(mom_last):+.2f} | HACt {S.hac_tstat(mom_last.to_numpy())[1]:+.2f} | corr {np.corrcoef(df['f'],df['l'])[0,1]:+.3f}")
    mom_rest = np.sign(df["f"]) * df["r"]
    print(f"  MOM first30->rest      : grossSR {shp(mom_rest):+.2f} | HACt {S.hac_tstat(mom_rest.to_numpy())[1]:+.2f}")
    print(f"  REV first30->last30    : grossSR {shp(-mom_last):+.2f}")
    # conditional: only when |first30| large
    big = df["f"].abs() > df["f"].abs().median()
    print(f"  Gao MOM (big-move days): grossSR {shp((np.sign(df['f'])*df['l'])[big]):+.2f} (n={int(big.sum())})")
    return df


for sym in ["XAUUSD", "USOIL"]:
    try:
        analyse(sym)
    except Exception as e:
        print(sym, "ERR", repr(e)[:120])
