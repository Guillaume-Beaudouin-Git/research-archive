# Research protocol — stat-arb on FTMO (institutional-grade charter)
*Pre-registered before any data work. Every idea is held against this. Honesty > optimism. Reconciliation > regeneration.*

## How to use this doc
This is a **pre-registration**: we freeze the rules of evidence *before* seeing results, so we can't later rationalize a curve-fit into a "discovery". If a result requires breaking a rule here to look good, the result is wrong, not the rule.

---

## PART A — The big mistakes, why they kill, and how we avoid each

Ordered by how lethal they are for *this specific project* (single-leg stat-arb under a prop-firm barrier).

### 1. Cost mis-specification — THE #1 killer (the L33 lesson)
- **Why it kills:** stat-arb is high-turnover with a thin per-trade edge. A reversion signal that is +0.02R at 2 bps flips to **−0.07R at 6 bps**. On a symmetric barrier a negative-drift never converges — it drifts to bust. Backtests at idealized cost are *fiction*.
- **Avoid:** model **measured, instrument-specific round-trip cost from day one** = floating spread + slippage + overnight swap (CFDs have 0 commission on indices but real spread+swap). Always run a **cost-sensitivity sweep** and require the edge to survive at the *upper* cost estimate. The single open measurement (log the live spread on demo) is mandatory before any deploy claim.

### 2. Look-ahead baked into the spread itself (the stat-arb-specific trap)
- **Why it kills:** the classic error is estimating the hedge ratio / mean / z-score normalization on the **full sample**, then "backtesting" on it. The spread definition leaks the future; the reversion looks perfect and is untradeable.
- **Avoid:** all spread parameters (hedge ratio β, mean, σ) must be computed from **data ≤ t−1** only — rolling OLS or a **Kalman filter** for a time-varying β. The z-score at t uses trailing stats. Prove it: the signal series must be reconstructable in a strict streaming pass.

### 3. Negative-skew blow-up vs the 5% daily / 10% static barrier
- **Why it kills:** reversion = many small wins + a rare large loss when the spread *keeps diverging*. That tail is exactly what breaches the daily cap and busts. Optimizing Sharpe/mean hides it.
- **Avoid:** evaluate on the **barrier (first-passage), not Sharpe**. Hard **spread stop + time stop** (exit if z>3 or past N×half-life). **Vol-target** so a single non-convergence ≤ 5% in a day. Stress against the **worst historical divergence**, including a synthetic shock worse than anything in-sample.

### 4. FTMO compliance blindness (the hedging rule)
- **Why it kills:** FTMO forbids "hedging or holding opposing positions on the same or highly correlated instruments." A textbook market-neutral two-leg pair can be flagged/banned → strategy void regardless of edge. HFT/tick-scalping turnover is also prohibited.
- **Avoid:** **single-leg expression only** (trade a cross/symbol that *is* the spread; or use the z-score as signal and trade one leg; or single-instrument OU). Keep holding times above tick-scalp thresholds. Re-read the forbidden-practices page and confirm the exact holding pattern per idea.

### 5. In-sample pair/parameter selection & multiple testing (data snooping)
- **Why it kills:** pick the best-cointegrating pair over all history, tune lookback/z-thresholds/half-life to the best backtest → you've fit noise. The reported Sharpe is inflated by the number of things you tried.
- **Avoid:** **pre-specify the economic rationale before testing**; select pairs/params on a **training window only**; correct for trials with the **Deflated Sharpe Ratio (Bailey & López de Prado)** using an honest trial count; keep the parameter count tiny (≤2–3); pre-register the grid.

### 6. Spurious / unstable cointegration (it breaks when you need it)
- **Why it kills:** cointegration is not a law; relationships break — often precisely in the stress that also blows the spread. A pair that cointegrated 2015–2020 can decouple in 2022.
- **Avoid:** test stability with **rolling cointegration / structural-break tests**, Johansen on subsamples; require a **stable half-life**; build an explicit **"relationship broke" kill rule** (β drift, ADF p-value degradation) into the strategy, not just the research.

### 7. IID bootstrap / destroying autocorrelation (we made this error before)
- **Why it kills:** IID resampling of returns destroys the **clustering of divergences and regimes**, giving wrong (often optimistic) tail and pass-rate estimates for a path-dependent barrier strategy.
- **Avoid:** simulate on **contiguous real paths**; for confidence intervals use a **block / stationary bootstrap** that preserves runs. Never IID for a barrier/first-passage question.

### 8. Favorable-window cherry-picking / regime overfit
- **Why it kills:** reporting the good-regime number (the "2022–2025 = 50.9%" / "2026 = 93%" trap from prior work) overstates everything.
- **Avoid:** evaluate on the **full sample across all regimes**; always report a **by-year / by-regime breakdown**; hold out a genuine **out-of-sample** window touched only once, at the end.

### 9. Microstructure / bid-ask-bounce inflation
- **Why it kills:** close-to-close reversion backtests implicitly "buy at bid, sell at ask", inflating the edge; live you pay the spread.
- **Avoid:** use **mid/trade prices**, realistic fills (next-bar or resting-stop-at-level), and the **delay-sensitivity test** — a real edge survives a 1-bar entry delay; a microstructure artifact collapses. (This is our standard artifact filter.)

### 10. Barrier-mechanics & data errors
- **Why it kills:** mis-modeling the FTMO daily-loss (from start-of-day balance, server time, **unrealized** intraday loss counts) or the static $9k floor; or using non-point-in-time / unadjusted / survivorship-biased data (esp. the 23-name stock list).
- **Avoid:** encode the **exact FTMO rules** (intraday mark-to-market, static floor, min days, no time limit); use **point-in-time, split/dividend-adjusted** data; verify timezone (US cash open = 16:30 EET on the broker feed).

---

## PART B — Institutional workflow (the sequence we follow)

1. **Pre-register** (this doc + per-idea one-pager): economic hypothesis, exact spec, evaluation window, cost model, success criteria — *before* results.
2. **Data hygiene:** point-in-time, adjusted, timezone-correct, measured costs, gap/outlier audit.
3. **Split discipline:** train (research) → validate (lock spec) → **test once** (OOS, never re-touched). Or expanding-window walk-forward for parameter-light models.
4. **Causal signal build:** rolling/Kalman params, strict streaming reconstruction, delay-test.
5. **Realistic execution & cost:** measured spread + swap + slippage; honest fills.
6. **Barrier evaluation:** first-passage Monte-Carlo on **contiguous real paths**; block-bootstrap CIs; report p(funded), bust, time-to-pass, **by-regime**.
7. **Robustness battery:** parameter sensitivity, cost sensitivity, regime breakdown, **Deflated Sharpe**, escape-N.
8. **Compliance gate:** single-leg, forbidden-practices, turnover within limits.
9. **Forward/demo validation:** measure real cost, compare realized edge vs backtest over ≥50 trades; pre-set **kill criteria**.
10. **Reproducibility:** one canonical trade ledger, **frozen spec**, one config, versioned script; reconciliation-over-regeneration if numbers ever disagree.

---

## PART C — Stat-arb gold-standard toolkit (what "good" looks like)

- **Dynamic hedge ratio / fair value:** Kalman filter (time-varying β) over static OLS — relationships drift.
- **Mean-reversion modeling:** Ornstein-Uhlenbeck → estimate **half-life**; set entry/exit bands and the time-stop from it.
- **Mean-reversion confirmation:** **Hurst exponent (H<0.5)** and **variance ratio (<1)** to confirm the series reverts rather than random-walks — *before* trading it.
- **Stationarity tests:** ADF / KPSS on the residual (use as evidence, not gospel; combine with stability tests).
- **Cointegration (if ever >2 legs):** Johansen > Engle-Granger; but our single-leg compliance means the multi-leg relationship is the *signal*, executed one-legged.
- **Significance:** Deflated Sharpe Ratio, HAC (Newey-West) t-stats for autocorrelated returns, minimum-track-record length.
- **Sizing:** first-passage-aware, vol-targeted, leverage-cap-aware; size is the primary barrier lever under no time limit (smaller → higher p(pass), slower).

---

## PART D — Per-idea acceptance checklist (must pass ALL before "promote to deploy")

- [ ] Economic rationale stated **before** backtest
- [ ] Single-leg / FTMO-compliant expression confirmed
- [ ] Signal reconstructable in a strict no-look-ahead streaming pass
- [ ] Edge survives **measured** cost (+ survives the *upper* cost estimate)
- [ ] Edge survives a 1-bar entry delay (not a microstructure artifact)
- [ ] Positive in OOS / held-out window, and **across regimes** (by-year shown)
- [ ] First-passage p(funded)/bust on contiguous real paths, with block-bootstrap CI
- [ ] Hard spread + time stop; vol-target keeps worst day ≤ 5%
- [ ] Deflated Sharpe accounts for the trial count
- [ ] Reproducible from one frozen spec + one ledger

*If an idea fails a box, that's information — we record it and move on, exactly as a negative result should be banked. We are not trying to make any single idea pass; we are trying to find whether one honestly does.*

---

## PART E — Banked data-source lessons (FX)
- **yfinance daily FX is corrupted for daily-RETURN analysis** — BOTH the ratio of two USD pairs (e.g. EURUSD/GBPUSD) AND the direct `=X` ticker (e.g. EURGBP=X) have daily-return correlation ≈ 0 with the real tradeable cross (level corr ~0.96, return corr ~0). Backtesting reversion on it trades phantom noise (this is the historical "+9.4R EURGBP" artifact class). **Never use yfinance daily FX for return-level strategy research.**
- **Clean FX daily sources:** (1) **ECB euro reference rates** (official daily fixing ~16:00 CET, 1999+, all majors incl. GBP) — return-corr 0.99 vs real M1 when sampled at the same time; (2) **real broker M1** (e.g. the MT5 uploads) resampled. Validate any new FX source with the **return-corr-vs-real anti-artifact check at a matched time-of-day** before trusting it.
- **Anti-artifact check is mandatory and it works:** it caught both a false positive (synthetic EURGBP "18/18, t=3.9") and a false negative (AUDNZD "kill") in this project — both were data artifacts, not real results.
