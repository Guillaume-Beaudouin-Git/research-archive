"""Le micro-ORB a-t-il JAMAIS ete PIVOTAL dans un franchissement ?

Sur chaque bust : marge de franchissement = lim_eff - equite au barreau de breche.
Si marge < excursion micro (dip 1.31R), le micro a fait basculer ce barreau.
"""
import numpy as np, pandas as pd, mo_common as K, mo_engine as G
M,WT,ON=K.load(); V,C22,E=K.V,K.C22,K.E
L=[]; w=L.append
for tag,c0 in (("v2.2",C22.CFG_CHALLENGE),("v2.8",C22.CFG_CHALLENGE_V28)):
    rows=[]
    for win,lo,hi in C22.WINDOWS:
        for i0 in V.starts(M,lo,hi,C22.COHORT_STEP):
            start=M["dates"][int(i0)]; i=int(i0)
            while True:
                if (M["dates"][min(i,M["n"]-1)]-start).days>C22.WALL or i>=M["n"]-5: break
                lg=[]; r1=G.run_phase(M,i,WT,ON,dict(c0,target=E.TARGET1,max_cal=C22.WALL),log=lg)
                rows+=lg
                if r1["out"]=="pass":
                    j=min(r1["last"]+3,M["n"]-1)
                    if (M["dates"][j]-start).days>C22.WALL: break
                    lg=[]; r2=G.run_phase(M,j,WT,ON,dict(c0,target=E.TARGET2,max_cal=C22.WALL,
                        vm=c0["vm"]*c0.get("p2_mult",1.0)),log=lg); rows+=lg
                    if r2["out"] in ("pass","timeout"): break
                    i=min(r2["last"]+2,M["n"]-1)
                else:
                    if r1["out"]=="timeout": break
                    i=min(r1["last"]+2,M["n"]-1)
    D=pd.DataFrame(rows); bu=D[D.event=="bust"].copy()
    bu["breach_margin"]=bu.breach_margin.astype(float); bu["micro_dip"]=bu.micro_dip.astype(float)
    piv=bu[(bu.micro_dip>0)&(bu.breach_margin<bu.micro_dip)]
    w(f"[{tag}] busts N={len(bu)} | marge de franchissement: mediane ${bu.breach_margin.median():.1f}"
      f" p5 ${bu.breach_margin.quantile(.05):.2f} min ${bu.breach_margin.min():.3f}")
    w(f"        busts ou le micro etait expose : {int((bu.micro_dip>0).sum())}")
    w(f"        >>> busts PIVOTAUX (marge < excursion micro) : {len(piv)}"
      f" = {len(piv)/len(bu)*100:.2f}% des busts")
    if len(piv): w("        detail: "+piv[["date","breach_margin","micro_dip"]].head(10).to_string())
    q=(bu.breach_margin<8.16).mean()
    w(f"        part des busts dont la marge est < borne dure micro ($8.16) : {q*100:.2f}%")
t="\n".join(L); print(t); (K.OUT/"q3_pivot.txt").write_text(t)
