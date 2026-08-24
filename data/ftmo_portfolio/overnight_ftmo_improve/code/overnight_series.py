"""Generalized overnight-drift per-sleeve series builder (gold/silver/WTI/soybean).

net/pos reuse the EXACT metals/gold engine (gold_research/intraday.hourly_pivot + win_ret) so
they reproduce the report to the cent; winsorised 0.5/99.5% x VT(expanding-median/rolling-20,
cap 3x). SEPARATELY, raw hourly LOW PATHS (log dip from entry) are computed from M1->H1 for the
basket's DIVERSIFIED intraday low (not in the report).

Indexed by EXIT-MORNING date (gold/silver/WTI enter 23:00 D, exit 07:00 D+1 => shift +1;
soybean 01:00->07:00 D => no shift) so all sleeves exit 07:00 UTC on the same book day.
Columns: pos, net_simple (winsorised, simple, net of spread), win_w, and lp_<h> on the
8-hour grid [23,0,1,2,3,4,5,6] = raw log low-path from entry (NaN where no bar -> flat in basket).
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
YT = REPO / "yt_strategy_replications"
GRID = [23, 0, 1, 2, 3, 4, 5, 6]
ANN = 252.0

_data = None
def _D():
    """Load engine/data.py by explicit path (avoids the `from engine import` sys.modules collision
    with the cleanroom engine that engine_v22 inserts on sys.path)."""
    global _data
    if _data is None:
        s = importlib.util.spec_from_file_location("yt_engine_data", YT / "engine" / "data.py")
        _data = importlib.util.module_from_spec(s); s.loader.exec_module(_data)
    return _data


def _hourly_pivot(sym, anchor):
    """Replica of gold_research/intraday.hourly_pivot (self-contained, no `from engine`)."""
    g = _load_h1(sym)
    g = g.assign(lr=np.log(g["close"] / g["close"].shift(1))).dropna(subset=["lr"])
    aday = (g.index - pd.Timedelta(hours=anchor)).normalize()
    g = g.assign(aday=aday, hour=g.index.hour)
    piv = g.pivot_table(index="aday", columns="hour", values="lr", aggfunc="sum")
    return piv[piv.notna().sum(axis=1) >= 18].fillna(0.0)


def _win_ret(piv, hours):
    return piv[[h for h in hours if h in piv.columns]].sum(axis=1)


def _load_h1(sym):
    D = _D()
    try:
        return D.load_h1(sym)
    except (FileNotFoundError, OSError):
        return D.build_deephist_h1(sym)


def _vt(w):
    rv = w.rolling(20, min_periods=20).std().shift(1)
    return (rv.expanding(min_periods=20).median() / rv).clip(upper=3.0).fillna(0.0)


def _wins(s):
    return s.clip(s.quantile(0.005), s.quantile(0.995))


SPECS = {
    "GOLD":    dict(sym="XAUUSD", hours=[23, 0, 1, 2, 3, 4, 5, 6], anchor=13, lo=None,   shift=True),
    "SILVER":  dict(sym="XAGUSD", hours=[23, 0, 1, 2, 3, 4, 5, 6], anchor=13, lo="2014", shift=True),
    "WTI":     dict(sym="USOIL",  hours=[23, 0, 1, 2, 3, 4, 5, 6], anchor=13, lo=None,   shift=True),
    "SOYBEAN": dict(sym="SOYBEAN",hours=[1, 2, 3, 4, 5, 6],        anchor=0,  lo=None,   shift=False),
}


def _low_paths(sym, hours, anchor, lo):
    """Raw per-aday hourly log low-path (cum lr + within-bar low_gap), on the window grid."""
    h1 = _load_h1(sym)
    lr = np.log(h1["close"] / h1["close"].shift(1))
    low_gap = np.log(h1["low"] / h1["close"])
    aday = (h1.index - pd.Timedelta(hours=anchor)).normalize()
    df = pd.DataFrame({"lr": lr, "low_gap": low_gap, "aday": aday, "hour": h1.index.hour}).dropna()
    if lo:
        df = df[df.index >= pd.Timestamp(lo)]
    df = df[df["hour"].isin(hours)].sort_index()
    df["cum"] = df.groupby("aday")["lr"].cumsum()
    df["low_path"] = df["cum"] + df["low_gap"]
    lp = df.pivot_table(index="aday", columns="hour", values="low_path", aggfunc="min")
    return lp.reindex(columns=GRID).rename(columns={h: f"lp_{h}" for h in GRID})


def build(name, spread_bps=2.0, winsorise=True):
    s = SPECS[name]
    piv = _hourly_pivot(s["sym"], s["anchor"])
    if s["lo"]:
        piv = piv.loc[s["lo"]:]
    wr = _win_ret(piv, s["hours"])
    win_w = _wins(wr) if winsorise else wr
    pos = _vt(win_w)
    sp = spread_bps * 1e-4
    net_simple = pos * (np.exp(win_w) - 1.0) - pos.abs() * sp
    base = pd.concat([pos.rename("pos"), net_simple.rename("net_simple"),
                      win_w.rename("win_w")], axis=1)
    lp = _low_paths(s["sym"], s["hours"], s["anchor"], s["lo"]).reindex(base.index)
    out = pd.concat([base, lp], axis=1).dropna(subset=["pos", "net_simple"])
    out = out[out["pos"] > 0]
    if s["shift"]:
        out.index = out.index + pd.Timedelta(days=1)
    out = out.groupby(out.index.normalize()).last()
    out.attrs["half_spread"] = sp / 2.0
    return out


if __name__ == "__main__":
    for nm in SPECS:
        d = build(nm, 2.0)
        gross = (d["pos"] * d["win_w"]).to_numpy()
        net = d["net_simple"].to_numpy()
        shg = gross.mean() / gross.std() * np.sqrt(ANN)
        shn = net.mean() / net.std() * np.sqrt(ANN)
        print(f"{nm:8s} n={len(d):4d} {d.index.min().date()}->{d.index.max().date()} | "
              f"gross Sh {shg:.2f} | net@2bp Sh {shn:.2f} | worst net {net.min()*100:.1f}% | lp8={sum(c.startswith('lp_') for c in d.columns)}")
    print("expected gross (metals/final_analysis): SILVER 1.45, WTI 1.09 ; GOLD ~asia")
