"""
Cross-Sectional Short-Term Reversal (STR) — 30-min Feasibility Check
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

# ── Constants ─────────────────────────────────────────────────────────────────
ROUND_TRIP_COST = 0.0034
TOP_N = 3
TURNOVER_EST = 0.60
START = "2021-01-01"
END   = "2025-01-01"
UNIVERSE = [
    "BTC-USD","ETH-USD","SOL-USD","BNB-USD","AVAX-USD",
    "LINK-USD","DOT-USD","AAVE-USD","LTC-USD","ADA-USD",
    "ATOM-USD","DOGE-USD","XRP-USD","TRX-USD","NEAR-USD"
]

# ── Data Download ──────────────────────────────────────────────────────────────
print("Downloading data...")
raw = yf.download(UNIVERSE, start=START, end=END, auto_adjust=True, progress=False)["Close"]
if isinstance(raw, pd.Series):
    raw = raw.to_frame()

# Weekly resample: last close of each week
prices = raw.resample("W").last()

# Drop assets with >10% missing weeks
missing_frac = prices.isna().mean()
prices = prices.loc[:, missing_frac <= 0.10]
prices = prices.dropna(how="all")

# Drop all-NaN rows
prices = prices.dropna(how="all")
assets = list(prices.columns)
n_assets = len(assets)
print(f"Assets retained: {assets}")

# Weekly returns
weekly_ret = prices.pct_change()

# Drop first row (NaN returns)
weekly_ret = weekly_ret.iloc[1:]
prices     = prices.iloc[1:]

# ── Signal ─────────────────────────────────────────────────────────────────────
signal_t    = -1 * weekly_ret.shift(1)
signal_norm = signal_t.rank(axis=1, pct=True) - 0.5

# Align: drop rows where either is all-NaN
valid_idx = signal_norm.dropna(how="all").index.intersection(
            weekly_ret.dropna(how="all").index)
signal_norm = signal_norm.loc[valid_idx]
weekly_ret  = weekly_ret.loc[valid_idx]

# ── 1. Weekly IC ───────────────────────────────────────────────────────────────
ic_list = []
for t in valid_idx:
    s = signal_norm.loc[t].dropna()
    r = weekly_ret.loc[t].dropna()
    common = s.index.intersection(r.index)
    if len(common) < 4:
        continue
    rho, _ = spearmanr(s[common], r[common])
    if not np.isnan(rho):
        ic_list.append(rho)

IC = pd.Series(ic_list)
mean_IC  = IC.mean()
std_IC   = IC.std()
n_weeks  = len(IC)
t_stat   = mean_IC / (std_IC / np.sqrt(n_weeks))
ICIR     = mean_IC / std_IC
hit_rate = (IC > 0).mean()

# ── 2. Long-only IC ────────────────────────────────────────────────────────────
long_ic_list = []
for t in valid_idx:
    s = signal_norm.loc[t].dropna()
    r = weekly_ret.loc[t].dropna()
    common = s.index.intersection(r.index)
    if len(common) < TOP_N + 1:
        continue
    top_assets = s[common].nlargest(TOP_N).index
    s_top = s[top_assets]
    r_top = r[top_assets]
    if len(s_top) < 2:
        continue
    rho, _ = spearmanr(s_top, r_top)
    if not np.isnan(rho):
        long_ic_list.append(rho)

long_IC = np.mean(long_ic_list) if long_ic_list else np.nan

# ── 3. Cost Breakeven IC ───────────────────────────────────────────────────────
avg_weekly_vol = weekly_ret.std().mean()
min_IC = ROUND_TRIP_COST * TURNOVER_EST / avg_weekly_vol

# ── 4. Rolling IC Chart ────────────────────────────────────────────────────────
ic_series = pd.Series(IC.values, index=valid_idx[:len(IC)])
rolling_52 = ic_series.rolling(52).mean()
rolling_std = ic_series.rolling(52).std()

fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(rolling_52.index, rolling_52, label="52w Rolling Mean IC", color="steelblue", lw=1.8)
ax.fill_between(
    rolling_52.index,
    rolling_52 - rolling_std,
    rolling_52 + rolling_std,
    alpha=0.2, color="steelblue", label="±1 Std"
)
ax.axhline(0, color="black", lw=0.8, ls="--")
ax.axhline(min_IC, color="red", lw=1, ls=":", label=f"Cost Breakeven ({min_IC:.3f})")
ax.set_title("STR — 52-Week Rolling IC (Cross-Sectional)")
ax.set_ylabel("Spearman IC")
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("str_ic_rolling.png", dpi=150)
plt.close(fig)
print("Chart saved: str_ic_rolling.png")

# ── Verdict ────────────────────────────────────────────────────────────────────
pass_count = sum([
    mean_IC > 0.02,
    t_stat > 1.5,
    ICIR > 0.3,
    hit_rate > 0.52,
])
marginal = (
    (1.0 <= t_stat <= 1.5 or 0.2 <= ICIR <= 0.3) and
    (long_IC > min_IC)
)

if pass_count == 4:
    verdict = "PASS"
elif t_stat < 1.0 or hit_rate < 0.50 or mean_IC < min_IC:
    verdict = "FAIL"
elif marginal:
    verdict = "MARGINAL"
else:
    verdict = "FAIL"

def flag(cond): return "✓" if cond else "✗"

print()
print("─────────────────────────────────────────")
print("  STR FEASIBILITY REPORT")
print("─────────────────────────────────────────")
print(f"  Assets:         {n_assets} (after dropping thin)")
print(f"  Weeks:          {n_weeks}")
print(f"  Period:         {START} → {END}")
print()
print(f"  Mean IC:        {mean_IC:.3f}  {flag(mean_IC > 0.02)} [PASS if > 0.02]")
print(f"  IC t-stat:      {t_stat:.2f}   {flag(t_stat > 1.5)} [PASS if > 1.5]")
print(f"  ICIR:           {ICIR:.2f}   {flag(ICIR > 0.3)} [PASS if > 0.3]")
print(f"  Hit rate:       {hit_rate*100:.1f}%  {flag(hit_rate > 0.52)} [PASS if > 52%]")
print(f"  Long-only IC:   {long_IC:.3f}")
print(f"  Cost breakeven: {min_IC:.3f}  (need Mean IC > this)")
print()
print(f"  VERDICT: {verdict}")
print("─────────────────────────────────────────")
print()
print("  MARGINAL = t-stat 1.0-1.5 OR ICIR 0.2-0.3 (worth full backtest")
print("             only if long-only IC also > cost breakeven)")
print("  FAIL = any of: t-stat < 1.0, hit rate < 50%,")
print("         mean IC < cost breakeven")
