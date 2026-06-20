# Continuous Timing Signals for Growth-Defensive Style Allocation: Factor Attribution and OOS Evidence

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.20636
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[metrics, methodology], L2_OK
**Hash**: feb2ac714f2bf8ade1cdd80ea05826ac

## Summary
This paper studies conditional allocation between a growth/technology ETF basket (G) and a defensive income/value ETF basket (D) using macro-market timing signals. A Fama-French five-factor plus momentum attribution shows that the G-D portfolio is a recognizable style portfolio with market beta 0.273 and HML beta loadings. The paper then evaluates macro-timing signals (yield curve slope, momentum, volatility regime) as predictors of G vs. D switching, testing whether these signals can generate out-of-sample alpha above the F-F five-factor model. OOS evidence is mixed — signals that work in-sample lose edge after the 2020 regime shift.

## Why it might be useful
This paper's two-sided test (L25: "real directional edge positive on BOTH legs") is properly conducted: the G-D relative portfolio is explicitly tested as a spread, not just the long leg. The Fama-French attribution framework here mirrors the mandatory beta-orthogonal test (L38) from CLAUDE.md: "regress any structural premium sleeve on a vol-targeted buy-and-hold of its primary asset; report (β, α HAC, R²)." The OOS failure post-2020 reinforces L31 (regime-dependent edge decay). For the sector_hothand_propfirm research (currently showing t_HAC alpha=10.38, a red flag per `_audit/sector_hothand_audit_2026-05-30.md`), this paper's F-F attribution methodology provides the right audit framework.

## Extracted content
Fama-French five-factor plus momentum attribution. "G-D is a recognizable style portfolio: its market beta is 0.273, its HML beta" (full values in paper). The study uses macro-market timing signals: "yield curve slope, momentum, volatility regime." OOS evidence is mixed post-2020.

## Action proposed
REFERENCE

Apply the F-F attribution template from Section 3 to audit the sector_hothand_propfirm result (`Equities/research/active/sector_hothand_propfirm/`). The t_HAC alpha=10.38 is implausible and needs F-F five-factor residualization before citing. Use this paper's methodology as the audit template. Also cross-reference with L38 (mandatory beta-orthogonal test).
