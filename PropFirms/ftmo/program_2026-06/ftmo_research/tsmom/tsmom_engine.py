#!/usr/bin/env python3
"""Diversified multi-asset TSMOM (trend-following). Vol-targeted, two-sided.
v1 + iteration knobs (K, trend filter, instruments, vol-target). FTMO first-passage."""
import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
D = "/sessions/affectionate-epic-faraday/mnt/data"


def load_basket():
    px = {}
    fc = pd.read_csv(f"{D}/panels/ftmo_close.csv", index_col=0, parse_dates=True)
    for s in ["US500", "US100", "GER40"]:
        if s in fc.columns: px[s] = fc[s]
    cp = pd.read_csv(f"{D}/panels/commodity_panel.csv", index_col=0, parse_dates=True)
    mac = pd.read_csv(f"{D}/panels/macro_etf_panel.csv", index_col=0, parse_dates=True)
    px["GLD"] = mac["GLD"]; px["SLV"] = cp["SLV"]; px["USO"] = cp["USO"]
    px["BTC"] = pd.read_csv(f"{D}/panels/btc_full.csv", index_col=0, parse_dates=True)["BTC-USD"]
    px["ETH"] = pd.read_csv(f"{D}/panels/crypto_panel.csv", index_col=0, parse_dates=True)["ETHUSD"]
    df = pd.DataFrame(px).sort_index()
    df.index = pd.to_datetime(df.index)
    return df


def tsmom(px, K=100, target_vol=0.10, inst=None, theta=0.0, cost_bps=2.0, port_vol=0.10):
    inst = inst or list(px.columns)
    px = px[inst].dropna(how="all")
    rets = px.pct_change().clip(-0.5, 0.5)
    mom = px.pct_change(K)                       # trailing K-day return (known at t)
    rv = rets.rolling(60).std() * np.sqrt(252)   # realized vol, trailing
    sig = np.sign(mom)
    if theta > 0:                                # trend-strength filter
        strength = (mom.abs() / (rv / np.sqrt(252) * np.sqrt(K)))
        sig = sig.where(strength > theta, 0.0)
    w = (target_vol / rv).clip(upper=5.0)        # vol-target per instrument
    pos = (sig * w).shift(1)                      # trade tomorrow on today's signal (causal)
    # opposing-correlated monitor (equities block)
    eq = [c for c in ["US500", "US100", "GER40"] if c in inst]
    opp = 0.0
    if len(eq) > 1:
        s = np.sign(pos[eq]); opp = ((s.gt(0).any(axis=1)) & (s.lt(0).any(axis=1))).mean()
    gross = (pos * rets).sum(axis=1)
    # scale to portfolio target vol (trailing, causal)
    pv = gross.rolling(60).std() * np.sqrt(252)
    scale = (port_vol / pv).clip(upper=3.0).shift(1)
    port = gross * scale
    # cost on turnover
    turn = pos.diff().abs().sum(axis=1)
    port = port - turn * cost_bps * 1e-4
    return port.dropna(), float(opp)


def stats(x, lab=""):
    x = np.asarray(x); x = x[~np.isnan(x)]; s = x.std(ddof=1)
    eq = np.cumprod(1 + x); dd = (eq / np.maximum.accumulate(eq) - 1).min()
    sk = ((x - x.mean())**3).mean() / s**3
    return dict(lab=lab, ann=round(x.mean()*252*100, 1), sharpe=round(x.mean()/s*np.sqrt(252), 2),
                skew=round(float(sk), 2), maxdd=round(dd*100, 1), t=round(x.mean()/s*np.sqrt(len(x)), 2))


def ftmo_daily(sr, L, init=1e4, p1=1.10, p2=1.05, floor=9e3, dcap=0.05, step=3):
    N=len(sr); st=np.arange(0,N-5,step)
    def ph(s,tg):
        eq=init;i=s
        while i<N:
            c=L*sr[i]
            if c<=-dcap: return i,'b'
            eq*=1+c
            if eq<floor: return i,'b'
            if eq>=init*tg: return i,'p'
            i+=1
        return N-1,'r'
    f=b=r=0; tt=[]
    for s in st:
        e1,s1=ph(s,p1)
        if s1!='p': b+=s1=='b'; r+=s1=='r'; continue
        e2,s2=ph(e1+1,p2)
        if s2=='p': f+=1; tt.append(e2-s)
        elif s2=='b': b+=1
        else: r+=1
    n=len(st); return dict(L=L,p_funded=round(f/n,3),bust=round(b/n,3),med_mo=round(float(np.median(tt))/21,1) if tt else None)


def main():
    px = load_basket()
    core = ["US500","GER40","GLD","SLV","USO"]
    full = ["US500","GER40","GLD","SLV","USO","BTC","ETH"]
    print(f"data {px.index.min().date()}..{px.index.max().date()}")
    for name, inst in [("CORE 2006+", core), ("FULL +crypto 2014+", full)]:
        port, opp = tsmom(px, K=100, inst=inst)
        st = stats(port.values, name)
        print(f"\n{name} ({len(inst)} inst): {st} | opposing-correlated(eq) {opp*100:.0f}% of days")
        # by-year (check bear-year short profits)
        by = port.groupby(port.index.year).apply(lambda x:(np.prod(1+x.values)-1)*100)
        print("  by-year:", {int(y):round(v,0) for y,v in by.items() if y in (2008,2011,2015,2018,2020,2022,2023,2024,2025,2026)})
        print("  FTMO first-passage:")
        for L in (3,5,8,12):
            print("   ", ftmo_daily(port.values, L))


if __name__ == "__main__":
    main()
