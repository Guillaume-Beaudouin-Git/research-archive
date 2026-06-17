# Market Effect Research: Turnaround Tuesday Effect

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=e3IXH7pOPF&source=feedburner
**Captured**: 2026-06-17 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: e30835edcb0f5d07f2bdb7042993b9f2

## Summary
The fourth article in a market effects series, after the holiday effect and turn-of-month effect (both on SPY), examines whether Monday's equity declines are systematically reversed on Tuesday — the so-called "Turnaround Tuesday" effect. The research tests whether a conditional long on Tuesday (after a losing Monday) generates statistically significant positive returns on SPY, which is a weekly seasonality / calendar anomaly claim.

## Why it might be useful
L42 already documents that pre-FOMC drift is real on equity indices (8 instruments, AMTP-significant); that lesson also notes that POST-event reversal is the wrong direction (momentum continues post-event). The Turnaround Tuesday effect is a different mechanism — Monday-conditioned reversal rather than event-conditioned momentum — but it lives in the same calendar-anomaly family. The NQ 1-min data in `data/raw/NQ_1min_databento_2010-2026.parquet` covers the period needed to test this. However, Strategy C NQ ORB was cancelled (Databento re-baseline SR 0.41, under PROPFIRM_PASS), and Strategy D (D3+D5) is focused on intraday openings; a weekly day-of-week seasonality overlay could be explored as a regime filter on D3 or D5 entries. Before testing: check the series cost structure — at $29 RT NQ, a weekly-conditioned signal annualizes at N≈52, meaning cost per trade needs edge > $29 just to break even on gross, which requires a meaningful mean expected move on Tuesday. Apply L12 event-count ceiling gate.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

A clean test on NQ (not SPY) is < 1 day with available data, but the propfirm vehicle for NQ is suspended (C cancelled, D not validated). Revisit if D3/D5 NQ research resumes and needs a calendar regime filter to improve pass rate. Apply L12 event-count ceiling before any backtest.
