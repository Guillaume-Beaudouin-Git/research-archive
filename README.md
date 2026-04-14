# Algo_claude

## Overview

Algo_claude is a daily algorithmic trading system that trains a PyTorch MLP classifier on OHLCV price history to generate directional signals (BUY / HOLD / SELL) for crypto perpetuals traded on [Hyperliquid](https://hyperliquid.xyz). It is designed for a solo operator running a daily cron job on a Linux VPS, with a layered safety system that halts trading automatically if any guardrail fails. The project is in testnet validation — no live capital has been deployed.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Daily cron trigger                        │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │  check_kill_switch()   │  ← STOP file present? halt.
                   └────────────┬───────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │   get_latest_bars()    │  yfinance 6-month daily OHLCV
                   └────────────┬───────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │ check_data_freshness() │  ← stale/future-dated? halt.
                   └────────────┬───────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │  extract_features()    │  TA indicators, look-ahead-free
                   └────────────┬───────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │  load_model() +        │
                   │  check_model_freshness │  ← model > 45 days old? halt.
                   └────────────┬───────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │ predict_proba()        │  MC Dropout (30 samples)
                   │ → BUY / HOLD / SELL    │  BatchNorm stays in eval mode
                   └────────────┬───────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │  reconcile_position()  │  ← exchange vs state.json mismatch? alert.
                   └────────────┬───────────┘
                                │
                                ▼
                   ┌────────────────────────┐
                   │  HyperliquidClient     │  testnet / mainnet perp order
                   │  pos_size × capital    │
                   └────────────┬───────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
           logs/trades.csv          Telegram alert
           logs/funding.csv         (heartbeat + errors)
```

*Position sizing is a fixed fraction of capital per trade (`config.py: position_size = 0.30`). This is deliberately simple; Kelly-based or volatility-scaled sizing is a natural next improvement.*

---

## Components

- **`config.py`** — Single dataclass holding all hyperparameters: model architecture, labeling thresholds, backtesting assumptions, position sizing, and walk-forward settings.
- **`features.py`** — Look-ahead-free feature engineering (momentum, volatility, volume, moving averages) following Parente et al. (2024) and Felizardo et al. (2022).
- **`labeler.py`** — Three-class label generator (BUY / HOLD / SELL) using forward-return thresholds with fee-adjusted filtering.
- **`model.py`** — PyTorch MLP with BatchNorm + LeakyReLU + Dropout layers and a `predict_proba()` method that enables MC Dropout sampling while keeping BatchNorm in eval mode.
- **`trainer.py`** — Chronological train/validation split pipeline with early stopping; data is never shuffled across the temporal boundary.
- **`train_and_save.py`** — Entry point that downloads full history, trains the model, and serialises the `.pt` weights, `.pkl` scaler, and `meta.json` to `model_store/`.
- **`live_trader.py`** — Daily cron entry point: loads model, fetches data, runs all guardrails, computes signal, decides action, and optionally executes on Hyperliquid.
- **`hyperliquid_client.py`** — Minimal wrapper around `hyperliquid-python-sdk` for opening/closing USD-notional perp positions on testnet or mainnet.
- **`notifier.py`** — Telegram alerting with severity levels (info / warning / error); credentials loaded from `.env`.
- **`backtest.py`** — Event-driven backtester with fractional position sizing (30%), per-trade slippage, stop-loss, and `max_hold_bars` forced exit.
- **`dsr.py`** — Deflated Sharpe Ratio implementation (Bailey & López de Prado, 2014) used for backtest validation against selection bias.
- **`oos_eval.py`** — True out-of-sample evaluation across multiple assets using a hard temporal cutoff (`oos_start_date = 2023-01-01`).
- **`walk_forward.py`** — Walk-forward validation: expanding training window with a fresh held-out test fold at each step, the industry standard for time-series strategy evaluation.
- **`main.py`** — End-to-end research pipeline: trains, evaluates, runs walk-forward, backtests, and computes DSR for a single asset.
- **`sanity_check.py`** — Quick smoke-test that verifies the full pipeline (data → features → model → signal) runs without error locally.
- **`test_live_dryrun.py`** — Integration test suite (7 tests) exercising every guardrail in dry-run mode.
- **`packages.py`** — Development utility that pip-installs missing dependencies. Not used in production deployment — `requirements.txt` and a proper venv replace it.

---

## Safety & Monitoring

- **Kill switch** — If a file named `STOP` exists in the working directory, the trader logs the reason and halt time, fires a Telegram alert, and exits cleanly before touching any data or placing any order. Create it over SSH (`touch STOP`) to pause the bot without touching cron; delete it to resume.
- **Data freshness check** — Verifies that the latest bar returned by yfinance is yesterday's UTC date before computing any signal; stale or future-dated data causes an immediate halt with a Telegram alert, preventing trades on incorrect prices.
- **Model freshness check** — Reads `trained_until` from `meta.json` and refuses to trade if the model is older than 45 days (hard limit), with a warning alert at 30 days, ensuring signals are never computed from an excessively outdated model.
- **Position reconciliation** — Queries the live exchange position before deciding any action and compares it against the local `state.json`; on mismatch, the exchange is treated as authoritative, `state.json` is overwritten, and an alert is fired, preventing double-opens after a mid-trade crash.
- **Slippage and fill logging** — Every executed order is appended to `logs/fills.csv` with expected mid-price at submission, actual fill price, slippage in basis points, fill size, and execution latency. This creates the data needed to compare live execution against backtest assumptions — the single most important diagnostic for a newly-deployed strategy.
- **Funding rate logging** — After each live trade session, the 24-hour funding paid is fetched from the exchange and logged, allowing the operator to account for carry costs that are invisible in spot-price backtests.

---

## Statistical Validation

The Deflated Sharpe Ratio (DSR), introduced by Bailey & López de Prado (2014), corrects the observed Sharpe Ratio of a backtest for two sources of inflation: **non-normality of returns** (skewness and excess kurtosis widen the SR distribution) and **selection bias from multiple testing** (the more strategy variants a researcher tries, the more likely one appears good by chance). Concretely, DSR computes the probability that the true SR exceeds the *expected maximum SR* one would obtain from *n* independent trials — if that probability is below 0.95, the backtest result is not statistically distinguishable from luck.

**DSR is used here exclusively as a backtest validation metric.** It tells you whether a historical equity curve is likely to reflect genuine edge rather than overfitting. It has no role in position sizing.

**Position sizing is fixed:** the live trader always deploys 30% of configured capital per trade (`config.py: position_size = 0.30`), regardless of model confidence or DSR score.

> Bailey, D. H., & López de Prado, M. (2014). *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality.* Journal of Portfolio Management, 40(5), 94–107. https://doi.org/10.3905/jpm.2014.40.5.094

---

## Testing

Seven integration tests in `test_live_dryrun.py` exercise every guardrail against real PyTorch and pandas objects — no mocks, no exchange calls:

| Test | What it verifies |
|---|---|
| `test_kill_switch_halts` | `sys.exit(0)` is raised when a `STOP` file exists |
| `test_data_freshness_stale` | `sys.exit(1)` is raised when the latest bar is more than one day old |
| `test_model_freshness_expired` | `sys.exit(1)` is raised when `trained_until` exceeds `max_age_days` |
| `test_telegram_alert_sent` | `notifier.send()` is called at least once during a stale-data halt |
| `test_state_roundtrip` | `save_state` / `load_state` preserve the full state dict through a JSON round-trip |
| `test_no_real_orders_placed` | `HyperliquidClient` is never instantiated in dry-run mode |
| `test_fills_csv_not_written_in_dry_run` | `logs/fills.csv` is not written when `dry_run=True` |

**A production bug was caught and fixed during integration testing.** The original `get_signal()` set `model.train()` to enable Dropout sampling, which simultaneously put BatchNorm layers into training mode. With `batch_size=1` (single-sample inference in the live loop), PyTorch BatchNorm in training mode raises `ValueError: Expected more than 1 value per channel when training` because batch variance is undefined. The fix routes all inference through `model.predict_proba()`, which selectively sets only Dropout layers to train mode while keeping BatchNorm in eval mode (using frozen running statistics from training). This makes single-sample MC Dropout inference numerically and mechanically stable.

---

## Deployment

The system is designed to run as a **daily cron job on a Linux VPS** (Hetzner CX22 or equivalent). One cron line per symbol:

```
5 0 * * * cd /opt/algo_claude && /opt/venv/bin/python live_trader.py --symbol BTC-USD --capital 1000
10 0 * * * cd /opt/algo_claude && /opt/venv/bin/python live_trader.py --symbol SOL-USD --capital 1000
```

(Daily crypto bars close at 00:00 UTC; running 5-10 minutes after close ensures the latest bar is available. Staggering the two symbols by 5 minutes avoids concurrent yfinance requests.)

**Phase sequence:**
1. **Testnet validation** — run `--live` against Hyperliquid testnet, verify order placement, reconciliation, and alerting with no real capital at risk.
2. **Paper monitoring** — run dry-run alongside the live market for several weeks; compare logged signals against actual price moves.
3. **Mainnet** — only after testnet validation is satisfactory and the operator understands the risk.

The system is currently in phase 1 (testnet validation). It has not been deployed to mainnet.

---

## Project Structure

```
Algo_claude/
├── config.py               # All hyperparameters
├── features.py             # Feature engineering
├── labeler.py              # Three-class labeling
├── model.py                # PyTorch MLP
├── trainer.py              # Training pipeline
├── train_and_save.py       # Serialise model to model_store/
├── live_trader.py          # Daily cron entry point
├── hyperliquid_client.py   # Hyperliquid SDK wrapper
├── notifier.py             # Telegram alerts
├── backtest.py             # Event-driven backtester
├── dsr.py                  # Deflated Sharpe Ratio
├── oos_eval.py             # Out-of-sample evaluation
├── walk_forward.py         # Walk-forward validation
├── main.py                 # Research pipeline
├── sanity_check.py         # Local smoke test
├── test_live_dryrun.py     # Integration tests (7)
├── packages.py             # VPS dependency bootstrap
├── requirements.txt        # Pinned dependencies
├── .env.example            # Template for secrets
├── touch_stop.sh           # Convenience: create STOP file
├── remove_stop.sh          # Convenience: delete STOP file
├── state_BTC_USD.json      # Live position state (runtime)
└── model_store/            # Trained artefacts (gitignored)
    ├── BTC_USD_model.pt
    ├── BTC_USD_scaler.pkl
    ├── BTC_USD_meta.json
    ├── SOL_USD_model.pt
    ├── SOL_USD_scaler.pkl
    └── SOL_USD_meta.json
```

---

## Status

The codebase is complete and hardened for testnet deployment: the full pipeline from data ingestion through signal generation, guardrail enforcement, order execution, and alerting is implemented and covered by integration tests. All seven tests pass from the current repository location. What is **not** done: the system has not yet been deployed to a VPS, no live or testnet trades have been executed, and no real performance track record exists. This is a **personal learning project** built to understand the engineering of a production-grade algorithmic trading system — it is not an audited fund, not a signal service, and the backtest results (where they exist) should not be interpreted as a reliable forecast of future returns. The backtested Sharpe numbers produced by `oos_eval.py` are gross of Hyperliquid taker fees (0.035%) and funding rate P&L, which are not yet modeled in the backtester — realistic live Sharpe is expected to be materially lower once these costs are applied.

---

## License

Proprietary — personal project — do not distribute.
