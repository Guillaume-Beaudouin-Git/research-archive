#!/usr/bin/env python3
"""PEAD v2 (iteration): deployable long-only basket of recent TOP-surprise names.
Refined signal = surprise in top quintile (optionally + positive announcement
reaction), hold H days. Measures basket Sharpe, market-adjusted alpha vs SPY,
by-year, and FTMO 2-step first-passage."""
import numpy as np, pandas as pd

D = "/sessions/affectionate-epic-faraday/mnt/data"


def load():
    px = pd.read_csv(f"{D}/panels/single_stocks.csv", index_col=0, parse_dates=True).sort_index()
    spy = pd.read_csv(f"{D}/panels/equity_close2.csv", index_col=0, parse_dates=True)["SPY"].sort_index().reindex(px.index).ffill()
    earn = pd.read_csv(f"{D}/panels/earnings_dates.csv")
    earn["date"] = pd.to_datetime(earn["date"], errors="coerce")
    earn["surprise_pct"] = pd.to_numeric(earn["surprise_pct"], errors="coerce")
    earn = earn.dropna(subset=["date", "surprise_pct"])
    return px, spy, earn


def build_positions(px, earn, H=40, q=0.8, require_react=False):
    """held[t, stock] = 1 if stock had a top-quintile-surprise earnings in (t-H, t]."""
    thr = earn["surprise_pct"].quantile(q)
    idx = px.index
    held = pd.DataFrame(0.0, index=idx, columns=px.columns)
    n_ev = 0
    for tk, g in earn.groupby("ticker"):
        if tk not in px.columns:
            continue
        s = px[tk]
        for _, r in g.iterrows():
            if r["surprise_pct"] < thr:
                continue
            a = idx.searchsorted(r["date"], side="right")
            if a < 2 or a >= len(idx):
                continue
            if require_react and not (s.iloc[a] / s.iloc[a-1] - 1 > 0):
                continue
            held.iloc[a:a + H, held.columns.get_loc(tk)] = 1.0
            n_ev += 1
    return held, n_ev


def basket_returns(px, held):
    rets = px.pct_change().clip(-0.3, 0.3)
    w = held.div(held.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    br = (w.shift(1) * rets).sum(axis=1)        # hold today what was selected by yesterday
    inmkt = held.sum(axis=1) > 0
    return br, inmkt


def stats(x, lab):
    x = np.asarray(x); x = x[~np.isnan(x)]
    nz = x[x != 0]; s = nz.std(ddof=1)
    eq = np.cumprod(1 + x); dd = (eq/np.maximum.accumulate(eq)-1).min()
    return (f"{lab}: ann {x.mean()*252*100:+.1f}% Sh {x.mean()/s*np.sqrt(252):+.2f} "
            f"t {nz.mean()/s*np.sqrt(len(nz)):+.2f} maxDD {dd*100:.0f}%")


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
    px, spy, earn = load()
    spyret = spy.pct_change().clip(-0.3,0.3)
    print(f"universe {px.shape[1]} | events {len(earn)} | SPY buy&hold: {stats(spyret.values,'SPY')}")
    for q, rr, H in [(0.8,False,40),(0.8,True,40),(0.9,True,40),(0.8,True,60)]:
        held, nev = build_positions(px, earn, H=H, q=q, require_react=rr)
        br, inmkt = basket_returns(px, held)
        alpha = (br - spyret).reindex(br.index)
        lab = f"q{q} react={rr} H{H} (n_ev {nev}, in-mkt {inmkt.mean()*100:.0f}%)"
        print(f"\n--- {lab} ---")
        print("  basket abs : " + stats(br.values, "basket"))
        print("  vs SPY     : " + stats(alpha.values, "alpha"))
    # by-year + first-passage on the refined config
    held, nev = build_positions(px, earn, H=40, q=0.8, require_react=True)
    br, inmkt = basket_returns(px, held)
    by = br.groupby(br.index.year).apply(lambda x: round((np.prod(1+x.values)-1)*100,1))
    print("\nby-year basket %:", dict(by))
    print("\nFTMO 2-step first-passage (refined PEAD basket, daily-MTM):")
    sr = br.fillna(0).values
    for L in (3,5,8,12):
        print("  ", ftmo_daily(sr, L))


if __name__ == "__main__":
    main()
