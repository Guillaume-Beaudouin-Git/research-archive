# RESULTS H9 — Mean-reverting underlying for the grid (economically-anchored spreads)

**Verdict: 4 genuinely OOS-mean-reverting spreads found (beats repo 0/12) — but the grid on them is a
MODEST, DD-heavy sleeve (~3-5%/yr at 1×, real max-DD −29 to −39%), NOT the aggressive scaler sought.**
Data: yfinance =F 2005-2026; train 2005-2015, OOS 2016-2026.

## Stationarity scan (K1+K2)

OOS-stationary survivors (ADF p<0.05, half-life 3-60d): **WTI-Brent** (p=0.001, 19d), **Corn-Wheat**
(0.001, 46d), **Gasoline-Crude/crack** (0.001, 19d), **HeatOil-Crude/crack** (0.024, 42d). Failed:
gold-platinum/silver, platinum-palladium, soy complex (OOS non-stationary — the repo's usual outcome).
**The economic-anchor thesis works:** structurally-linked spreads (crude grades, refining margin, feed
substitution) mean-revert OOS where data-mined pairs do not (L44 mechanism-first validated).

## Grid on the real OOS path (K3) — the honest numbers

| Spread | 1× CAGR | 1× max-DD | 2× CAGR | 2× max-DD | two-sided |
|---|---|---|---|---|---|
| Gasoline-Crude | +5.4% | −29% | +9.0% | −49% | ✅ |
| HeatOil-Crude | +4.3% | −30% | +7.4% | −47% | ✅ |
| WTI-Brent | +3.2% | −39% | +5.7% | −66% (ruin) | ✅ |
| Corn-Wheat | +3.3% | −36% | +5.8% | −58% | ✅ |

**Audit catch:** the OU-MC (calibrated to half-life+vol) reported 0% ruin and €13k — it was IDEALIZED
(stable mean). The real path (drifting mean, 2020 oil crash) shows −29 to −39% DD at 1× and ruin at 2×.
Lead with the real path, not the MC.

## Findings

1. Real, OOS-stationary, two-sided mean-reversion confirmed on 4 anchored spreads — genuine result.
2. **Return is modest** (~3-5%/yr at 1×); the grid harvests real oscillations but the mean drifts, so
   realized ≪ idealized OU-MC.
3. **DD is large and regime-driven** (−29 to −39% at 1×): the drawdowns come from exactly the H8-predicted
   trend-against-grid mode (2020 crack blowout). **H8 trend kill-switch is mandatory** (would have cut 2020).
4. **Not an aggressive scaler:** leverage to raise return breaches the DD budget (2× → −47 to −66%).
5. **€12k deployment blockers:** granularity (crack = full-size RB+HO+CL, no micros → ~$60-140k notional →
   untradable at €12k); L5 roll contamination of continuous front-month spreads → magnitude provisional.

## Verdict

The grid hunt succeeded on its narrow question (a real mean-reverting underlying exists) and failed on the
user's actual goal (aggressive scaling). Gasoline-Crude / HeatOil-Crude crack-spread grids are a
**legitimate but modest decorrelated sleeve** (~SR 0.5-0.7 class), on par with H3/H4, more DD-heavy, with
a mandatory trend kill-switch and a €12k granularity blocker. Consistent with the session's constant
lesson: **real edges are modest (~SR 0.5-1.0); no single-engine aggressive scaler exists** — growth comes
from combining modest decorrelated sleeves at fractional Kelly, not from a hot strategy or a sizing trick.
