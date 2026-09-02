import pandas as pd, numpy as np

daily = pd.read_csv("<HOME>/Desktop/Algo_claude/Multi_Asset/research/active/funded_1y_mono_2026-08/attribution/daily_raw.csv", parse_dates=['date'])
daily['year'] = daily['date'].dt.year

# Overnight sleeve: only rows where is_on_day==1 have live px_ret; but gaps/vol should be computed on ON days only
on = daily[daily['is_on_day']==1].copy()
on['on_combo_ret'] = on['on_us100'] + on['on_ger40']  # net-of-cost overnight per trading occasion

print("=== L54 test — OVERNIGHT sleeve: yearly vol vs yearly mean, ON-days only ===")
g = on.groupby('year').agg(
    n=('on_combo_ret','size'),
    mean_ret=('on_combo_ret','mean'),
    std_ret=('on_combo_ret','std'),
    mean_us100_pxret=('on_us100_px_ret','mean'),
    std_us100_pxret=('on_us100_px_ret','std'),
)
print(g)
print("\ncorr(std_ret, mean_ret) across years:", g['std_ret'].corr(g['mean_ret']))
print("corr(std_us100_pxret, mean_ret) across years:", g['std_us100_pxret'].corr(g['mean_ret']))

print("\n=== ORB sleeve (funded ledger, post-2013) — yearly vol vs mean, ORB days only ===")
orb_daily = daily[daily['orb_live']==1].copy() if 'orb_live' in daily.columns else daily.copy()
g2 = orb_daily.groupby('year').agg(
    n=('orb','size'),
    mean_ret=('orb','mean'),
    std_ret=('orb','std'),
    mean_or_bps=('orb_or_bps','mean'),
    std_or_bps=('orb_or_bps','std'),
)
print(g2)
print("\ncorr(std_ret, mean_ret) across years:", g2['std_ret'].corr(g2['mean_ret']))
print("corr(mean_or_bps, mean_ret) across years:", g2['mean_or_bps'].corr(g2['mean_ret']))

# gap_days distribution -- weekend/holiday gaps
print("\n=== gap_days distribution on ON days ===")
print(on['gap_days'].value_counts())
