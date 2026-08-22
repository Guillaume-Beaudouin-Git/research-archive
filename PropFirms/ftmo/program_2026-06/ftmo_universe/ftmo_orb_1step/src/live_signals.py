"""
LIVE signal generator for the ORB Nasdaq 1-step strategy (the config that passes).

Usage (each trading day, around the US cash open):
    python live_signals.py --equity 10250 --days_left 28
It prints today's opening-range levels, whether a LONG setup is valid (trend filter),
the entry/stop, and the DP-OPTIMAL position size for your current account state.

Rules recap: US cash open OR = first 30 min (09:30-10:00 ET). LONG only, on a break of OR-high,
only if OR-end price > prior-day close. Stop = OR-low (1R). Exit: trail to breakeven after +1R,
else RTH close. Flat overnight. Risk per trade = DP-optimal rho*(equity, days_left), capped 4.5%.
"""
import argparse, numpy as np, pandas as pd
import dp_sizing as D
from config import CACHE

OR_OPEN_EET=16*60+30   # broker EET minutes; if your feed is ET, use 9*60+30
OR_MIN=30
MIN_WIDTH_BPS=8.0
RHO_CAP=0.045

# ---- DP-optimal sizing policy (solve once on the strategy's daily R-mult distribution) ----
_POL=None
def policy(series_path=CACHE+"cand_LO.parquet", T=42):
    global _POL
    if _POL is None:
        s=pd.read_parquet(series_path)["rmult"]
        _,pol=D.solve(s,T=T,two_step=False)
        _POL=pol
    return _POL

def rho_star(equity, days_left):
    pol=policy(); E1=pol["E1"]; P1=pol["P1"]
    d=int(np.clip(days_left,1,P1.shape[0]-1))
    return float(np.clip(np.interp(equity,E1,P1[d]),0,RHO_CAP))

# ---- opening-range setup from today's 1-min session bars ----
def orb_setup(bars, prior_close):
    """bars: DataFrame [dt, open, high, low, close] for today's session (broker EET), sorted.
    Returns the OR levels, trend-filter check, and the long entry/stop if valid."""
    b=bars.copy(); b["tod"]=pd.to_datetime(b["dt"]).dt.hour*60+pd.to_datetime(b["dt"]).dt.minute
    orb=b[(b.tod>=OR_OPEN_EET)&(b.tod<OR_OPEN_EET+OR_MIN)]
    post=b[b.tod>=OR_OPEN_EET+OR_MIN]
    if len(orb)<OR_MIN*0.6:
        return dict(status="OR not complete yet")
    orh,orl=float(orb.high.max()),float(orb.low.min())
    or_end_px=float(orb.close.iloc[-1])
    width_bps=(orh-orl)/or_end_px*1e4
    trend_ok = or_end_px > prior_close
    res=dict(OR_high=round(orh,2),OR_low=round(orl,2),width_bps=round(width_bps,1),
             prior_close=round(prior_close,2),trend_long_ok=bool(trend_ok),
             entry=round(orh,2),stop=round(orl,2),R_frac=round((orh-orl)/orh,5))
    if width_bps<MIN_WIDTH_BPS: res["status"]="NO TRADE: OR too narrow (<8bps)"
    elif not trend_ok:          res["status"]="NO TRADE: down-day (OR-end <= prior close), long filtered"
    else:
        broke = len(post)>0 and float(post.high.max())>=orh
        res["status"]="LONG TRIGGERED" if broke else "ARMED: go long on break of OR-high"
    return res

def size(equity, days_left, R_frac, entry, contract_pnl_per_point=1.0):
    rho=rho_star(equity,days_left)
    risk_usd=rho*equity
    R_points=R_frac*entry
    lots=risk_usd/(R_points*contract_pnl_per_point)   # US100.cash: $1/point/lot
    return dict(rho_pct=round(rho*100,2),risk_usd=round(risk_usd,2),
                R_points=round(R_points,1),lots=round(lots,2))

def _last_complete_day(df):
    s=df[(df.tod>=OR_OPEN_EET)&(df.tod<=22*60+55)].groupby("date").size()
    return s[s>=60].index.max()

def demo():
    df=pd.read_parquet(CACHE+"US100.parquet")
    last=_last_complete_day(df)
    today=df[df["date"]==last]
    prior=df[df["date"]<last].groupby("date")["close"].last().iloc[-1]
    s=orb_setup(today.rename(columns={"dt":"dt"})[["dt","open","high","low","close"]], float(prior))
    print(f"=== LIVE DEMO on last cached US100 day ({last}) ===")
    for k,v in s.items(): print(f"  {k}: {v}")
    if s.get("status","").startswith(("LONG","ARMED")):
        for eq,dl in [(10000,35),(10250,28),(10700,12)]:
            print(f"  size @ equity ${eq}, {dl}d left -> {size(eq,dl,s['R_frac'],s['entry'])}")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--equity",type=float,default=None); ap.add_argument("--days_left",type=int,default=30)
    a=ap.parse_args()
    if a.equity is None: demo()
    else:
        df=pd.read_parquet(CACHE+"US100.parquet"); last=df["date"].max(); today=df[df["date"]==last]
        prior=df[df["date"]<last].groupby("date")["close"].last().iloc[-1]
        s=orb_setup(today[["dt","open","high","low","close"]],float(prior))
        print(f"[{last}] "+s.get("status","?"))
        for k,v in s.items():
            if k!="status": print(f"   {k}: {v}")
        if s.get("status","").startswith(("LONG","ARMED")):
            print("   SIZE:",size(a.equity,a.days_left,s["R_frac"],s["entry"]))
