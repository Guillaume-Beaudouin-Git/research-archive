"""Diversified intraday book: ORB sleeves across instruments x sessions.
Goal: raise the book's daily Sharpe via decorrelation (sqrt-N), which is what limits p(pass).
Sleeve daily value = sum of trade R-multiples that day (risk-1R units). delay=True (real fills)."""
import engine as E, numpy as np, pandas as pd

# sleeve defs: (sym, sess_open_min, sess_close_min, label). None,None = native cash session.
SLEEVES = [
    ("US100", None, None,           "US100_NY"),
    ("US500", None, None,           "US500_NY"),
    ("GER40", None, None,           "GER40_cash"),
    ("XAUUSD", 600,  960,           "XAU_London"),
    ("XAUUSD", 990,  1350,          "XAU_NY"),
    ("EURUSD", 600,  1020,          "EUR_London"),
    ("EURUSD", 900,  1320,          "EUR_NY"),
]

def sleeve_daily(sym, so, sc, min_width_bps=8.0):
    tr = E.backtest_orb(sym, min_width_bps=min_width_bps, trail_be=True, delay=True,
                        sess_open=so, sess_close=sc)
    tr = tr[tr.R_frac>0].copy()
    tr["rmult"] = tr["net"]/tr["R_frac"]
    d = tr.groupby("date")["rmult"].sum()
    d.index = pd.to_datetime(d.index)
    return d.sort_index()

def build_panel():
    cols={}
    live={}
    for sym,so,sc,lab in SLEEVES:
        d=sleeve_daily(sym,so,sc)
        cols[lab]=d
        live[lab]=(d.index.min(),d.index.max())
    # union of dates
    alldates=sorted(set().union(*[set(s.index) for s in cols.values()]))
    panel=pd.DataFrame(index=pd.DatetimeIndex(alldates))
    for lab,d in cols.items():
        s=d.reindex(panel.index)
        lo,hi=live[lab]
        # fill 0 within live range (flat/no-trade day), NaN outside
        inrange=(panel.index>=lo)&(panel.index<=hi)
        s=s.where(~(inrange & s.isna()), 0.0)
        panel[lab]=s
    return panel, live

if __name__=="__main__":
    panel,live=build_panel()
    ann=np.sqrt(252)
    print("=== per-sleeve standalone (full available history) ===")
    for lab in panel.columns:
        s=panel[lab].dropna()
        sh=s.mean()/s.std()*ann if s.std()>0 else 0
        print(f"{lab:11s} n={len(s):5d} {str(live[lab][0].date())}->{str(live[lab][1].date())} "
              f"meanRmult={s.mean():+.4f} dSharpe={sh:+.2f}")
    panel.to_parquet("cache/sleeve_panel.parquet")
    print("\n=== correlation of daily R-mult (overlap 2022+) ===")
    sub=panel.loc[panel.index>="2022-01-01"].dropna()
    print(sub.corr().round(2).to_string())
    print("\nsaved cache/sleeve_panel.parquet  shape",panel.shape)
