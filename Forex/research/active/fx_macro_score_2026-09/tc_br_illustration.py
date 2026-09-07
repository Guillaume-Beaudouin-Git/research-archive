"""
Illustrative TC/BR measurement on the FLAGGED (subsequently REJECTED on regime-stability
grounds, see RAPPORT §C) AUDUSD/z/h20 case -- demonstrates the measurement methodology
the mission asked for (TC measured, not fixed at 0.20; BR = actual tradable opportunities,
not observation count), NOT a validated result to deploy.
"""
import numpy as np, pandas as pd
from build_scores import load_events
from analysis import PAIRS, CATS_DEFAULT, CACHE, HALF_LIVES
from placebo import currency_daily_contrib, decayed_scores_fast

events = load_events()
pair = "AUDUSD"; base, quote = PAIRS[pair]
fx = pd.read_parquet(f"{CACHE}/{pair}_daily_ny17.parquet")
fx.index = pd.to_datetime(fx.index)

hl = 90  # half-life that dominated fold selection for this pair/xi
contribs = {ccy: currency_daily_contrib(events, ccy, CATS_DEFAULT) for ccy in (base, quote)}
idx_full = None
for ccy in (base, quote):
    idx_full = contribs[ccy].index if idx_full is None else idx_full.union(contribs[ccy].index)
idx_full = pd.date_range(idx_full.min(), idx_full.max(), freq="D")
sb = decayed_scores_fast(contribs[base], hl, idx_full)
sq = decayed_scores_fast(contribs[quote], hl, idx_full)
pair_score = sb - sq
s_aligned = pair_score.reindex(fx.index.union(pair_score.index)).sort_index().ffill()
s_aligned = s_aligned.reindex(fx.index)
s_lag1 = s_aligned.shift(1)

fwd_ret = fx["close"].apply(np.log).diff(20).shift(-20)

# BR: rolling causal quantile threshold (q=0.80, 2y=504d lookback), pre-registered choice
abs_s = s_lag1.abs()
thresh = abs_s.rolling(504, min_periods=252).quantile(0.80)
raw_sign = np.sign(s_lag1)
active = abs_s > thresh
position = pd.Series(np.where(active, raw_sign, 0.0), index=s_lag1.index)
position = position.replace(0.0, np.nan).ffill().fillna(0.0)  # hold last active direction until flat/flip
# count direction changes (entries) as "trades"
trade_flags = (position != position.shift(1)) & (position != 0)
n_years = (fx.index[-1] - fx.index[0]).days / 365.25
BR_measured = trade_flags.sum() / n_years
print(f"BR (measured, trades/year, q=0.80 rolling threshold): {BR_measured:.2f}")
print(f"  (vs. raw observation count / year = {len(s_lag1.dropna())/n_years:.1f} -- Dedale's breadth=1755 conflated these)")

# TC: IC of the realized discretized position vs continuous frictionless sign(score)
y = fwd_ret.values
m_all = np.isfinite(y) & np.isfinite(raw_sign.values) & np.isfinite(position.values)
ic_continuous = np.corrcoef(raw_sign.values[m_all], y[m_all])[0, 1]
ic_realized = np.corrcoef(position.values[m_all], y[m_all])[0, 1]
print(f'  n valid for TC calc: {m_all.sum()} (raw_sign nan: {np.isnan(raw_sign.values).sum()})')
TC_measured = ic_realized / ic_continuous if ic_continuous != 0 else np.nan
print(f"IC continuous (frictionless sign(score)): {ic_continuous:.4f}")
print(f"IC realized (discretized T-1/T rule, q=0.80 gate): {ic_realized:.4f}")
print(f"TC measured = IC_realized / IC_continuous: {TC_measured:.4f}")

IC_flagged = 0.176641  # abs value of the (rejected) walk-forward pooled OOS IC
sigma_target = 0.10
gross_annual = 0.40 * IC_flagged * np.sqrt(BR_measured) * sigma_target
print(f"\n--- IJR gate on the (REJECTED) flagged IC, for reference only ---")
print(f"gross_annual = 0.40 x {IC_flagged} x sqrt({BR_measured:.1f}) x {sigma_target} = {gross_annual:.4%}")
for name, cost_bps in [("Eightcap Raw (~0.75bps, UNVERIFIED)", 0.75), ("FTMO (2.48bps, measured)", 2.48), ("IBKR IDEALPRO (~0.45bps + $2 min/order)", 0.45)]:
    cost_frac = cost_bps / 1e4
    drag = cost_frac * BR_measured
    ratio = gross_annual / drag if drag > 0 else np.nan
    print(f"  {name}: annual drag {drag:.4%}, gate ratio {ratio:.2f}x {'PASS' if ratio>=3 else 'FAIL'}")
