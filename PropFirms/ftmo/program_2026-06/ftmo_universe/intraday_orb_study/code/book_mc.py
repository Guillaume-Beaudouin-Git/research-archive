import numpy as np, pandas as pd, ftmo_sim as F
panel=pd.read_parquet("cache/sleeve_panel.parquet")
ann=np.sqrt(252)

# regime robustness of the only full-depth positive sleeve
print("=== XAU_NY yearly meanRmult (full depth 2018-2026) ===")
xn=panel["XAU_NY"].dropna()
print((xn.groupby(xn.index.year).mean()).round(3).to_string())

POS=["US100_NY","US500_NY","GER40_cash","XAU_NY"]      # positive-EV sleeves only
DECOR=["US100_NY","GER40_cash","XAU_NY"]                # drop US500 (corr 0.66 w US100)

def book_series(cols, start="2022-01-01"):
    sub=panel[cols].loc[panel.index>=start].dropna(how="all")
    # equal-risk: sum of sleeve R-mults (each risked rho); flat day = 0
    return sub.fillna(0.0).sum(axis=1)

def stats(s,lab):
    sh=s.mean()/s.std()*ann
    print(f"{lab:28s} ndays={len(s):4d} mean={s.mean():+.3f} std={s.std():.2f} dSharpe={sh:+.2f}")
    return sh

print("\n=== book daily Sharpe (equal-risk, 2022+) ===")
b1=book_series(POS);   stats(b1,"B1 = US100+US500+GER40+XAU")
b2=book_series(DECOR); stats(b2,"B2 = US100+GER40+XAU (decorrel)")
for c in POS: stats(panel[c].loc[panel.index>="2022-01-01"].dropna(),f"  single {c}")
# inverse-vol weighted book (down-weight redundant/volatile sleeves)
sub=panel[POS].loc[panel.index>="2022-01-01"].fillna(0.0)
w=1.0/sub.std(); w=w/w.sum()*len(POS)   # scale so avg weight=1 (comparable risk)
b3=(sub*w).sum(axis=1); stats(b3,"B3 = inverse-vol weighted")

b1.to_frame("rmult").to_parquet("cache/book_B1.parquet")
b2.to_frame("rmult").to_parquet("cache/book_B2.parquet")

print("\n=== FTMO 2-step MC on diversified book B1 (rho = risk per sleeve) ===")
sizings=[dict(mode="fixed",rho=r) for r in (0.005,0.0075,0.01,0.0125,0.015)]+\
        [dict(mode="floor_taper",c=c,rho_max=0.04) for c in (0.05,0.08,0.12)]
F.report(b1,"BOOK B1 (4 sleeves, 2022+)",sizings,N=30000,T=252)
print("\n--- single US100 reference (2021+) ---")
us=pd.read_parquet("cache/rmult_DELAY_2021+.parquet")["rmult"]
F.report(us,"single US100 2021+",[dict(mode="fixed",rho=r) for r in (0.02,0.025,0.03)],N=30000,T=252)
