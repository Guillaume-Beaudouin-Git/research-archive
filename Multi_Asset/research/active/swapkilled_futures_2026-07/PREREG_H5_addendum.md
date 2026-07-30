# PRE-REG ADDENDUM — H5 Pre-FOMC drift (equity index)

**Date frozen:** 2026-07-15, before any H5 result. Same PERSONAL_PASS gate.

## H5 — Pre-FOMC announcement drift (Lucca-Moench 2015)

- **Mechanism / prior:** Lucca-Moench (JF 2015) document that US equity excess returns are heavily
  concentrated in the ~24h BEFORE scheduled FOMC announcements (accounting for a large share of the
  equity premium since 1994). Because the drift is *concentrated*, a pre-FOMC-only sleeve can beat B&H
  equity (the H3/H4 "concentration beats beta" property) despite equity's positive baseline drift.
  Repo L42: pre-FOMC drift confirmed real on 8 instruments.
- **Documented decay risk (the decisive test):** several post-2015 studies report the effect weakened
  after publication/arbitrage. → the **regime split is the kill switch** (L31 alpha-decay).
- **Signal (frozen):** long S&P (via ES/MES) on the single trading day immediately preceding each
  scheduled FOMC announcement date (close[T-2] → close[T-1]), flat otherwise. Robustness variant
  (reported, not primary): 2-day window {T-2, T-1}. NO other tuning.
- **Instruments/data:** ^GSPC (fetch yfinance, long history) primary; FOMC dates
  `data/personal_book/post_fomc_drift/data_cache/fomc_events.csv` (2004-2026, 182 meetings). Cross-check
  ^NDX. Cost: MES ~0.8 bps RT, 8 events/yr → negligible.
- **Kill rules (frozen):**
  - (K1) net Sharpe of the pre-FOMC sleeve < 0.5 → fail.
  - (K2) does NOT beat vol-targeted B&H S&P (#1) → beta, KILL.
  - (K3) **regime split 2004-2014 vs 2015-2026: if 2015+ Sharpe < 0.5 or sign-flips → DECAYED, KILL**
    (this is the pre-registered decisive test; publication was 2015).
  - (K4) placebo: pre-FOMC day return vs 1000 random single-day-per-cycle picks (matched count) — must
    exceed p95.
  - (K5) DSR (session-N) reported; skew/kurtosis reported (event days can have fat tails).
- **N:** 1 family test.

*Score the OOS-agnostic full series but the PROMOTE decision hinges on K3 (post-2015 survival).*
