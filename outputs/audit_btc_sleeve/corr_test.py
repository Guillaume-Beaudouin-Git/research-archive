"""VOLET C — correlation of a BTC trend sleeve to the book legs (risk-on overload test).
Recipe proxy of engine.build_signals: 60/120/250 trend blend, vol-targeted, shift(1).
Aligned on a common weekday calendar (BTC reindexed to the legs' trading days)."""
import numpy as np, pandas as pd
from pathlib import Path
ROOT = Path("<HOME>/Desktop/Algo_claude")
C = ROOT / "data/ftmo_portfolio/cache"

def norm(s):
    s = s.copy(); s.index = pd.to_datetime(s.index).normalize()
    return s[~s.index.duplicated()]

def load_leg(n):
    d = pd.read_parquet(C/f"{n}_daily_cet.parquet"); return norm(d["close"].astype(float))

raw = {"BTC": norm(pd.read_csv(ROOT/"data/panels/btc_full.csv", parse_dates=["Date"]).set_index("Date")["BTC-USD"].astype(float)),
       "US100": load_leg("US100"), "XAUUSD": load_leg("XAUUSD"), "USDJPY": load_leg("USDJPY"), "GER40": load_leg("GER40")}
panel = pd.DataFrame(raw).sort_index()
panel = panel.dropna(subset=["US100","XAUUSD","USDJPY","GER40"])   # weekday rows
panel["BTC"] = panel["BTC"].ffill()
panel = panel.dropna()
ret = np.log(panel).diff()

def trend_sleeve(p):
    r = np.log(p).diff()
    mom = np.sign(sum((p/p.shift(n)-1.0) for n in (60,120,250)))
    vol = (r.rolling(60).std()*np.sqrt(252)).clip(lower=1e-3)
    pos = (mom*(0.10/vol)).clip(-3,3)
    return pos.shift(1)*r

sleeves = pd.DataFrame({k: trend_sleeve(panel[k]) for k in panel})
book = sleeves[["US100","XAUUSD","USDJPY","GER40"]].mean(axis=1)

for lab, idx in [("full", sleeves.dropna().index), ("2023+", sleeves.loc["2023":].dropna().index)]:
    sub = sleeves.loc[idx]; bk = book.loc[idx]; rr = ret.loc[idx]
    print(f"\n=== {lab}  N={len(sub)} ===")
    print("  raw daily-ret corr(BTC,leg):   " + "  ".join(f"{l} {rr['BTC'].corr(rr[l]):+.2f}" for l in ["US100","XAUUSD","USDJPY","GER40"]))
    print("  TREND-SLEEVE corr(BTC,leg):    " + "  ".join(f"{l} {sub['BTC'].corr(sub[l]):+.2f}" for l in ["US100","XAUUSD","USDJPY","GER40"]))
    print(f"  corr(BTC-trend, BOOK composite) = {sub['BTC'].corr(bk):+.3f}   [kill rule: >0.35 -> NO-GO]")
    print(f"  sign-overlap(BTC,book) = {(np.sign(sub['BTC'])==np.sign(bk)).mean():.3f}   |  frac BTC-trend LONG = {(sub['BTC'].where(sub['BTC']!=0)>0).mean():.2f}")

# capitulation coincidence (3 trading-day flush <= -15%)
r3 = panel["BTC"]/panel["BTC"].shift(3)-1.0
fd = r3[r3<=-0.15].index
print(f"\n=== capitulation entries (BTC 3d <= -15%): N={len(fd)} (2023+: {int((r3.loc['2023':]<=-0.15).sum())}) ===")
for leg in ["US100","XAUUSD","USDJPY","GER40"]:
    print(f"  concurrent {leg}: mean {ret.loc[fd,leg].mean()*1e4:+.1f} bps, P(down)={(ret.loc[fd,leg]<0).mean():.2f}")
