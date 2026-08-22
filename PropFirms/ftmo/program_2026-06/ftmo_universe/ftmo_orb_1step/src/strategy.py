"""
Intraday backtest engine for the FTMO study. Page-blanche rebuild.

Clock = broker EET (UTC+2/+3). Sessions defined in EET minutes-of-day.
All trade returns are expressed as RETURN ON 1x NOTIONAL (price move / entry),
net of round-trip cost. The FTMO sim later scales by a leverage/notional multiple.

Correctness:
- No look-ahead: signals use only bars up to (and including) the decision bar;
  entries fill on the decision/trigger bar at a defined price.
- Conservative intrabar fills: if both stop and target are touchable in the same
  bar, assume the STOP fills first (worst case).
- Cost = full spread (cross on entry + exit) + commission + slippage, in price frac.
"""
import pandas as pd, numpy as np
from config import CACHE

# ---- instrument meta: point size, commission (RT frac of notional), digits ----
META = {
    "US100":  dict(point=0.01, comm_rt=0.0,      slip_bps=0.3),
    "US500":  dict(point=0.01, comm_rt=0.0,      slip_bps=0.3),
    "GER40":  dict(point=0.01, comm_rt=0.0,      slip_bps=0.3),
    "XAUUSD": dict(point=0.01, comm_rt=0.000014, slip_bps=0.3),  # 0.0007%/side -> 0.0014% RT
    "EURUSD": dict(point=0.00001, comm_rt=0.0000454, slip_bps=0.15),  # $5 RT / ~110k notional
    "BTCUSD": dict(point=0.01, comm_rt=0.0, slip_bps=4.0),            # crypto CFD: spread(price)+~4bps slip
}

# Cash-session anchors in EET minutes-of-day.
SESS = {
    "US100": dict(open=16*60+30, close=22*60+55),
    "US500": dict(open=16*60+30, close=22*60+55),
    "GER40": dict(open=10*60,    close=18*60+25),
    "XAUUSD":dict(open=16*60+30, close=22*60+55),  # NY anchor
    "EURUSD":dict(open=10*60,    close=18*60+0),   # London anchor
    "BTCUSD":dict(open=16*60+30, close=22*60+55),  # US-session anchor (intraday, flat by close)
}

def load(sym):
    df = pd.read_parquet(f"{CACHE}{sym}.parquet")
    return df

def cost_frac(sym, price, spread_pts):
    """round-trip cost as fraction of price."""
    m = META[sym]
    spread_price = spread_pts * m["point"]
    return (spread_price / price) + m["comm_rt"] + m["slip_bps"]*1e-4

# --------------------------------------------------------------------------
# ORB: opening-range breakout
# --------------------------------------------------------------------------
def backtest_orb(sym, or_min=30, min_width_bps=10.0, trail_be=True, delay=False,
                 sess_open=None, sess_close=None, trend="none", long_only=False, partial=False):
    df = load(sym); s = SESS[sym]
    o0 = s["open"] if sess_open is None else sess_open
    c  = s["close"] if sess_close is None else sess_close
    o_start, o_end_off = o0, o0+or_min
    prev_close = df.groupby("date")["close"].last().shift(1).to_dict()
    trades=[]
    for date, g in df.groupby("date", sort=True):
        g = g[(g.tod>=o_start) & (g.tod<=c)]
        if len(g) < or_min+5: continue
        orb = g[g.tod < o_end_off]
        if len(orb) < or_min*0.6: continue
        orh, orl = orb.high.max(), orb.low.min()
        if orh<=orl: continue
        width = orh - orl
        entry_px0 = orb.close.iloc[-1]
        if (width/entry_px0)*1e4 < min_width_bps: continue
        post = g[g.tod >= o_end_off]
        if len(post) < 3: continue
        H,L,C,T = post.high.values, post.low.values, post.close.values, post.tod.values
        O = post.open.values; SP = post.spread.values
        pcl = prev_close.get(date, np.nan)
        side=0; entry=np.nan; ei=-1
        for i in range(len(post)):
            if H[i] >= orh: cand=1
            elif L[i] <= orl: cand=-1
            else: continue
            if trend=="pc" and not np.isnan(pcl):
                if cand==1 and entry_px0 < pcl: continue
                if cand==-1 and entry_px0 > pcl: continue
            if long_only and cand==-1: continue
            side=cand; lvl = orh if cand==1 else orl
            if delay and i+1<len(post): entry=O[i+1]; ei=i+1
            else: entry=lvl; ei=i
            break
        if side==0: continue
        stop = orl if side==1 else orh
        R = abs(entry-stop)
        if R<=0: continue
        be_armed=False; exit_px=C[-1]; exit_reason="close"
        for j in range(ei, len(post)):
            hi,lo = H[j],L[j]
            # check stop first (conservative)
            if side==1:
                cur_stop = entry if be_armed else stop
                if lo <= cur_stop:
                    exit_px=cur_stop; exit_reason="stop" if not be_armed else "be"; break
                if trail_be and (not be_armed) and hi >= entry+R:
                    be_armed=True
            else:
                cur_stop = entry if be_armed else stop
                if hi >= cur_stop:
                    exit_px=cur_stop; exit_reason="stop" if not be_armed else "be"; break
                if trail_be and (not be_armed) and lo <= entry-R:
                    be_armed=True
        cf = cost_frac(sym, entry, np.nanmedian(SP) if np.isfinite(np.nanmedian(SP)) else 0)
        gross_full = side*(exit_px-entry)/entry
        if partial and be_armed:
            gross = 0.5*(R/entry) + 0.5*gross_full   # bank half at +1R, runner = remaining half
            net = gross - cf*1.5
        else:
            gross = gross_full; net = gross - cf
        trades.append((date, side, entry, exit_px, R/entry, gross, net, exit_reason))
    cols=["date","side","entry","exit","R_frac","gross","net","reason"]
    return pd.DataFrame(trades, columns=cols)

# --------------------------------------------------------------------------
# VWAP mean-reversion fade
# --------------------------------------------------------------------------
def backtest_vwap_mr(sym, z_in=2.0, z_out=0.3, z_stop=3.5, lookback=30):
    df = load(sym); s=SESS[sym]; o,c=s["open"],s["close"]
    trades=[]
    for date,g in df.groupby("date",sort=True):
        g=g[(g.tod>=o)&(g.tod<=c)].reset_index(drop=True)
        if len(g)<lookback+10: continue
        px=g.close.values; hi=g.high.values; lo=g.low.values; sp=g.spread.values
        # session VWAP proxy (no volume -> typical price cumulative mean)
        tp=(g.high.values+g.low.values+g.close.values)/3.0
        cumvwap=np.cumsum(tp)/np.arange(1,len(tp)+1)
        dev=px-cumvwap
        # rolling std of deviation
        sd=pd.Series(dev).rolling(lookback,min_periods=lookback//2).std().values
        z=np.where(sd>0, dev/sd, 0.0)
        pos=0; entry=np.nan; ei=-1
        for i in range(lookback,len(g)-1):
            if pos==0:
                if z[i] <= -z_in:
                    pos=1; entry=px[i]; ei=i; estop=entry-z_stop*sd[i]; etgt=cumvwap[i]
                elif z[i] >= z_in:
                    pos=-1; entry=px[i]; ei=i; estop=entry+z_stop*sd[i]; etgt=cumvwap[i]
            else:
                done=False; exit_px=px[i]; reason="hold"
                if pos==1:
                    if lo[i]<=estop: exit_px=estop; reason="stop"; done=True
                    elif z[i]>=-z_out or px[i]>=etgt: exit_px=px[i]; reason="tgt"; done=True
                else:
                    if hi[i]>=estop: exit_px=estop; reason="stop"; done=True
                    elif z[i]<=z_out or px[i]<=etgt: exit_px=px[i]; reason="tgt"; done=True
                if i==len(g)-2 and not done: exit_px=px[i]; reason="close"; done=True
                if done:
                    cf=cost_frac(sym, entry, np.nanmedian(sp))
                    gross=pos*(exit_px-entry)/entry; net=gross-cf
                    trades.append((date,pos,entry,exit_px,np.nan,gross,net,reason))
                    pos=0
    cols=["date","side","entry","exit","R_frac","gross","net","reason"]
    return pd.DataFrame(trades,columns=cols)

# --------------------------------------------------------------------------
# Intraday momentum (Gao-style): direction of session-so-far at decision time
# predicts the move into the close. One trade/day.
# --------------------------------------------------------------------------
def backtest_intraday_mom(sym, decide_min_before_close=60):
    df=load(sym); s=SESS[sym]; o,c=s["open"],s["close"]
    dec=c-decide_min_before_close
    trades=[]
    for date,g in df.groupby("date",sort=True):
        g=g[(g.tod>=o)&(g.tod<=c)].reset_index(drop=True)
        if len(g)<30: continue
        op=g.close.iloc[0]
        gd=g[g.tod<=dec]
        if len(gd)<5: continue
        px_dec=gd.close.iloc[-1]
        sig=np.sign(px_dec/op-1.0)
        if sig==0: continue
        entry=px_dec; exit_px=g.close.iloc[-1]
        cf=cost_frac(sym, entry, np.nanmedian(g.spread.values))
        gross=sig*(exit_px-entry)/entry; net=gross-cf
        trades.append((date,int(sig),entry,exit_px,np.nan,gross,net,"close"))
    cols=["date","side","entry","exit","R_frac","gross","net","reason"]
    return pd.DataFrame(trades,columns=cols)

# --------------------------------------------------------------------------
def daily_pnl(trades):
    """sum net trade returns by date -> daily return on 1x notional."""
    if len(trades)==0: return pd.Series(dtype=float)
    d=trades.groupby("date")["net"].sum()
    d.index=pd.to_datetime(d.index)
    return d.sort_index()

def metrics(trades, name=""):
    if len(trades)==0: return dict(name=name,n=0)
    net=trades.net.values
    d=daily_pnl(trades)
    ann = np.sqrt(252)
    sharpe_tr = net.mean()/net.std()*np.sqrt(252/ (len(net)/ ((d.index.max()-d.index.min()).days/365.25*252+1)) ) if net.std()>0 else 0
    # simpler: daily-sharpe annualized
    dsh = d.mean()/d.std()*ann if d.std()>0 else 0
    long=trades[trades.side==1].net; short=trades[trades.side==-1].net
    from scipy.stats import skew
    return dict(name=name, n=len(net),
        meanR_bps=net.mean()*1e4, hit=(net>0).mean(),
        skew=float(skew(net)) if len(net)>5 else np.nan,
        daily_sharpe=dsh, gross_bps=trades.gross.mean()*1e4,
        long_bps=long.mean()*1e4 if len(long) else np.nan,
        short_bps=short.mean()*1e4 if len(short) else np.nan,
        n_long=len(long), n_short=len(short),
        ndays=len(d))
