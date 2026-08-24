"""Concentration diagnostic (PRE_REGISTRATION §3-§7).
Tests whether loss events over-represent macro-regime buckets vs all trading days,
with autocorrelation-robust circular-shift permutation nulls + Holm/BH correction.
T-1 (causal) governs the verdict; T (contemporaneous) reported as the 'trap' check.

DEVIATION FROM PRE-REG (data-driven, pre-results): full-history HY OAS is absent from
the store (in-store 2023-05+ only). A3 credit => reduced-coverage secondary on 2023+;
primary Holm family = 3 axes x 2 books = 6 (A1 vol, A2 dollar, A4 FOMC). Disclosed.
"""
import sys, json, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import chi2_contingency
import lib_regime as R

HERE = Path(__file__).resolve().parent; CACHE = HERE / "_cache"; RES = HERE / "results"; RES.mkdir(exist_ok=True)
MAIN = "<HOME>/Desktop/Algo_claude"
SEED = 20260620; B_PRIMARY = 5000; B_SEC = 3000
t0 = time.time()

BD = pd.read_parquet(CACHE / "book_daily.parquet")
P = pd.read_parquet(CACHE / "regime_panel.parquet").reindex(BD.index)
EV = pd.read_parquet(CACHE / "challenge_busts.parquet")
FMC = pd.read_parquet(CACHE / "funded_mc.parquet")
bd = BD.index

# ---- event indicators over book dates -------------------------------------------------
ev_days = set(EV.date.dt.normalize())
evd_daily = set(EV.loc[EV.cause == "daily", "date"].dt.normalize())
ch_bust = pd.Series(bd.normalize().isin(ev_days), index=bd)
ch_bust_daily = pd.Series(bd.normalize().isin(evd_daily), index=bd)
r = BD.daily_ret
tail1 = r <= r.quantile(0.01)
tail5 = r <= r.quantile(0.05)
roll10 = r.rolling(10).sum(); roll10_tail5 = roll10 <= roll10.quantile(0.05)
roll5 = r.rolling(5).sum(); roll5_tail5 = roll5 <= roll5.quantile(0.05)
eq = (1 + r).cumprod(); dd = 1 - eq / eq.cummax(); dd_p90 = dd >= dd.quantile(0.90)
fmc_busts = set(pd.to_datetime(FMC.bust_date.dropna()).dt.normalize())
fmc_dd = set(pd.to_datetime(FMC.worst_dd_date.dropna()).dt.normalize())
fmc_bust_ev = pd.Series(bd.normalize().isin(fmc_busts), index=bd)
fmc_dd_ev = pd.Series(bd.normalize().isin(fmc_dd), index=bd)

EVENTS = {  # name -> (indicator series, book label)
    "Q1_ch_bust": (ch_bust, "challenge"), "Q1_ch_bust_daily": (ch_bust_daily, "challenge"),
    "Q1_tail1": (tail1, "challenge"), "Q1_tail5": (tail5, "challenge"),
    "Q2_roll10_tail5": (roll10_tail5, "funded"), "Q2_roll5_tail5": (roll5_tail5, "funded"),
    "Q2_dd_p90": (dd_p90, "funded"), "Q2_fmc_dd": (fmc_dd_ev, "funded"),
}
print("event counts:", {k: int(v[0].sum()) for k, v in EVENTS.items()},
      "| fmc_busts(sparse)", len(fmc_busts), "[%ds]" % (time.time()-t0))

# ---- concentration test ---------------------------------------------------------------
def chi2_stat(e, g, buckets):
    tab = np.array([[((g == b) & (e == v)).sum() for b in buckets] for v in (0, 1)], float)
    tab = tab[:, tab.sum(0) > 0]
    if tab.shape[1] < 2 or tab.sum() == 0: return 0.0
    return chi2_contingency(tab, correction=False)[0]

def concentration(event, regime, risk_off=None, B=B_PRIMARY, seed=SEED):
    mask = regime.notna().values & event.notna().values
    e = event.values[mask].astype(int); g = regime.values[mask].astype(object)
    n = len(e); ne = int(e.sum())
    buckets = sorted(pd.unique(g[~pd.isna(g)]))
    if ne == 0 or ne == n or len(buckets) < 2:
        return dict(n=n, n_events=ne, base=ne/max(n,1), chi2=0, p_perm=1.0, p_chi2=1.0,
                    lift_worst=np.nan, bucket_worst=None, lift_riskoff=np.nan,
                    ev_share_worst=np.nan, day_share_worst=np.nan)
    obs = chi2_stat(e, g, buckets)
    rng = np.random.default_rng(seed); cnt = 1
    for _ in range(B):
        k = int(rng.integers(1, n))
        if chi2_stat(e, np.roll(g, k), buckets) >= obs - 1e-12: cnt += 1
    p_perm = cnt / (B + 1)
    base = e.mean()
    lifts = {b: (e[g == b].mean() / base if base > 0 else np.nan) for b in buckets}
    bw = max(lifts, key=lambda b: lifts[b])
    ev_share = (e[g == bw].sum()) / ne; day_share = (g == bw).mean()
    return dict(n=n, n_events=ne, base=base, chi2=obs, p_perm=p_perm,
                p_chi2=chi2_contingency(np.array([[((g==b)&(e==v)).sum() for b in buckets] for v in (0,1)],float))[1],
                lift_worst=lifts[bw], bucket_worst=str(bw),
                lift_riskoff=(lifts.get(risk_off, np.nan) if risk_off else np.nan),
                ev_share_worst=ev_share, day_share_worst=day_share, lifts={b: round(lifts[b],3) for b in buckets})

def holm(pvals):
    order = np.argsort(pvals); m = len(pvals); adj = np.empty(m); run = 0.0
    for rank, i in enumerate(order):
        run = max(run, (m - rank) * pvals[i]); adj[i] = min(run, 1.0)
    return adj

def bh(pvals):
    order = np.argsort(pvals); m = len(pvals); adj = np.empty(m); prev = 1.0
    for rank in range(m-1, -1, -1):
        i = order[rank]; prev = min(prev, pvals[i] * m / (rank+1)); adj[i] = prev
    return adj

# ---- PRIMARY family: 3 full-sample axes x {Q1 challenge bust, Q2 roll10 tail}, T-1 -----
PRIM_AXES = [("A1_vol", "A1_vol", "hi"), ("A2_usd", "A2_usd", None), ("A4_fomc", "A4_fomc", "fomc")]
PRIM_EVENTS = [("Q1_ch_bust", ch_bust), ("Q2_roll10_tail5", roll10_tail5)]
rows = []
for ename, ev in PRIM_EVENTS:
    for aname, acol, roff in PRIM_AXES:
        res = concentration(ev, P[acol], risk_off=roff)
        rows.append(dict(family="primary", event=ename, axis=aname, align="T-1", **res))
prim = pd.DataFrame(rows)
prim["p_holm"] = holm(prim.p_perm.values)
print(f"\n===== PRIMARY (Holm over {len(prim)}), T-1 causal =====")
print(prim[["event","axis","n_events","base","lift_worst","bucket_worst","ev_share_worst",
            "day_share_worst","p_perm","p_holm"]].to_string(index=False,
            formatters={"base":"{:.3f}".format,"lift_worst":"{:.2f}".format,
                        "ev_share_worst":"{:.2f}".format,"day_share_worst":"{:.2f}".format,
                        "p_perm":"{:.4f}".format,"p_holm":"{:.4f}".format}))

# ---- 'TRAP' check: contemporaneous (T) for A1/A2 on the two primary events -------------
trap = []
for ename, ev in PRIM_EVENTS:
    for aname, ctcol, roff in [("A1_vol", "A1_vol_ct", "hi"), ("A2_usd", "A2_usd_ct", None)]:
        res = concentration(ev, P[ctcol], risk_off=roff, B=B_SEC)
        trap.append(dict(event=ename, axis=aname, align="T(contemp)", **res))
trap = pd.DataFrame(trap)
print("\n===== TRAP CHECK: contemporaneous T (compare lift/p to T-1 above) =====")
print(trap[["event","axis","lift_worst","bucket_worst","p_perm"]].to_string(index=False,
      formatters={"lift_worst":"{:.2f}".format,"p_perm":"{:.4f}".format}))

# ---- SECONDARY family (power-confirmation + A3 credit 2023+ + extra events), BH --------
sec = []
SEC_AXES = [("A1_vol","A1_vol","hi"),("A2_usd","A2_usd",None),("A4_fomc","A4_fomc","fomc"),
            ("A3_credit","A3_credit","wide")]
SEC_EVENTS = ["Q1_ch_bust_daily","Q1_tail1","Q1_tail5","Q2_roll5_tail5","Q2_dd_p90","Q2_fmc_dd"]
for ename in SEC_EVENTS:
    ev = EVENTS[ename][0]
    for aname, acol, roff in SEC_AXES:
        res = concentration(ev, P[acol], risk_off=roff, B=B_SEC)
        sec.append(dict(family="secondary", event=ename, axis=aname, align="T-1", **res))
sec = pd.DataFrame(sec)
sec["p_bh"] = bh(sec.p_perm.values)
print(f"\n===== SECONDARY (BH over {len(sec)}), T-1 — power-confirmation + A3 credit(2023+) =====")
print(sec[["event","axis","n_events","lift_worst","bucket_worst","p_perm","p_bh"]].to_string(index=False,
      formatters={"lift_worst":"{:.2f}".format,"p_perm":"{:.4f}".format,"p_bh":"{:.4f}".format}))

# ---- VIX quintile top-Q share (the metric the prompt asks for) -------------------------
print("\n===== VIX top-quintile share of events (vs 20% baseline) =====")
qrows=[]
for ename,(ev,_) in EVENTS.items():
    m = P["A1_vol_q"].notna().values & ev.notna().values
    e = ev.values[m].astype(int); q = P["A1_vol_q"].values[m]
    if e.sum()==0: continue
    topq = (e[(q=="q5")].sum())/e.sum(); bot = (e[(q=="q1")].sum())/e.sum()
    qrows.append(dict(event=ename, n=int(e.sum()), share_q5=topq, share_q1=bot, ratio_q5_to_20pct=topq/0.2))
qdf=pd.DataFrame(qrows); print(qdf.to_string(index=False,formatters={"share_q5":"{:.2f}".format,
    "share_q1":"{:.2f}".format,"ratio_q5_to_20pct":"{:.2f}".format}))

# ---- save -----------------------------------------------------------------------------
out = dict(primary=prim.to_dict("records"), trap=trap.to_dict("records"),
          secondary=sec.to_dict("records"), vix_quintile=qdf.to_dict("records"),
          meta=dict(n_days=len(BD), book_vol=float(r.std()*np.sqrt(252)),
                    challenge_bust_days=int(ch_bust.sum()), p_funded=0.851,
                    B_primary=B_PRIMARY, seed=SEED))
json.dump(out, open(RES/"diagnostic_results.json","w"), indent=1, default=str)
prim.to_csv(RES/"primary.csv",index=False); sec.to_csv(RES/"secondary.csv",index=False)
print(f"\nsaved results/ [{time.time()-t0:.0f}s]")
