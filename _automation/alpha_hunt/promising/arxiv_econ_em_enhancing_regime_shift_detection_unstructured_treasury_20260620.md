# Enhancing Regime Shift Detection Using Unstructured Data: Evidence from the Treasury Market

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.30363
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[methodology, macro_trading], L2_OK
**Hash**: 6d81ea54b077da7f7ea61d533e5db3be

## Summary
This paper combines structured time-series data (yield spreads, macro indicators) with unstructured Fed communications text to improve Treasury market regime shift detection. Standard methods fail because they rely solely on structured data and ignore policy communications, even though text often signals shifts before they appear in prices. The paper uses NLP to extract regime signals from FOMC minutes and Fed speeches, then combines them with structured VaR-based regime indicators in a joint framework. In-sample and OOS results on the U.S. Treasury market from 2000–2024 show the combined approach detects regime shifts earlier and with fewer false positives than structure-only methods.

## Why it might be useful
The ZN Baltussen research (`Futures/research/active/zn_baltussen/`) targets bond futures momentum. FOMC communications are the single largest driver of Treasury regime shifts — a momentum signal on ZN that ignores FOMC regime changes will have systematically poor performance during policy pivots (2022: hiking regime, 2023: plateau, 2024: easing). The NLP-based Fed communication signal described here is exactly the macro overlay needed for ZN momentum. FRED data is available (DTB3 daily, already in CLAUDE.md Data sources), and FOMC minutes are public domain. Implementation cost: ~2 days (scrape FOMC text + NLP sentiment + combine with structured regime indicator).

## Extracted content
Combined structured (yield spreads, macro) + unstructured (FOMC minutes, Fed speeches) approach. Uses NLP for text. "Standard regime shift detection methods rely solely on structured time-series data and ignore policy communications." OOS on U.S. Treasury market 2000–2024. "Detects regime shifts earlier and with fewer false positives."

## Action proposed
TEST_LATER

Apply as Phase B regime overlay for the ZN Baltussen momentum research. After baseline ZN momentum tests confirm edge, add FOMC-communication-based regime filter as a conditioning signal. Implementation requires FOMC minutes scraper (public domain) + sentiment model (BERT-based). Budget: ~2 days. Pre-register before implementing to avoid modification budget overrun.
