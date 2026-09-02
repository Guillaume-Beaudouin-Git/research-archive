import pandas as pd, numpy as np

df = pd.read_parquet("<HOME>/Desktop/Algo_claude/PropFirms/ftmo/program_2026-06/ftmo_research/audit/nq_v2_trades.parquet").reset_index()
df['date'] = pd.to_datetime(df['date'])
df['or_bps'] = 1e4*df['or_range']/df['entry']
df['r'] = df['r_2 bps RT (median)']
df = df.sort_values('date').reset_index(drop=True)

# EX-ANTE test: trailing 60-trade avg or_bps (lagged, no lookahead) -> next 60-trade forward mean return
W = 60
df['or_bps_trail'] = df['or_bps'].shift(1).rolling(W).mean()  # strictly past info
df['r_fwd60'] = df['r'].shift(-1).rolling(W).mean().shift(-(W-1))  # forward window starting next trade
valid = df.dropna(subset=['or_bps_trail','r_fwd60'])
print("ORB: corr(trailing OR-width(60), forward 60-trade mean r):", valid['or_bps_trail'].corr(valid['r_fwd60']), "n=",len(valid))

# split into high/low trailing or_bps and see forward return
med = valid['or_bps_trail'].median()
hi = valid[valid['or_bps_trail']>med]['r_fwd60']
lo = valid[valid['or_bps_trail']<=med]['r_fwd60']
print(f"  high trailing OR -> fwd mean {hi.mean():.4f} (n={len(hi)})  |  low trailing OR -> fwd mean {lo.mean():.4f} (n={len(lo)})")

# Same test but trailing realized mean-r (does past performance predict future performance -- momentum in the strategy itself)
df['r_trail'] = df['r'].shift(1).rolling(W).mean()
valid2 = df.dropna(subset=['r_trail','r_fwd60'])
print("\nORB: corr(trailing 60-trade mean r, forward 60-trade mean r) [strategy momentum test]:", valid2['r_trail'].corr(valid2['r_fwd60']), "n=",len(valid2))

print("\n--- OVERNIGHT ex-ante test ---")
daily = pd.read_csv("<HOME>/Desktop/Algo_claude/Multi_Asset/research/active/funded_1y_mono_2026-08/attribution/daily_raw.csv", parse_dates=['date'])
on = daily[daily['is_on_day']==1].copy().sort_values('date').reset_index(drop=True)
on['ret'] = on['on_us100']+on['on_ger40']
on['pxvol'] = on['on_us100_px_ret'].abs()  # realized overnight move magnitude, proxy for vol
Wd = 26  # ~half year of ON occasions (weekly-ish, 2/wk => ~13 weeks)
on['pxvol_trail'] = on['pxvol'].shift(1).rolling(Wd).mean()
on['ret_fwd'] = on['ret'].shift(-1).rolling(Wd).mean().shift(-(Wd-1))
validO = on.dropna(subset=['pxvol_trail','ret_fwd'])
print("Overnight: corr(trailing realized overnight-move(26 occ), forward mean ret):", validO['pxvol_trail'].corr(validO['ret_fwd']), "n=",len(validO))
med2 = validO['pxvol_trail'].median()
hi2 = validO[validO['pxvol_trail']>med2]['ret_fwd']
lo2 = validO[validO['pxvol_trail']<=med2]['ret_fwd']
print(f"  high trailing vol -> fwd mean {hi2.mean():.5f} (n={len(hi2)}) | low trailing vol -> fwd mean {lo2.mean():.5f} (n={len(lo2)})")

# detection lag: how many ON-occasions for a rolling realized-vol z-score to flag current regime shift (2015->2016) as example
on['year']=on['date'].dt.year
print("\ntrailing pxvol(26) by year (mean):")
print(on.groupby('year')['pxvol_trail'].mean())
