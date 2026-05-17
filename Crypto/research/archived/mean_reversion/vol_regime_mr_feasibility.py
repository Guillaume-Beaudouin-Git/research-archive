"""
Vol-Regime Mean Reversion — Feasibility Check
Signal: -1 * 5-day price z-score, filtered to low-vol regime days only
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
ROUND_TRIP_COST    = 0.0034
LOW_VOL_PERCENTILE = 0.40
LOOKBACK_VOL       = 20
SIGNAL_WINDOW      = 5
ASSET              = "BTC-USD"
START              = "2019-01-01"
END                = "2025-01-01"

# ── Data ──────────────────────────────────────────────────────────────────────
print("Downloading data...")
raw   = yf.download(ASSET, start=START, end=END, auto_adjust=True, progress=False)["Close"].squeeze()
price = raw.dropna()

daily_ret = price.pct_change()

# ── Vol Regime ────────────────────────────────────────────────────────────────
rv_20d          = daily_ret.rolling(LOOKBACK_VOL).std() * np.sqrt(252)
vol_threshold   = rv_20d.expanding(min_periods=60).quantile(LOW_VOL_PERCENTILE)
low_vol_mask    = rv_20d < vol_threshold          # True on low-vol days (no lookahead)
duty_cycle      = float(low_vol_mask.mean())

# ── Signal ────────────────────────────────────────────────────────────────────
roll_mean = price.rolling(LOOKBACK_VOL).mean()
roll_std  = price.rolling(LOOKBACK_VOL).std()
zscore    = (price - roll_mean) / roll_std
signal    = -1.0 * zscore                         # mean-reversion direction

# Outcome = next-day return
outcome   = daily_ret.shift(-1)

# ── Build aligned frame, restrict to low-vol regime ──────────────────────────
df = pd.DataFrame({"signal": signal, "outcome": outcome, "low_vol": low_vol_mask})
df = df.dropna()
df_lv = df[df["low_vol"]].copy()

# ── IC per day (within low-vol days) ─────────────────────────────────────────
# Daily IC is degenerate (one obs per row in a single-asset context).
# Use weekly blocks instead: group by ISO week, compute IC within each week.
df_lv["week"] = df_lv.index.to_period("W")
weekly_ic = []
for _, grp in df_lv.groupby("week"):
    if len(grp) < 3:
        continue
    rho, _ = spearmanr(grp["signal"], grp["outcome"])
    if not np.isnan(rho):
        weekly_ic.append(rho)

IC       = pd.Series(weekly_ic)
mean_IC  = float(IC.mean())
std_IC   = float(IC.std())
n_obs    = len(IC)
t_stat   = mean_IC / (std_IC / np.sqrt(n_obs))
ICIR     = mean_IC / std_IC
hit_rate = float((IC > 0).mean())

# ── Cost Breakeven ────────────────────────────────────────────────────────────
avg_daily_vol = float(daily_ret.std())
# Express in weekly terms (signal predicts next-day return, so use daily vol)
min_IC = ROUND_TRIP_COST / avg_daily_vol

# ── Rolling IC chart + duty cycle overlay ────────────────────────────────────
ic_series = pd.Series(IC.values)
rolling_26 = ic_series.rolling(26).mean()
rolling_std_ic = ic_series.rolling(26).std()

fig, axes = plt.subplots(2, 1, figsize=(13, 9), sharex=False)

# Top: BTC price with low-vol shading
ax1 = axes[0]
ax1.plot(price.index, price.values, color="steelblue", lw=1.2, label="BTC-USD")
# Shade low-vol periods
in_regime = False
start_shade = None
for date, is_lv in low_vol_mask.fillna(False).items():
    if is_lv and not in_regime:
        start_shade = date
        in_regime = True
    elif not is_lv and in_regime:
        ax1.axvspan(start_shade, date, color="gold", alpha=0.25)
        in_regime = False
if in_regime:
    ax1.axvspan(start_shade, low_vol_mask.index[-1], color="gold", alpha=0.25)
ax1.set_ylabel("Price (USD)")
ax1.set_title(f"BTC-USD — Low-Vol Regime (gold) | Duty Cycle: {duty_cycle:.1%} | Threshold: {float(vol_threshold.dropna().iloc[-1]):.1%} ann. vol (expanding)")
ax1.legend()
ax1.grid(alpha=0.3)

# Bottom: rolling IC
ax2 = axes[1]
x = np.arange(len(rolling_26))
ax2.plot(x, rolling_26, color="steelblue", lw=1.8, label="26w Rolling Mean IC")
ax2.fill_between(x,
                 rolling_26 - rolling_std_ic,
                 rolling_26 + rolling_std_ic,
                 alpha=0.2, color="steelblue", label="±1 Std")
ax2.axhline(0,      color="black", lw=0.8, ls="--")
ax2.axhline(min_IC, color="red",   lw=1.0, ls=":", label=f"Cost Breakeven ({min_IC:.3f})")
ax2.set_xlabel("Weeks (low-vol regime only)")
ax2.set_ylabel("Spearman IC")
ax2.set_title("Vol-Regime MR — 26-Week Rolling IC (low-vol weeks only)")
ax2.legend()
ax2.grid(alpha=0.3)

fig.tight_layout()
fig.savefig("vol_regime_ic.png", dpi=150)
plt.close(fig)
print("Chart saved: vol_regime_ic.png")

# ── Verdict ───────────────────────────────────────────────────────────────────
duty_ok = 0.25 <= duty_cycle <= 0.60
verdict = "PASS" if (t_stat > 1.5 and mean_IC > min_IC and duty_ok) else "FAIL"

def flag(cond): return "✓" if cond else "✗"

print()
print("─────────────────────────────────────────────")
print("  VOL-REGIME MR FEASIBILITY REPORT")
print("─────────────────────────────────────────────")
print(f"  Asset:          {ASSET}")
print(f"  Period:         {START} → {END}")
print(f"  Total days:     {len(df)}")
print(f"  Low-vol days:   {len(df_lv)}  ({duty_cycle:.1%} duty cycle) {flag(duty_ok)}")
print(f"  Low-vol weeks:  {n_obs}  (≥3 obs per week)")
print(f"  Vol threshold:  {float(vol_threshold.dropna().iloc[-1]):.1%} annualized (expanding, final value)")
print()
print(f"  Mean IC:        {mean_IC:.3f}  {flag(mean_IC > min_IC)} [PASS if > cost breakeven]")
print(f"  IC t-stat:      {t_stat:.2f}   {flag(t_stat > 1.5)} [PASS if > 1.5]")
print(f"  ICIR:           {ICIR:.2f}   {flag(abs(ICIR) > 0.3)}")
print(f"  Hit rate:       {hit_rate*100:.1f}%  {flag(hit_rate > 0.52)}")
print(f"  Cost breakeven: {min_IC:.3f}  (daily vol = {avg_daily_vol:.3f})")
print()
print(f"  VERDICT: {verdict}")
print("─────────────────────────────────────────────")
print()
print("  PASS = t-stat > 1.5 AND mean IC > cost breakeven AND duty cycle 25-60%")
