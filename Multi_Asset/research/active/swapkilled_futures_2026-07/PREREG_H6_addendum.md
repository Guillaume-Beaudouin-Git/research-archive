# PRE-REG ADDENDUM — H6 Month-end FX rebalancing flow (Melvin-Prins)

**Date frozen:** 2026-07-15, before any H6 result. Same PERSONAL_PASS gate.

## H6 — Month-end USD rebalancing flow (Melvin & Prins 2015)

- **Mechanism / prior:** global equity/bond funds rebalance FX hedges at month-end. Melvin-Prins (JIMF
  2015): when foreign (non-US) equities OUTPERFORM in a month, US-based hedgers must BUY USD (raise the
  USD hedge on their now-larger foreign book) into month-end → **month-end USD strength conditional on
  the month's foreign-vs-US equity divergence.** FX is near-zero baseline drift → eligible for
  concentration-beats-beta (unlike equity H5). Repo FX closures (L43/L34/E) were intraday-flat / fix /
  carry — NOT this daily month-end hedge-flow on futures.
- **Signal (frozen):** on the last 3 business days of each month, take a USD position sized by the sign
  of (prior-month MSCI-World-ex-US proxy return − prior-month S&P return). Long-USD when foreign
  outperformed. Traded as a basket of USD vs {EUR, GBP, JPY, AUD, CAD, CHF}. Proxy for foreign equity:
  equal-weight {^GDAXI, ^N225, ^FTSE} ; US = ^GSPC. Robustness (reported): unconditional month-end USD.
- **Instruments/data:** FX majors via yfinance (EURUSD=X etc.) or deep_history_utc FX daily; equity
  proxies via yfinance. Cost: CME FX futures ~0.5-1 bp RT, monthly → negligible.
- **Kill rules (frozen):**
  - (K1) net Sharpe < 0.5 → fail.
  - (K2) does NOT beat vol-targeted B&H the FX basket (#1) → KILL.
  - (K3) regime split pre/post-2015 (publication): if 2015+ Sharpe < 0.3 or sign-flips → DECAYED, KILL.
  - (K4) placebo: month-end conditional vs 1000 random 3-day windows → exceed p95.
  - (K5) DSR (session-N) reported; the conditioning must beat the UNCONDITIONAL month-end (else it is
    just calendar, not the hedge-flow mechanism).
- **N:** 1 family test.
