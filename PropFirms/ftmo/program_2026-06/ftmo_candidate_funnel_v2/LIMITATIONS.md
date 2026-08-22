# v2 Limitations & what is NOT testable

Output (4). Reported honestly. **[material]** = would change the verdict if wrong.

## 1. Intraday data & session windows
- 15/30min bars resampled from true-UTC M1 (US500 2012+, US100/US30/GER40 2013+). Tradable window is a **fixed UTC session** (US 14:00–21:00, GER40 07:00–16:00) — the DST shift (±1h) is unmodelled, so a few bars near the open/close are mis-included seasonally. Immaterial to the verdict: the gross IS Sharpe is negative across *all* indices and *both* frequencies, so no plausible window tweak flips a −0.07…−0.70 gross into a >2.13 net.
- **[material-adjacent]** Intraday execution is modelled at **bar close** with bar-median spread × 3 markup + ≥1-tick slippage + commission. Real sub-60min fills can be worse (queue position, partial fills) — i.e. costs here are if anything **optimistic**, and they already bury every intraday config. True tick-level slippage would only widen the kill.
- No order-book / latency modelling. A genuine HFT-grade intraday edge (sub-second) is **not testable** on M1-derived bars and is out of scope (not retail-FTMO-executable anyway, L23b).

## 2. FTMO compliance of the multi-leg RV (space A)
- **[material for tradability]** The cross-sectional and butterfly index structures are **long one index / short another highly-correlated index** = an FTMO **hedging-rule violation**. They are reported as *price-edge exploration*, not FTMO-tradable. Even setting compliance aside, they have **no gross edge** (IS ≤ 0), so the point is moot. The only compliant RV (equity-basket vs gold, cross-asset) is flat-to-negative.
- Triangular FX RV is "partial" compliance (related but not identical legs); it is cost-killed by ~10× regardless.

## 3. DSR / noise-floor modelling
- DSR deflated with the **frozen Gate-0 noise SE (0.845)** as `std_sr_trials`, at cumulative **N=97**. This makes DSR>0.5 exactly "beat the pre-registered noise floor". Using the *empirical* edge-dispersion (0.690) instead would give an even **lower** bar — yet still nothing clears, because the binding fact is the **max OOS Sharpe (1.50) < floor (2.13)**.
- **[material]** N is cumulative and honest (70 burned + 27) — understating it (e.g. ignoring the 70) would lower the bar but **still** leaves 0 survivors (even at N=27, threshold ≈ 1.9 > 1.50). The verdict is robust to N.
- OOS = 369 business days. A genuine edge with true Sharpe ~1.0 would be *indistinguishable* from noise on 369 days at N=97 — so v2 cannot **certify** a moderate edge; it can only report that none **exceeded the noise envelope**. (This is the same power ceiling iter-1 hit; it is a property of the fixed 17-month OOS, not a v2 defect.)

## 4. Inherited from iter-1 (unchanged, see iter-1 LIMITATIONS.md)
- Real costs via `CFDCostModel` × markup 3.0; daily median spread; splice-seam & SNB/2008 extreme nulling; 22:00-UTC FX-day anchor; BTC = yfinance daily close; FTMO daily-floor approximated close-to-close in p_funded (not used as the gate here).

## 5. What is NOT testable on our data (reported, not invented)
- **Sub-minute / order-flow intraday edges** — need tick + book data; not available, not retail-executable.
- **Genuinely uncorrelated multi-leg RV** — would need instruments *outside* the 16-symbol set with validated spreads (e.g. sector indices, single-stock CFDs, rates, energy). The `ftmo_close` panel has AUS200/UK100/JP225/HK50/EU50/US2000 but **without per-bar spread** → no honest cost → excluded. This is the one structural gap a *paid* data source could reopen (more legs, lower pairwise correlation, diluted cost) — flagged, not claimed.
- **Options / vol-surface RV, calendar spreads on futures** — not FTMO-executable.
- **Intraday regime conditioning at finer granularity** (e.g. minute-level vol state) — limited by the M1→bar resolution and the absence of a gross intraday edge to condition.
