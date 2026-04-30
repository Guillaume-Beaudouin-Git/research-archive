"""
TSMOM Feasibility Check — BTC, ETH, SOL
Moskowitz, Ooi & Pedersen (2012) applied to crypto.
Quick signal test — no costs, no ML, no classes.
"""

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import warnings
import os

warnings.filterwarnings("ignore")
os.makedirs("outputs", exist_ok=True)

# ─── CONFIG ──────────────────────────────────────────────────────────────────
ASSETS      = ["BTC-USD", "ETH-USD", "SOL-USD"]
LOOKBACKS   = [7, 14, 21, 28, 56, 90, 180]
TARGET_VOL  = 0.15   # 15% annualized
VOL_WINDOW  = 30     # days for realized vol
TRADING_DAYS = 252


# ─── STEP 1: DATA ────────────────────────────────────────────────────────────
print("=" * 70)
print("TSMOM FEASIBILITY CHECK — BTC / ETH / SOL")
print("=" * 70)
print("\nStep 1: Downloading data (period=max)…")

def _get_close(raw: pd.DataFrame, ticker: str) -> pd.Series:
    """Handle both flat and multi-level column DataFrames from yfinance."""
    if isinstance(raw.columns, pd.MultiIndex):
        return raw["Close"][ticker].squeeze()
    return raw["Close"].squeeze()


prices = {}
for ticker in ASSETS:
    raw = yf.download(ticker, start="2014-01-01", interval="1d",
                      auto_adjust=True, progress=False)
    prices[ticker] = _get_close(raw, ticker)
    print(f"  {ticker}: {len(raw)} days ({raw.index[0].date()} → {raw.index[-1].date()})")

# Align to common dates
price_df = pd.DataFrame(prices).dropna()
returns   = np.log(price_df / price_df.shift(1)).dropna()
print(f"\nAligned sample: {len(returns)} trading days "
      f"({returns.index[0].date()} → {returns.index[-1].date()})")


# ─── HELPERS ─────────────────────────────────────────────────────────────────
def sharpe(rets: pd.Series) -> float:
    if rets.std() == 0 or rets.empty:
        return np.nan
    return (rets.mean() / rets.std()) * np.sqrt(TRADING_DAYS)


def ann_return(rets: pd.Series) -> float:
    return rets.mean() * TRADING_DAYS


def max_drawdown(rets: pd.Series) -> float:
    equity = (1 + rets).cumprod()
    rolling_max = equity.cummax()
    drawdowns = (equity - rolling_max) / rolling_max
    return drawdowns.min()


def build_signal(rets: pd.Series, lookback: int) -> pd.Series:
    """
    signal(t) = sign of cumulative return from t-lookback to t-1.
    .shift(1) ensures value at t uses data through t-1 only — no look-ahead.
    """
    return np.sign(rets.rolling(lookback).sum().shift(1))


def vol_scalar(rets: pd.Series) -> pd.Series:
    """
    Annualized realized vol (rolling), shifted by 1 so the scalar used
    on day t is known at end of day t-1.
    """
    rvol = rets.rolling(VOL_WINDOW).std() * np.sqrt(TRADING_DAYS)
    return (TARGET_VOL / rvol).shift(1)


# ─── STEP 2-4: COMPUTE STRATEGY RETURNS ──────────────────────────────────────
print("\nStep 2-4: Computing signals and strategy returns…")

results_raw  = []   # (asset, lookback, ann_ret, sharpe, maxdd, bh_sharpe)
results_vol  = []
strat_rets   = {}   # (asset, lookback, "raw"/"vol") → daily return Series

for ticker in ASSETS:
    r = returns[ticker]
    bh_sh = sharpe(r)

    scalar = vol_scalar(r)

    for lb in LOOKBACKS:
        sig = build_signal(r, lb)

        # Raw (unscaled)
        raw = sig * r
        # Drop NaN rows (lookback warm-up period)
        raw = raw.dropna()

        # Vol-scaled
        scaled = sig * scalar * r
        scaled = scaled.dropna()

        strat_rets[(ticker, lb, "raw")] = raw
        strat_rets[(ticker, lb, "vol")] = scaled

        results_raw.append({
            "Asset":       ticker,
            "Lookback":    lb,
            "Ann.Return":  ann_return(raw),
            "Sharpe":      sharpe(raw),
            "MaxDD":       max_drawdown(raw),
            "B&H Sharpe":  bh_sh,
        })
        results_vol.append({
            "Asset":       ticker,
            "Lookback":    lb,
            "Ann.Return":  ann_return(scaled),
            "Sharpe":      sharpe(scaled),
            "MaxDD":       max_drawdown(scaled),
            "B&H Sharpe":  bh_sh,
        })


# ─── STEP 5: RESULTS TABLE ────────────────────────────────────────────────────
def fmt_row(row, highlight_sharpe=True):
    sh = row["Sharpe"]
    flag = ""
    if highlight_sharpe:
        if sh > 1.0:
            flag = " *** STRONG"
        elif sh > 0.5:
            flag = " *   WORTH INVESTIGATING"
    return (
        f"  {row['Asset']:<10} {row['Lookback']:>8}d  "
        f"{row['Ann.Return']:>+9.1%}  "
        f"{row['Sharpe']:>7.2f}  "
        f"{row['MaxDD']:>8.1%}  "
        f"{row['B&H Sharpe']:>10.2f}"
        f"{flag}"
    )


def print_table(rows, title):
    print(f"\n{'─'*70}")
    print(f"  {title}")
    print(f"{'─'*70}")
    print(f"  {'Asset':<10} {'Lookback':>8}   {'Ann.Ret':>9}  "
          f"{'Sharpe':>7}  {'MaxDD':>8}  {'B&H Sharpe':>10}")
    print(f"  {'-'*10} {'-'*8}   {'-'*9}  {'-'*7}  {'-'*8}  {'-'*10}")
    for row in rows:
        print(fmt_row(row))
    print(f"{'─'*70}")


df_raw = pd.DataFrame(results_raw)
df_vol = pd.DataFrame(results_vol)

print_table(results_raw, "TABLE 1 — Raw signal (no vol scaling)")
print_table(results_vol, "TABLE 2 — Vol-scaled signal (target vol = 15%)")


# ─── STEP 6a: EQUITY CURVE PLOT ───────────────────────────────────────────────
# Best lookback = highest mean Sharpe across assets (raw)
mean_sharpe_by_lb = df_raw.groupby("Lookback")["Sharpe"].mean()
best_lb = int(mean_sharpe_by_lb.idxmax())
print(f"\nBest lookback (mean Sharpe): {best_lb} days (avg Sharpe = {mean_sharpe_by_lb[best_lb]:.2f})")

fig, ax = plt.subplots(figsize=(12, 6))
colors = {"BTC-USD": "#F7931A", "ETH-USD": "#627EEA", "SOL-USD": "#9945FF"}

for ticker in ASSETS:
    strat = strat_rets[(ticker, best_lb, "raw")].dropna()
    bh    = returns[ticker].loc[strat.index]

    eq_strat = (1 + strat).cumprod()
    eq_bh    = (1 + bh).cumprod()

    c = colors[ticker]
    ax.plot(eq_strat.index, eq_strat.values, color=c,      lw=1.8, label=f"{ticker} TSMOM")
    ax.plot(eq_bh.index,    eq_bh.values,    color=c, lw=0.9,
            linestyle="--", alpha=0.5, label=f"{ticker} B&H")

ax.axhline(1.0, color="grey", lw=0.7, linestyle=":")
ax.set_yscale("log")
ax.set_title(f"TSMOM Equity Curves — {best_lb}-day lookback (raw, log scale)", fontsize=13)
ax.set_ylabel("Cumulative Return (log scale)")
ax.set_xlabel("Date")
ax.legend(ncol=3, fontsize=8)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("outputs/tsmom_feasibility_equity.png", dpi=150)
plt.close(fig)
print("Saved: outputs/tsmom_feasibility_equity.png")


# ─── STEP 6b: SHARPE HEATMAP ─────────────────────────────────────────────────
asset_labels = [a.replace("-USD", "") for a in ASSETS]

# Build matrices: rows=assets, cols=lookbacks
mat_raw = np.array([[df_raw[(df_raw.Asset == a) & (df_raw.Lookback == lb)]["Sharpe"].values[0]
                     for lb in LOOKBACKS] for a in ASSETS])
mat_vol = np.array([[df_vol[(df_vol.Asset == a) & (df_vol.Lookback == lb)]["Sharpe"].values[0]
                     for lb in LOOKBACKS] for a in ASSETS])

# Custom colormap: red → white → green
cmap = mcolors.LinearSegmentedColormap.from_list(
    "rwg", [(0, "#d73027"), (0.35, "#fee08b"), (0.5, "#ffffff"),
            (0.65, "#a6d96a"), (1.0, "#1a7837")]
)

fig, axes = plt.subplots(1, 2, figsize=(14, 3.5))
for ax, mat, title in zip(axes, [mat_raw, mat_vol],
                           ["Raw (no vol scaling)", "Vol-scaled (target 15%)"]):
    vmax = max(abs(mat).max(), 1.0)
    im = ax.imshow(mat, cmap=cmap, vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(LOOKBACKS)))
    ax.set_xticklabels([f"{lb}d" for lb in LOOKBACKS], fontsize=9)
    ax.set_yticks(range(len(ASSETS)))
    ax.set_yticklabels(asset_labels, fontsize=10)
    ax.set_title(f"Sharpe — {title}", fontsize=11)
    for i in range(len(ASSETS)):
        for j in range(len(LOOKBACKS)):
            ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center",
                    fontsize=9, color="black" if abs(mat[i, j]) < 0.7 * vmax else "white")
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

fig.suptitle("TSMOM Sharpe Heatmap — BTC / ETH / SOL", fontsize=13, y=1.02)
fig.tight_layout()
fig.savefig("outputs/tsmom_feasibility_heatmap.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("Saved: outputs/tsmom_feasibility_heatmap.png")


# ─── STEP 7: HONEST ASSESSMENT ───────────────────────────────────────────────
print("\n" + "=" * 70)
print("  HONEST ASSESSMENT")
print("=" * 70)

# Q1: Any positive signal?
positive_raw = (df_raw["Sharpe"] > 0).sum()
total_combos = len(df_raw)
pct_pos = positive_raw / total_combos * 100
print(f"\n1. POSITIVE SIGNAL (Sharpe > 0)?")
print(f"   Raw:       {positive_raw}/{total_combos} combos positive ({pct_pos:.0f}%)")
positive_vol = (df_vol["Sharpe"] > 0).sum()
pct_pos_vol = positive_vol / total_combos * 100
print(f"   Vol-scaled: {positive_vol}/{total_combos} combos positive ({pct_pos_vol:.0f}%)")
if pct_pos >= 60:
    print(f"   → YES — majority of lookback/asset combos show positive Sharpe")
elif pct_pos >= 40:
    print(f"   → MIXED — roughly half positive, half negative")
else:
    print(f"   → WEAK — most combos are negative, signal is unreliable")

# Q2: Vol scaling
avg_sh_raw = df_raw["Sharpe"].mean()
avg_sh_vol = df_vol["Sharpe"].mean()
print(f"\n2. DOES VOL SCALING HELP?")
print(f"   Avg Sharpe raw:       {avg_sh_raw:+.3f}")
print(f"   Avg Sharpe vol-scaled: {avg_sh_vol:+.3f}")
delta = avg_sh_vol - avg_sh_raw
if delta > 0.05:
    print(f"   → YES — vol scaling adds +{delta:.2f} Sharpe on average")
elif delta < -0.05:
    print(f"   → NO  — vol scaling hurts by {abs(delta):.2f} Sharpe on average")
else:
    print(f"   → NEUTRAL — vol scaling has minimal effect (Δ = {delta:+.3f})")

# Q3: Best lookbacks
print(f"\n3. BEST LOOKBACK PERIODS?")
lb_perf = df_vol.groupby("Lookback")["Sharpe"].mean().sort_values(ascending=False)
for lb, sh in lb_perf.items():
    bar = "█" * max(0, int(sh * 10)) if sh > 0 else "░" * max(0, int(abs(sh) * 10))
    print(f"   {lb:>5}d: {sh:+.3f}  {bar}")

# Q4: Cost survival (rough)
COST_PER_TRIP = 0.001  # 0.1% round trip
print(f"\n4. COST SURVIVAL (0.1% round-trip)?")
print(f"   Signals flip ~every {best_lb} days → ~{TRADING_DAYS/best_lb:.0f} round-trips/year")
for ticker in ASSETS:
    sig = strat_rets[(ticker, best_lb, "raw")]
    # Count signal changes
    raw_sig = np.sign(returns[ticker].rolling(best_lb).sum().shift(1)).dropna()
    n_trades = (raw_sig.diff().abs() > 0).sum()
    annual_trades = n_trades / (len(raw_sig) / TRADING_DAYS)
    annual_cost   = annual_trades * COST_PER_TRIP
    avg_daily_ret = sig.mean()
    avg_ann_ret   = avg_daily_ret * TRADING_DAYS
    net_ret = avg_ann_ret - annual_cost
    print(f"   {ticker}: ~{annual_trades:.0f} RT/yr, cost ≈ {annual_cost:.1%}/yr, "
          f"gross ≈ {avg_ann_ret:+.1%}/yr, net ≈ {net_ret:+.1%}/yr "
          f"({'viable' if net_ret > 0 else 'not viable'} at best lb={best_lb}d)")

# Q5: Which assets work?
print(f"\n5. WHICH ASSETS WORK?")
asset_perf = df_vol.groupby("Asset")[["Sharpe"]].mean().rename(columns={"Sharpe": "Avg Sharpe (vol)"})
asset_perf["Avg Sharpe (raw)"] = df_raw.groupby("Asset")["Sharpe"].mean()
asset_perf["Best Sharpe"] = df_vol.groupby("Asset")["Sharpe"].max()
for ticker, row in asset_perf.iterrows():
    status = "STRONG" if row["Best Sharpe"] > 1.0 else "MARGINAL" if row["Avg Sharpe (vol)"] > 0.3 else "WEAK"
    print(f"   {ticker:<10} avg Sharpe (vol) = {row['Avg Sharpe (vol)']:+.2f}, "
          f"best Sharpe = {row['Best Sharpe']:.2f}  [{status}]")

# Q6: Recommendation
print(f"\n6. RECOMMENDATION")
strong_combos = (df_vol["Sharpe"] > 1.0).sum()
marginal_combos = ((df_vol["Sharpe"] > 0.5) & (df_vol["Sharpe"] <= 1.0)).sum()
print(f"   Combos with Sharpe > 1.0: {strong_combos}")
print(f"   Combos with Sharpe > 0.5: {marginal_combos}")

if strong_combos >= 3:
    verdict = "PROCEED to full backtest with cost modeling and position sizing."
    detail  = ("Multiple strong signals found. Worth implementing proper "
               "execution mechanics, cross-sectional combination, and OOS testing.")
elif marginal_combos >= 4 or pct_pos >= 70:
    verdict = "CAUTIOUS PROCEED — signal exists but is moderate."
    detail  = ("Some lookbacks show promise. Build full backtest before committing. "
               "Focus on longer lookbacks and vol scaling.")
else:
    verdict = "SKEPTICAL — weak or inconsistent signal."
    detail  = ("Signal is noisy across assets/lookbacks. "
               "May need cross-sectional scoring or different universe.")

print(f"\n   VERDICT: {verdict}")
print(f"   {detail}")

print("\n" + "=" * 70)
print("  TIMING VERIFICATION")
print("=" * 70)
print(f"  Signal at t uses returns through t-1 (.rolling(lb).sum().shift(1))")
print(f"  Strategy return = signal(t) × return(t)")
print(f"  ✓ No look-ahead bias — signal is formed before the return it trades on")
print("=" * 70 + "\n")
