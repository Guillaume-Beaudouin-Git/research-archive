# Idea 1A — AUD/NZD mean-reversion (single-leg) — PRE-REGISTRATION
*Frozen 2026-06-03 BEFORE any backtest result, per `RESEARCH_PROTOCOL_statarb.md`. Results appended only after this spec is locked. If a result needs this spec changed to look good, the result is wrong.*

## Hypothesis (economic, stated before testing)
AUD and NZD are tightly linked (Antipodean commodity exporters; RBA↔RBNZ policy co-movement; shared China/dairy/metals terms-of-trade). Their cross **AUDNZD** is historically band-/range-reverting around a slowly-drifting fair value (set by the rate differential). **Fast deviations from that adaptive fair value revert.** This is tradeable on FTMO as a **single compliant symbol** (the cross is itself the spread → no two-leg hedging-rule violation).

## Compliance (FTMO)
Single instrument (AUDNZD). No opposing/correlated-leg positions → not "hedging". Holding horizon is days (not tick-scalping). ✅ compliant by construction.

## Data
- **Signal/backtest:** synthetic daily AUDNZD = AUDUSD_close / NZDUSD_close, yfinance daily **2015-01 → 2026-05** (~11y, covers 2015 CNY-deval, 2018 vol, 2020 COVID, 2022 bear, 2023-25). USD cancels (same-day same-source close) → clean cross.
- **Cross-check:** validate the synthetic against the same-source MT5 M1 (2021-12→2025-06) daily AUDNZD in the overlap.
- **Cost grounding:** MT5 `spread` column → AUDUSD ~0.4 pip / NZDUSD ~0.6 pip (liquid hours). AUDNZD cross modeled at **2 pips RT ≈ 1.85 bps** baseline.

## Mean-reversion CONFIRMATION gate (run BEFORE trading — charter Part C)
Trade only if the cross is statistically reverting, not random-walking:
- **Hurst exponent H < 0.5**, **variance ratio < 1**, **ADF** rejects unit root on the deviation, finite **OU half-life**. If these fail → KILL (no edge to trade), recorded as a clean negative.

## Signal (frozen, strictly causal)
On daily closes, all stats from data **≤ t** (decision at close t, fill next day open):
- Adaptive fair value `f_t` = rolling mean of `log(AUDNZD)` over window **W** (baseline 60d) [also Kalman local-level as a robustness variant].
- Trailing dispersion `σ_t` = rolling std of `(log_px − f)` over W.
- `z_t = (log_px_t − f_t) / σ_t`.
- **Entry:** long if `z_t ≤ −Z_in`; short if `z_t ≥ +Z_in`  (Z_in baseline **2.0**) — single-leg directional on the cross.
- **Exit:** `z` reverts through **0** (target), OR hard **stop** `|z| ≥ Z_stop` (baseline **3.0**), OR **time stop** `T_max` (baseline 20 trading days ≈ k×half-life).
- **Sizing:** vol-target — per-trade risk set so a stop-out (z 2→3) and a plausible adverse daily move stay **≤ 5% daily / well within the 10% floor**; fixed fractional risk per trade, swept.

## Cost model (the make-or-break test)
- Baseline RT cost **2 pips (~1.85 bps)** on the cross; **sweep 1 / 2 / 3 / 4 / 6 pips**.
- Swap ~0.2–0.4 bps/day × holding days (rate differential; small, AUD/NZD close).
- **Require the edge to survive the UPPER cost estimate.** Real AUDNZD spread to be measured on FTMO demo (open item).

## Evaluation
- Full sample 2015–2026 + **by-year regime** breakdown.
- **Train 2015–2020 / OOS 2021–2026** (or expanding walk-forward, since param-light).
- **1-bar entry-delay test** (real edge survives; microstructure artifact collapses).
- **FTMO 2-step first-passage** on contiguous real paths (p(funded), bust, time-to-pass), **block-bootstrap CI**.
- **Deflated Sharpe** with honest trial count.

## Pre-registered parameter grid (the ONLY grid; DSR-corrected)
W ∈ {40, 60, 90}, Z_in ∈ {1.5, 2.0, 2.5}, Z_stop ∈ {3, 4}. Baseline = (60, 2.0, 3). Total ≤ 18 trials → feed the DSR trial count. No other tuning.

## Acceptance criteria (charter Part D — must pass ALL to promote)
Mean-reversion confirmed (H<0.5) · single-leg compliant · no-look-ahead streaming · survives measured cost AND upper cost · survives 1-bar delay · positive OOS AND across regimes · first-passage p(funded)/bust on contiguous paths with CI · stops keep worst day ≤5% · DSR>~1 after trial count · reproducible from this frozen spec.

---
*(Results section appended below after the engine runs — never above this line.)*

---

# RESULTS & VERDICT (2026-06-03)

## ⚠ CORRECTION (2026-06-03, later same day): the KILL below is RETRACTED — it ran on corrupted data.
The verdict below used a **synthetic daily AUDNZD = yfinance EURUSD/GBPUSD-style ratio (AUDUSD/NZDUSD)**. The anti-artifact check (run for 1B) revealed that **yfinance daily USD-pair closes are not time-aligned**, so the ratio's *daily returns* are largely phantom (return-corr with the real cross ≈ 0). Re-running on **real, direct-cross M1 data (2021-12→2025-06)** gives the opposite: AUDNZD is **18/18 grid configs positive** (Hurst 0.468; best t≈2.21 but at tiny n=8). So AUD/NZD reversion is **weakly POSITIVE on clean data**, not a kill — but small-N (3.5y) and underpowered. **Status: inconclusive/weak-positive, superseded by 1B (EURGBP) which is the stronger clean signal.** The synthetic-data result below is kept only as a record of the artifact.

---

## (RETRACTED — corrupted synthetic data) VERDICT: ❌ KILL — no robust, significant, FTMO-compliant edge.

The single-symbol (compliant) AUD/NZD level mean-reversion does not work over 2015–2026. Recorded as a clean negative, per the charter.

### What the engine found
- **Mean-reversion gate: barely passes → red flag.** Hurst(logpx) **0.481**, VR(5) 0.978, VR(10) 0.967, OU half-life 24 d. The cross is statistically *almost a random walk* — it reverts far too weakly to trade.
- **Baseline (W60, Z_in2, Z_stop3, fill t+1):** raw cost-aware return **−2.6%** total, **−3.2 bps/trade**, **t −0.26**, win 35%, **OOS −9.8%**. Exit mix 41 stops / 21 time / 17 targets → it fades moves that keep trending.
- **Pre-registered grid (18 trials, W×Z_in×Z_stop):** only **10/18** positive total return; best **t-stat +1.49** (W90/2/3, +10.3% over 11y ≈ 0.9%/yr). With 18 trials the expected max |t| under the null ≈ 2.0–2.2 → **best result is NOT significant; Deflated Sharpe < 0.** (Two "positive" configs were R-normalization artifacts — division by a near-zero stop distance — confirmed via the raw-return recheck; verdict rests on raw returns, not R.)
- **Underperforms passive:** best config ≈ 0.9%/yr vs **buy-&-hold AUDNZD +16.3%**.

### Why it fails (diagnosis)
The FTMO hedging rule forces the **compliant** expression to be the **β=1 cross level** (single AUDNZD symbol). But the cross level is **not stationary** — AUD/NZD trends for months on RBA↔RBNZ rate differentials (2018, 2021–22, 2025–26). Fading an adaptive band in a trending series = negative-skew "fade-and-get-run-over." The *stationary* object would be the **cointegration residual with an estimated hedge ratio β≠1** — but trading that needs **two legs (long AUDUSD / short β·NZDUSD) = the prohibited hedging pattern.** So the version that might revert is non-compliant, and the compliant version barely reverts. **That tension is the core result.**

### Acceptance checklist (charter Part D)
✅ single-leg compliant · ✅ no-look-ahead (t+1 fill) · ✅ mean-reversion *measured* (and found too weak) · ❌ **edge not positive/ significant** · ❌ **fails OOS** · ❌ **DSR insignificant on 18 trials** · ❌ underperforms buy-&-hold · *(barrier first-passage not run — moot for a non-positive-EV signal; a negative drift busts the floor ~surely).*

### Implication for the broader plan
This likely **generalizes to 1B (EUR-bloc cross)** and any "trade-the-cross-level" idea: the hedging rule strips the cointegration edge (the β) and leaves a weak, trend-prone single-symbol signal. The compliant stat-arb forms with more hope are **(i) RV-ratio-as-signal traded single-leg directionally** (2A/3A/4A — but that's beta, not neutral) or **(ii) single-instrument intraday OU** (2B/4B — but cost/L33-exposed). Decision deferred to the user (per process).

