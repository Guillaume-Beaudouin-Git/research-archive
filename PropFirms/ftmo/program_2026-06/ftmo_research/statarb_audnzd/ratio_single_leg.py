#!/usr/bin/env python3
"""Ideas 3A (GLD/SLV) & 4A (ETH/BTC): ratio-as-signal, single-leg directional.
Decisive test: does ratio-timing add alpha OVER buy-and-hold the traded leg, net
of cost? Causal OU z on log-ratio; trade the dislocated real leg; daily."""
import numpy as np, pandas as pd

D = "/sessions/affectionate-epic-faraday/mnt/data"


def ann(x):
    x = np.asarray(x); x = x[~np.isnan(x)]; s = x.std(ddof=1)
    return dict(sharpe=round(float(x.mean()/s*np.sqrt(252)),2) if s>0 else 0.0,
                t=round(float(x.mean()/s*np.sqrt(len(x))),2) if s>0 else 0.0,
                ann_ret=round(float(x.mean()*252*100),1),
                maxdd=round(float((np.cumprod(1+x)/np.maximum.accumulate(np.cumprod(1+x))-1).min())*100,1))


def load_3A():
    gld = pd.read_csv(f"{D}/panels/macro_etf_panel.csv", index_col=0, parse_dates=True)["GLD"]
    slv = pd.read_csv(f"{D}/panels/commodity_panel.csv", index_col=0, parse_dates=True)["SLV"]
    df = pd.DataFrame({"GLD": gld, "SLV": slv}).dropna()
    df["ratio"] = df["GLD"] / df["SLV"]          # gold/silver
    return df, ("GLD", "SLV")   # high ratio -> long SLV ; low -> long GLD


def load_4A():
    btc = pd.read_csv(f"{D}/panels/btc_full.csv", index_col=0, parse_dates=True)["BTC-USD"]
    eth = pd.read_csv(f"{D}/panels/crypto_panel.csv", index_col=0, parse_dates=True)["ETHUSD"]
    df = pd.DataFrame({"ETH": eth, "BTC": btc}).dropna()
    df["ratio"] = df["ETH"] / df["BTC"]
    return df, ("ETH", None)    # single instrument ETH: high ratio -> short ETH ; low -> long ETH


def strat(df, legs, W=120, Zin=2.0, Zstop=3.0, Tmax=60, lag=1, cost_bps=0.0, kind="rotate"):
    lr = np.log(df["ratio"]).values
    f = pd.Series(lr).rolling(W).mean().values
    sd = pd.Series(lr - f).rolling(W).std().values
    z = (lr - f) / sd
    T = len(df)
    # daily returns of each instrument
    legA = df[legs[0]].pct_change().clip(-0.5, 0.5).values
    legB = df[legs[1]].pct_change().clip(-0.5, 0.5).values if legs[1] else None
    pos = np.zeros(T)          # +1 long traded leg, -1 short; for rotate: +1=legA-cheap-long etc
    ret = np.zeros(T)
    state = 0; entry_dir = 0; held = 0
    for t in range(W + lag, T):
        if state == 0:
            if z[t-lag] >= Zin: state = +1   # ratio high
            elif z[t-lag] <= -Zin: state = -1
            held = 0
        else:
            held += 1
            if (state == 1 and z[t-lag] <= 0) or (state == -1 and z[t-lag] >= 0) or abs(z[t-lag]) >= Zstop or held >= Tmax:
                state = 0
        # realize today's return given yesterday's state
        if kind == "rotate":   # 3A: high ratio(state+1)->long SLV(legB); low(state-1)->long GLD(legA)
            if state == 1 and legB is not None: ret[t] = legB[t]
            elif state == -1: ret[t] = legA[t]
        else:                  # 4A single instrument: high ratio(state+1)->short ETH; low->long ETH
            if state == 1: ret[t] = -legA[t]
            elif state == -1: ret[t] = legA[t]
        # cost on state changes
        if t > 0 and ((pos[t-1] == 0) != (state == 0) or np.sign(pos[t-1]) != np.sign(state)):
            ret[t] -= cost_bps * 1e-4
        pos[t] = state
    inmkt = pos != 0
    return ret, inmkt, (legA, legB)


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
    n=len(st)
    return dict(p_funded=round(f/n,3), bust=round(b/n,3), run=round(r/n,3),
                med_mo=round(float(np.median(tt))/21,1) if tt else None)


def run(name, df, legs, kind):
    print(f"\n{'='*68}\n{name}: {df.index.min().date()}..{df.index.max().date()} n={len(df)}")
    # buy & hold the traded leg(s) benchmark
    bhA = df[legs[0]].pct_change().clip(-0.5,0.5).dropna().values
    print(f"  buy&hold {legs[0]}: {ann(bhA)}")
    if legs[1]:
        bhB=df[legs[1]].pct_change().clip(-0.5,0.5).dropna().values
        print(f"  buy&hold {legs[1]}: {ann(bhB)}")
    print("  grid (gross): W/Zin -> strat Sharpe / t / ann% / maxDD% / %time-in")
    best=None
    for W in (60,120):
        for Zin in (1.5,2.0):
            ret,inmkt,_=strat(df,legs,W=W,Zin=Zin,kind=kind,cost_bps=0)
            a=ann(ret[ret!=0]); tin=inmkt.mean()
            print(f"    W{W} Zin{Zin}: Sh {a['sharpe']:+.2f} t {a['t']:+.2f} ann {a['ann_ret']:+.1f}% dd {a['maxdd']}% time-in {tin*100:.0f}%")
            if best is None or a['t']>best[1]: best=((W,Zin),a['t'],a['sharpe'])
    # cost sweep on baseline
    cb_list = (0,4,8) if kind=="rotate" else (0,10,25)
    print(f"  cost sweep (baseline W120/Zin2): ")
    for cb in cb_list:
        ret,inmkt,_=strat(df,legs,W=120,Zin=2.0,kind=kind,cost_bps=cb)
        a=ann(ret[ret!=0])
        print(f"    {cb}bps: Sh {a['sharpe']:+.2f} t {a['t']:+.2f} ann {a['ann_ret']:+.1f}%")
    # delay
    r1,_,_=strat(df,legs,W=120,Zin=2.0,kind=kind,cost_bps=0,lag=1)
    r2,_,_=strat(df,legs,W=120,Zin=2.0,kind=kind,cost_bps=0,lag=2)
    print(f"  delay: t+1 t {ann(r1[r1!=0])['t']:+.2f} | t+2 t {ann(r2[r2!=0])['t']:+.2f}")
    # FTMO first-passage on full daily series (cost included realistic)
    cb = 6 if kind=="rotate" else 20
    ret,_,_=strat(df,legs,W=120,Zin=2.0,kind=kind,cost_bps=cb)
    print(f"  FTMO 2-step (cost {cb}bps, daily-MTM):")
    for L in ((3,5,8) if kind=="rotate" else (1,2,3)):
        print(f"    L={L}x: {ftmo_daily(ret,L)}")


if __name__ == "__main__":
    df3, legs3 = load_3A(); run("3A GOLD/SILVER (rotate cheap metal)", df3, legs3, "rotate")
    df4, legs4 = load_4A(); run("4A ETH/BTC (ETH directional)", df4, legs4, "single")
