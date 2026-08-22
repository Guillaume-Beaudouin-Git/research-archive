#!/usr/bin/env python3
"""Turn-of-Month index seasonality (long-only, single-leg). Tests existence,
post-discovery decay (by-decade/OOS), multi-index, and FTMO 2-step first-passage.
Causal: TOM window membership is known from the (deterministic) trading calendar."""
import numpy as np, pandas as pd

D = "/sessions/affectionate-epic-faraday/mnt/data"
NQ = f"{D}/raw/NQ_1min_databento_2010-2026.parquet"


def nq_daily_close():
    df = pd.read_parquet(NQ, columns=["close", "is_rth", "is_roll_day"])
    df = df[df["is_rth"] & ~df["is_roll_day"]]
    idx = df.index.tz_convert("US/Eastern")
    di = (idx.year * 10000 + idx.month * 100 + idx.day).to_numpy()
    C = df["close"].to_numpy()
    last = np.where(np.diff(di) != 0)[0]
    ends = np.concatenate([last, [len(C) - 1]])
    days = idx[ends].normalize().tz_localize(None)   # tz-naive ET dates (align w/ panel)
    return pd.Series(C[ends], index=days)


def panel_close(col):
    p = pd.read_csv(f"{D}/panels/ftmo_close.csv", index_col=0, parse_dates=True).sort_index()
    return p[col].dropna() if col in p.columns else None


def tom_mask(idx, Kf, Kl):
    df = pd.DataFrame(index=idx); df["ym"] = idx.to_period("M")
    df["tdom"] = df.groupby("ym").cumcount() + 1
    n = df.groupby("ym")["tdom"].transform("max")
    df["rtdom"] = n - df["tdom"] + 1
    return ((df["tdom"] <= Kf) | (df["rtdom"] <= Kl)).to_numpy()


def analyze(close, Kf=3, Kl=1, cost_bps=1.0, label=""):
    ret = close.pct_change().fillna(0.0).to_numpy()
    mask = tom_mask(close.index, Kf, Kl)
    tom, non = ret[mask], ret[~mask]
    # strategy: long only on TOM days, cost on transitions
    sr = np.where(mask, ret, 0.0).copy()
    trans = np.abs(np.diff(np.concatenate([[0], mask.astype(int)])))
    sr -= trans * cost_bps * 1e-4
    yrs = (close.index[-1] - close.index[0]).days / 365.25
    out = dict(label=label, n_days=len(close), pct_in_market=round(mask.mean()*100, 1),
               tom_mean_bps=round(tom.mean()*1e4, 2), non_mean_bps=round(non.mean()*1e4, 2),
               diff_t=round((tom.mean()-non.mean())/np.sqrt(tom.var(ddof=1)/len(tom)+non.var(ddof=1)/len(non)), 2),
               strat_ann_pct=round((np.prod(1+sr)**(1/yrs)-1)*100, 2),
               strat_sharpe=round(sr.mean()/sr[sr!=0].std(ddof=1)*np.sqrt(252), 2),
               strat_maxdd=round((np.cumprod(1+sr)/np.maximum.accumulate(np.cumprod(1+sr))-1).min()*100, 1))
    return out, sr, mask


def by_decade(close, Kf=3, Kl=1):
    ret = close.pct_change().fillna(0.0)
    mask = tom_mask(close.index, Kf, Kl)
    s = pd.Series(np.where(mask, ret.to_numpy(), 0.0), index=close.index)
    out = {}
    for lo, hi, name in [(2000,2010,"2000s"),(2010,2020,"2010s"),(2020,2027,"2020s")]:
        sub = s[(s.index.year>=lo)&(s.index.year<hi)]
        m = sub[sub!=0]
        if len(m) > 20:
            yrs = (sub.index[-1]-sub.index[0]).days/365.25
            out[name] = dict(ann_pct=round((np.prod(1+sub.to_numpy())**(1/yrs)-1)*100,2),
                             tom_day_bps=round(m.mean()*1e4,2), t=round(m.mean()/m.std(ddof=1)*np.sqrt(len(m)),2), n=len(m))
    return out


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
    return dict(L=L,p_funded=round(f/n,3),bust=round(b/n,3),run=round(r/n,3),
                med_mo=round(float(np.median(tt))/21,1) if tt else None)


def main():
    nq = nq_daily_close()
    us500 = panel_close("US500"); us100 = panel_close("US100")
    # anti-artifact: panel US100 vs NQ databento daily returns (overlap)
    if us100 is not None:
        ov = pd.DataFrame({"nq": nq, "p": us100}).dropna()
        print(f"[validate] panel US100 vs NQ databento daily-return corr: {ov.nq.pct_change().corr(ov.p.pct_change()):.3f} (overlap {len(ov)})")
    series = {"NQ(databento)": nq}
    if us500 is not None: series["US500(panel)"] = us500
    if us100 is not None: series["US100(panel)"] = us100
    print("\n=== TOM existence + strategy (baseline Kf=3,Kl=1, cost 1bp) ===")
    for name, s in series.items():
        o, sr, mask = analyze(s, label=name)
        print(f"  {name}: in-mkt {o['pct_in_market']}% | TOM-day {o['tom_mean_bps']:+.2f}bps vs non {o['non_mean_bps']:+.2f}bps "
              f"(diff t {o['diff_t']:+.2f}) | strat ann {o['strat_ann_pct']:+.2f}% Sh {o['strat_sharpe']:+.2f} maxDD {o['strat_maxdd']}%")
    print("\n=== DECAY: by-decade (NQ where avail, US500 for 2000s) ===")
    for name, s in series.items():
        print(f"  {name}: {by_decade(s)}")
    print("\n=== grid (US500 long history): Kf/Kl -> diff_t / strat ann% ===")
    base_s = us500 if us500 is not None else nq
    for Kf in (2,3,4):
        for Kl in (1,2):
            o,_,_ = analyze(base_s, Kf=Kf, Kl=Kl)
            print(f"  Kf{Kf}/Kl{Kl}: diff_t {o['diff_t']:+.2f}  ann {o['strat_ann_pct']:+.2f}%  in-mkt {o['pct_in_market']}%")
    print("\n=== FTMO 2-step first-passage (NQ TOM strategy, leverage sweep) ===")
    _, sr_nq, _ = analyze(nq)
    for L in (3,5,8,12):
        print(f"  L={L}x: {ftmo_daily(sr_nq, L)}")
    # post-2013 OOS first-passage
    _, sr_nq_full, _ = analyze(nq)
    nq_oos = nq[nq.index.year>=2018]; _, sr_oos, _ = analyze(nq_oos)
    print("  OOS 2018-2026 @L=8:", ftmo_daily(sr_oos, 8))


if __name__ == "__main__":
    main()
