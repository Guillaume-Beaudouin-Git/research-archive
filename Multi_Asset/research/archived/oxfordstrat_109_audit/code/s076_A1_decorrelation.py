"""
A.1 — DECORRELATION of Ross Hook (#76) vs the existing book sleeves.
Team's recommended first step: "Un sleeve validé mais corrélé n'ajoute rien a la robustesse 50%."
Question: are Ross Hook MTM daily returns decorrelated from the deployed book
(TSMOM trend engine, commodity seasonality, market beta)? And does adding it
to the book improve risk-adjusted return at the margin?

Ross Hook series = close-to-close MTM, deployable config (indices+commodities+crypto,
ex-forex), delay+1 (fill='next_open'), frozen params MN/HK/TM=10/20/10, scaled by RISK_FRAC.
ftmo_lab.py UNCHANGED. Reuses rosshook.py exactly as in s076_report_analytics.py.
"""
import numpy as np, pandas as pd, os
import ftmo_lab as lab, rosshook as rh

DATA = "/sessions/serene-elegant-faraday/mnt/data"
OUT  = "results"; os.makedirs(OUT, exist_ok=True)
RF = lab.RISK_FRAC; CLASS = lab.CLASS
MN, HK, TM = 10, 20, 10

# ---------- 1. Ross Hook MTM daily portfolio series (deployable ex-forex) ----------
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
cal = pd.DatetimeIndex(sorted(set().union(*[set(df.index) for df in uni.values()])))
DEPLOY = [t for t in uni if CLASS.get(t) in ('indices', 'commodities', 'crypto')]

def rh_daily(instrs, side='both'):
    s = pd.Series(0.0, index=cal)
    for t in instrs:
        _, dm = rh.simulate_rosshook(uni[t], MN, HK, TM, cost_bps=costs[t],
                                     fill='next_open', side=side, daily=True)
        s = s.add(dm.reindex(cal).fillna(0))
    return s * RF

RHk = rh_daily(DEPLOY)
RHk = RHk[RHk.index >= RHk[RHk != 0].index.min()]
RHk.name = "RossHook"

# same-universe internal factors (apples-to-apples on DEPLOY)
mkt = pd.concat([uni[t]['close'].pct_change().reindex(cal) for t in DEPLOY], axis=1).mean(axis=1)
mkt.name = "MKT_buyhold(DEPLOY)"
tsmom_int = pd.concat([(np.sign(uni[t]['close'].shift(1)-uni[t]['close'].shift(253))
                        *uni[t]['close'].pct_change()).reindex(cal) for t in DEPLOY], axis=1).mean(axis=1)
tsmom_int.name = "TSMOM_factor(DEPLOY,12-1)"

# ---------- 2. Existing BOOK sleeves (the team's real return series) ----------
def load_ser(path, col, name):
    d = pd.read_csv(os.path.join(DATA, path))
    d.columns = ['date'] + list(d.columns[1:])
    d['date'] = pd.to_datetime(d['date'])
    s = pd.Series(d[col].values, index=d['date']).astype(float)
    s.name = name
    return s

book = {}
book['TSMOM_deployed']   = load_ser('ftmo_research/tsmom/chosen_returns.csv', '0', 'TSMOM_deployed')
book['TSMOM_P1']         = load_ser('skew_research/MERGE_portfolio_returns.csv', 'P1_TSMOM_only', 'TSMOM_P1')
book['TSMOM_long_only']  = load_ser('trend_research/g1_sleeves.csv', 'TSMOM_long_only', 'TSMOM_long_only')
book['CommoditySeason']  = load_ser('skew_research/session_basic_trend/commodity_seasonality_oos.csv', '0', 'CommoditySeason')
book['BH_market']        = load_ser('trend_research/g1_sleeves.csv', 'BH', 'BH_market')

# drop all-zero leading rows for TSMOM_deployed
for k in book:
    s = book[k]; nz = s[s != 0]
    if len(nz): book[k] = s[s.index >= nz.index.min()]

comparators = {RHk.name: RHk, mkt.name: mkt, tsmom_int.name: tsmom_int, **book}

# ---------- 3. Correlation table (Ross Hook vs each), max-overlap ----------
def corr_row(a, b):
    d = pd.concat([a, b], axis=1).dropna()
    if len(d) < 60: return dict(n=len(d), pearson=np.nan, spearman=np.nan)
    x, y = d.iloc[:, 0], d.iloc[:, 1]
    spear = x.rank().corr(y.rank())  # Spearman = Pearson on ranks (no scipy)
    return dict(n=len(d), pearson=x.corr(y), spearman=spear)

rows = []
for name, s in comparators.items():
    if name == RHk.name: continue
    r = corr_row(RHk, s); r['sleeve'] = name; rows.append(r)
ctab = pd.DataFrame(rows)[['sleeve', 'n', 'pearson', 'spearman']]
ctab.to_csv(f"{OUT}/s076_A1_corr.csv", index=False)

# ---------- 4. Rolling 1y correlation stability (vs deployed TSMOM & commodity season) ----------
def roll_corr(a, b, win=252):
    d = pd.concat([a, b], axis=1).dropna()
    rc = d.iloc[:, 0].rolling(win).corr(d.iloc[:, 1]).dropna()
    return rc

roll_stats = {}
for k in ['TSMOM_deployed', 'TSMOM_P1', 'CommoditySeason']:
    rc = roll_corr(RHk, book[k])
    if len(rc):
        roll_stats[k] = dict(min=rc.min(), med=rc.median(), max=rc.max(), n=len(rc))

# ---------- 5. Marginal diversification: does RH improve the book Sharpe? ----------
# vol-normalise each leg to 10% annual vol, then blend. corr decides the benefit.
def vol_norm(s, target=0.10/np.sqrt(252)):
    s = s.dropna(); return s * (target / s.std())

def sharpe(s): s = s.dropna(); return s.mean()/s.std()*np.sqrt(252)

def blend_curve(book_leg, rh_leg):
    d = pd.concat([vol_norm(book_leg), vol_norm(rh_leg)], axis=1).dropna()
    d.columns = ['book', 'rh']
    out = []
    for w in np.linspace(0, 1, 11):  # w = weight on Ross Hook
        b = (1-w)*d['book'] + w*d['rh']
        out.append((round(w, 2), sharpe(b), b.std()*np.sqrt(252)))
    cur = pd.DataFrame(out, columns=['w_rh', 'sharpe', 'vol'])
    # 2-asset long-only Sharpe-optimal weight (closed form on vol-normed corr)
    rho = d['book'].corr(d['rh']); mb, mr = d['book'].mean(), d['rh'].mean()
    # marginal Sharpe of adding RH at w=0: positive iff corr(rh,book) < Sh_rh/Sh_book
    sh_b, sh_r = sharpe(d['book']), sharpe(d['rh'])
    adds = rho < (sh_r/sh_b) if sh_b > 0 else None
    return cur, rho, sh_b, sh_r, adds, len(d)

blend = {}
for k in ['TSMOM_deployed', 'TSMOM_P1', 'CommoditySeason']:
    cur, rho, sh_b, sh_r, adds, n = blend_curve(book[k], RHk)
    cur.to_csv(f"{OUT}/s076_A1_blend_{k}.csv", index=False)
    blend[k] = dict(rho=rho, sh_book=sh_b, sh_rh=sh_r, adds=adds, n=n,
                    sh_at_0=cur.iloc[0]['sharpe'], sh_best=cur['sharpe'].max(),
                    w_best=cur.loc[cur['sharpe'].idxmax(), 'w_rh'])

# ---------- print ----------
print("="*72)
print("A.1 DECORRELATION — Ross Hook (#76) vs existing book")
print(f"Ross Hook MTM daily series: {RHk.index.min().date()} -> {RHk.index.max().date()}  "
      f"N={len(RHk)}  ann.Sharpe={sharpe(RHk):.2f}  ann.vol={RHk.std()*np.sqrt(252)*100:.1f}%(RF-scaled)")
print("\n--- Pearson / Spearman correlation (max overlap) ---")
print(ctab.to_string(index=False, float_format=lambda x: f"{x:+.3f}"))
print("\n--- Rolling 1y correlation stability ---")
for k, v in roll_stats.items():
    print(f"  {k:18s}: min {v['min']:+.2f}  median {v['med']:+.2f}  max {v['max']:+.2f}  (n={v['n']})")
print("\n--- Marginal diversification (vol-normed 10%, blend book+RossHook) ---")
print("  rule: RH adds Sharpe at margin iff corr < Sharpe_RH/Sharpe_book")
for k, v in blend.items():
    print(f"  {k:16s}: corr={v['rho']:+.3f}  Sh_book={v['sh_book']:.2f}  Sh_RH={v['sh_rh']:.2f}  "
          f"adds={v['adds']}  | blend Sh {v['sh_at_0']:.2f}(w0)->{v['sh_best']:.2f}(w*={v['w_best']})")
print("="*72)
