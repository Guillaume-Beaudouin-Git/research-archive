# Reconciliation with the Independent Audit — FTMO 3-Sleeve Portfolio

**Date:** 2026-06-08 · **Author response to:** `research/ftmo_portfolio_audit/AUDIT_REPORT.md`
**Verdict: I accept the audit in full. The 0.55 headline is retracted. The objective is NOT met.**

A reproducible 0.43 beats an unreproducible 0.55. Below is my independent verification of each
load-bearing claim (I re-ran everything myself; I did not take the audit on faith), and the honest
re-baseline with a monotone engine, CIs on every p(pass), and DSR at the true trial count.

---

## 1. Root causes — verified independently

### (a) Timezone: the panel is EET, not UTC (CONFIRMED)
Empirical test (my run): hourly returns of `panels/m5_indices/EURUSD` vs true-UTC
`deep_history_utc/EURUSD` **peak-correlate at a −3h shift** (≈0 at 0h). The panel stamp `timestamp_utc`
is **EET/EEST (UTC+3)**. Consequence: my Sleeves B (BTC) and C (US30), both loaded from that panel,
traded windows **shifted 3 hours from their documented labels**. My "US30 13-20 UTC" was actually
10-17 UTC — a more favorable (London+NY) window. On genuinely true-UTC `deep_history` at 13-20 UTC the
sleeve is **+0.19 full / +0.17 OOS and not positive every year** (2024 −0.24, 2026 −0.29), not +1.00.

### (b) Sleeve A: an execution-convention artifact (CONFIRMED)
My cached MR gave +0.72 (equal) / +0.89 (inv-vol). My `th()` used **open-to-open execution + booked
each trade's full P&L on its entry day**. Rebuilt as a standard **close-to-close position MTM**, the
same two-sided RSI2 on the same 11 instruments gives **−0.04 (2022-26)**. The edge is not a look-ahead
but it is **convention-fragile and does not survive a standard MTM** → no robust edge. (Per-instrument
the signal is scattered and small; aggregate ≈ 0.)

### (c) Sleeve B: OOS-negative on clean data (CONFIRMED)
True-UTC binance BTC, stated 120m/z2 config: **+0.38 full / −0.92 OOS**. An illusory hedge — and a
+1-bar execution delay already destroyed it (audit Gate E). 

### (d) No reproducible artifact (CONFIRMED)
The entire pipeline lived in a scratch sandbox; **no runner was ever committed** that builds the
3-sleeve portfolio or its p(pass) table. The report's "cached and regenerable end-to-end" was false.
This is the deepest finding: a number that cannot be regenerated cannot be defended.

---

## 2. Honest re-baseline (clean sleeves, monotone engine, CIs, DSR)

**Clean sleeves (vol-targeted, full / OOS Sharpe):** A −0.10 / +0.19 · B +0.30 / −0.92 · C +0.34 / +0.14.
**Clean equal-weight combo:** Sharpe **+0.32 full / −0.32 OOS**; kurtosis 2.1; |ρ| < 0.06 (decorrelation
real). Per-year: 2022 +2.74, 2023 +0.71, 2024 −0.28, 2025 −0.12, 2026 −0.82 — positive only 2022-23.

**p(pass), monotone sequential two-phase engine, best leverage, 90% outer block-resample CIs:**

| Horizon | FULL (2022-26) | OOS (2025-26) |
|---|--:|--:|
| ≤ 3 months | 0.43 · [0.32, 0.55] | **0.35 · [0.25, 0.53]** |
| ≤ 6 months | 0.52 | 0.39 |
| ≤ 9 months | 0.55 | 0.40 |

(Monotone in horizon by construction — the report's 0.580→0.531 violation is gone. My engine **omits the
min-4-days constraint, so these are if anything optimistic**; the audit's stricter engine gives ≈0.20-0.30.)

**DSR at the true trial count** (combined Sharpe +0.32): **0.13 (N=100), 0.07 (N=500)** — the edge is
**not statistically distinguishable from zero**.

---

## 3. Plain verdict

**No version clears 0.50 with its confidence interval.** Central p(pass ≤ 3mo) ≈ 0.35 (OOS) to 0.43
(full); both 90% CIs and medians sit below 0.50, and the underlying Sharpe fails DSR. The ~0.43 "full"
figure is essentially the **zero-edge barrier-geometry baseline**, not an edge-driven pass. The
portfolio, as implemented, is **consistent with failure** of the FTMO 10k 2-step in 3 months.

---

## 4. What survives, and honest next steps

**Survives:** the **multi-sleeve-decorrelated thesis** (|ρ|<0.06, co-breach ≈ independence, kurtosis
averages 27→2.1). The architecture is sound; the *inputs* (the three sleeves) are not real edges.
**Also confirmed:** the execution-lag diagnostics (Sleeve B was an illusory hedge regardless).

**Process fixes adopted going forward (non-negotiable):**
1. **One committed runner** builds every sleeve and the portfolio end-to-end; no scratch-only numbers.
2. **Verify timezone empirically** on every data source before use (the −3h test); use the EET build =
   the broker's actual server day for indices.
3. **Standard close-to-close MTM only**; no entry-day-booking or open-to-open conventions that don't
   survive a vanilla mark.
4. **Monotone first-passage engine + outer-resample CIs on every p(pass)**; never a naked point.
5. **DSR at the true N** (≈ hundreds, given the search breadth) before any Sharpe is cited.

**Research implication:** decorrelating ≈-zero sleeves yields ≈-zero. To use the (real) decorrelation
machinery we need sleeves that are **individually positive net of honest costs on true-UTC, out-of-sample,
under DSR** — which the systematic search (correctly) showed are scarce in the free-data FTMO price
universe. The honest options remain: a longer horizon does not rescue a zero-edge book (the DSR, not the
clock, is binding here); a genuinely orthogonal **new-data** edge; or accept that this universe does not
support a > 0.50 / 3-month book and report that plainly — which is what this document does.

*All figures regenerated independently over read-only source data; the audit deliverables were not
modified. Where the audit and my regeneration differ in magnitude (e.g. 0.43 vs 0.20 on full ≤3mo,
from min-days handling), both are below 0.50 and the conclusion is identical.*
