# Idea 5B — Cross-sectional short-term reversion, US stocks (long-only) — PRE-REGISTRATION
*Frozen 2026-06-03 BEFORE results, per `RESEARCH_PROTOCOL_statarb.md`.*

## Hypothesis (economic)
Short-term cross-sectional **reversal** (Lehmann 1990 / Jegadeesh 1990): among liquid US large-caps, recent k-day **losers** tend to bounce relative to **winners** over the next few days (liquidity-provision / overreaction). **Compliant expression: LONG-ONLY the bottom-m losers, rotating** — one-sided, no opposing legs → no FTMO hedging violation. The reversal is an **alpha tilt on top of long-equity beta** (single-leg compliant).

## Caveats stated UP FRONT (likely failure modes)
1. **Weak in mega-caps:** short-term reversal is strongest in small/illiquid names; the FTMO-tradeable mega-caps are the most efficient → edge likely thin.
2. **Cost / turnover (L33):** daily rotation of m names × stock-CFD spread+commission. Decisive cost test.
3. **Long-only = market beta:** bleeds in down markets (2008, 2022) — not market-neutral. The pure market-neutral signal (losers − winners) **is non-compliant (hedging)** and is computed only as a *diagnostic* to confirm the signal exists.
4. **Earnings gaps:** a "loser" may be a bad-earnings drop that keeps falling (confound). Flagged; full earnings-exclusion needs a calendar (note as limitation).
5. **Survivorship:** universe is currently-large names (mild upward bias).

## Data
`panels/single_stocks.csv`, **adjusted** daily close, 2005-01 → 2026-05 (21y). Universe: **70 full-history names** (broad, for signal power) and the **FTMO-proxy 27 mega-caps** (deployable). Daily returns **winsorized at ±30%** (2008 financials).

## Signal (frozen, causal)
- Trailing k-day return per name using closes **≤ t**; rank ascending.
- **Long-only** the bottom-m (biggest losers), equal weight; **fill t+1**; hold H days; rotate.
- Diagnostics (non-deployable): winners (top-m), benchmark (equal-weight all), spread **L−W** (signal existence) and **L−bench** (compliant alpha over beta).

## Tests
- **Existence:** L−W spread Sharpe / t-stat (does reversal exist at all?).
- **Compliant alpha:** L−bench Sharpe / t (does long-losers beat just holding the universe, net of cost?).
- **Cost sweep:** 0 / 5 / 10 / 20 bps per name per rebalance (stock-CFD realistic).
- **1-day delay test**, **by-year** (incl. 2008/2020/2022 beta years), broad-vs-FTMO27.
- **FTMO 2-step first-passage** on the deployable long-only variant (daily-MTM) + DSR on the grid.

## Pre-registered grid (only this)
k ∈ {1, 3, 5}, m ∈ {3, 5, 10}, H ∈ {1, 3, 5}. Baseline (k=5, m=5, H=5).

## Acceptance (charter Part D)
single-leg/long-only compliant · causal/no-look-ahead · reversal signal confirmed (L−W) · **compliant L−bench alpha positive net of measured cost** · survives delay · positive across regimes (esp. beta years) · first-passage p(funded)/bust · DSR-significant · reproducible.

---
*(Results appended below after the engine runs — never above this line.)*

---

# RESULTS & VERDICT (2026-06-03)

## VERDICT: ❌ KILL — the reversal signal is weak, its tradeable form is non-compliant, and the compliant long-only version's alpha is cost-killed to pure beta.

Universe: single_stocks.csv adjusted daily 2005–2026; broad (70) and FTMO-proxy (27); returns winsorized ±30%.

- **Signal exists but weak.** Multi-day reversal L−W (losers−winners): best t ≈ **+2.9 broad / +2.2 ftmo27** (k=3) — borderline and barely at the multiple-testing bar over 27 configs. **1-day reversal is a bid-ask-bounce artifact** — delay test L−W t+1 ≈ +0.1 → t+2 ≈ +1.1–2.2 (appears only under delay = microstructure, not tradeable at real fills).
- **The edge form is non-compliant.** L−W (long losers / short winners) is market-neutral = **opposing positions on correlated instruments = FTMO hedging violation.** Computed only as a diagnostic.
- **Compliant long-only alpha is cost-killed (L33).** Long-losers − equal-weight benchmark: **+6–7%/yr gross**, but t → **+0.6 at 5 bps/name and NEGATIVE by 10 bps** (realistic stock-CFD cost). The reversion *selection* adds ~0 net of cost.
- **What survives cost is just beta.** Long-only absolute return stays +11–16%/yr at 10 bps — but L−bench shows that is the **market rising**, not reversion alpha. It is long equity beta with a tilt that washes out after cost.

**Checklist:** ✅ compliant (long-only) · ✅ causal · 🟡 signal weak/borderline · ❌ tradeable (neutral) form non-compliant · ❌ **compliant alpha not positive net of cost** · (beta-only survives). **KILL as a stat-arb edge.**

