# FX Carry + Trend Filter — Feasibility Summary

**Run date**: 2026-05-20  
**Period**: 2005-01-14 → 2026-05-22  
**n_tests**: 85 (this run adds tests 83, 84, 85)

## Motivation
Raw FX carry has confirmed predictive power (IC=0.027, t=2.02) but severe
crash drawdowns: GFC -24%, EM unwind -15%, COVID -21%.
AMP (2013): trend filter reduces crash exposure by shorting currencies
where 12M-1M momentum contradicts carry direction.

## Signal construction
- **Carry**: weekly 3M interbank spread (FRED), shifted 1 week
- **Trend**: `close[T-5w] / close[T-53w] - 1` (12M-1M momentum)
- **Universe**: 8 G10 currencies vs USD
- **Portfolio**: long top-2 / short bottom-2 (equal weight)
- **Cost**: 15 bps RT (institutional FX)

## Crash protection (MaxDD during crash window)

| Strategy           | GFC 2008 | EM 2015 | COVID 2020 |
|--------------------|----------|---------|-----------|
| Raw carry          | -33.3% | -5.8% | -14.4% |
| Var A (hard)       | -7.5% | -1.5% | -4.1% |
| Var B (soft blend) | -14.6% | -6.0% | -11.6% |
| Var C (mom stop)   | -14.9% | -4.5% | -6.8% |

## Full-period statistics

| Metric       | Raw carry | Var A | Var B | Var C |
|--------------|-----------|-------|-------|-------|
| Sharpe (HAC) | -0.154 | -0.206 | -0.146 | -0.078 |
| Ann ret      | -1.3% | -1.1% | -1.1% | -0.5% |
| MaxDD        | -52.6% | -37.6% | -42.2% | -36.5% |
| WF%          | 55% | 32% | 41% | 55% |
| Alpha t      | -1.43 | -1.62 | -0.96 | -1.02 |
| AMTP p       | 0.894 | 0.932 | 0.887 | 0.814 |
| Filter fire (GFC) | — | 98.1% | — | — |

## Verdicts

- **Variant A**: RESEARCH FAIL / PROPFIRM FAIL
- **Variant B**: RESEARCH FAIL / PROPFIRM FAIL
- **Variant C**: RESEARCH FAIL / PROPFIRM FAIL

## Root cause notes
- AMP (2013) documented trend filter reduces carry crash MaxDD by 30-50%
- Filter effectiveness measured by fire rate concentrated in crash windows
- GFC 2008 filter fire rate (Var A): 98.1%

## Gates reference
RESEARCH_PASS: Sharpe>0.60, GFC MaxDD>-15%, COVID MaxDD>-12%, MaxDD<-30%, WF%≥40%, Alpha t>1.0, AMTP p<0.30
PROPFIRM_PASS: Sharpe>1.0, GFC MaxDD>-10%, COVID MaxDD>-8%, MaxDD<-15%, WF%≥55%, Alpha t>1.5, AMTP p<0.15
