# Market Effect Research: Turn of the Month Effect [TradeQuantiX]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=E2dI0Cx3kE&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 85e794cf82d00cfc0626c19a0755fb61

## Summary
TradeQuantiX documents the turn-of-month (TOM) effect — the historical tendency for equity markets to drift higher in the last few days of one month and the first few days of the next. The article provides a systematic examination of this calendar anomaly, quantifying the effect across different instruments and testing periods.

## Why it might be useful
Potentially relevant to Strategy C (NQ opening momentum): if the TOM effect creates a systematic upward drift bias in NQ around month-end/month-start, the ORB signal during those days may exhibit different directional bias than the rest of the month. Testing whether Strategy C's win rate or direction distribution differs around TOM would take 30 minutes with the existing 346-trade backtest. This is a quick sanity check, not a modification. For Strategy A (crypto TSMOM), the 28-day lookback window already partially captures monthly periodicity, so TOM-specific behavior is absorbed into the vol-normalized signal.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Quick diagnostic: split Strategy C's 346 backtest trades by TOM (last 3 / first 3 days of month) vs non-TOM and compare win rates. 30-minute analysis with existing data. Not a modification — just a bias check.
