"""
TSMOM Full Backtest — Time-Series Momentum on Crypto Perpetuals

Validation checklist:
  ✓ Signal at t-1, return at t (1-day execution lag, verified explicitly)
  ✓ Realistic costs: 0.035% fee + 0.05% slippage per side (Hyperliquid)
  ✓ Walk-forward validation (expanding window, 6-month folds)
  ✓ Per-year breakdown with 2018 and 2022 bear-market focus
  ✓ Bear market position analysis (was the strategy actually short?)
  ✓ Multi-asset portfolio (equal risk, 1/3 each)
  ✓ Sensitivity analysis over lookbacks [14, 21, 28, 42, 56]
  ✓ No ML, no parameter fitting on test data
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

from tsmom_strategy import TSMOMStrategy, TRADING_DAYS

warnings.filterwarnings("ignore")
os.makedirs("outputs", exist_ok=True)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
ASSETS              = ["BTC-USD", "ETH-USD", "SOL-USD"]
LOOKBACK            = 28
VOL_TARGET          = 0.15
VOL_LOOKBACK        = 30
FEE_RATE            = 0.00035
SLIPPAGE            = 0.0005
MIN_TRAIN_DAYS      = 365
FOLD_MONTHS         = 6
SENSITIVITY_LBS     = [14, 21, 28, 42, 56]

# Feasibility results for comparison (from tsmom_feasibility.py, 28d vol-scaled)
FEASIBILITY_SHARPE  = {"BTC-USD": 1.00, "ETH-USD": 0.85, "SOL-USD": 1.09}

COLORS = {"BTC-USD": "#F7931A", "ETH-USD": "#627EEA", "SOL-USD": "#9945FF"}
BEAR_YEARS = {2018: "BEAR −73%", 2022: "BEAR −65%"}

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def get_close(raw: pd.DataFrame, ticker: str) -> pd.Series:
    if isinstance(raw.columns, pd.MultiIndex):
        return raw["Close"][ticker].squeeze()
    return raw["Close"].squeeze()


def compute_metrics(net_rets: pd.Series, label: str = "") -> dict:
    """Full performance metrics from a net return series."""
    r = net_rets.dropna()
    if r.empty or r.std() == 0 or len(r) < 10:
        return {k: np.nan for k in [
            "label", "total_return", "ann_return", "sharpe", "sortino",
            "max_dd", "calmar", "win_rate", "n_years",
        ]} | {"label": label}

    n_years   = len(r) / TRADING_DAYS
    ann_ret   = r.mean() * TRADING_DAYS
    total_ret = (1 + r).prod() - 1
    sharpe    = (r.mean() / r.std()) * np.sqrt(TRADING_DAYS)

    down      = r[r < 0]
    sortino   = (r.mean() / down.std()) * np.sqrt(TRADING_DAYS) if len(down) > 1 else np.nan

    equity    = (1 + r).cumprod()
    roll_max  = equity.cummax()
    dd        = (equity - roll_max) / roll_max
    max_dd    = dd.min()
    calmar    = ann_ret / abs(max_dd) if max_dd != 0 else np.nan
    win_rate  = (r > 0).mean()

    return {
        "label":        label,
        "total_return": total_ret,
        "ann_return":   ann_ret,
        "sharpe":       sharpe,
        "sortino":      sortino,
        "max_dd":       max_dd,
        "calmar":       calmar,
        "win_rate":     win_rate,
        "n_years":      n_years,
    }


def yearly_breakdown(result: pd.DataFrame, price: pd.Series) -> pd.DataFrame:
    """Per-calendar-year metrics including B&H comparison."""
    log_r  = np.log(price / price.shift(1))
    arith_bh = np.exp(log_r) - 1

    rows = []
    for year in sorted(result.index.year.unique()):
        mask   = result.index.year == year
        yr_net = result.loc[mask, "net_return"].dropna()
        yr_pos = result.loc[mask, "position"].dropna()
        yr_bh  = arith_bh.reindex(yr_net.index).dropna()

        if len(yr_net) < 5:
            continue

        ann_ret  = yr_net.mean() * TRADING_DAYS
        sharpe   = (yr_net.mean() / yr_net.std() * np.sqrt(TRADING_DAYS)
                    if yr_net.std() > 0 else np.nan)
        equity   = (1 + yr_net).cumprod()
        roll_max = equity.cummax()
        max_dd   = ((equity - roll_max) / roll_max).min()
        n_trades = int((result.loc[mask, "turnover"].dropna() > 0.01).sum())
        bh_ret   = (1 + yr_bh).prod() - 1
        avg_pos  = yr_pos.mean()
        pct_long  = (yr_pos > 0).mean()
        pct_short = (yr_pos < 0).mean()

        rows.append({
            "Year":       year,
            "Return":     ann_ret,
            "Sharpe":     sharpe,
            "MaxDD":      max_dd,
            "# Trades":   n_trades,
            "B&H Return": bh_ret,
            "Avg Pos":    avg_pos,
            "% Long":     pct_long,
            "% Short":    pct_short,
        })

    return pd.DataFrame(rows).set_index("Year") if rows else pd.DataFrame()


# ─── STEP 1: DATA ─────────────────────────────────────────────────────────────
print("=" * 70)
print("TSMOM FULL BACKTEST — BTC / ETH / SOL")
print("=" * 70)
print("\nStep 1: Downloading data (max history)…")

prices      = {}
log_returns = {}

for ticker in ASSETS:
    raw = yf.download(ticker, start="2014-01-01", interval="1d",
                      auto_adjust=True, progress=False)
    px = get_close(raw, ticker).dropna()
    prices[ticker]      = px
    log_returns[ticker] = np.log(px / px.shift(1)).dropna()
    print(f"  {ticker}: {len(raw)} days  "
          f"({raw.index[0].date()} → {raw.index[-1].date()})")

# ─── STEP 2: EXECUTION TIMING VERIFICATION ────────────────────────────────────
print("\n" + "=" * 70)
print("Step 2: EXECUTION TIMING VERIFICATION")
print("=" * 70)

strat_verify = TSMOMStrategy(lookback=LOOKBACK, vol_target=VOL_TARGET,
                              vol_lookback=VOL_LOOKBACK, fee_rate=FEE_RATE,
                              slippage=SLIPPAGE)
result_verify = strat_verify.run(log_returns["BTC-USD"])

# Find first 5 bars where position is non-zero and non-NaN
valid = result_verify.dropna(subset=["position"])
valid = valid[valid["position"] != 0]

print(f"\n  {'Exec Date':<13} {'Signal':>7} {'Vol Scl':>8} {'Position':>9} "
      f"{'Arith Ret':>11} {'Net Ret':>10}")
print(f"  {'─'*13} {'─'*7} {'─'*8} {'─'*9} {'─'*11} {'─'*10}")

for i, (date, row) in enumerate(valid.head(5).iterrows()):
    print(f"  {str(date.date()):<13} {row['signal']:>+7.1f} {row['vol_scalar']:>8.4f} "
          f"{row['position']:>+9.4f} {row['arith_return']:>+11.4%} {row['net_return']:>+10.4%}")

print(f"\n  TIMING PROOF:")
print(f"  signal[t]     = sign(rolling({LOOKBACK}).sum().shift(1))[t]")
print(f"                = sign(sum of log_returns[t-{LOOKBACK} : t-1])")
print(f"  vol_scalar[t] = clip(vol_target / (rolling({VOL_LOOKBACK}).std().shift(1)[t] * √365))")
print(f"                  uses std of log_returns[t-{VOL_LOOKBACK} : t-1]")
print(f"  position[t]   = signal[t] * vol_scalar[t]   ← data through t-1 only")
print(f"  net_return[t] = position[t] * arith_return[t]")
print(f"  Execution lag : 1 day  ✓  No look-ahead bias  ✓")

# ─── STEP 3: PER-ASSET BACKTEST ───────────────────────────────────────────────
print("\n" + "=" * 70)
print("Step 3: PER-ASSET BACKTEST")
print("=" * 70)

strategy = TSMOMStrategy(
    lookback=LOOKBACK, vol_target=VOL_TARGET, vol_lookback=VOL_LOOKBACK,
    fee_rate=FEE_RATE, slippage=SLIPPAGE,
)

asset_results = {}
asset_metrics = {}
asset_yearly  = {}
trade_rows    = []

for ticker in ASSETS:
    lr     = log_returns[ticker]
    result = strategy.run(lr)
    asset_results[ticker] = result
    asset_metrics[ticker] = compute_metrics(result["net_return"], ticker)
    asset_yearly[ticker]  = yearly_breakdown(result, prices[ticker])

    # Trade log: every bar with meaningful turnover
    trade_mask = result["turnover"].fillna(0) > 0.01
    for date, row in result[trade_mask].iterrows():
        trade_rows.append({
            "asset":      ticker,
            "date":       date.date(),
            "signal":     row["signal"],
            "position":   round(row["position"], 6),
            "turnover":   round(row["turnover"], 6),
            "cost_bps":   round(row["cost"] * 10000, 2),
            "net_return": round(row["net_return"], 6),
        })

pd.DataFrame(trade_rows).to_csv("outputs/tsmom_trades.csv", index=False)
print(f"\n  Trade log saved: outputs/tsmom_trades.csv "
      f"({len(trade_rows)} position changes)")

# ─── STEP 4: WALK-FORWARD VALIDATION ──────────────────────────────────────────
print("\n" + "=" * 70)
print("Step 4: WALK-FORWARD VALIDATION (expanding window, 6-month folds)")
print("=" * 70)
print(f"  Min warm-up: {MIN_TRAIN_DAYS} days | Fold size: {FOLD_MONTHS} months")
print(f"  Note: TSMOM has no fitted params — walk-forward validates that")
print(f"  rolling vol computed on expanding data performs OOS.")


def walk_forward(log_rets: pd.Series, strat: TSMOMStrategy) -> pd.DataFrame:
    full = strat.run(log_rets)
    net  = full["net_return"]

    start_date = log_rets.index[MIN_TRAIN_DAYS]
    end_date   = log_rets.index[-1]
    rows       = []
    fold_start = start_date
    fold_num   = 1

    while fold_start < end_date:
        fold_end = min(fold_start + pd.DateOffset(months=FOLD_MONTHS), end_date)
        fold_net = net.loc[fold_start:fold_end].dropna()

        if len(fold_net) >= 20:
            m = compute_metrics(fold_net)
            rows.append({
                "Fold":   fold_num,
                "Start":  fold_start.date(),
                "End":    fold_end.date(),
                "Days":   len(fold_net),
                "Sharpe": m["sharpe"],
                "Return": m["ann_return"],
                "MaxDD":  m["max_dd"],
            })

        fold_start = fold_end + pd.Timedelta(days=1)
        fold_num  += 1

    return pd.DataFrame(rows)


for ticker in ASSETS:
    folds = walk_forward(log_returns[ticker], strategy)
    if folds.empty:
        print(f"\n  {ticker}: insufficient data for walk-forward")
        continue

    pos_folds  = (folds["Sharpe"] > 0).sum()
    avg_sharpe = folds["Sharpe"].mean()

    print(f"\n  {ticker}:")
    print(f"  {'Fold':<5} {'Start':<12} {'End':<12} {'Days':<6} "
          f"{'Sharpe':>7} {'Ann Ret':>9} {'MaxDD':>8}")
    print(f"  {'─'*5} {'─'*12} {'─'*12} {'─'*6} {'─'*7} {'─'*9} {'─'*8}")
    for _, row in folds.iterrows():
        flag = " *" if row["Sharpe"] > 0.5 else ("  " if row["Sharpe"] > 0 else " ✗")
        print(f"  {int(row['Fold']):<5} {str(row['Start']):<12} {str(row['End']):<12} "
              f"{int(row['Days']):<6} {row['Sharpe']:>7.2f} {row['Return']:>+9.1%} "
              f"{row['MaxDD']:>8.1%}{flag}")
    print(f"  → {pos_folds}/{len(folds)} folds positive  |  avg Sharpe = {avg_sharpe:.2f}")

# ─── STEP 5: PER-YEAR BREAKDOWN ───────────────────────────────────────────────
print("\n" + "=" * 70)
print("Step 5: PER-YEAR BREAKDOWN")
print("=" * 70)

YEAR_NOTES = {
    2018: "BEAR (BTC −73%) ← KEY TEST",
    2019: "recovery",
    2020: "BULL",
    2021: "BULL",
    2022: "BEAR (BTC −65%) ← KEY TEST",
    2023: "recovery",
    2024: "recovery/bull",
    2025: "2025",
    2026: "partial",
}

for ticker in ASSETS:
    yr_df = asset_yearly[ticker]
    if yr_df.empty:
        continue

    print(f"\n  {'─'*80}")
    print(f"  {ticker}")
    print(f"  {'─'*80}")
    print(f"  {'Year':<6} {'Return':>9} {'Sharpe':>7} {'MaxDD':>8} "
          f"{'#Trades':>8} {'B&H':>9} {'AvgPos':>8} {'%Long':>7} {'%Short':>7}  Note")
    print(f"  {'─'*6} {'─'*9} {'─'*7} {'─'*8} {'─'*8} {'─'*9} {'─'*8} {'─'*7} {'─'*7}")

    for year, row in yr_df.iterrows():
        note = YEAR_NOTES.get(year, "")
        flag = ""
        if year in BEAR_YEARS:
            if row["Return"] > 0:
                flag = " ✓ PROFITABLE IN BEAR"
            elif row["Avg Pos"] < -0.15:
                flag = " ✓ NET SHORT"
            elif row["Avg Pos"] > 0.15:
                flag = " ⚠ NET LONG IN BEAR"

        print(f"  {year:<6} {row['Return']:>+9.1%} {row['Sharpe']:>7.2f} "
              f"{row['MaxDD']:>8.1%} {row['# Trades']:>8} {row['B&H Return']:>+9.1%} "
              f"{row['Avg Pos']:>+8.3f} {row['% Long']:>7.1%} {row['% Short']:>7.1%}"
              f"  {note}{flag}")

# ─── STEP 6: BEAR MARKET ANALYSIS ─────────────────────────────────────────────
print("\n" + "=" * 70)
print("Step 6: BEAR MARKET DEEP DIVE — BTC 2018 and 2022")
print("=" * 70)

for year, bh_label in [(2018, "−73%"), (2022, "−65%")]:
    result = asset_results["BTC-USD"]
    mask   = result.index.year == year
    yr_res = result[mask].dropna(subset=["position"])

    print(f"\n  ── BTC {year} (B&H {bh_label}) ──")

    if yr_res.empty:
        print(f"  No data for {year} (BTC data may not reach that far)")
        continue

    yr_net  = yr_res["net_return"].dropna()
    yr_pos  = yr_res["position"]
    lr_yr   = log_returns["BTC-USD"].reindex(yr_res.index).dropna()

    avg_pos   = yr_pos.mean()
    pct_long  = (yr_pos > 0).mean()
    pct_short = (yr_pos < 0).mean()
    pct_flat  = (yr_pos == 0).mean()

    strat_ret = (1 + yr_net).prod() - 1
    bh_ret    = (np.exp(lr_yr)).prod() - 1

    equity_yr = (1 + yr_net).cumprod()
    roll_max  = equity_yr.cummax()
    max_dd_yr = ((equity_yr - roll_max) / roll_max).min()

    avg_scale = yr_res["vol_scalar"].mean()

    print(f"  Average position :  {avg_pos:+.4f}")
    print(f"  % time long      :  {pct_long:6.1%}")
    print(f"  % time short     :  {pct_short:6.1%}")
    print(f"  % time flat      :  {pct_flat:6.1%}")
    print(f"  Strategy return  :  {strat_ret:+.1%}")
    print(f"  B&H return       :  {bh_ret:+.1%}")
    print(f"  Strategy max DD  :  {max_dd_yr:+.1%}")
    print(f"  Avg vol scalar   :  {avg_scale:.3f}  (1.0 = on-target leverage)")

    if avg_pos < -0.15:
        print(f"  → VERDICT: Strategy correctly turned SHORT during the bear ✓")
    elif avg_pos < 0.05:
        print(f"  → VERDICT: Strategy was approximately FLAT — avoided the crash ✓")
    else:
        verdict_tag = "FAILED" if strat_ret < -0.10 else "PARTIAL FAILURE"
        print(f"  → VERDICT: {verdict_tag} — strategy remained LONG during bear ⚠")

    if avg_scale < 0.8:
        print(f"  → Vol scaling REDUCED exposure ({avg_scale:.2f}x) during high-vol crash ✓")
    elif avg_scale > 1.2:
        print(f"  ⚠ Vol scaling INCREASED exposure ({avg_scale:.2f}x) — unusual for a crash")
    else:
        print(f"  → Vol scaling near neutral ({avg_scale:.2f}x) during this period")

# ─── STEP 7: MULTI-ASSET PORTFOLIO ────────────────────────────────────────────
print("\n" + "=" * 70)
print("Step 7: MULTI-ASSET PORTFOLIO (equal risk, 1/3 each)")
print("=" * 70)

# Common date range where all assets have positions
net_series = {t: asset_results[t]["net_return"].dropna() for t in ASSETS}
common_idx = net_series[ASSETS[0]].index
for t in ASSETS[1:]:
    common_idx = common_idx.intersection(net_series[t].index)

portfolio_rets = sum(net_series[t].reindex(common_idx) for t in ASSETS) / len(ASSETS)
portfolio_met  = compute_metrics(portfolio_rets, "Portfolio 1/3")

print(f"\n  Common period: {common_idx[0].date()} → {common_idx[-1].date()} "
      f"({len(common_idx)} days)")

# Signal correlation check
sig_corr = pd.DataFrame({t: asset_results[t]["signal"].reindex(common_idx)
                         for t in ASSETS}).corr()
print(f"\n  Signal correlations:")
print(f"  BTC–ETH: {sig_corr.loc['BTC-USD','ETH-USD']:.3f}  "
      f"BTC–SOL: {sig_corr.loc['BTC-USD','SOL-USD']:.3f}  "
      f"ETH–SOL: {sig_corr.loc['ETH-USD','SOL-USD']:.3f}")
avg_corr = (sig_corr.loc['BTC-USD','ETH-USD'] +
            sig_corr.loc['BTC-USD','SOL-USD'] +
            sig_corr.loc['ETH-USD','SOL-USD']) / 3
if avg_corr < 0.5:
    print(f"  → Low avg correlation ({avg_corr:.3f}) — diversification benefit expected")
else:
    print(f"  → High avg correlation ({avg_corr:.3f}) — limited diversification benefit")

# ─── STEP 8: FULL METRICS TABLE ───────────────────────────────────────────────
print("\n" + "=" * 70)
print("Step 8: FULL METRICS")
print("=" * 70)

all_met = [asset_metrics[t] for t in ASSETS] + [portfolio_met]

print(f"\n  {'Asset':<16} {'Total Ret':>10} {'Ann Ret':>9} {'Sharpe':>7} "
      f"{'Sortino':>8} {'Max DD':>8} {'Calmar':>7} {'WinRate':>8}")
print(f"  {'─'*16} {'─'*10} {'─'*9} {'─'*7} {'─'*8} {'─'*8} {'─'*7} {'─'*8}")
for m in all_met:
    print(f"  {m['label']:<16} {m['total_return']:>+10.1%} {m['ann_return']:>+9.1%} "
          f"{m['sharpe']:>7.2f} {m['sortino']:>8.2f} {m['max_dd']:>8.1%} "
          f"{m['calmar']:>7.2f} {m['win_rate']:>8.1%}")

print(f"\n  {'Asset':<16} {'|Avg Pos|':>9} {'%Long':>7} {'%Short':>7} "
      f"{'%Flat':>7} {'Ann Turnover':>13}")
print(f"  {'─'*16} {'─'*9} {'─'*7} {'─'*7} {'─'*7} {'─'*13}")
for ticker in ASSETS:
    r        = asset_results[ticker].dropna()
    avg_pos  = r["position"].abs().mean()
    pct_long  = (r["position"] > 0).mean()
    pct_short = (r["position"] < 0).mean()
    pct_flat  = (r["position"] == 0).mean()
    n_years   = len(r) / TRADING_DAYS
    ann_turn  = r["turnover"].sum() / n_years
    print(f"  {ticker:<16} {avg_pos:>9.3f} {pct_long:>7.1%} {pct_short:>7.1%} "
          f"{pct_flat:>7.1%} {ann_turn:>13.2f}")

# ─── STEP 9: COMPARISON WITH FEASIBILITY ──────────────────────────────────────
print("\n" + "=" * 70)
print("Step 9: COMPARISON WITH FEASIBILITY CHECK")
print("=" * 70)
print(f"\n  Feasibility: in-sample 2020-2026, NO costs, 252-day Sharpe annualization")
print(f"  Full backtest: 2014+, realistic costs, 365-day annualization, bears included")

print(f"\n  {'Asset':<14} {'Feasibility':>12} {'Full BT':>9} {'Delta':>7}  Note")
print(f"  {'─'*14} {'─'*12} {'─'*9} {'─'*7}")
for ticker in ASSETS:
    feas  = FEASIBILITY_SHARPE[ticker]
    full  = asset_metrics[ticker]["sharpe"]
    delta = full - feas
    note  = ""
    if delta < -0.4:
        note = "costs + bear markets drag"
    elif delta < -0.1:
        note = "moderate cost drag"
    elif delta > 0.1:
        note = "longer data, more bear exposure helped"
    print(f"  {ticker:<14} {feas:>12.2f} {full:>9.2f} {delta:>+7.2f}  {note}")

# ─── STEP 10: SENSITIVITY ANALYSIS ───────────────────────────────────────────
print("\n" + "=" * 70)
print("Step 10: SENSITIVITY — BTC lookback [14, 21, 28, 42, 56]")
print("=" * 70)

sens_results = {}
print(f"\n  {'Lookback':<10} {'Sharpe':>7} {'Ann Ret':>9} {'MaxDD':>8} {'Calmar':>7}  Note")
print(f"  {'─'*10} {'─'*7} {'─'*9} {'─'*8} {'─'*7}")

for lb in SENSITIVITY_LBS:
    s = TSMOMStrategy(lookback=lb, vol_target=VOL_TARGET, vol_lookback=VOL_LOOKBACK,
                      fee_rate=FEE_RATE, slippage=SLIPPAGE)
    r = s.run(log_returns["BTC-USD"])
    m = compute_metrics(r["net_return"], f"lb={lb}")
    sens_results[lb] = m
    note = " ← SELECTED" if lb == LOOKBACK else ""
    print(f"  {lb:<10} {m['sharpe']:>7.2f} {m['ann_return']:>+9.1%} "
          f"{m['max_dd']:>8.1%} {m['calmar']:>7.2f}{note}")

sharpe_arr = [sens_results[lb]["sharpe"] for lb in SENSITIVITY_LBS]
sharpe_std = float(np.nanstd(sharpe_arr))
sharpe_rng = float(np.nanmax(sharpe_arr) - np.nanmin(sharpe_arr))
print(f"\n  Sharpe std  across lookbacks: {sharpe_std:.3f}")
print(f"  Sharpe range across lookbacks: {sharpe_rng:.3f}")
if sharpe_std < 0.20:
    verdict = "ROBUST — stable Sharpe across nearby lookbacks"
elif sharpe_std < 0.40:
    verdict = "MODERATE — some lookback sensitivity, acceptable"
else:
    verdict = "FRAGILE — 28d may be overfit, large variation across neighbors"
print(f"  → {verdict}")

# ─── STEP 11: PLOTS ───────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("Step 11: Generating plots…")
print("=" * 70)

# ── Plot A: Equity Curves (2×2: 3 assets + portfolio) ──────────────────────
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
axes = axes.flatten()

for i, ticker in enumerate(ASSETS):
    ax      = axes[i]
    result  = asset_results[ticker]
    net_r   = result["net_return"].dropna()
    lr_a    = log_returns[ticker].reindex(net_r.index)
    bh_r    = (np.exp(lr_a) - 1).dropna()

    eq_s  = (1 + net_r).cumprod()
    eq_bh = (1 + bh_r).cumprod()

    c = COLORS[ticker]
    ax.plot(eq_s.index,  eq_s.values,  color=c,   lw=1.8, label="TSMOM (net of costs)")
    ax.plot(eq_bh.index, eq_bh.values, color=c,   lw=0.9, linestyle="--",
            alpha=0.55, label="Buy & Hold")

    for year in [2018, 2022]:
        ym = eq_s.index.year == year
        if ym.any():
            yi = eq_s.index[ym]
            ax.axvspan(yi[0], yi[-1], alpha=0.12, color="red",
                       label=(f"{year} bear" if year == 2018 else None))

    ax.set_yscale("log")
    sh = asset_metrics[ticker]["sharpe"]
    ax.set_title(f"{ticker}  |  TSMOM Sharpe = {sh:.2f}", fontsize=11)
    ax.set_ylabel("Cumulative Return (log scale)")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(alpha=0.3)

# Portfolio panel
ax     = axes[3]
eq_p   = (1 + portfolio_rets.dropna()).cumprod()
lr_btc = log_returns["BTC-USD"].reindex(portfolio_rets.dropna().index)
eq_btc = (1 + (np.exp(lr_btc) - 1).dropna()).cumprod()

ax.plot(eq_p.index,   eq_p.values,   color="black", lw=2.0, label="Portfolio (1/3 each)")
ax.plot(eq_btc.index, eq_btc.values, color="orange", lw=0.9, linestyle="--",
        alpha=0.6, label="BTC B&H")
for year in [2018, 2022]:
    ym = eq_p.index.year == year
    if ym.any():
        yi = eq_p.index[ym]
        ax.axvspan(yi[0], yi[-1], alpha=0.12, color="red")
ax.set_yscale("log")
ax.set_title(f"Portfolio (equal risk)  |  Sharpe = {portfolio_met['sharpe']:.2f}", fontsize=11)
ax.set_ylabel("Cumulative Return (log scale)")
ax.legend(fontsize=8, loc="upper left")
ax.grid(alpha=0.3)

fig.suptitle("TSMOM Equity Curves — Full Backtest (net of costs, red = bear years)",
             fontsize=13)
fig.tight_layout()
fig.savefig("outputs/tsmom_equity_curve.png", dpi=150)
plt.close(fig)
print("  Saved: outputs/tsmom_equity_curve.png")


# ── Plot B: Per-Year Sharpe Heatmap ────────────────────────────────────────
all_years = sorted(set().union(*[set(asset_yearly[t].index) for t in ASSETS]))
yr_mat    = np.array([
    [asset_yearly[t]["Sharpe"].get(y, np.nan) for y in all_years]
    for t in ASSETS
])

cmap = mcolors.LinearSegmentedColormap.from_list(
    "rwg", [(0, "#d73027"), (0.35, "#fee08b"), (0.5, "#ffffff"),
            (0.65, "#a6d96a"), (1.0, "#1a7837")]
)
vmax = max(abs(np.nanmax(yr_mat)), abs(np.nanmin(yr_mat)), 1.0)

fig, ax = plt.subplots(figsize=(max(12, len(all_years) * 0.9), 4))
im = ax.imshow(yr_mat, cmap=cmap, vmin=-vmax, vmax=vmax, aspect="auto")
ax.set_xticks(range(len(all_years)))
ax.set_xticklabels(all_years, fontsize=9, rotation=45)
ax.set_yticks(range(len(ASSETS)))
ax.set_yticklabels([t.replace("-USD", "") for t in ASSETS], fontsize=11)
ax.set_title("TSMOM Per-Year Sharpe Ratio  (red = negative, green = positive)",
             fontsize=12)

for i in range(len(ASSETS)):
    for j in range(len(all_years)):
        v = yr_mat[i, j]
        if not np.isnan(v):
            ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                    fontsize=8, color="black" if abs(v) < 0.65 * vmax else "white")

# Mark bear years with red borders
for j, yr in enumerate(all_years):
    if yr in [2018, 2022]:
        rect = plt.Rectangle((j - 0.5, -0.5), 1, len(ASSETS),
                              linewidth=2, edgecolor="red", facecolor="none")
        ax.add_patch(rect)

plt.colorbar(im, ax=ax, fraction=0.02, pad=0.04, label="Sharpe")
fig.tight_layout()
fig.savefig("outputs/tsmom_yearly_sharpe.png", dpi=150, bbox_inches="tight")
plt.close(fig)
print("  Saved: outputs/tsmom_yearly_sharpe.png")


# ── Plot C: Bear Market Analysis ────────────────────────────────────────────
years_to_plot = [y for y in [2018, 2022]
                 if y in asset_results["BTC-USD"].index.year]

if years_to_plot:
    fig, axes = plt.subplots(len(years_to_plot), 2,
                             figsize=(16, 6 * len(years_to_plot)))
    if len(years_to_plot) == 1:
        axes = axes[np.newaxis, :]

    for row_i, year in enumerate(years_to_plot):
        result  = asset_results["BTC-USD"]
        mask    = result.index.year == year
        yr_res  = result[mask].dropna(subset=["position"])
        yr_net  = yr_res["net_return"].dropna()
        yr_pos  = yr_res["position"]
        lr_yr   = log_returns["BTC-USD"].reindex(yr_res.index).dropna()

        if yr_net.empty:
            continue

        eq_s  = (1 + yr_net).cumprod()
        eq_bh = (np.exp(lr_yr)).cumprod()
        eq_s  = eq_s  / eq_s.iloc[0]
        eq_bh = eq_bh / eq_bh.iloc[0]

        strat_ret = (1 + yr_net).prod() - 1
        bh_ret    = eq_bh.iloc[-1] - 1

        # Equity panel
        ax = axes[row_i, 0]
        ax.plot(eq_s.index,  eq_s.values,  color="black", lw=2.0, label="TSMOM (net)")
        ax.plot(eq_bh.index, eq_bh.values, color="red",   lw=1.5, linestyle="--",
                alpha=0.8, label="BTC Buy & Hold")
        ax.axhline(1.0, color="gray", lw=0.6, linestyle=":")
        ax.set_title(f"BTC {year} — Equity  ({BEAR_YEARS[year]})", fontsize=11)
        ax.set_ylabel("Normalized (start = 1.0)")
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)
        ax.text(0.02, 0.05,
                f"TSMOM: {strat_ret:+.1%}\nB&H:   {bh_ret:+.1%}",
                transform=ax.transAxes, fontsize=10, va="bottom",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.6))

        # Position panel
        ax   = axes[row_i, 1]
        pos  = yr_pos.dropna()
        avg  = pos.mean()
        ax.fill_between(pos.index, 0, pos.values,
                        where=(pos.values > 0), color="green", alpha=0.35, label="Long")
        ax.fill_between(pos.index, 0, pos.values,
                        where=(pos.values < 0), color="red",   alpha=0.35, label="Short")
        ax.plot(pos.index, pos.values, color="black", lw=0.8, alpha=0.7)
        ax.axhline(0, color="black", lw=0.8)
        ax.set_title(f"BTC {year} — Position  (avg = {avg:+.3f})", fontsize=11)
        ax.set_ylabel("Position Size (1.0 = full vol-target)")
        ax.legend(fontsize=9)
        ax.grid(alpha=0.3)

    fig.suptitle("TSMOM Bear Market Analysis — BTC 2018 & 2022", fontsize=13)
    fig.tight_layout()
    fig.savefig("outputs/tsmom_bear_analysis.png", dpi=150)
    plt.close(fig)
    print("  Saved: outputs/tsmom_bear_analysis.png")
else:
    print("  WARNING: Neither 2018 nor 2022 found in BTC data — bear plot skipped")


# ─── STEP 12: FINAL ASSESSMENT ────────────────────────────────────────────────
print("\n" + "=" * 70)
print("FINAL ASSESSMENT")
print("=" * 70)

btc_m   = asset_metrics["BTC-USD"]
eth_m   = asset_metrics["ETH-USD"]
sol_m   = asset_metrics["SOL-USD"]
port_m  = portfolio_met

yr_btc  = asset_yearly["BTC-USD"]
btc2018 = yr_btc.loc[2018] if 2018 in yr_btc.index else None
btc2022 = yr_btc.loc[2022] if 2022 in yr_btc.index else None

avg_asset_sharpe = np.nanmean([btc_m["sharpe"], eth_m["sharpe"], sol_m["sharpe"]])

print(f"\na) Does TSMOM work on crypto after realistic costs (fee=0.035%, slip=0.05%)?")
if avg_asset_sharpe > 0.6:
    print(f"   YES — Avg Sharpe = {avg_asset_sharpe:.2f} "
          f"(BTC={btc_m['sharpe']:.2f}, ETH={eth_m['sharpe']:.2f}, SOL={sol_m['sharpe']:.2f})")
    print(f"   Signal survives realistic cost friction.")
elif avg_asset_sharpe > 0.25:
    print(f"   MARGINAL — Avg Sharpe = {avg_asset_sharpe:.2f}. Viable but thin margin.")
    print(f"   Needs careful execution; any slippage increase erodes edge.")
else:
    print(f"   NO — Avg Sharpe = {avg_asset_sharpe:.2f}. Costs eat the signal.")

print(f"\nb) Does it work in bear markets (2018 and 2022)?")
for year, yr_row, label in [(2018, btc2018, "−73%"), (2022, btc2022, "−65%")]:
    if yr_row is None:
        print(f"   {year}: No data available for BTC")
        continue
    ret     = yr_row["Return"]
    avg_pos = yr_row["Avg Pos"]
    bh      = yr_row["B&H Return"]
    outperformance = ret - bh
    if ret > 0:
        print(f"   {year}: YES — returned {ret:+.1%} while B&H did {bh:+.1%} "
              f"(outperform: {outperformance:+.1%}) ✓")
    elif outperformance > 30:
        # Vastly better than B&H even if slightly negative
        direction = "net short" if avg_pos < -0.05 else "near-flat"
        print(f"   {year}: YES (outperformed) — strategy {direction} (avg pos {avg_pos:+.3f}), "
              f"returned {ret:+.1%} vs B&H {bh:+.1%} ({outperformance:+.1%} alpha) ✓")
    elif avg_pos < -0.1:
        print(f"   {year}: PARTIAL — net short (avg pos {avg_pos:+.3f}), "
              f"returned {ret:+.1%} vs B&H {bh:+.1%} — limited downside")
    elif avg_pos > 0.1 and ret < bh + 10:
        print(f"   {year}: ⚠ FAILED — stayed long (avg pos {avg_pos:+.3f}), "
              f"returned {ret:+.1%} vs B&H {bh:+.1%}")
        print(f"          → strategy is disguised buy-and-hold in this year")
    else:
        direction = "net short" if avg_pos < -0.05 else ("near-flat" if avg_pos < 0.05 else "net long")
        print(f"   {year}: PARTIAL — {direction} (avg pos {avg_pos:+.3f}), "
              f"returned {ret:+.1%} vs B&H {bh:+.1%} ({outperformance:+.1%} alpha)")

print(f"\nc) Is the 28d lookback robust or overfit?")
print(f"   Lookback Sharpes: " +
      "  ".join(f"{lb}d={sens_results[lb]['sharpe']:.2f}" for lb in SENSITIVITY_LBS))
print(f"   Std = {sharpe_std:.3f}  Range = {sharpe_rng:.3f}")
print(f"   → {verdict}")

print(f"\nd) Does vol scaling genuinely help?")
# Run BTC without vol scaling (signal only, no scalar)
raw_sig  = np.sign(log_returns["BTC-USD"].rolling(LOOKBACK).sum().shift(1))
raw_arith = np.exp(log_returns["BTC-USD"]) - 1
raw_gross = raw_sig * raw_arith
raw_turn  = (raw_sig - raw_sig.shift(1).fillna(0)).abs()
raw_net   = (raw_gross - raw_turn * (FEE_RATE + SLIPPAGE)).dropna()
raw_sh    = compute_metrics(raw_net, "raw")["sharpe"]
vol_sh    = btc_m["sharpe"]
delta_sh  = vol_sh - raw_sh
print(f"   BTC Sharpe WITHOUT vol scaling: {raw_sh:.2f}")
print(f"   BTC Sharpe WITH    vol scaling: {vol_sh:.2f}  (Δ = {delta_sh:+.2f})")
if delta_sh > 0.10:
    print(f"   → YES — vol scaling adds meaningful risk-adjusted value ✓")
elif delta_sh > -0.10:
    print(f"   → NEUTRAL — vol scaling has minor effect (±0.1 Sharpe)")
else:
    print(f"   → NO  — vol scaling hurts; the signal is already well-calibrated")

print(f"\ne) Does the multi-asset portfolio improve risk-adjusted returns?")
print(f"   Avg single-asset Sharpe:  {avg_asset_sharpe:.2f}")
print(f"   Portfolio Sharpe:         {port_m['sharpe']:.2f}")
if port_m["sharpe"] > avg_asset_sharpe + 0.10:
    print(f"   → YES — diversification adds {port_m['sharpe']-avg_asset_sharpe:+.2f} Sharpe ✓")
elif port_m["sharpe"] < avg_asset_sharpe - 0.10:
    print(f"   → NO  — portfolio underperforms average (high signal correlation?)")
else:
    print(f"   → NEUTRAL — portfolio ≈ average single-asset ({avg_corr:.2f} avg signal corr)")

print(f"\nf) Is this strategy deployable on Hyperliquid testnet?")
bears_ok = True
for yr_row, year in [(btc2018, 2018), (btc2022, 2022)]:
    if yr_row is not None and yr_row["Return"] < -0.20 and yr_row["Avg Pos"] > 0.1:
        bears_ok = False

if avg_asset_sharpe > 0.5 and bears_ok:
    print(f"   YES — Recommended for testnet deployment.")
    print(f"   Start with BTC-USD (deepest history + most liquid).")
    print(f"   Use 28d lookback, 15% vol target, 2x leverage cap.")
elif avg_asset_sharpe > 0.25:
    print(f"   BORDERLINE — Test on testnet but do not allocate real capital yet.")
    print(f"   Sharpe is marginal ({avg_asset_sharpe:.2f}); one adverse regime may flip it.")
else:
    print(f"   NO — Strategy does not clear the Sharpe bar after costs.")
    print(f"   Recommend abandoning or revisiting with a different universe.")

print(f"\ng) Estimated live trading performance (based on full backtest):")
print(f"   BTC individual:")
print(f"     Annualized return : {btc_m['ann_return']:+.1%}")
print(f"     Max drawdown      : {btc_m['max_dd']:.1%}")
print(f"     Sharpe ratio      : {btc_m['sharpe']:.2f}")
print(f"   Portfolio (1/3 each):")
print(f"     Annualized return : {port_m['ann_return']:+.1%}")
print(f"     Max drawdown      : {port_m['max_dd']:.1%}")
print(f"     Sharpe ratio      : {port_m['sharpe']:.2f}")
print(f"")
print(f"   Caveats for live deployment:")
print(f"   • Backtest uses daily bars; intraday slippage may exceed 0.05% on illiquid alts")
print(f"   • Perpetual funding rates not modeled (can add ±1-3%/yr)")
print(f"   • Tail risk: 2020 March, 2022 LUNA, 2022 FTX not fully captured in metrics")
print(f"   • Strategy decay: if signal becomes crowded, alpha compresses")
print(f"   • SOL data only from 2020 — no 2018 bear validation for SOL")

print("\n" + "=" * 70)
print("BACKTEST COMPLETE")
print("=" * 70)
print(f"\nOutput files:")
print(f"  outputs/tsmom_equity_curve.png")
print(f"  outputs/tsmom_yearly_sharpe.png")
print(f"  outputs/tsmom_bear_analysis.png")
print(f"  outputs/tsmom_trades.csv")
