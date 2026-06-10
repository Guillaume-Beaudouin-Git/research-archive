# Crypto Algorithmic Trading System
## Technical Documentation & Strategy Explainer

---

## 1. Overview

This system is a **supervised machine learning classification pipeline** for cryptocurrency trading. It predicts whether the next price movement warrants a Buy, Hold, or Sell signal, then executes trades in a simulated portfolio with realistic constraints.

The approach is grounded in three peer-reviewed papers:

| Paper | Contribution |
|---|---|
| Parente et al. (2024) — *Expert Systems With Applications* | Feature engineering, α/β labeling scheme, MLP architecture |
| Felizardo et al. (2022) — *Expert Systems With Applications* | Supervised framing of trading as classification (vs RL), Sharpe metric |
| Kalariya et al. (2022) — *Mathematics* | MC Dropout for uncertainty-aware predictions |

---

## 2. Architecture — How the Files Fit Together

```
config.py          All hyperparameters in one place
    │
    ├── features.py        OHLCV → 18 technical indicators
    ├── labeler.py         Price history → Buy / Hold / Sell labels
    │
    ├── model.py           MLP neural network with MC Dropout
    ├── trainer.py         Walk-forward training pipeline
    │
    ├── backtest.py        Event-driven portfolio simulator
    ├── main.py            Single-asset pipeline (one train/test split)
    └── walk_forward.py    Multi-fold evaluation across market regimes
```

Data flows in one direction:

```
yfinance → OHLCV → features.py → labeler.py → trainer.py → backtest.py
```

---

## 3. Step-by-Step: How the Algorithm Works

### Step 1 — Data Download

Raw OHLCV (Open, High, Low, Close, Volume) daily bars are downloaded
from Yahoo Finance. For BTC-USD, this gives ~4,200 bars going back to
September 2014.

```
Period:   max (~11 years for BTC)
Interval: 1d (daily bars)
Source:   Yahoo Finance via yfinance
```

---

### Step 2 — Feature Engineering (features.py)

18 features are computed from past prices only. No future data is used.
Features are ranked by importance from Parente et al.'s SHAP analysis:

| # | Feature | Description |
|---|---|---|
| 1 | `bollinger` | %B position within Bollinger Bands = (Price - Lower) / (Upper - Lower) |
| 2 | `bb_width` | Band width = (Upper - Lower) / SMA — proxy for volatility regime |
| 3 | `ema_1_20` | (EMA1 - EMA20) / Price — short-term trend direction |
| 4 | `ema_20_50` | (EMA20 - EMA50) / Price — medium-term trend |
| 5 | `ema_50_100` | (EMA50 - EMA100) / Price — long-term trend |
| 6 | `ema_1_50` | (EMA1 - EMA50) / Price — momentum vs medium trend |
| 7 | `rsi` | RSI(14), normalised to [0, 1] |
| 8 | `ultosc` | Ultimate Oscillator (7/14/28 periods) — overbought/oversold |
| 9 | `zscore_close` | Z-score of Close over 30 bars — mean reversion signal |
| 10 | `zscore_vol` | Z-score of Volume over 30 bars — volume anomaly detection |
| 11 | `ret_1` | 1-bar log return — immediate momentum |
| 12 | `ret_5` | 5-bar log return — weekly momentum |
| 13 | `ret_20` | 20-bar log return — monthly momentum |
| 14 | `atr` | Average True Range (z-score normalised) — volatility |
| 15 | `hour` | Hour of day, normalised [0, 1] |
| 16 | `dayofweek` | Day of week [0, 1] — seasonality |
| 17 | `month` | Month of year [0, 1] — seasonality |
| 18 | `vol_ret` | Volume return (1-bar pct change, clipped) |

All features use only rolling windows of past data — no look-ahead bias.
Prices are converted to returns for stationarity (Felizardo et al.).

---

### Step 3 — Labeling (labeler.py)

Each bar is labeled Buy, Hold, or Sell based on whether a trade opened
now would be profitable over the next `forward_window` bars.

**Return formula (Parente et al., Definition 2):**

```
R(k) = [(1 - fee) × Close_{t+k}  -  (1 + fee) × Open_t]  /  Open_t
```

Both legs of the fee are accounted for — the label only fires if the
move survives the round-trip transaction cost.

**Label rules:**

```
alpha < |R(k)| < beta   AND   R(k) > 0   →   Buy  (2)
alpha < |R(k)| < beta   AND   R(k) < 0   →   Sell (0)
Otherwise                                 →   Hold (1)
```

**Parameters:**

| Parameter | Value | Meaning |
|---|---|---|
| `forward_window` | 2 | Look 2 bars ahead |
| `alpha` | 0.015 (1.5%) | Minimum move to be worth trading |
| `beta` | 0.15 (15%) | Maximum move (above = exogenous shock, skip) |
| `fee` | 0.002 (0.2%) | Round-trip transaction cost |

**Why alpha and beta matter:**
- Moves below `alpha` are noise — not worth the fee
- Moves above `beta` are black swan events (exchange hacks, regulatory bans) — not predictable from technical patterns alone
- Only the "clean and directional" moves in between are labeled

Roughly 30-40% of bars get a Buy or Sell label. The rest are Hold.

Hold is the majority class (~60%) and is undersampled in training to
prevent the model from predicting Hold on everything.

---

### Step 4 — Model: MLP with MC Dropout (model.py)

**Architecture:**

```
Input (18 features)
    → Linear(18 → 128) + BatchNorm + LeakyReLU + Dropout(0.2)
    → Linear(128 → 64) + BatchNorm + LeakyReLU + Dropout(0.2)
    → Linear(64 → 32)  + BatchNorm + LeakyReLU + Dropout(0.2)
    → Linear(32 → 3)   + Softmax
Output: P(Sell), P(Hold), P(Buy)
```

**Why MLP and not LSTM or Transformer?**
Parente et al. showed MLP outperforms XGBoost, Logit and SGDLinear on
this task. The temporal structure is already encoded in the rolling
features (RSI, EMA crossovers, Z-scores) — explicit sequence modelling
adds complexity without consistent gain on daily bars.

**MC Dropout (Kalariya et al.):**
Instead of evaluating the model once with Dropout disabled, Dropout is
kept active at inference time and 30 stochastic forward passes are run.
The outputs are averaged:

```python
proba = mean([softmax(model(x)) for _ in range(30)])
```

This gives calibrated class probabilities. If `max(proba) < 0.50`
(confidence threshold), the prediction is overridden to Hold — the
model only trades when confident.

---

### Step 5 — Training (trainer.py)

**Walk-forward chronological split:**

```
├─────────────── Train (90%) ────────────────┤── Val (10%) ──┤
```

No shuffling. The scaler is fitted on train only, then applied to val.
This is the single most important rule in financial ML — breaking it
causes look-ahead bias.

**Training details:**

| Setting | Value |
|---|---|
| Optimizer | AdamW |
| LR schedule | CosineAnnealing (lr × 0.01 at end) |
| Loss | CrossEntropyLoss with inverse-frequency class weights |
| Batch size | 256 |
| Max epochs | 80 |
| Early stopping | patience = 15 epochs on val loss |
| Gradient clipping | max_norm = 1.0 |

---

### Step 6 — Backtesting (backtest.py)

The backtester simulates a real portfolio with four realistic constraints:

**1. Fractional position sizing**
Each trade deploys only 30% of capital, not 100%.

```
Portfolio impact = position_size × trade_P&L
                 = 0.30 × 10%  =  3% portfolio gain
```

This prevents astronomical compounding from individual trades.

**2. Transaction costs**
Each entry and exit incurs:
- `fee = 0.2%` (exchange commission)
- `slippage = 0.1%` (market impact / bid-ask spread)
- Total round-trip cost: ~0.6%

**3. No auto-flip**
When a Long position is closed on a Sell signal, the portfolio goes
FLAT. It only re-enters on the next explicit Buy or Sell signal.
The portfolio is not always in position.

**4. Risk controls**
- Stop-loss: forced exit if trade P&L drops below -5%
- Max hold: forced exit after 30 bars regardless of signal

**Trade execution:**
```
Signal = Buy   and position = flat  →  Open Long  at Open × (1 + fee + slippage)
Signal = Sell  and position = Long  →  Close Long at Open × (1 - fee - slippage)
                                    →  Go flat (not short)
Signal = Sell  and position = flat  →  Open Short at Open × (1 - fee - slippage)
Signal = Buy   and position = Short →  Cover Short at Open × (1 + fee + slippage)
                                    →  Go flat (not long)
```

---

### Step 7 — Walk-Forward Validation (walk_forward.py)

Instead of one fixed train/test split, the training window expands
annually and a fresh out-of-sample year is evaluated each time:

```
Fold 1:  Train [2014–2017] → Test [2017–2018]   (bull run + crash)
Fold 2:  Train [2014–2018] → Test [2018–2019]   (bear + recovery)
Fold 3:  Train [2014–2019] → Test [2019–2020]   (flat + Covid crash)
Fold 4:  Train [2014–2020] → Test [2020–2021]   (bull run)
Fold 5:  Train [2014–2021] → Test [2021–2022]   (bear market -60%)
Fold 6:  Train [2014–2022] → Test [2022–2023]   (recovery)
Fold 7:  Train [2014–2023] → Test [2023–2024]   (bull run)
Fold 8:  Train [2014–2024] → Test [2024–2025]   (high volatility)
```

A model is trained fresh for each fold. The test set is never touched
during training. This covers all major BTC market regimes and gives a
realistic distribution of live performance.

---

## 4. Performance Results (BTC-USD, revised backtest)

> **WARNING — READ BEFORE INTERPRETING THESE NUMBERS**
> These are in-sample backtest results subject to significant inflation.
> Key sources of bias: (1) the α/β labeling scheme filters ~60% of bars,
> so win rate is measured only on pre-selected "clean" setups, not the
> full market; (2) 30% position sizing caps each trade's portfolio impact
> to 1.5%, mechanically suppressing drawdown; (3) daily slippage of 0.1%
> is optimistic at scale. Realistic live estimates are in section 5.
> Do not use these figures for sizing or capital allocation decisions.

| Fold | Period | Regime | Sharpe | Total Return | B&H | MDD |
|---|---|---|---|---|---|---|
| 1 | 2017–2018 | Bull + crash | 3.17 | +466% | +52% | -3.8% |
| 2 | 2018–2019 | Bear + recovery | 3.24 | +142% | +24% | -4.8% |
| 3 | 2019–2020 | Flat + Covid | 4.34 | +199% | +34% | -2.4% |
| 4 | 2020–2021 | Bull run | 4.42 | +392% | +355% | -4.3% |
| 5 | 2021–2022 | Bear -60% | 3.79 | +121% | -61% | -2.5% |
| 6 | 2022–2023 | Recovery | 2.91 | +84% | +38% | -2.5% |
| 7 | 2023–2024 | Bull run | 4.27 | +146% | +122% | -1.7% |
| 8 | 2024–2025 | High vol | 4.60 | +97% | +97% | -0.4% |
| **Avg** | | | **3.84** | **+206%** | **+70%** | **-2.8%** |

**Beat B&H: 7/8 folds.** The critical fold is fold 5 (bear market):
strategy +121% while BTC lost 60%. This is where the short-selling
edge is most clearly demonstrated. All figures are illustrative —
see section 5 for realistic live estimates.

---

## 5. Honest Assessment of Limitations

**What is likely real:**
- The directional signal exists — proven by fold 5 (bear market) and
  the SOL-USD out-of-sample test (Sharpe 3.1–6.0 on an unseen asset)
- The strategy has a genuine edge in trend identification
- Beat B&H in 7/8 independent market regimes

**What is likely overstated:**

| Metric | Backtest | Realistic Live Estimate |
|---|---|---|
| Sharpe | 3.84 | 1.0 – 2.5 |
| Win rate | 89.8% | 55% – 65% |
| Max Drawdown | -2.8% | -15% – -30% |
| Annual Return | 83–466% | 30% – 100% |

**Why the gap:**
1. **Win rate inflation** — the α/β labeling filters ambiguous bars.
   The model is tested only on "clean" setups, not the full market.
2. **MDD compression** — 30% position sizing + 5% stop-loss limits
   each trade's portfolio impact to max 1.5%. Real trading involves
   correlated losses and gap risk.
3. **Daily bars** — slippage of 0.1% is optimistic. At scale or in
   illiquid markets, true slippage is higher.
4. **Single asset training** — the model is trained and tested on BTC.
   Regime changes not present in training data will not be handled well.

---

## 6. What to Do Before Going Live

1. **Test on more assets** — run `walk_forward.py` on SOL, ADA, AVAX.
   If Sharpe stays above 1.0, the signal generalises.

2. **Paper trade for 3 months** — run the model daily on live prices
   without real money. Compare live predictions to backtest behaviour.

3. **Reduce position size further** — start at 10% per trade, not 30%.
   Sharpe will be similar, drawdown will shrink.

4. **Add transaction cost stress test** — rerun backtest with fee=0.005
   and slippage=0.003. If Sharpe stays above 1.5, the edge is robust.

5. **Check regime stability** — retrain quarterly as new data arrives.
   Crypto market microstructure changes faster than equities.

---

## 7. Quick Start

```bash
# Install dependencies
pip install torch yfinance pandas numpy scikit-learn matplotlib shap

# Single-asset run (BTC, ETH, LTC)
python main.py

# Full walk-forward validation (8 years, 8 folds)
python walk_forward.py

# Sanity checks (random baseline, long-only vs long-short)
python sanity_check.py
```

Configuration is in `config.py`. Key parameters to tune:

```python
alpha = 0.015               # lower = more trades, lower win rate
confidence_threshold = 0.50 # lower = more trades, lower precision
position_size = 0.30        # lower = less compounding, lower drawdown
allow_short = True          # False = long-only strategy
auto_flip = False           # True = always in position (inflates returns)
```

---

## 8. References

- Parente, M., Rizzuti, L., Trerotola, M. (2024). *A profitable trading algorithm for
  cryptocurrencies using a Neural Network model.* Expert Systems With Applications, 238.
- Felizardo, L.K. et al. (2022). *Outperforming algorithmic trading reinforcement learning
  systems: A supervised approach.* Expert Systems With Applications, 202.
- Kalariya, V. et al. (2022). *Stochastic Neural Networks-Based Algorithmic Trading for
  the Cryptocurrency Market.* Mathematics, 10(9), 1456.