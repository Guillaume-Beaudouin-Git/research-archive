# Ideas 3A (Gold/Silver) & 4A (ETH/BTC) — ratio-as-signal, single-leg directional — PRE-REGISTRATION
*Frozen 2026-06-03 BEFORE results.*

## Hypothesis
A relative-value **ratio mean-reverts**; trade the **dislocated single leg directionally** toward convergence (compliant — one position, no opposing legs).
- **3A:** GLD/SLV (gold/silver) ratio reverts (monetary vs industrial demand). High ratio → silver cheap → **long SLV**; low → **long GLD**. (Rotate into the cheap metal.)
- **4A:** ETH/BTC ratio reverts. High → ETH rich → **short ETH**; low → ETH cheap → **long ETH**. (Single instrument ETH, directional.)

## Honest framing (stated up front)
These are **beta + an RV-timing overlay, NOT market-neutral stat-arb.** The traded P&L is the real single leg's return. **The decisive question: does the ratio-timing add alpha OVER simply buy-and-holding the traded leg, net of cost?** If not, it's just delivering the leg's beta (the expected outcome per the 4/4 prior kills).

## Data (single-leg traded return is REAL/clean → robust to the ratio artifact)
- 3A: **GLD** (macro_etf_panel) + **SLV** (commodity_panel), adjusted ETF daily.
- 4A: **ETHUSD** + **BTC-USD** (crypto panels, 2014-09 → 2026-05, daily, 24/7 consistent close).
- Ratio used only as signal; trade GLD/SLV/ETH (real adjusted series).

## Signal (causal)
- log-ratio; adaptive fair value = rolling mean over **W** (≤ t); z = (logratio − f)/rolling-std.
- Enter the cheap/dislocated leg when **|z| ≥ Z_in**; fill t+1; exit when z reverts through 0, or **|z| ≥ Z_stop** (stop), or **T_max** days. One position at a time.

## Tests
- Strategy Sharpe / t; **vs buy-&-hold the traded leg(s)** (the alpha test); cost sweep (3A metals ~3–8 bps; 4A crypto ~10–30 bps + funding); **1-bar delay**; by-year (incl. 2020/2022); **FTMO 2-step first-passage** (daily-MTM, leverage sweep); **DSR** on grid.

## Grid
W ∈ {60, 120}, Z_in ∈ {1.5, 2.0}, Z_stop = 3, T_max = 60. Baseline (W=120, Z_in=2).

## Acceptance (charter Part D)
single-leg compliant · causal · ratio reversion confirmed · **adds alpha over buy-&-hold the leg, net of measured cost** · survives delay · positive across regimes · first-passage p(funded)/bust · DSR-significant.

---
*(Results appended below.)*

---

# RESULTS & VERDICT (2026-06-03)

## 4A — ETH/BTC: ❌ KILL.
RV-timing of ETH direction **underperforms passive ETH**: strategy Sharpe **0.35** vs buy-&-hold ETH **0.57**; t=**0.72** (insignificant); maxDD −80%; cost sweep t 0.72→0.32. **FTMO first-passage p(funded) 16–23%, bust 75–84%.** The overlay destroys value; pure beta would be better, and even that fails the barrier. Kill.

## 3A — Gold/Silver: ❌ KILL for FTMO (but a real edge in the wrong container).
- **The one genuine result of the whole stat-arb effort:** rotating long into the cheap metal (GLD↔SLV) timed by the ratio z-score beats buy-&-hold gold — strategy **Sharpe 0.77 vs GLD 0.59**, t=**2.16**, +22%/yr, **survives 8 bps cost (t 1.83) and the 1-bar delay (t+2 1.65)**. A real, cost-robust, delay-robust risk-adjusted edge over its benchmark.
- **But it fails FTMO on the barrier:** maxDD **−50%** (high-vol long-metal beta). Silver's daily volatility breaches the 5% daily / −10% static floor before +10% is reached → **FTMO p(funded) 24–27%, bust 73%** at L=3/5/8 (no sizing rescues it — bust stays ~73% even at L=3).
- **Interpretation:** "real strategy, wrong account." It would be a legitimate medium-Sharpe swing strategy in a *normal* account (no −10% floor), but the FTMO barrier is fundamentally incompatible with the volatility needed to harvest the gold/silver RV.

**Checklist (both):** ✅ compliant · ✅ causal · 3A: ✅ edge over benchmark / 4A: ❌ no edge · ❌ **both fail the FTMO first-passage barrier** (p(funded) ≤27%, bust ≥73%). KILL for FTMO.

