import pandas as pd
import numpy as np
import statsmodels.api as sm

df = pd.read_parquet("<HOME>/Desktop/Algo_claude/PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet")
df = df.reset_index()
df['date'] = pd.to_datetime(df['date'])
df['year'] = df['date'].dt.year

cost_cols = ['r_gross', 'r_1 bps RT (aggressive)', 'r_2 bps RT (median)', 'r_3 bps RT (conservative)', 'r_Futures 1 pt (realistic)']

def hac_t(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 5:
        return np.nan, np.nan, n
    X = np.ones(n)
    model = sm.OLS(x, X).fit(cov_type='HAC', cov_kwds={'maxlags': 6})
    return model.params[0], model.tvalues[0], n

tranches = [(2010,2013),(2014,2017),(2018,2021),(2022,2026)]

print("=== 4-year tranches, per cost column ===")
for col in cost_cols:
    print(f"\n--- {col} ---")
    for lo,hi in tranches:
        sub = df[(df['year']>=lo)&(df['year']<=hi)][col].dropna()
        mean, t, n = hac_t(sub.values)
        print(f"{lo}-{hi}: n={n:5d} mean={mean:+.4f}R  t_HAC={t:+.2f}")

print("\n=== yearly breakdown, r_2 bps RT (median) ===")
for y, g in df.groupby('year'):
    x = g['r_2 bps RT (median)'].dropna().values
    mean, t, n = hac_t(x)
    wr = (g['r_realised']>0).mean()
    print(f"{y}: n={n:4d} mean={mean:+.4f}R t={t:+.2f} WR={wr:.3f} outcome_stop_frac={(g['outcome']=='STOP').mean():.3f}")

print("\n=== yearly breakdown, r_gross ===")
for y, g in df.groupby('year'):
    x = g['r_gross'].dropna().values
    mean, t, n = hac_t(x)
    print(f"{y}: n={n:4d} mean={mean:+.4f}R t={t:+.2f}")

print("\n=== regime_tag distribution by tranche ===")
for lo,hi in tranches:
    sub = df[(df['year']>=lo)&(df['year']<=hi)]
    print(lo,hi, sub['regime_tag'].value_counts(normalize=True).to_dict())

print("\n=== or_range (opening range size) stats by tranche ===")
for lo,hi in tranches:
    sub = df[(df['year']>=lo)&(df['year']<=hi)]
    print(lo,hi, "or_range mean", sub['or_range'].mean(), "median", sub['or_range'].median(), "ttb_5min mean", sub['ttb_5min'].mean())

print("\n=== outcome (STOP vs TIME_STOP) by tranche ===")
for lo,hi in tranches:
    sub = df[(df['year']>=lo)&(df['year']<=hi)]
    print(lo,hi, sub['outcome'].value_counts(normalize=True).to_dict(), "n=",len(sub))

print("\n=== direction win rate by tranche ===")
for lo,hi in tranches:
    sub = df[(df['year']>=lo)&(df['year']<=hi)]
    for d in [1,-1]:
        s2 = sub[sub['direction']==d]
        print(lo,hi,"dir",d,"n=",len(s2),"WR",(s2['r_realised']>0).mean(),"mean_r_gross",s2['r_gross'].mean())

df.to_csv("<HOME>/Desktop/Algo_claude/.worktrees/regime-diag/Multi_Asset/research/active/regime_diagnostic_2026-09/out/orb_trades_annotated.csv", index=False)

print("\n=== or_range as bps of entry (normalized vol proxy) ===")
df['or_bps'] = 1e4 * df['or_range'] / df['entry']
for lo,hi in tranches:
    sub = df[(df['year']>=lo)&(df['year']<=hi)]
    print(lo,hi, "or_bps mean", round(sub['or_bps'].mean(),1), "median", round(sub['or_bps'].median(),1))

print("\n=== yearly or_bps ===")
for y,g in df.groupby('year'):
    print(y, round(g['or_bps'].mean(),1), round(g['or_bps'].median(),1))

print("\n=== monthly seasonality, r_2bps RT median, pooled all years ===")
df['month'] = df['date'].dt.month
for m,g in df.groupby('month'):
    x = g['r_2 bps RT (median)'].dropna().values
    mean,t,n = hac_t(x)
    print(f"month {m:2d}: n={n:4d} mean={mean:+.4f} t={t:+.2f}")

print("\n=== monthly seasonality restricted to 2022-2026 ===")
sub = df[df['year']>=2022]
for m,g in sub.groupby('month'):
    x = g['r_2 bps RT (median)'].dropna().values
    mean,t,n = hac_t(x)
    print(f"month {m:2d}: n={n:4d} mean={mean:+.4f} t={t:+.2f}")

print("\n=== rolling 1-year (252 trade approx not applicable; use calendar year) already done above ===")

# correlate or_bps with subsequent-year performance: does high or_bps year predict positive mean_r?
yearly = df.groupby('year').agg(or_bps=('or_bps','mean'), mean_r2=('r_2 bps RT (median)','mean'), n=('r_2 bps RT (median)','size'))
print(yearly)
print("\ncorr(or_bps, mean_r2) across years:", yearly['or_bps'].corr(yearly['mean_r2']))

print("\n=== distribution shape (skew, top-decile contribution) per tranche, r_2bps ===")
from scipy import stats as sstats
for lo,hi in tranches:
    sub = df[(df['year']>=lo)&(df['year']<=hi)]['r_2 bps RT (median)'].dropna()
    total = sub.sum()
    top_decile_n = max(1,int(len(sub)*0.1))
    top_decile_sum = sub.sort_values(ascending=False).head(top_decile_n).sum()
    print(lo,hi,"skew",round(sstats.skew(sub),2),"total_R",round(total,1),
          "top10pct_contrib_frac", round(top_decile_sum/total,2) if total!=0 else np.nan,
          "n_trades", len(sub))

print("\n=== regime column raw values ===")
print(df['regime'].value_counts())

print("\n=== direction bias per year (mean direction, +1=long -1=short) ===")
for y,g in df.groupby('year'):
    print(y, "mean_dir", round(g['direction'].mean(),3), "n_long", (g['direction']==1).sum(), "n_short",(g['direction']==-1).sum())
