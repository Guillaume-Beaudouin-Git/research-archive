"""
Vol-Regime Mean Reversion Backtest — BTC-USD 2019-2025
Signal at Friday close → entry Monday close (≈ Monday open, noted approximation)
                       → exit Friday close of same week
Non-overlapping weekly observations to avoid z-score autocorrelation.
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Constants ─────────────────────────────────────────────────────────────────
ROUND_TRIP_COST   = 0.0034
SIGNAL_WINDOW     = 5
LOOKBACK_MEAN_STD = 20
LOOKBACK_VOL      = 20
VOL_TARGET        = 0.15
START             = "2019-01-01"
END               = "2025-01-01"
N_FOLDS           = 12

# ── Download ──────────────────────────────────────────────────────────────────
print("Downloading BTC-USD...")
raw   = yf.download("BTC-USD", start=START, end=END, auto_adjust=True, progress=False)
price = raw["Close"].squeeze().dropna()

# ── Daily features (all rolling — no lookahead) ───────────────────────────────
daily_ret = price.pct_change()
rv_20d    = daily_ret.rolling(LOOKBACK_VOL).std() * np.sqrt(252)
roll_mean = price.rolling(LOOKBACK_MEAN_STD).mean()
roll_std  = price.rolling(LOOKBACK_MEAN_STD).std()
zscore    = (price - roll_mean) / roll_std
signal    = -zscore                                           # mean-reversion
ann_vol   = daily_ret.rolling(LOOKBACK_VOL).std() * np.sqrt(252)
position  = (signal.clip(-1, 1) * VOL_TARGET / ann_vol.replace(0, np.nan)).clip(-1, 1).fillna(0)

# Expanding-window regime threshold (no lookahead)
rv_thresh_exp = rv_20d.expanding(min_periods=60).quantile(0.40)
regime_exp    = rv_20d < rv_thresh_exp

# ── Weekly frame ──────────────────────────────────────────────────────────────
# Entry = Monday close (first bar of week) ≈ Monday open [approximation noted]
# Exit  = Friday close (last bar of week)
w_entry  = price.resample("W-FRI").first()          # Mon close
w_exit   = price.resample("W-FRI").last()           # Fri close
w_intra  = (w_exit - w_entry) / w_entry             # Mon-to-Fri return
w_pos    = position.resample("W-FRI").last()        # position decided at Fri t
w_regime = regime_exp.resample("W-FRI").last()      # regime flag at Fri t
w_rv     = rv_20d.resample("W-FRI").last()          # for fold-level threshold

wdf = pd.DataFrame({
    "intraweek_ret": w_intra,
    "position":      w_pos,
    "regime":        w_regime,
    "rv":            w_rv,
}).dropna()

# ── Backtest engine ────────────────────────────────────────────────────────────
def backtest(df, regime_series=None):
    """
    regime_series: optional override (aligned to df.index).
    Signal from Friday t → trade intraweek return of week t+1 (shift by 1).
    Cost triggered when |Δposition| > 0.1.
    """
    d = df.copy()
    if regime_series is not None:
        d["regime"] = regime_series.reindex(d.index)

    # Apply prev-Friday position only if prev-Friday regime was active
    d["active"]      = d["position"].shift(1) * d["regime"].shift(1).fillna(False)
    d["active_long"] = d["active"].clip(0, 1)

    d["dpos"]        = (d["active"] - d["active"].shift(1)).abs()
    d["dpos_long"]   = (d["active_long"] - d["active_long"].shift(1)).abs()
    d["cost"]        = (d["dpos"] > 0.1).astype(float) * ROUND_TRIP_COST
    d["cost_long"]   = (d["dpos_long"] > 0.1).astype(float) * ROUND_TRIP_COST

    d["ret"]         = d["active"]      * d["intraweek_ret"] - d["cost"]
    d["ret_long"]    = d["active_long"] * d["intraweek_ret"] - d["cost_long"]
    return d.dropna(subset=["ret"])

def metrics(ret):
    if len(ret) < 4:
        return dict(sharpe=np.nan, ann_ret=np.nan, mdd=np.nan, win_rate=np.nan)
    ann = (1 + ret).prod() ** (52 / len(ret)) - 1
    sh  = ret.mean() / ret.std() * np.sqrt(52)
    cum = (1 + ret).cumprod()
    mdd = ((cum - cum.cummax()) / cum.cummax()).min()
    return dict(sharpe=sh, ann_ret=ann, mdd=mdd, win_rate=(ret > 0).mean())

# ── Full-period backtest ───────────────────────────────────────────────────────
full = backtest(wdf)
m    = metrics(full["ret"])
m_lo = metrics(full["ret_long"])

total_trips      = int((full["dpos"] > 0.1).sum())
total_cost       = float(full["cost"].sum())
avg_regime_weeks = float(full["regime"].shift(1).fillna(False).mean() * 52)

# ── Walk-forward (12 expanding folds, regime threshold on train only) ─────────
n         = len(wdf)
fold_size = n // N_FOLDS          # ≈ 26 weeks per fold
fold_sharpes = []

for i in range(N_FOLDS):
    t0 = i * fold_size
    t1 = (i + 1) * fold_size if i < N_FOLDS - 1 else n

    if t0 == 0:                   # fold 0: no training data — skip
        fold_sharpes.append(np.nan)
        continue

    train_end = wdf.index[t0 - 1]
    rv_train  = rv_20d.loc[:train_end].dropna()
    thresh    = float(rv_train.quantile(0.40))

    test_wdf      = wdf.iloc[t0:t1].copy()
    regime_fold   = (test_wdf["rv"] < thresh)
    fold_bt       = backtest(test_wdf, regime_series=regime_fold)
    fold_sharpes.append(metrics(fold_bt["ret"])["sharpe"])

valid     = [s for s in fold_sharpes if not np.isnan(s)]
pos_folds = sum(s > 0 for s in valid)

# ── Verdict ───────────────────────────────────────────────────────────────────
sh = m["sharpe"]
if sh > 0.8 and pos_folds >= 8:
    verdict = "PASS"
elif 0.5 <= sh <= 0.8 or 6 <= pos_folds <= 8:
    verdict = "MARGINAL"
else:
    verdict = "FAIL"

# ── Chart ─────────────────────────────────────────────────────────────────────
cum_s   = (1 + full["ret"]).cumprod()
cum_lo  = (1 + full["ret_long"]).cumprod()
cum_btc = (1 + full["intraweek_ret"]).cumprod()
dd      = (cum_s - cum_s.cummax()) / cum_s.cummax()

fig, axes = plt.subplots(3, 1, figsize=(13, 11),
                          gridspec_kw={"height_ratios": [3, 1.5, 1.5]})

# Equity curve
ax1 = axes[0]
ax1.plot(full.index, cum_s,   label="Strategy (L/S)", color="steelblue", lw=1.8)
ax1.plot(full.index, cum_lo,  label="Long-only",      color="seagreen",  lw=1.5, ls="--")
ax1.plot(full.index, cum_btc, label="BTC Buy & Hold", color="orange",    lw=1.2, alpha=0.7)
active_regime = full["regime"].shift(1).fillna(False)
in_r = False; s0 = None
for d, r in active_regime.items():
    if r and not in_r:  s0 = d;  in_r = True
    elif not r and in_r: ax1.axvspan(s0, d, color="gold", alpha=0.18); in_r = False
if in_r: ax1.axvspan(s0, full.index[-1], color="gold", alpha=0.18)
ax1.set_ylabel("Growth of $1"); ax1.legend(); ax1.grid(alpha=0.3)
ax1.set_title("Vol-Regime MR — Equity Curve  |  gold = low-vol regime active")

# Drawdown
ax2 = axes[1]
ax2.fill_between(full.index, dd.values.astype(float), 0, color="crimson", alpha=0.5)
ax2.set_ylabel("Drawdown"); ax2.grid(alpha=0.3)
ax2.set_title("Strategy Drawdown")

# Walk-forward bar chart
ax3 = axes[2]
xs  = np.arange(N_FOLDS)
ys  = np.array(fold_sharpes, dtype=float)
clr = ["steelblue" if v > 0 else "tomato" for v in np.nan_to_num(ys)]
ax3.bar(xs, np.nan_to_num(ys), color=clr, alpha=0.85)
ax3.axhline(0,   color="black", lw=0.8)
ax3.axhline(0.8, color="green", lw=1.0, ls=":", label="PASS (0.8)")
for j, v in enumerate(ys):
    if np.isnan(v): ax3.text(j, 0.05, "N/A", ha="center", fontsize=7, color="gray")
ax3.set_xlabel("Fold"); ax3.set_ylabel("Sharpe")
ax3.set_title(f"Walk-Forward Sharpe — {N_FOLDS} folds, expanding train window")
ax3.legend(); ax3.grid(alpha=0.3, axis="y")

fig.tight_layout()
fig.savefig("vol_regime_equity_curve.png", dpi=150)
plt.close(fig)
print("Chart saved: vol_regime_equity_curve.png")

# ── Print report ──────────────────────────────────────────────────────────────
print()
print("─────────────────────────────────────────────────────────")
print("  VOL-REGIME MR BACKTEST REPORT")
print("─────────────────────────────────────────────────────────")
print(f"  Full period Sharpe (after costs):     {m['sharpe']:.2f}")
print(f"  Full period Sharpe (long-only):       {m_lo['sharpe']:.2f}")
print(f"  Annualized return (after costs):      {m['ann_ret']*100:.1f}%")
print(f"  Max drawdown:                         {m['mdd']*100:.1f}%")
print(f"  Win rate (weekly):                    {m['win_rate']*100:.1f}%")
print(f"  Avg weeks in regime per year:         {avg_regime_weeks:.0f}")
print(f"  Total round trips:                    {total_trips}")
print(f"  Total cost drag:                      {total_cost*100:.1f}%")
print()
print(f"  Walk-forward results ({N_FOLDS} folds, fold 0 skipped — no train):")
print(f"  Positive folds:     {pos_folds}/{len(valid)}")
print(f"  Median fold Sharpe: {np.nanmedian(fold_sharpes):.2f}")
print(f"  Min fold Sharpe:    {np.nanmin(fold_sharpes):.2f}")
print("─────────────────────────────────────────────────────────")
print(f"  VERDICT: {verdict}")
print("─────────────────────────────────────────────────────────")
print()
print("  PASS:     full Sharpe > 0.8  AND positive folds >= 8/12")
print("  MARGINAL: full Sharpe 0.5-0.8 OR positive folds 6-8/12")
print("  FAIL:     full Sharpe < 0.5  OR positive folds < 6/12")
