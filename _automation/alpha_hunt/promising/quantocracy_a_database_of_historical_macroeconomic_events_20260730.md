# A Database of Historical Macroeconomic Events

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=aJ8y8wDgCx&source=feedburner
**Captured**: 2026-07-30 06:30 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 7eb5526236fc9a7944893e91e3bbdcd8

## Summary
Concretum Group announces a curated dataset of historical macroeconomic events, positioning it as a complement to the usual price-history databases that quant backtests rely on. The framing note observes that most backtests start from clean OHLC prices free of survivorship bias, but says comparatively little attention is paid to building an equally clean, systematic record of the macro events (rate decisions, data releases, crises, etc.) that price series react to. The excerpt is introductory and does not describe the database's coverage period, event taxonomy, or licensing/access terms.

## Why it might be useful
An events database is directly relevant to two open threads: the ZN Baltussen research (`Futures/research/active/zn_baltussen/`) and the treasury-auction/seasonality work referenced under L58, where the project's own auction-blackout placebo interacted badly with day-of-month seasonality — a broader, independent macro-events calendar could serve as a cleaner exogenous control set for that kind of placebo test. It's also relevant to L42 (pre-FOMC drift is real on equity indices, but the reversal direction claim needs two-sided support) and to the FX intraday deepdive family, where event-time alignment quality has repeatedly been the deciding factor (L26 delay-1/same-bar, L56 exchange-clock vs UTC). Before using it for anything, the source, coverage, and cost would need vetting since CLAUDE.md's Data sources section has no existing macro-events feed beyond FRED series.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — need to check the database's actual coverage/cost/access before it can plug into any active family (ZN Baltussen or the treasury-auction placebo work), which requires reading the full source first.
