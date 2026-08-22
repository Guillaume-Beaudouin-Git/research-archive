# Commodities — extended signal exploration (relative-value, COT, skewness)

**Mandate:** after the carry NO-GO, explore what the literature says works on the **non-oil** commodities
(wheat, metals, cocoa, soybeans) — the markets with weather/supply/positioning dynamics rather than a
secular drift. Tested the documented two-sided, low-turnover signals that avoid our known traps (beta,
carry-uncollectable). Same discipline: two-sided, real costs, OOS, cointegration/half-life where relevant.

## Verdict

> **Comprehensively explored, the commodity complex does not beat the FTMO incumbent.** Every individual literature signal is **weak at our scale** (10 FTMO commodities, real CFD costs): seasonality 0.28 (the best), momentum ~0.1–0.25, COT/hedging-pressure 0.20–0.26, skewness 0.06. **Combining all of them (decorrelated, two-sided): Sharpe 0.34 → p(pass) ~42 %** — ties-to-slightly-below ORB+floor (~46–50 %). Metals relative-value (gold/silver ratio) failed outright. **Commodities is the best *asset class* found (the signals are genuinely two-sided and some OOS-stable — a real break from the beta everywhere else), but no signal is strong enough, and the one that would have beaten it (carry) was hindsight.**

---

## What was tested this round

**1. Metals relative-value (gold/silver ratio + platinum ratios) — FAILED.**
| pair | cointegrated? | half-life | backtest |
|---|---|---:|---|
| XAU/XAG (gold/silver) | no (EG p=0.15) | **285 d (~14 mo)** | **loses, t=−6.4** |
| XPT/XAU | no | 980 d (~4 yr) | loses |
| XPT/XPD, XPD/XAU, XAG/XPT | no | 583–964 d | loses |

The ratios **aren't cointegrated** and have **multi-year half-lives** → no tradeable mean-reversion. Fading
the gold/silver ratio at extremes **loses** — the classic 2019–20 trap (ratio went 80→**120** instead of
reverting). "Gold/silver mean-reversion" is a *decade*-scale story, not an FTMO one. (Same failure as the
FX stat-arb: not cointegrated, half-life too long.)

**2. COT / hedging-pressure (free CFTC data, 2008–2025, 9 commodities) — WEAK.**
| variant | Sharpe | t | note |
|---|---:|---:|---|
| HP level, XS (long high-HP) | 0.08 | 0.32 | regime-dependent (+0.58 '10-14, **−0.37 '15-19**) |
| COT-index percentile, XS | −0.20 | −0.81 | one-sided (short leg drags) |
| HP-change (positioning mom) | −0.37 | −1.6 | worse |
| **COT-index, time-series (long>0.8/short<0.2)** | **+0.26** | 1.04 | best COT variant, still weak |

The hedging-pressure premium is real in theory (Kang-Rouwenhorst-Tang) but **decayed post-financialization**
(2015–19 negative) — consistent with the literature. Best variant (TS COT-index 0.26) ties seasonality, not
better. *Fundamentally the soundest signal (a real risk premium, free data), but empirically too weak now.*

**3. Skewness (Fernandez-Perez: long neg-skew / short pos-skew) — WEAK.** Sharpe 0.06. Two-sided but no edge at N=10.

**4. Combination (all dynamic-safe two-sided signals).**
| signal | Sharpe | pairwise corr |
|---|---:|---|
| seasonality | +0.28 | low (≤0.22) |
| momentum | ~+0.1 | — |
| COT-index TS | +0.20 | — |
| skewness | +0.06 | — |
| **Combined (eq-risk, real costs)** | **0.34** | **t=1.30** |

Decorrelated (good), but **p(pass) L2 ~42 % / L3 ~40 %** — below the incumbent. A Sharpe-0.34 book is too
thin for the +10 %/+5 % barrier; the no-time-limit floor_taper exploit (~46–50 %) manages the barrier better.

---

## The honest, comprehensive conclusion on commodities

After testing **momentum, seasonality, carry/basis, metals relative-value, COT/hedging-pressure, and
skewness**:

- **Commodities is the best asset class in the arc** — the signals are **genuinely two-sided** (no secular
  drift to contaminate the short leg) and **seasonality is OOS-stable**. That is a real qualitative win
  over every FX/index/crypto family (all one-sided beta).
- **But every signal is weak** (Sharpe ≤0.30 standalone, ≤0.34 combined), and even the decorrelated
  combination **does not beat the ~50 % incumbent**. The literature's strong Sharpes come from ~24–30
  commodities, monthly, low/zero cost; at **10 FTMO CFDs with real costs**, they shrink below the bar.
- **The one signal that would have beaten it (carry) was a hindsight snapshot** (proven NO-GO).

**Keeper:** seasonality (the single OOS-stable signal in the whole arc) — worth holding in the toolkit,
but not an FTMO upgrade on its own. **Incumbent remains ORB-30min + floor.**

**Reusable assets built:** `outputs/commod_daily.parquet` (10 commodities), `outputs/cot/*.parquet`
(18 years CFTC COT, 9 commodities — a genuinely useful free dataset for future fundamental work).

### Research-log entry
*Commodities (FTMO) — best asset class (two-sided, OOS-stable signals) but NO individual or combined signal
beats ~50 %. Carry = hindsight (NO-GO). Metals relative-value = not cointegrated, multi-year half-life
(NO). COT/hedging-pressure = weak/decayed (best TS variant 0.26). Skewness = 0.06. Combined two-sided book
Sharpe 0.34 → p(pass) ~42 %, ties-to-below incumbent. Seasonality (0.30) the one keeper. No FTMO upgrade.*

### Sources
- Gold/silver ratio MR; Kang-Rouwenhorst-Tang (hedging pressure); CFTC COT (data); Fernandez-Perez et al. 2018 (skewness); Boons-Prado 2019 (basis-momentum, untested — needs term structure).
