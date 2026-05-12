"""
Fear & Greed Contrarian — Feasibility Check
Signal: extreme fear → long, extreme greed → short, 5-day hold
"""
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

# ── Constants ─────────────────────────────────────────────────────────────────
ROUND_TRIP_COST         = 0.0034
EXTREME_FEAR_THRESHOLD  = 20
EXTREME_GREED_THRESHOLD = 80
MIN_SIGNAL_GAP_DAYS     = 5
FORWARD_DAYS            = 5
START                   = "2018-02-01"
END                     = "2025-01-01"

# ── 1. Fear & Greed data ──────────────────────────────────────────────────────
print("Fetching Fear & Greed Index...")
url  = "https://api.alternative.me/fng/?limit=3000&format=json"
resp = requests.get(url, timeout=20)
resp.raise_for_status()
raw_fg = resp.json()["data"]

fg = pd.DataFrame(raw_fg)[["value", "timestamp"]].copy()
fg["value"]     = fg["value"].astype(int)
fg["timestamp"] = fg["timestamp"].astype(int)
fg["date"]      = pd.to_datetime(fg["timestamp"], unit="s").dt.normalize()
fg = fg.sort_values("date").drop_duplicates("date").set_index("date")[["value"]]
fg.index = fg.index.tz_localize(None)
fg = fg.loc[START:END]
print(f"  F&G rows: {len(fg)}  ({fg.index[0].date()} → {fg.index[-1].date()})")

# ── 2. BTC price ──────────────────────────────────────────────────────────────
print("Downloading BTC-USD...")
btc = yf.download("BTC-USD", start=START, end=END,
                  auto_adjust=True, progress=False)["Close"].squeeze()
btc = btc.dropna()
btc.index = pd.to_datetime(btc.index).tz_localize(None)

# ── 3. Align ──────────────────────────────────────────────────────────────────
df = fg.join(btc.rename("price"), how="inner").dropna()
df.columns = ["fg", "price"]
df["ret_1d"] = df["price"].pct_change()

# Forward 5-day return: (price[t+5] / price[t]) - 1
# Using close t+1 as entry (noted approximation for "open t+1")
df["fwd_ret"] = df["price"].shift(-FORWARD_DAYS) / df["price"].shift(-1) - 1

n_years = (df.index[-1] - df.index[0]).days / 365.25
daily_vol = float(df["ret_1d"].std())

# ── 4. Raw signal (before gap filter) ────────────────────────────────────────
df["raw_signal"] = 0
df.loc[df["fg"] < EXTREME_FEAR_THRESHOLD,  "raw_signal"] = 1   # long
df.loc[df["fg"] > EXTREME_GREED_THRESHOLD, "raw_signal"] = -1  # short

# ── 5. Gap filter (MIN_SIGNAL_GAP_DAYS = 5) ──────────────────────────────────
df["signal"] = 0
last_signal_day = -999
for i, (idx, row) in enumerate(df.iterrows()):
    if row["raw_signal"] != 0 and (i - last_signal_day) >= MIN_SIGNAL_GAP_DAYS:
        df.at[idx, "signal"] = row["raw_signal"]
        last_signal_day = i

# ── 6. Signal subset ──────────────────────────────────────────────────────────
sig_df = df[df["signal"] != 0].copy().dropna(subset=["fwd_ret"])

fear_df  = sig_df[sig_df["signal"] ==  1]
greed_df = sig_df[sig_df["signal"] == -1]

n_signals     = len(sig_df)
n_fear        = len(fear_df)
n_greed       = len(greed_df)
avg_per_year  = n_signals / n_years

# ── 7. Metrics ────────────────────────────────────────────────────────────────
# Signal returns: signal × forward_return (so fear long profits from up moves)
sig_df["signal_ret"] = sig_df["signal"] * sig_df["fwd_ret"]

mean_ret_fear  = float(fear_df["fwd_ret"].mean())        # long: raw forward ret
mean_ret_greed = float((-greed_df["fwd_ret"]).mean())    # short: negated forward ret
mean_ret_all   = float(sig_df["signal_ret"].mean())

rho, _ = spearmanr(sig_df["signal"], sig_df["fwd_ret"])
ic     = float(rho)
t_stat = ic * np.sqrt(n_signals) / np.sqrt(max(1 - ic**2, 1e-9))
hit_rate = float((np.sign(sig_df["signal"]) == np.sign(sig_df["fwd_ret"])).mean())

cost_breakeven = ROUND_TRIP_COST / (daily_vol * np.sqrt(FORWARD_DAYS))

# ── 8. Equity curve ───────────────────────────────────────────────────────────
# Build day-by-day P&L: position is +1 or -1 for FORWARD_DAYS after each signal
df["position"] = 0.0
for idx, row in sig_df.iterrows():
    loc     = df.index.get_loc(idx)
    end_loc = min(loc + 1 + FORWARD_DAYS, len(df))
    df.iloc[loc + 1 : end_loc, df.columns.get_loc("position")] = row["signal"]

# Daily strategy return
df["strat_ret"] = df["position"] * df["ret_1d"]

# Apply cost on entry days (close t → effective entry at t+1)
df["cost_applied"] = 0.0
for idx in sig_df.index:
    loc = df.index.get_loc(idx)
    if loc + 1 < len(df):
        df.iloc[loc + 1, df.columns.get_loc("cost_applied")] = ROUND_TRIP_COST

df["strat_ret_net"] = df["strat_ret"] - df["cost_applied"]

cum_strat = (1 + df["strat_ret_net"]).cumprod()
cum_btc   = (1 + df["ret_1d"].fillna(0)).cumprod()

fig, axes = plt.subplots(2, 1, figsize=(13, 8),
                          gridspec_kw={"height_ratios": [2.5, 1]})

ax1 = axes[0]
ax1.plot(df.index, cum_strat, label="F&G Contrarian (after costs)", color="steelblue", lw=1.8)
ax1.plot(df.index, cum_btc,   label="BTC Buy & Hold",               color="orange",    lw=1.2, alpha=0.7)
# Mark signal days
ax1.scatter(fear_df.index,  cum_strat.reindex(fear_df.index),
            marker="^", color="green", s=40, zorder=5, label="Fear (long)")
ax1.scatter(greed_df.index, cum_strat.reindex(greed_df.index),
            marker="v", color="red",   s=40, zorder=5, label="Greed (short)")
ax1.set_ylabel("Growth of $1"); ax1.legend(fontsize=8); ax1.grid(alpha=0.3)
ax1.set_title(f"F&G Contrarian — Equity Curve  |  {n_signals} signals ({n_fear} fear, {n_greed} greed)")

# Rolling annual signal return
sig_df_sorted = sig_df.sort_index()
sig_df_sorted["signal_ret_net"] = sig_df_sorted["signal_ret"] - ROUND_TRIP_COST
rolling_annual = sig_df_sorted["signal_ret_net"].rolling(
    min(52, len(sig_df_sorted)), min_periods=4).mean() * (252 / FORWARD_DAYS)

ax2 = axes[1]
ax2.plot(sig_df_sorted.index, rolling_annual, color="steelblue", lw=1.5)
ax2.axhline(0, color="black", lw=0.8, ls="--")
ax2.fill_between(sig_df_sorted.index, rolling_annual, 0,
                 where=rolling_annual > 0, color="green", alpha=0.2)
ax2.fill_between(sig_df_sorted.index, rolling_annual, 0,
                 where=rolling_annual < 0, color="red",   alpha=0.2)
ax2.set_ylabel("Rolling Ann. Return"); ax2.grid(alpha=0.3)
ax2.set_title("Rolling Annualized Signal Return (per-signal, net of costs)")

fig.tight_layout()
fig.savefig("fg_contrarian_equity.png", dpi=150)
plt.close(fig)
print("Chart saved: fg_contrarian_equity.png")

# ── 9. Verdict ────────────────────────────────────────────────────────────────
if t_stat < 1.0 or hit_rate < 0.50 or mean_ret_all < cost_breakeven:
    verdict = "FAIL"
elif 1.0 <= t_stat <= 1.5 or 0.50 <= hit_rate <= 0.52:
    verdict = "MARGINAL"
else:
    verdict = "PASS"

print()
print("─────────────────────────────────────────────────")
print("  FEAR & GREED CONTRARIAN FEASIBILITY REPORT")
print("─────────────────────────────────────────────────")
print(f"  Period:            {START} → {END}")
print(f"  Total signals:     {n_signals}  (fear: {n_fear}, greed: {n_greed})")
print(f"  Avg signals/year:  {avg_per_year:.1f}")
print()
print(f"  Mean return — fear signals (long):   {mean_ret_fear*100:.1f}%")
print(f"  Mean return — greed signals (short): {mean_ret_greed*100:.1f}%")
print(f"  Overall mean return per signal:      {mean_ret_all*100:.1f}%")
print()
print(f"  IC (signal vs 5d return):  {ic:.3f}  {'✓' if ic > 0.05 else '✗'} [PASS if > 0.05]")
print(f"  IC t-stat:                 {t_stat:.2f}   {'✓' if t_stat > 1.5 else '✗'} [PASS if > 1.5]")
print(f"  Hit rate:                  {hit_rate*100:.1f}%  {'✓' if hit_rate > 0.52 else '✗'} [PASS if > 52%]")
print(f"  Cost breakeven return:     {cost_breakeven*100:.1f}%   [need mean return > this]")
print()
print(f"  VERDICT: {verdict}")
print("─────────────────────────────────────────────────")
print()
print("  MARGINAL = t-stat 1.0-1.5 OR hit rate 50-52%")
print("  FAIL = t-stat < 1.0 OR hit rate < 50% OR")
print("         mean return < cost breakeven")
