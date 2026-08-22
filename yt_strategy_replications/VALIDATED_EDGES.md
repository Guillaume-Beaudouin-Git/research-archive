# Validated Edges — keep / build on these

Out of 13 strategies across 5 videos, these are the ones with **real, documented structure**. None is a turnkey money-printer; each is a building block with explicit caveats and a clear "what would make it tradable" path.

## 🟢 Tier 0 — DEPLOYABLE candidate (own research) — `ASIA_23_8` (swap-free)
- **What:** long XAUUSD over **23:00→07:00 UTC** (Asian session), flat otherwise; vol-targeted (avg leverage ~1.05×). Enters *after* the 21:00–22:00 UTC rollover and exits before the next → **swap-free** (no overnight financing); spread cost only, one round trip/day. Code: `gold_research/strategy_overnight.py`.
- **Evidence (XAUUSD M1 true-UTC, 2007–2026, swap = 0):** Sharpe **1.18 full / 1.07 OOS at 1.5 bp spread** (0.98 / 0.88 at 2 bp); Deflated Sharpe **0.92**; HAC t 3.9; walk-forward 5/5; maxDD −15.6%.
- **Why structural:** gold's drift concentrates in the US-close→Asia window (Asian physical/official-sector demand).
- **Audited & stress-tested** (`reports/gold_strategy_risk_audit.md`): no look-ahead; it is **alpha, not gold beta** (β 0.01, R² 0.001, α t 4.8); positive 17/20 years incl. the 2013–15 bear; MC P(Sharpe>1)=66%, 5th-pct 0.71; robust to dropping the top-20 days.
- **The catch — hard conditions:** (1) broker rollover ≤ 22:00 UTC — if it hits 23:00 the long swap (−3.3 bp) re-applies and the edge dies (Sharpe −0.34); (2) spread ≤ ~1.5 bp; (3) **enter at 23:00 UTC to the hour** (1h late → Sharpe 0.37 — the alpha is the first post-rollover hour); (4) tolerate long drawdowns (max −19%, up to ~4.8y underwater).
- **⚠ Do not use the naive `ON_22_8`** (22:00→06:00): it *looks* like Sharpe 1.85 on price but **holds across the rollover → the long swap (−3.3 bp/night) cuts it to Sharpe 0.46** (lesson L30/L36). The whole point is to be flat across the rollover.
- **Status:** **meets DSR > 0.5; meets Sharpe > 1 (full & OOS) at ≤1.5 bp spread, swap-free.** Next: a de-beta'd market-neutral variant. Full write-up in `reports/gold_overnight_strategy.md`.

## ✅ Tier 1 — real and statistically significant

### Variance Risk Premium (VRP) — *the single strongest edge found*
- **Evidence (this repo):** implied vol (VIX) exceeds subsequent realised SPY vol **83.7%** of the time; non-overlapping monthly short-variance premium has **annualised Sharpe 0.52**, 83% of months positive, 2004–2026 (`module_5_structural_edges/`).
- **Why it's structural:** institutions overpay for crash insurance (Carr–Wu 2009; Bondarenko). The premium is compensation for tail risk.
- **The catch:** distribution is `skew −4.9, kurtosis 45`; the worst month is **−64× the mean**. Naive OTM selling is how accounts blow up (Feb-2018 Volmageddon, Mar-2020).
- **To make it tradable:** (1) hard tail hedge (buy deep-OTM puts / cap notional), (2) regime-gate on VIX level and term-structure (don't sell when backwardated), (3) size by a tail-risk budget, not Sharpe. Needs options/variance execution infra. Lesson L13 (measure in correct units, net of tail) applies.
- **Status:** candidate for a derivatives sleeve; requires options infrastructure before deployment.

### Post-Earnings Announcement Drift (PEAD)
- **Evidence (literature):** Ball–Brown 1968; Bernard–Thomas 1989 — high-SUE stocks drift up ~4% over 60 days vs low-SUE. One of the most replicated anomalies in finance.
- **The catch:** alpha-decaying since ~2000s; concentrated in smaller/illiquid names; needs short-sale access for the full spread.
- **To make it tradable:** rank by standardized unexpected earnings each quarter, long top decile / short bottom, ~60-day hold, monthly rebalance, dollar-neutral; gate on liquidity; HAC + DSR before sizing.
- **Status:** **data-gated** — needs an earnings-surprise (estimates + actuals) dataset (I/B/E/S, or limited free Nasdaq/AlphaVantage). Worth acquiring.

## ⚠️ Tier 2 — real structure, not standalone alpha (use as components)

- **Intraday upside skew on index futures / ORB long side:** NQ opening-range long breakouts follow through **55%** of the time (real structural drift) but the +5% skew is below the cost line for a blind 1:1 trade. Useful only inside a filtered, direction-confirmed system (cf. repo Strategy C).
- **MVRV / price-z sizing on Bitcoin:** a z-vs-trend overlay improved DCA capital efficiency **+17%** vs static DCA (buy more in capitulation). It does **not** reduce drawdown and is Bitcoin beta with a sizing overlay (repo: MVRV ≈ momentum proxy, corr 0.73). Keep as an accumulation-sizing rule, not an alpha.

## Decision
- **Deploy / paper-trade `ON_22_8`** (Tier 0) — the one strategy that meets Sharpe > 1 and DSR > 0.5 out-of-sample with a low-leverage, codeable rule. Next: a market-neutral (de-beta'd) variant and portfolio sizing against the existing crypto/FX book.
- Pursue **VRP** and **PEAD** (Tier 1) once options-execution and earnings-surprise data infrastructure are in place.
- The pin-bar gold idea is archived (`archived/POSTMORTEM.md`); it was correctly replaced by the overnight-drift edge.
