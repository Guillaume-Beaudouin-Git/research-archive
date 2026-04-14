"""
Sanity check for the trading pipeline.
Run this from your ml_pipeline/ folder.

Checks:
    1. What period is the test set actually covering?
    2. What do the individual trades look like?
    3. What happens with a RANDOM classifier? (red flag detector)
    4. Is the annualized return formula misleading?
    5. What does the strategy look like without short selling?
"""

import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

from config   import Config
from features import extract_features
from labeler  import compute_labels
from trainer  import SingleSplitTrainer
from backtest import Backtester


# ── Setup ──────────────────────────────────────────────────────────────────────
cfg         = Config()
cfg.symbols = ["BTC-USD"]
cfg.max_epochs = 80

df = yf.download("BTC-USD", period=cfg.period, interval=cfg.interval,
                 auto_adjust=True, progress=False)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
df = df[["Open","High","Low","Close","Volume"]].dropna()

feat   = extract_features(df)
labels = compute_labels(df, cfg)
valid  = feat.dropna().index.intersection(labels.index)
X      = feat.loc[valid].values.astype("float32")
y      = labels.loc[valid].values.astype("int64")
prices = df.loc[valid, ["Open","Close"]]

trainer = SingleSplitTrainer(cfg)
history = trainer.fit(X, y)
X_test, y_test = trainer.get_test_split(X, y)
prices_test    = prices.iloc[-len(X_test):]
preds          = trainer.predict(X_test)

print("\n" + "="*55)
print("SANITY CHECK REPORT")
print("="*55)


# ── Check 1: Test period dates ─────────────────────────────────────────────────
print(f"\n[1] TEST SET PERIOD")
print(f"    Start : {prices_test.index[0].date()}")
print(f"    End   : {prices_test.index[-1].date()}")
print(f"    Bars  : {len(prices_test)} trading days")
print(f"    BTC price change over this period: "
      f"{prices_test['Close'].iloc[-1]/prices_test['Close'].iloc[0]-1:+.2%}")


# ── Check 2: Individual trade inspection ───────────────────────────────────────
print(f"\n[2] INDIVIDUAL TRADES (model predictions)")
bt = Backtester(cfg)
equity, trades = bt.run(prices_test, preds)

if len(trades):
    print(trades[["position","entry","exit","trade_pnl_pct","reason"]].to_string())
    print(f"\n    Min trade pnl : {trades['trade_pnl_pct'].min():.2f}%")
    print(f"    Max trade pnl : {trades['trade_pnl_pct'].max():.2f}%")
    print(f"    Mean trade pnl: {trades['trade_pnl_pct'].mean():.2f}%")
else:
    print("    No trades executed.")


# ── Check 3: Random classifier baseline ───────────────────────────────────────
print(f"\n[3] RANDOM CLASSIFIER BASELINE (red flag test)")
print("    If random predictions give similar Sharpe -> backtest is broken.\n")

rng = np.random.default_rng(42)
n_runs = 50
random_sharpes, random_returns = [], []

for _ in range(n_runs):
    # Random predictions with same label distribution as model
    rand_preds = rng.integers(0, 3, size=len(X_test))
    eq_rand, tr_rand = bt.run(prices_test, rand_preds)
    m_rand = bt.compute_metrics(eq_rand, tr_rand, freq="1d")
    random_sharpes.append(m_rand["sharpe"])
    random_returns.append(m_rand["total_return"])

model_metrics = bt.compute_metrics(equity, trades, freq="1d")

print(f"    Model  Sharpe : {model_metrics['sharpe']:.3f}")
print(f"    Random Sharpe : {np.mean(random_sharpes):.3f} "
      f"(mean over {n_runs} runs, std={np.std(random_sharpes):.3f})")
print(f"    Model  Total Return : {model_metrics['total_return']:+.2%}")
print(f"    Random Total Return : {np.mean(random_returns):+.2%} "
      f"(mean, std={np.std(random_returns):.2%})")

z_score = (model_metrics["sharpe"] - np.mean(random_sharpes)) / (np.std(random_sharpes) + 1e-9)
print(f"\n    Z-score of model Sharpe vs random: {z_score:.2f}")
if z_score > 2:
    print("    -> Model is statistically better than random. (but read checks below)")
else:
    print("    -> WARNING: Model is NOT significantly better than random.")


# ── Check 4: Annualization problem ────────────────────────────────────────────
print(f"\n[4] ANNUALIZATION SANITY CHECK")
n_days   = len(prices_test)
tot_ret  = model_metrics["total_return"]
ann_ret  = (1 + tot_ret) ** (365 / n_days) - 1
print(f"    Test period   : {n_days} days ({n_days/365:.2f} years)")
print(f"    Total return  : {tot_ret:+.2%}")
print(f"    Annualized    : {ann_ret:+.2%}  <- USE THIS WITH CAUTION if < 2 years")
print(f"    Note: annualizing {tot_ret:+.0%} over {n_days} days is {'' if n_days >= 500 else 'NOT '}reliable.")


# ── Check 5: Long-only vs long+short ──────────────────────────────────────────
print(f"\n[5] LONG-ONLY vs LONG+SHORT COMPARISON")

cfg_long          = Config()
cfg_long.allow_short = False
bt_long           = Backtester(cfg_long)
eq_long, tr_long  = bt_long.run(prices_test, preds)
m_long            = bt_long.compute_metrics(eq_long, tr_long, freq="1d")

print(f"    Long+Short  -> Total Return: {model_metrics['total_return']:+.2%}  "
      f"Sharpe: {model_metrics['sharpe']:.3f}  Trades: {model_metrics.get('n_trades',0)}")
print(f"    Long-Only   -> Total Return: {m_long['total_return']:+.2%}  "
      f"Sharpe: {m_long['sharpe']:.3f}  Trades: {m_long.get('n_trades',0)}")
bh = bt.buy_and_hold(prices_test, cfg.initial_capital)
bh_ret = bh.iloc[-1]/bh.iloc[0]-1
print(f"    Buy & Hold  -> Total Return: {bh_ret:+.2%}")

print(f"\n    If Long+Short >> Long-Only in a bear market -> the strategy")
print(f"    profits mainly from shorting, not from predictive skill on longs.")


# ── Check 6: Trade count statistical power ────────────────────────────────────
print(f"\n[6] STATISTICAL POWER")
n_trades = model_metrics.get("n_trades", 0)
win_rate = model_metrics.get("win_rate", 0)
# Binomial confidence interval (Wilson)
from math import sqrt
z = 1.96
denom = 1 + z**2 / n_trades if n_trades else 1
center = (win_rate + z**2 / (2*n_trades)) / denom if n_trades else 0
margin = (z * sqrt(win_rate*(1-win_rate)/n_trades + z**2/(4*n_trades**2))) / denom if n_trades else 0
print(f"    N trades      : {n_trades}")
print(f"    Win rate      : {win_rate:.1%}")
print(f"    95% CI        : [{max(0,center-margin):.1%}, {min(1,center+margin):.1%}]")
print(f"    Note: need ~100+ trades for reliable win rate estimate.")


# ── Summary verdict ────────────────────────────────────────────────────────────
print(f"\n{'='*55}")
print("VERDICT")
print(f"{'='*55}")
print(f"""
Issues to investigate:
  - Annualized return ({ann_ret:+.0%}) is misleading on {n_days} days.
    Report Total Return ({tot_ret:+.2%}) instead.

  - {n_trades} trades is too few for reliable statistics.
    Loosen confidence_threshold (currently {cfg.confidence_threshold})
    to generate more trades, even if win rate drops.

  - Compare Long-Only vs Long+Short (Check 5 above).
    If Long-Only underperforms badly, shorting is doing all the work.

  - alpha/beta labeling filters ambiguous bars -> inflated win rate.
    The model predicts on pre-filtered 'clean' setups, not the full market.

What to do next:
  1. Extend to 3+ years of test data (use period='10y' if available)
  2. Set allow_short=False and see if strategy still beats B&H
  3. Lower confidence_threshold to 0.40 to get 100+ trades
  4. Run on out-of-sample assets (e.g. SOL-USD, ADA-USD) not used in training
""")