import pandas as pd, numpy as np
import statsmodels.api as sm

sm_df = pd.read_csv("<HOME>/Desktop/Algo_claude/Multi_Asset/research/active/funded_1y_mono_2026-08/attribution/serie_mensuelle.csv")
sm_df['on_combo'] = sm_df['on_us100'] + sm_df['on_ger40']
print("n months:", len(sm_df), sm_df['mois'].min(), sm_df['mois'].max())

def hac_t(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    X = np.ones(n)
    model = sm.OLS(x, X).fit(cov_type='HAC', cov_kwds={'maxlags': 6})
    return model.params[0], model.tvalues[0], n

print("\ncorr(on_combo, orb) monthly:", sm_df['on_combo'].corr(sm_df['orb']))
print("corr(on_us100, orb):", sm_df['on_us100'].corr(sm_df['orb']))
print("corr(on_ger40, orb):", sm_df['on_ger40'].corr(sm_df['orb']))

# worst decile months for on_combo -> what does orb do
q10 = sm_df['on_combo'].quantile(0.10)
q25 = sm_df['on_combo'].quantile(0.25)
worst_on = sm_df[sm_df['on_combo']<=q25]
rest_on = sm_df[sm_df['on_combo']>q25]
print(f"\non_combo worst quartile (<= {q25:.2f}%), n={len(worst_on)}: orb mean = {worst_on['orb'].mean():.3f}%  vs rest orb mean = {rest_on['orb'].mean():.3f}%  (unconditional orb mean {sm_df['orb'].mean():.3f}%)")

q10o = sm_df['orb'].quantile(0.25)
worst_orb = sm_df[sm_df['orb']<=q10o]
rest_orb = sm_df[sm_df['orb']>q10o]
print(f"orb worst quartile (<= {q10o:.2f}%), n={len(worst_orb)}: on_combo mean = {worst_orb['on_combo'].mean():.3f}%  vs rest on_combo mean = {rest_orb['on_combo'].mean():.3f}%  (unconditional on_combo mean {sm_df['on_combo'].mean():.3f}%)")

# joint bad months: both below their own median
med_on = sm_df['on_combo'].median()
med_orb = sm_df['orb'].median()
both_bad = ((sm_df['on_combo']<med_on) & (sm_df['orb']<med_orb)).sum()
expected = len(sm_df)*0.25
print(f"\nmonths both below median: {both_bad} / {len(sm_df)} (expected under independence: {expected:.1f})")

both_bad10 = ((sm_df['on_combo']<=sm_df['on_combo'].quantile(0.25)) & (sm_df['orb']<=sm_df['orb'].quantile(0.25))).sum()
expected10 = len(sm_df)*0.0625
print(f"months both in worst quartile: {both_bad10} / {len(sm_df)} (expected under independence: {expected10:.2f})")

# portfolio combined drawdown analysis: does combining reduce tail vs either solo?
print("\nportfolio (on+ger+orb weighted?) vol vs solo legs (using raw sum, not weighted):")
sm_df['combo_naive'] = sm_df['on_us100'] + sm_df['on_ger40'] + sm_df['orb']
print("std on_combo:", sm_df['on_combo'].std(), "std orb:", sm_df['orb'].std(), "std combo_naive:", sm_df['combo_naive'].std())
print("worst month on_combo:", sm_df.loc[sm_df['on_combo'].idxmin(), ['mois','on_combo','orb']].to_dict())
print("worst month orb:", sm_df.loc[sm_df['orb'].idxmin(), ['mois','on_combo','orb']].to_dict())
print("worst month combo_naive:", sm_df.loc[sm_df['combo_naive'].idxmin(), ['mois','on_combo','orb','combo_naive']].to_dict())

# annual table combining orb_annual with on_combo_annual
sm_df['year'] = sm_df['mois'].str[:4]
ann = sm_df.groupby('year').agg(on_combo=('on_combo','sum'), orb=('orb','sum'))
ann['orb_rank'] = ann['orb'].rank()
ann['on_rank'] = ann['on_combo'].rank()
print("\nannual table (sum of monthly %):")
print(ann)
print("\nspearman corr annual on_combo vs orb:", ann['on_combo'].corr(ann['orb'], method='spearman'))
print("pearson corr annual on_combo vs orb:", ann['on_combo'].corr(ann['orb']))
