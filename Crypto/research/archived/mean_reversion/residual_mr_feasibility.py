"""
BTC-Neutral Residual Mean Reversion — Feasibility Check
Signal: -1 * z-score of alt's residual log return after BTC beta hedge
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
ROUND_TRIP_COST   = 0.0034
BETA_WINDOW       = 180
ZSCORE_WINDOW     = 30
ENTRY_THRESHOLD   = 1.5
EXIT_THRESHOLD    = 0.0
FORWARD_DAYS      = 5
START             = "2020-01-01"
END               = "2025-01-01"
ASSETS            = ["ETH-USD", "SOL-USD", "BNB-USD"]

# ── Download ──────────────────────────────────────────────────────────────────
print("Downloading data...")
tickers = ["BTC-USD"] + ASSETS
raw = yf.download(tickers, start=START, end=END, auto_adjust=True, progress=False)["Close"]
if isinstance(raw, pd.Series):
    raw = raw.to_frame()
raw = raw.dropna(how="all")

# Drop assets with >5% missing days
missing = raw.isna().mean()
dropped = [c for c in raw.columns if missing[c] > 0.05 and c != "BTC-USD"]
if dropped:
    print(f"  Dropped (>5% missing): {dropped}")
    raw = raw.drop(columns=dropped)

raw = raw.dropna(subset=["BTC-USD"])
prices   = raw.copy()
log_ret  = np.log(prices / prices.shift(1))
btc_ret  = log_ret["BTC-USD"]
active   = [a for a in ASSETS if a in raw.columns]
labels   = [a.replace("-USD", "") for a in active]
n_years  = (prices.index[-1] - prices.index[0]).days / 365.25
print(f"  Assets retained: {labels}  |  {len(prices)} days  ({prices.index[0].date()} → {prices.index[-1].date()})")

# ── Per-asset: beta → residual → z-score → signal → forward return ────────────
sig_dict = {}
fwd_dict = {}

for asset in active:
    r = log_ret[asset]

    # Rolling beta: corr(ret_i, ret_btc) * std_i / std_btc
    corr  = r.rolling(BETA_WINDOW, min_periods=60).corr(btc_ret)
    std_i = r.rolling(BETA_WINDOW, min_periods=60).std()
    std_b = btc_ret.rolling(BETA_WINDOW, min_periods=60).std()
    beta  = corr * (std_i / std_b.replace(0, np.nan))

    resid = r - beta * btc_ret

    # Residual z-score
    rm  = resid.rolling(ZSCORE_WINDOW).mean()
    rs  = resid.rolling(ZSCORE_WINDOW).std().replace(0, np.nan)
    z   = (resid - rm) / rs

    # signal = -z  (low residual → expect reversion up → long)
    sig_dict[asset] = -z

    # 5-day simple forward return: (close[t+5] / close[t]) - 1
    # Entry approx at close t+1 (noted); using close[t] as base for IC measurement
    fwd_dict[asset] = prices[asset].pct_change(FORWARD_DAYS).shift(-FORWARD_DAYS)

sig_df = pd.DataFrame(sig_dict)
fwd_df = pd.DataFrame(fwd_dict)
common = sig_df.dropna(how="all").index.intersection(fwd_df.dropna(how="all").index)
sig_df = sig_df.loc[common]
fwd_df = fwd_df.loc[common]
cost_breakeven = ROUND_TRIP_COST / np.sqrt(FORWARD_DAYS)

# ── Non-overlapping 5-day window index ───────────────────────────────────────
win_idx = pd.Series(
    (common - common[0]).days // FORWARD_DAYS, index=common, name="win"
)

# ── Pooled long-format frame ──────────────────────────────────────────────────
sig_stack = sig_df.stack().rename_axis(["date", "asset"]).reset_index(name="sig")
fwd_stack = fwd_df.stack().rename_axis(["date", "asset"]).reset_index(name="fwd")
pool = sig_stack.merge(fwd_stack, on=["date", "asset"]).dropna(subset=["sig", "fwd"])
pool["win"] = (pool["date"] - pool["date"].min()).dt.days // FORWARD_DAYS

# Map window → start date (for plotting)
win_to_date = pool.groupby("win")["date"].min()

# ── IC helper ─────────────────────────────────────────────────────────────────
def ic_series_from_pool(df):
    out = {}
    for w, grp in df.groupby("win"):
        if len(grp) < 3:
            continue
        rho, _ = spearmanr(grp["sig"], grp["fwd"])
        if not np.isnan(rho):
            out[w] = rho
    return pd.Series(out)

# ── Per-asset IC ──────────────────────────────────────────────────────────────
per_asset_ic  = {}
per_asset_met = {}

for asset, label in zip(active, labels):
    sub = pool[pool["asset"] == asset]
    ics = ic_series_from_pool(sub)
    per_asset_ic[asset] = ics

    mn, sd, n = ics.mean(), ics.std(), len(ics)
    t  = mn / (sd / np.sqrt(n)) if sd > 0 else np.nan
    hr = (ics > 0).mean()
    n_sig_yr = (sig_df[asset].abs() > ENTRY_THRESHOLD).sum() / n_years
    per_asset_met[label] = dict(ic=mn, t=t, hit=hr, sig_yr=n_sig_yr)

# ── Pooled IC ─────────────────────────────────────────────────────────────────
pool_ic  = ic_series_from_pool(pool)
p_mn, p_sd, p_n = pool_ic.mean(), pool_ic.std(), len(pool_ic)
p_t    = p_mn / (p_sd / np.sqrt(p_n)) if p_sd > 0 else np.nan
p_icir = p_mn / p_sd if p_sd > 0 else np.nan
p_hit  = (pool_ic > 0).mean()

# ── Threshold signals: |signal| > 1.5 ────────────────────────────────────────
long_r, short_r = [], []
for asset in active:
    s = sig_df[asset].dropna()
    f = fwd_df[asset].reindex(s.index).dropna()
    s = s.reindex(f.index)
    long_r.extend(f[s >  ENTRY_THRESHOLD].tolist())         # signal > 1.5 → long
    short_r.extend((-f[s < -ENTRY_THRESHOLD]).tolist())     # signal < -1.5 → short (negate)

mean_long  = np.mean(long_r)  if long_r  else np.nan
mean_short = np.mean(short_r) if short_r else np.nan

# ── Verdict ───────────────────────────────────────────────────────────────────
fail = (p_t < 1.0 or p_hit < 0.50 or
        (not np.isnan(mean_long) and not np.isnan(mean_short) and
         mean_long < cost_breakeven and mean_short < cost_breakeven))
marginal = (not fail) and (1.0 <= p_t <= 1.5 or 0.15 <= p_icir <= 0.25)
verdict = "FAIL" if fail else ("MARGINAL" if marginal else "PASS")

# ── Chart: 3-panel rolling IC + BTC regime shading ───────────────────────────
btc_28d = prices["BTC-USD"].pct_change(28)

fig, axes = plt.subplots(len(active), 1, figsize=(13, 4.5 * len(active)))
if len(active) == 1:
    axes = [axes]

for ax, asset, label in zip(axes, active, labels):
    ics = per_asset_ic[asset]
    # Convert window keys → dates
    ic_dated = pd.Series(
        {win_to_date[w]: v for w, v in ics.items() if w in win_to_date},
        dtype=float
    ).sort_index()

    roll_mn  = ic_dated.rolling(18, min_periods=4).mean()
    roll_sd  = ic_dated.rolling(18, min_periods=4).std()

    ax.plot(ic_dated.index, roll_mn, color="steelblue", lw=1.8, label="90d Rolling IC")
    ax.fill_between(ic_dated.index,
                    (roll_mn - roll_sd).values.astype(float),
                    (roll_mn + roll_sd).values.astype(float),
                    alpha=0.15, color="steelblue")
    ax.axhline(0, color="black", lw=0.8, ls="--")

    # BTC regime shading (28d return > 0 = bullish = gold)
    btc_at = btc_28d.reindex(ic_dated.index, method="ffill")
    in_bull = False; s0 = None
    for d, v in btc_at.items():
        if pd.isna(v): continue
        if v > 0 and not in_bull:  s0 = d;  in_bull = True
        elif v <= 0 and in_bull:   ax.axvspan(s0, d, color="gold", alpha=0.18); in_bull = False
    if in_bull: ax.axvspan(s0, ic_dated.index[-1], color="gold", alpha=0.18)

    m = per_asset_met[label]
    ax.set_title(f"{label}  IC={m['ic']:.3f}  t={m['t']:.2f}  "
                 f"hit={m['hit']*100:.1f}%  signals/yr={m['sig_yr']:.0f}  |  gold=BTC bull (28d>0)")
    ax.set_ylabel("Spearman IC"); ax.legend(); ax.grid(alpha=0.3)

fig.suptitle("BTC-Neutral Residual MR — 90d Rolling IC per Asset", y=1.01, fontsize=12)
fig.tight_layout()
fig.savefig("residual_mr_ic.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("Chart saved: residual_mr_ic.png")

# ── Print table ───────────────────────────────────────────────────────────────
def f(c): return "✓" if c else "✗"
print()
print("─────────────────────────────────────────────────────────")
print("  BTC-NEUTRAL RESIDUAL MR FEASIBILITY REPORT")
print("─────────────────────────────────────────────────────────")
print(f"  Period:       {START} → {END}")
print(f"  Assets:       {', '.join(labels)}")
print(f"  Beta window:  {BETA_WINDOW}d | Z-score window: {ZSCORE_WINDOW}d")
print()
print("  Per-asset IC (pooled 5-day non-overlapping windows):")
for label, m in per_asset_met.items():
    print(f"    {label:<4s}  IC={m['ic']:.3f}  t={m['t']:.2f}  "
          f"hit={m['hit']*100:.1f}%  signals/yr={m['sig_yr']:.0f}")
print()
print("  Pooled (all assets combined):")
print(f"    Mean IC:      {p_mn:.3f}   {f(p_mn > 0.03)} [PASS if > 0.03]")
print(f"    IC t-stat:    {p_t:.2f}    {f(p_t > 1.5)} [PASS if > 1.5]")
print(f"    ICIR:         {p_icir:.2f}    {f(p_icir > 0.25)} [PASS if > 0.25]")
print(f"    Hit rate:     {p_hit*100:.1f}%   {f(p_hit > 0.52)} [PASS if > 52%]")
print()
print("  Threshold signals (|z| > 1.5):")
print(f"    Long mean fwd return:   {mean_long*100:.2f}%")
print(f"    Short mean fwd return:  {mean_short*100:.2f}%")
print(f"    Cost breakeven:         {cost_breakeven*100:.2f}%")
print()
print(f"  VERDICT: {verdict}")
print("─────────────────────────────────────────────────────────")
print()
print("  MARGINAL = pooled t-stat 1.0-1.5 OR ICIR 0.15-0.25")
print("  FAIL = pooled t-stat < 1.0 OR hit rate < 50% OR")
print("         threshold returns < cost breakeven on both sides")
