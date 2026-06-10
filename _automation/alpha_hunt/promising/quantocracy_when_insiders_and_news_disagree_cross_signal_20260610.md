# When Insiders and News Disagree: A First Look at the Cross-Signal

**Source**: quantocracy (via Tommi Johnsen)
**URL**: https://quantocracy.com/redirect.php?key=HCenMM1t5e&source=feedburner
**Captured**: 2026-06-10 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: f5e991834dbbac8eb8f5b61a60384f3b

## Summary
The author examines cases where corporate insider trading activity (SEC Form 4 filings — mandatory disclosures by executives and directors) diverges from concurrent news sentiment for the same stock. The central hypothesis is that insiders hold superior private information, so when they buy against negative public news or sell against positive news, the divergence is a predictive signal for future returns. This is framed as a first exploratory look, with the quantitative development presumably in subsequent posts.

## Why it might be useful
The most direct link is to sector_hothand_propfirm (`Equities/research/active/sector_hothand_propfirm/`), which has flagged a t_HAC=10.38 requiring a mandatory audit before promotion (`_audit/sector_hothand_audit_2026-05-30.md`). If sector_hothand passes the audit, an insider-divergence overlay is exactly the type of negative kill-switch signal (L15 in CLAUDE.md: regime overlay on high-SR strategy) that could filter out sectors where insider selling contradicts the hothand signal — reducing left-tail risk without affecting the core return stream. Secondary connection: SEC EDGAR Form 4 data is freely available via the EDGAR full-text search API, so this is one of the rare equity signals with zero data cost. Concrete action: after sector_hothand audit completes, check whether Form 4 filings can be pulled for the ~10 sector ETF underlying stocks via EDGAR API as a kill-switch filter; the implementation cost is low (~1 day) but the strategy must first survive the SR=10 audit.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — signal concept is relevant to sector_hothand but the audit gate must be cleared first (t_HAC=10.38 is a disqualifying red flag until explained). The insider-divergence overlay only makes sense on a validated base strategy; do not implement before sector_hothand audit result is known.
