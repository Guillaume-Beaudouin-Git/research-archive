# PRE-REG ADDENDUM — H4 Commodity seasonality (OOS-validated)

**Date frozen:** 2026-07-15, before any H4 result. Extends the session prereg (same PERSONAL_PASS gate).

## H4 — Physical-calendar seasonality on real commodity futures

- **Mechanism / prior:** commodity prices carry real physical-calendar flows (cold-season energy demand,
  harvest/planting cycles, driving-season gasoline). Underlyings have ~zero long-run drift → an edge that
  is real can beat B&H *by concentration* (the exact property that made H3 pass, and that overnight-drift
  H1 lacked). Repo brick `commodity_seasonality` already showed OOS Sharpe 0.33, corr 0.10 to TSMOM.
- **Anti-overfit design (frozen, decisive):** seasonality is notoriously data-mined → NO in-sample month
  cherry-picking. Method:
  1. Universe: liquid commodity futures, yfinance =F continuous front-month: CL, BZ, NG, HO, RB (energy);
     ZC, ZL, ZS, KC, SB, CC, CT, OJ (ags); GC, SI, HG, PL, PA (metals); LE, HE (livestock).
  2. **TRAIN 2000-2012:** estimate each commodity's mean return by calendar month.
  3. **Select** per commodity the calendar months with |mean| in the top tercile of that commodity's
     seasonal amplitude, sign = train sign. Frozen after train, no peeking at OOS.
  4. **OOS 2013-2026:** trade long (or short) that commodity in its selected months, flat otherwise.
     Pool across commodities = the seasonal book. This is the ONLY series scored.
- **Kill rules (frozen):**
  - (K1) OOS pooled Sharpe (net cost) < 0.5 → fail.
  - (K2) OOS book does NOT beat an equal-weight vol-targeted B&H of the same commodities → beta/no-timing,
    KILL (PERSONAL_PASS #1).
  - (K3) OOS placebo: pooled seasonal vs 1000 random month-selection books (matched count) — must exceed
    placebo p95, else it is calendar noise.
  - (K4) DSR (session-N) < 0.70 → fail. Report skew/kurtosis (roll-drag tail per L5 caveat).
  - (K5) regime split within OOS (2013-2019 vs 2020-2026): sign-consistent, not one-window.
- **Cost:** commodity futures RT ~1.5-3 bps (real futures); monthly rebalance → cost minor. Flag the L5
  roll-drag contamination of continuous front-month as a known limitation (front-month yfinance ≠ true
  excess return; a pass here is provisional pending true roll-adjusted data).
- **N:** counts as 1 family test (OOS-validated pooled book), not per-commodity.

*Score ONLY the OOS 2013-2026 pooled series. Train stats are for selection, never reported as edge.*
