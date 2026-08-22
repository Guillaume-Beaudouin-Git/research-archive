#!/usr/bin/env python3
"""NQ overnight-drift harvester — full metrics + FTMO 2-step first-passage distribution.
Clean contiguous real-path on NQ databento 2010-2026. No look-ahead:
gate decision at close(t) uses MA200 of closes <= t; overnight return = open(t+1)/close(t)-1.
"""
import numpy as np, pandas as pd, json, os

DATA = "/sessions/affectionate-epic-faraday/mnt/data/raw/NQ_1min_databento_2010-2026.parquet"
OUT  = "/sessions/affectionate-epic-faraday/mnt/data/ftmo_research/NQ_overnight_metrics"
os.makedirs(OUT, exist_ok=True)
COST = 0.0002          # 2 bps net per traded night (spread+commission; swap pending Check1)
MA   = 200
INIT = 10000.0
P1_TGT, P2_TGT = 1.10, 1.05     # +10%, +5%
DAILY_DD, FLOOR = 0.05, 9000.0  # 5% daily loss, $9k static floor
LEVS = [0.5, 0.75, 1.0]

# ---------- 1. Build clean daily O/C from RTH non-roll bars (US/Eastern) ----------
df = pd.read_parquet(DATA, columns=["open","close","is_rth","is_roll_day"])
df = df[df["is_rth"] & ~df["is_roll_day"]]
df.index = df.index.tz_convert("US/Eastern")
day = df.index.normalize()
g = df.groupby(day)
daily = pd.DataFrame({"O": g["open"].first(), "C": g["close"].last()})
daily = daily.dropna()
C = daily["C"].values
O = daily["O"].values
dates = daily.index
n = len(daily)

# overnight return: hold close(t) -> open(t+1)
ov = O[1:] / C[:-1] - 1.0                      # length n-1, indexed by t=0..n-2
# MA200 gate using closes <= t (info known at close t)
ma = pd.Series(C).rolling(MA).mean().values
gate = (C > ma)                                # gate[t]; decision at close t
gate_t = gate[:-1]                             # align to ov (t=0..n-2)
valid = ~np.isnan(ma[:-1])                     # MA defined
# nightly strategy return (net), flat when gate off or MA undefined
r_net = np.where(valid & gate_t, ov - COST, 0.0)
r_gross = np.where(valid & gate_t, ov, 0.0)
traded = valid & gate_t                        # nights with a position
ov_dates = dates[1:]                           # the date the position closes (open t+1)

# ---------- 2. Nightly + equity-curve metrics ----------
def stats(x):
    x = np.asarray(x, float)
    m, s = x.mean(), x.std(ddof=1)
    sk = ((x-m)**3).mean() / s**3 if s>0 else np.nan
    return dict(n=int(len(x)), mean_bps=float(m*1e4), std_bps=float(s*1e4),
                sharpe_ann=float(m/s*np.sqrt(252)) if s>0 else np.nan,
                skew=float(sk), hit=float((x>0).mean()))

traded_net = r_net[traded]
nightly = {"traded_net": stats(traded_net),
           "traded_gross": stats(r_gross[traded]),
           "all_nights_net": stats(r_net[valid])}

def curve_metrics(r, L):
    eq = np.cumprod(1.0 + L*r)
    yrs = len(r)/252.0
    cagr = eq[-1]**(1/yrs) - 1
    peak = np.maximum.accumulate(eq)
    dd = eq/peak - 1.0
    mdd = dd.min()
    daily_s = (L*r)
    sh = daily_s.mean()/daily_s.std(ddof=1)*np.sqrt(252)
    sk = stats(daily_s[daily_s!=0])["skew"]
    return dict(L=L, total_return=float(eq[-1]-1), CAGR=float(cagr),
                maxDD=float(mdd), Calmar=float(cagr/abs(mdd)),
                Sharpe_ann=float(sh), skew_active=float(sk))
curves = {f"{L}x": curve_metrics(r_net[valid], L) for L in LEVS}

# worst single traded-night gap (crash-from-highs tail)
worst_idx = np.argmin(np.where(traded, ov, np.inf))
worst_gap = dict(date=str(ov_dates[worst_idx].date()), gap_pct=float(ov[worst_idx]*100))

# ---------- 3. FTMO 2-step first-passage simulation ----------
r = r_net.copy()
N = len(r)

def run_phase(start, target_mult, L):
    """Walk nights from `start`. Return (end_idx, status) status in {'pass','bust','run'}."""
    eq = INIT; tgt = INIT*target_mult
    i = start
    while i < N:
        chg = L * r[i]
        # daily loss breach (overnight gap is the day's move)
        if chg <= -DAILY_DD:
            return i, "bust"
        eq *= (1.0 + chg)
        if eq < FLOOR:
            return i, "bust"
        if eq >= tgt:
            return i, "pass"
        i += 1
    return N-1, "run"

def run_funded(start, L):
    """P1 then P2. Returns dict with days and outcome."""
    e1, s1 = run_phase(start, P1_TGT, L)
    if s1 != "pass":
        return dict(out=s1, d1=e1-start+1, d2=0, dtot=e1-start+1, end=e1)
    d1 = e1 - start + 1
    e2, s2 = run_phase(e1+1, P2_TGT, L)   # continue contiguous path
    d2 = e2 - (e1+1) + 1
    if s2 == "pass":
        return dict(out="funded", d1=d1, d2=d2, dtot=d1+d2, end=e2)
    return dict(out=("bust" if s2=="bust" else "run"), d1=d1, d2=d2, dtot=d1+d2, end=e2)

# rolling starts: every trading day (dense) for the first-passage distribution
starts = np.arange(0, N-5)            # need a little forward room
results = {}
WEEKS = list(range(1,11))             # 1..10 weeks
MONTHS = [3,6,9,12,18,24,30,36,42,48,54,60]
for L in LEVS:
    recs = [run_funded(s, L) for s in starts]
    out = np.array([x["out"] for x in recs])
    dtot = np.array([x["dtot"] for x in recs])
    d1 = np.array([x["d1"] for x in recs]); d2 = np.array([x["d2"] for x in recs])
    fwd = (N-1) - starts                  # forward data available (days)
    funded = out=="funded"; bust = out=="bust"; run = out=="run"
    # terminal-conditioned & total p(funded)
    term = funded | bust
    p_funded_term = funded.sum()/max(term.sum(),1)
    p_funded_total = funded.sum()/len(out)
    # P1 / P2 conditional (use starts that reached terminal in each phase)
    p1_pass = ((out=="funded") | (np.array([x["d2"]>0 for x in recs]))).mean()  # reached P2 => P1 passed
    reached_p2 = np.array([x["d2"]>0 for x in recs])
    p_P1 = reached_p2.mean() + ((funded)&(~reached_p2)).sum()/len(out)  # safety; reached_p2 captures all P1 passes
    p_P1 = reached_p2.mean()
    p_P2_given_P1 = funded.sum()/max(reached_p2.sum(),1)
    # cumulative incidence by horizon (eligible = enough forward data OR already terminal)
    def cum_inc(Hdays):
        elig = term | (fwd >= Hdays)
        num = funded & (dtot <= Hdays) & elig
        return num.sum()/max(elig.sum(),1), int(elig.sum())
    by_week  = {w: cum_inc(w*5)  for w in WEEKS}
    by_month = {m: cum_inc(m*21) for m in MONTHS}
    # time-to-pass distribution among funded (in trading days)
    ttf = dtot[funded]
    def q(a,p): return float(np.percentile(a,p)) if len(a) else float("nan")
    results[f"{L}x"] = dict(
        n_starts=int(len(out)),
        p_funded_terminal=float(p_funded_term), p_funded_total=float(p_funded_total),
        p_P1=float(p_P1), p_P2_given_P1=float(p_P2_given_P1),
        pct_bust=float(bust.mean()), pct_running=float(run.mean()),
        ttf_days=dict(median=q(ttf,50), p25=q(ttf,25), p75=q(ttf,75), mean=float(ttf.mean()) if len(ttf) else float("nan")),
        ttf_years=dict(median=q(ttf,50)/252, p25=q(ttf,25)/252, p75=q(ttf,75)/252),
        ttP1_days=dict(median=q(d1[reached_p2|funded],50)),
        by_week={w:{"p":round(v[0],4),"elig":v[1]} for w,v in by_week.items()},
        by_month={m:{"p":round(v[0],4),"elig":v[1]} for m,v in by_month.items()},
    )

# ---------- 4. Regime: by-year ----------
yr = pd.Series(ov_dates.year, index=np.arange(len(ov)))
rows=[]
for y in sorted(set(ov_dates.year)):
    msk = (ov_dates.year==y)
    tnights = traded & msk
    nb = tnights.sum()
    if nb==0:
        rows.append(dict(year=int(y), traded_nights=0)); continue
    yr_net = r_net[tnights]
    # buy&hold NQ that year (close-to-close on RTH closes)
    cidx = np.where(dates.year==y)[0]
    bh = C[cidx[-1]]/C[cidx[0]]-1 if len(cidx)>1 else np.nan
    rows.append(dict(year=int(y), traded_nights=int(nb),
        gate_on_frac=float(tnights.sum()/max((valid&msk[ :len(valid)] if False else (valid & (ov_dates.year==y))).sum(),1)),
        mean_bps=float(yr_net.mean()*1e4), total_net_pct=float((np.prod(1+yr_net)-1)*100),
        worst_night_pct=float(yr_net.min()*100), buyhold_NQ_pct=float(bh*100) if bh==bh else None))
regime = pd.DataFrame(rows)

# ---------- save ----------
summary = dict(period=f"{dates[0].date()} .. {dates[-1].date()}", n_days=int(n),
               cost_bps=COST*1e4, MA=MA, nightly=nightly, curves=curves,
               worst_traded_night=worst_gap, ftmo=results)
with open(f"{OUT}/metrics_summary.json","w") as f: json.dump(summary,f,indent=2)
regime.to_csv(f"{OUT}/regime_by_year.csv", index=False)

# by-week / by-month tables to CSV
for L in LEVS:
    k=f"{L}x"
    wk=pd.DataFrame([{"weeks":w, "p_pass":results[k]["by_week"][w]["p"], "n_elig":results[k]["by_week"][w]["elig"]} for w in WEEKS])
    mo=pd.DataFrame([{"months":m, "p_pass":results[k]["by_month"][m]["p"], "n_elig":results[k]["by_month"][m]["elig"]} for m in MONTHS])
    wk.to_csv(f"{OUT}/p_pass_by_week_{k}.csv", index=False)
    mo.to_csv(f"{OUT}/p_pass_by_month_{k}.csv", index=False)

# ---------- console report ----------
print("="*70)
print(f"NQ overnight-drift harvester | {summary['period']} | {n} trading days | cost {COST*1e4:.0f}bps/night")
print("="*70)
print("\nNIGHTLY (traded nights, net):", json.dumps(nightly["traded_net"], indent=0))
print("NIGHTLY (traded nights, gross):", json.dumps(nightly["traded_gross"], indent=0))
print("\nEQUITY-CURVE METRICS (gated overnight, compounded):")
for L in LEVS:
    c=curves[f"{L}x"]
    print(f"  {L:>4}x  CAGR {c['CAGR']*100:6.2f}%  maxDD {c['maxDD']*100:6.2f}%  Calmar {c['Calmar']:.2f}  Sharpe {c['Sharpe_ann']:.2f}  skew {c['skew_active']:+.2f}")
print(f"\nWorst single traded night: {worst_gap['date']}  {worst_gap['gap_pct']:.2f}%")
print("\nFTMO 2-STEP FIRST-PASSAGE (chained P1+10% then P2+5%):")
for L in LEVS:
    R=results[f"{L}x"]
    print(f"\n  --- {L}x  (n_starts={R['n_starts']}) ---")
    print(f"    p(funded) terminal={R['p_funded_terminal']*100:.1f}%  total={R['p_funded_total']*100:.1f}%  | bust={R['pct_bust']*100:.1f}%  running={R['pct_running']*100:.1f}%")
    print(f"    p(P1)={R['p_P1']*100:.1f}%  p(P2|P1)={R['p_P2_given_P1']*100:.1f}%")
    print(f"    time-to-funded: median {R['ttf_years']['median']:.2f}y  p25 {R['ttf_years']['p25']:.2f}y  p75 {R['ttf_years']['p75']:.2f}y")
    print(f"    p(pass) by WEEK: " + "  ".join(f"{w}w={R['by_week'][w]['p']*100:.1f}%" for w in WEEKS))
    print(f"    p(pass) by MONTH: " + "  ".join(f"{m}mo={R['by_month'][m]['p']*100:.1f}%" for m in [6,12,24,36,48,60]))
print("\nsaved -> NQ_overnight_metrics/  (json + csv tables)")
