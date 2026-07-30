# RESULTS H4 — Commodity seasonality (OOS-validated)

**Verdict: PASSES `PERSONAL_PASS` (all 5) — PROVISIONAL on roll-adjustment (L5).** Second genuine edge
of the session, higher OOS Sharpe than H3. N: 1 family test (OOS-validated pooled book). Data: yfinance
=F continuous front-month, 20 commodities, 2000-2026. Selection FROZEN on train 2000-2012; scored ONLY on
OOS 2013-2026.

## Gate scorecard (OOS 2013-2026, N_months=161)

| # | Criterion | Result | Pass |
|---|---|---|---|
| 1 | Beat B&H | seasonal book **SR 1.13** vs EW B&H commodities **0.54** | ✅ |
| 2 | Non-beta / timing | selection sign-frozen on train, traded blind OOS; beats passive commodity hold | ✅ |
| 3 | DSR ≥ 0.70 | N=1 (OOS-validated single family) DSR=1.00; placebo corroborates | ✅ |
| 4 | Regime-stable | **2013-2019 SR 1.15 · 2020-2026 SR 1.16** — near-identical across two very different regimes | ✅ strong |
| 5 | Placebo / not-mined | book SR 1.13 vs 1000 random-month-selection books **p95=0.51, empirical p=0.000** | ✅ strong |

OOS ann 19.5%, vol 17.2%, MaxDD −32.0% (fits the DD budget), skew −0.32 (mild).

## What it is

Physical-calendar commodity flows (energy demand cycles, harvest/planting, driving season). The
OOS-validated design (seasonal months chosen on 2000-2012, traded blind on 2013-2026) + the placebo
p=0.000 make this hard to dismiss as data-mining — the exact failure mode seasonality usually dies of.
Regime-stability across 2013-19 and 2020-26 is the strongest of any candidate this session.

## The honest caveat (why PROVISIONAL)

**L5 — continuous front-month roll contamination.** yfinance =F continuous is NOT a true excess-return
series; for many commodities the roll yield (contango/backwardation) is itself seasonal, so part of the
measured "seasonal return" may be seasonal roll yield rather than price appreciation. **Both are tradable
by a real futures holder** (roll yield is real P&L), but the *magnitude* here is not trustworthy until
re-run on a properly roll-adjusted / true-excess-return series. **The signal is real (OOS + placebo);
the number 1.13 is provisional.** Confirm before sizing.

## Session picture — two decorrelated real edges

| Sleeve | Asset class | OOS Sharpe | Mechanism | Status |
|---|---|---|---|---|
| **H3 month-end Treasury** | rates | 0.90–1.15 | rebalancing flow | PASS, cost-immune |
| **H4 commodity seasonality** | commodities | 1.13 (provisional) | physical calendar | PASS, roll-caveat |

Different asset classes → expected low cross-correlation → the **foundation of the diversified book the
account was meant to be**. Two ~SR-1.0 sleeves at low correlation combine toward portfolio SR ≈ 1.3–1.5.
This — not a single levered engine — is the realistic path to controlled-DD scaling.

## Next

1. Re-run H4 on roll-adjusted / true-excess data → lift the PROVISIONAL flag (or discount the magnitude).
2. Measure H3×H4 realized correlation → confirm the diversification, build combined-book ERC sizing at €12k.
3. Optionally continue for a 3rd decorrelated sleeve (FX/rates flow, or the deferred H2 carry with curve data).

---
**⚠️ CORRECTION 2026-07-15 (roll audit, see ROLL_AUDIT.md):** on independent roll-clean data (deep_history broker-continuous) this sleeve collapses to Sharpe **0.47** and fails its placebo (p=0.086). The 1.13 was largely a seasonal roll-yield artefact. **H4 DROPPED from the deployable book** — the L5 flag is NOT lifted.
