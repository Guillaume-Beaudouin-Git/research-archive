#!/usr/bin/env python3
"""Phase 2 — post-limit-move reversion. Order: (1) two-sided L25 [decisive], then
power, cost, delay, OOS, VXX-corr. Daily data only (no NQ — OOM-safe)."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
D = "/sessions/affectionate-epic-faraday/mnt/data"; OUT = f"{D}/skew_research/session_cowork"


def load_daily():
    px = {}
    fc = pd.read_csv(f"{D}/panels/ftmo_close.csv", index_col=0, parse_dates=True)
    for s in ["US500", "US100", "GER40"]:
        if s in fc.columns: px[s] = fc[s]
    cp = pd.read_csv(f"{D}/panels/commodity_panel.csv", index_col=0, parse_dates=True)
    mac = pd.read_csv(f"{D}/panels/macro_etf_panel.csv", index_col=0, parse_dates=True)
    px["GLD"], px["SLV"], px["USO"] = mac["GLD"], cp["SLV"], cp["USO"]
    px["BTC"] = pd.read_csv(f"{D}/panels/btc_full.csv", index_col=0, parse_dates=True)["BTC-USD"]
    px["ETH"] = pd.read_csv(f"{D}/panels/crypto_panel.csv", index_col=0, parse_dates=True)["ETHUSD"]
    df = pd.DataFrame(px); df.index = pd.to_datetime(df.index)
    return df.sort_index()


def stt(x):
    x = np.asarray(x, float); x = x[~np.isnan(x)]; s = x.std(ddof=1)
    return dict(n=int(len(x)), mean_bps=round(float(x.mean()*1e4), 1),
                t=round(float(x.mean()/s*np.sqrt(len(x))), 2) if s > 0 and len(x) > 2 else 0,
                skew=round(float(((x-x.mean())**3).mean()/s**3), 2) if s > 0 and len(x) > 2 else 0,
                hit=round(float((x > 0).mean()), 2))


def events(s, k=2.5):
    r = s.pct_change(); sd = r.rolling(20).std(); fwd1 = r.shift(-1)
    ext = r.abs() > k*sd
    sign = np.sign(r)
    return pd.DataFrame({"r": r, "sign": sign, "fwd1": fwd1, "ext": ext}).dropna()


def test1_twosided(us500):
    e = events(us500); e = e[e["ext"]]
    bear = e[e["sign"] < 0]["fwd1"]          # after crash -> reversion = LONG = +fwd1
    bull = e[e["sign"] > 0]["fwd1"]          # after spike -> reversion = SHORT = -fwd1
    return dict(bear_long=stt(bear.values), bull_short=stt((-bull).values))


if __name__ == "__main__":
    px = load_daily()
    print("=== TEST 1 — TWO-SIDED (L25, decisive) on US500 ===")
    t1 = test1_twosided(px["US500"])
    print("  reversion after BEARISH shock (long the bounce) :", t1["bear_long"])
    print("  reversion after BULLISH shock (short the spike) :", t1["bull_short"])
    b, s = t1["bear_long"], t1["bull_short"]
    sym = (s["t"] > 1.5 and s["mean_bps"] > 0)
    print(f"  => {'SYMMETRIC — two-sided holds, proceed' if sym else 'ASYMMETRIC — bull-side weak => dip-buying = long beta in disguise => KILL'}")
