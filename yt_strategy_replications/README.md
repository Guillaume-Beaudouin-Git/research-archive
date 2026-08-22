# YouTube Trading-Strategy Replications — Rigorous Out-of-Sample Validation

> A quant-research project that takes trading strategies pitched in YouTube videos and subjects them to an honest, institutional-grade test: realistic costs, no look-ahead, cross-instrument robustness, walk-forward, HAC significance, and multiple-testing penalties. The goal is not to debunk for sport — it is to separate **real structural edges** from **cost-free, cherry-picked back-tests**, using one shared, unit-tested engine.

**Headline finding:** across **13 strategies from 5 videos**, exactly **one** is a genuinely real *and* statistically significant edge (the variance risk premium — and it carries catastrophic tail risk). One more (post-earnings drift) is real but needs proprietary data. **Everything else fails net of costs, does not survive out-of-sample, or is materially oversold.**

---

## Scorecard

| Module | Strategy (video pitch) | Data tested | Verdict | Decisive number |
|---|---|---|---|---|
| **1** | S1 Momentum breakout + vol (*+196%*) | 18 crypto pairs, 5m, 2021–26 | ❌ FAIL | net Sharpe −6.2, 0/18 instruments + |
| **1** | S2 SMA 50/100 cross (*+103%*) | 〃 | ❌ FAIL | net Sharpe −10.9 |
| **1** | S3 EMA/SMA + z-score (*+103%*) | 〃 | ❌ FAIL | gross edge +0.7 bp/trade vs 17 bp cost |
| **1** | S4 Body-fraction breakout (*+1,156%*) | 〃 | ❌ FAIL | net Sharpe −7.0 |
| **1** | S5 VWMA buy-the-dip (***+5,381%***) | 〃 | ❌ FAIL | break-even cost 0.8 bp vs ≥17 bp real |
| **2** | Pin-bar + EMA-50/200 trend filter | gold H1 + 7 instruments, 19y | ❌ FAIL | gross HAC t +0.5; dead > 2 bp; 0/8 markets |
| **3** | Reinforcement-learning agent (*+60% OOS*) | gold H1, 19y | ⚠️ UNPROVEN | a ≈0-edge agent passes the 5-fold gate |
| **4** | Pairs trade BRK-B / MSFT | US equities, daily, 2011–26 | ❌ FAIL | all variants net-negative; in-sample selection |
| **5** | Opening-Range Breakout (*13.5% skew*) | NQ 1-min, 2010–26 | ❌ FAIL (net) | real +5% long skew (not 13.5%), Sharpe −0.57 |
| **5** | **Variance Risk Premium** | VIX/SPY, 2004–26 | ✅ **REAL** ⚠️ | Sharpe 0.52 — but skew −4.9, kurtosis 45 |
| **5** | Bitcoin smart-DCA (MVRV) | BTC daily, 2014–26 | ⚠️ MODEST | +17% capital-eff, **no** drawdown cut |
| **5** | Post-Earnings Drift (PEAD) | data-gated | ✅ real / decaying | needs earnings-surprise (SUE) data |
| **5** | Congressional copy-trading | data-gated | ❓ dubious | 45-day lag + ex-post selection |

Full write-ups: [`reports/`](reports/) — one institutional report per module.

---

## Why most of them fail (the recurring patterns)

1. **Zero/again-zero costs.** TradingView-style back-tests default to no commission. A 1–2% scalper trades thousands of times; at realistic costs the edge is gone (Module 1: break-even costs of ~0.8 bp vs 17 bp reality).
2. **Single cherry-picked instrument** out of a large search (the Module 1 video states **50,000** back-tests). The same rule on a fixed cross-section of 18 instruments is net-negative on **all** of them.
3. **In-sample selection / look-ahead.** Choosing a pair by full-sample cointegration then trading that sample (Module 4): the pair "passes" on 2011–26 but is cointegrated in only **1 of 16** individual years.
4. **Spurious price-level correlation** instead of return correlation (Module 4: 0.97 → really 0.49).
5. **Weak validation gates.** A 5-fold "consistency gate" (Module 3) has a ~50% false-positive rate under the null — demonstrated by a near-zero-edge agent passing it.
6. **Real edge, wrong magnitude / hidden tail.** ORB's upside skew is real but ~2.6× overstated; VRP is real but its Sharpe hides skew −4.9 / kurtosis 45.

---

## Methodology (shared, in `engine/`)

- **Execution discipline (no look-ahead).** Signal computed at the close of bar *t*; position entered at the **open of bar t+1**. Intrabar SL/TP against each bar's high/low; same-bar ambiguity resolves **stop-first** (pessimistic). Enforced centrally and **unit-tested** (`tests/test_engine.py`, 5/5 pass, incl. loop-vs-vectorised trade-for-trade equivalence).
- **Costs.** Crypto 0.17% round-trip; gold ~3 bp (+ sensitivity 0–10 bp); equities 5 bp/leg; NQ ~1.5 pts. Every result reported **gross and net** to separate "no edge" from "killed by cost."
- **Significance.** Annualised Sharpe on a regularly-sampled daily return series (√ of actual trading days, not blind √252); HAC / Newey–West t-stats (lag 6); stationary block bootstrap; **Deflated Sharpe Ratio** (Bailey–López de Prado) to penalise the search.
- **Robustness.** Cross-instrument sweeps (a real edge generalises); ≥5-fold walk-forward; cost-sensitivity curves.
- **Gates.** RESEARCH_PASS = Sharpe > 0.7, MaxDD > −25%, WF > 50%. **0 of the tested strategies pass.**

---

## Repository layout

```
yt_strategy_replications/
├── engine/                      # shared, unit-tested core
│   ├── backtest.py              #   event-driven SL/TP engine (loop + vectorised, proven equal)
│   ├── stats.py                 #   Sharpe, MaxDD, HAC t, DSR, stationary bootstrap, walk-forward
│   ├── indicators.py            #   vectorised SMA/EMA/ATR/RSI/VWMA/z-score/candle anatomy
│   ├── data.py                  #   Binance 5m + repo gold/FX/index H1 loaders
│   └── plotting.py              #   figures (kept out of core logic)
├── module_1_crypto_scalping/    # 5 "scalping" strategies → all fail
├── module_2_pinbar_gold/        # pin-bar + EMA trend filter → fails, doesn't generalise
├── module_3_rl_gold/            # RL pipeline (env, reward, walk-forward, gate) + PPO adapter + demo
├── module_4_pairs_trading/      # cointegration / z-score pairs → fails OOS
├── module_5_structural_edges/   # ORB, VRP, MVRV tested; PEAD/Congress assessed
├── reports/                     # 5 institutional markdown reports
├── tests/test_engine.py         # engine integrity (no look-ahead, equivalence, costs)
└── data_cache/                  # gitignored (Binance 5m, gold/FX H1, equities, macro)
```

## Reproduce

```bash
# crypto data (≈1,170 monthly zips from data.binance.vision)
bash download_crypto.sh                 # resumable; then build parquet via engine.data
python tests/test_engine.py             # 5/5 engine integrity checks

python module_1_crypto_scalping/run.py ALL && python module_1_crypto_scalping/aggregate.py
python module_2_pinbar_gold/run.py
python module_3_rl_gold/run_demo.py train 0 1 2 3 4 && python module_3_rl_gold/run_demo.py aggregate
python module_4_pairs_trading/run.py
python module_5_structural_edges/run_edges.py all
```

Gold/FX/index history comes from the repo's canonical true-UTC M1 store; crypto from Binance; equities/macro (VIX, SPY, BTC, BRK-B, MSFT) from yfinance. Full-scale RL (PPO) runs via `module_3_rl_gold/ppo_adapter.py` on a machine with `torch` + `stable-baselines3`.

## Honest caveats

- Module 1 is tested on crypto (the only free long 5-minute history); the video's exact equity tickers would have lower trade frequency but a sub-1-bp gross edge cannot survive any realistic cost.
- Module 3's in-sandbox agent is a linear policy (reduced capacity vs the video's deep PPO); it audits the *methodology* (which is sound) and shows the consistency gate is statistically weak — a full PPO run on the user's hardware is the way to a definitive answer.
- Module 5's MVRV uses a price-z proxy (true MVRV needs paid on-chain data); PEAD and Congressional are assessed, not back-tested, because they require earnings-surprise and disclosure datasets respectively.

---

*Built as a systematic research exercise: one engine, explicit assumptions, gross-vs-net everywhere, and a verdict that follows the data rather than the thumbnail.*
