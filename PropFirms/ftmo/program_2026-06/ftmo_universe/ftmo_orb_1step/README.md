<!-- ============================================================= -->
<!-- ⚠️ SUPERSEDED BY ../FTMO_CANONICAL_STATE.md (single source of truth, 2026-06-03) -->
<!-- Verdict: FTMO = CONFIRMED-CLOSED. This repo's p(pass) used ~1 bp round-trip cost (optimistic). -->
<!-- Per canonical L33, the REAL cost (3 bps futures-direct / 6-10 bps FTMO CFD: commission 0 + floating -->
<!-- spread) flips mean_R NEGATIVE -> the barrier exploit drifts to bust. The regime figures (44%/64%) are -->
<!-- cherry-picks to reject; full-history p(pass) ~30% aligns with the canonical ~33% (itself at idealized -->
<!-- 2 bps). Spec here = long-only-filtered ("doc3"); canonical reference = ORB V2+E7 two-sided. Treat as -->
<!-- NO-GO pending the single open item: measure US100.cash spread (canonical §5). -->
<!-- ============================================================= -->

> ⚠️ **Superseded by `../FTMO_CANONICAL_STATE.md`.** Verdict: **FTMO = CONFIRMED-CLOSED.** The pass
> probabilities below use ~1 bp cost (optimistic); at the **real cost (3–10 bps)** the per-trade edge is
> **negative** (canonical §4/L33) and the strategy drifts to bust. Regime figures (44%) are cherry-picks to
> reject. Read the canonical first.

# FTMO ORB — passing a prop-firm challenge with optimal bet-sizing

A systematic study of whether a retail-tradeable intraday strategy can pass an **FTMO-style
prop-firm challenge** ($10k account, +10% target, 5% max daily loss, 10% max total loss) on a
**single attempt**, and at what probability — solved end-to-end with realistic costs, multi-regime
data, a Monte-Carlo challenge simulator, and **stochastic dynamic programming for the bet-sizing**.

> **Headline result (single attempt, real FTMO rules):**
> A long-only, gap- and trend-filtered **Opening-Range Breakout on the Nasdaq-100** **does not pass
> >50% in <2 months on a single attempt.** The best vehicle is the **2-step challenge** (5% daily,
> 10% static): **p ≈ 30%** on 16y out-of-sample (robust), **≈ 44%** in the recent regime (≈52% if you
> allow 3 months). The **1-step challenge is *harder*** (3% daily, 10% *trailing* floor, plus a
> *Best-Day 50% consistency rule* that penalises this strategy's positive skew): only **≈23–29%**.
> The binding constraints are the daily-loss cap and the barrier structure; sizing is optimised (DP),
> so lifting this needs a higher-Sharpe signal — none exists in this liquid-retail-intraday universe.

This repo is as much about **what doesn't work** (rigorously shown) as what does — the discipline is the deliverable.

---

## Why this is non-trivial

A symmetric profit/loss barrier with no per-trade alpha gives ≈50% pass by gambler's-ruin math; costs
push it below. Passing **>50%** requires either a real edge or exploiting the **rule structure**
(static drawdown floor, uncapped daily upside vs capped daily loss) via **sizing**. This project
quantifies both, honestly.

## Key ideas

- **Realistic execution.** Next-bar-open fills (not fills at the breakout level), per-instrument
  spread from tick data + commissions + slippage, broker-EET session clock verified empirically.
- **Multi-regime truth.** The Nasdaq edge is validated on **16 years of NQ futures (2010–2026)**, a
  clean proxy for the US100 CFD — it is *positive only 2021–2024 and ~zero full-history with realistic
  fills*, i.e. the recent strength is a regime + favorable-fill artifact, not robust alpha.
- **FTMO challenge Monte-Carlo** (`ftmo_sim.py`): 1-step & 2-step, daily/total drawdown rules, personal
  daily stop, **stationary block bootstrap** to preserve volatility clustering (an IID bootstrap
  flatters the pass rate — we show the difference).
- **Optimal bet-sizing via dynamic programming** (`dp_sizing.py`): state = (equity, days left, phase),
  action = risk fraction ρ ≤ 4.5%. Backward induction yields the policy ρ\*(equity, days left) that
  *maximises* p(pass) — then we **validate that policy in the clustering-aware bootstrap** (the honest
  number, lower than the IID DP optimum).
- **Live signal generator** (`live_signals.py`): each day outputs the OR levels, trend-filter check,
  entry/stop, and the DP-optimal position size for the current account state.

## Results (single attempt, real FTMO rules, block-bootstrap, realistic fills)

2-step = 5% daily / 10% static. 1-step = 3% daily / 10% trailing-EOD / Best-Day 50% rule.

| Strategy | 2-step <2mo | 2-step <3mo | 1-step <2mo | 1-step <3mo |
|---|---:|---:|---:|---:|
| **Nasdaq, full 16y (robust)** | **30%** (bust 42%) | 39% | 23% (bust 28%) | 33% |
| **US100+GER40 book (2022+ regime)** | **44%** (bust 49%) | **52%** | 29% (bust 23%) | 41% |

Nothing clears 50% in <2 months. The **2-step is the better single-attempt path** (the 1-step's
tighter daily cap + trailing floor + Best-Day rule make it harder, and the Best-Day rule specifically
penalises this strategy's +1.2–2.0 skew, costing ~13pp).

See `results/figs/`: `fig1_regime.png` (edge is regime-bound), `figW1_pass.png` (pass curves),
`figDP_policy.png` (the optimal sizing surface).

## What was tested and rejected (the rigour)

| Lever | Result |
|---|---|
| Mean-reversion (VWAP/z), intraday momentum | −EV / Sharpe<0.4 after costs |
| Multi-sleeve diversification, equal-risk | dilutes Sharpe (1.03 < US100 1.16); only **GER40** is a +EV decorrelated partner |
| Walk-forward ML entry filter | Sharpe 0.68 — and only after catching a look-ahead leak that faked Sharpe 11 |
| HMM regime + macro/VIX score (causal) | regime edge is real but gating **slows** the grind → worse for a *timed* challenge |
| Event/news conditioning | ORB does *worse* on high-impact days (whipsaw) |
| Cross-sectional intraday (US index family) | Sharpe +0.03 (~0) after costs |
| Crypto (BTC) long-ORB sleeve | −EV (Sharpe −0.66), dilutes the book |
| **DP-optimal sizing** | **the one real gain** — more pass, less bust; and it *proves* the 2-step ceiling |

**Unifying finding:** the liquid retail-intraday space is efficient; the only usable edge is the
**intraday long-equity drift** (ORB up-days), and the binding constraint is the **5% daily-loss cap**
(forces max sizing) **+ the 2-step's double barrier**.

## Repo structure
```
src/
  data.py          # clean M1 CSV -> parquet cache (sessions, gap-masking)
  strategy.py      # ORB engine: long-only gap/trend filter, conservative intrabar fills, costs
  ftmo_sim.py      # FTMO 1-step/2-step Monte-Carlo (block bootstrap, DD rules, sizing)
  dp_sizing.py     # optimal sizing via dynamic programming + honest bootstrap validation
  live_signals.py  # daily live signal + DP-optimal position size
tests/             # no-look-ahead, cost monotonicity, simulator & DP invariants
scripts/run_backtest.py   # reproduce the headline numbers
results/           # strategy spec + figures
```

## Quickstart
```bash
pip install -r requirements.txt
export FTMO_CACHE=./cache                 # where parquet caches live
python src/data.py US100 GER40            # build caches from source M1 CSVs (set FTMO_DATA)
python scripts/run_backtest.py            # headline numbers
python src/live_signals.py --equity 10250 --days_left 28   # today's signal
pytest -q                                 # tests
```
Data paths are configured via env vars `FTMO_CACHE` (parquet cache) and `FTMO_DATA` (source CSV dir).

## Honest limitations
- **No single-attempt config passes >50% in <2 months** under real rules. Best is the 2-step book at
  44% (recent regime) / 30% (full-history, the robust claim); ~52% only if you allow 3 months.
- **The 1-step is harder, not easier** — 3% daily, trailing floor, and a Best-Day consistency rule that
  penalises this strategy's positive skew. A *smooth, high-hit-rate* +EV strategy would suit it better,
  but the smooth strategies in this universe (mean-reversion) are −EV after costs.
- **Long-biased beta**, not market-neutral alpha; regime-dependent. Costs/fills are realistic but a live
  account adds platform slippage; size on a small account.
- An earlier version of this repo mis-modelled the 1-step with the 2-step's rules — corrected here.

*Built as a quantitative-finance portfolio project: systematic research, backtesting rigor, risk
management, and intellectual honesty (a well-proven "no" is a result).*
