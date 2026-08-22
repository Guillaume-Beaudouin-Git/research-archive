# Mechanism-justified instrument/time selectivity — session_basic_trend (5 candidates)
*2026-06, MEASURED. Profile lens: skew + decorrelation + **additionality to TSMOM**. GATE-0 FTMO-tradeable. Daily only (OOM-safe); #3 (intraday forex) characterized. Nothing frozen/merged.*

## TL;DR
**One genuinely-additional brick: commodity seasonality** — OOS Sharpe **0.33** (confirms the archive keeper), **decorrelated from TSMOM (0.10) and equity (0.03)**, FTMO-tradeable. It's a *return* diversifier (caveat: negative daily-skew −0.83, not a convexity brick). The trend-selectivity candidates (#1/#2) confirm trend works best on crypto (Sharpe 1.12, skew +0.68) but are **redundant with TSMOM (corr ~0.5)** → engine-tuning, not new bricks. Day-of-week (#4) = mining (no mechanism). Session-forex (#3) = intraday cost/delay-fragile.

## #1/#2 — Trend by FTMO asset class (where does trend work? + additionality)

| Class | trend Sharpe | daily-skew | corr→equity | **corr→TSMOM** |
|---|---:|---:|---:|---:|
| Indices (US500/100/GER40) | +0.45 | −0.67 | +0.05 | **+0.48** |
| Commodities (FTMO set) | +0.52 | −0.02 | −0.08 | **+0.49** |
| **Crypto (BTC/ETH only)** | **+1.12** | **+0.68** | −0.08 | **+0.52** |

**Mechanism confirmed:** trend is strongest where markets are least efficient — **crypto (Sharpe 1.12, positive skew)** ≫ commodities ≫ efficient indices. **But all three are corr ~0.5 with TSMOM → REDUNDANT.** TSMOM already trades these as trend; per-class/crypto trend is a *subset*, not a new sleeve. **Implication = engine tuning, not a brick: TSMOM should overweight crypto/commodities and de-emphasize efficient indices.** (Recorded as a TSMOM-improvement lesson, not a portfolio brick.)

## #5 — Commodity seasonality (the archive keeper, operationalized) ★
Train 2006–15 → month-of-year seasonal sign per commodity (mechanism: real production/demand cycles — natgas winter, gasoline summer, ag harvest, etc.), applied **OOS 2016–26** (no mining):

| | Sharpe | daily-skew | corr→equity | **corr→TSMOM** |
|---|---:|---:|---:|---:|
| OOS 2016–26 | **+0.33** | **−0.83** | +0.03 | **+0.10** |
| Train 06–15 (ref, in-sample) | +1.84 | — | — | — |

**This is the genuine find of the session: the only candidate that is BOTH decorrelated from TSMOM (0.10) AND OOS-stable (0.33, matching the archive).** Unlike the trend bricks (redundant, corr ~0.5) and MACD (near-zero return), commodity seasonality adds a **decorrelated RETURN source** — calendar-driven, not trend, hence the low correlation. **Caveats:** (a) **negative daily-skew (−0.83)** → a return diversifier, NOT a convexity/skew+ brick (it can take a large adverse seasonal day); (b) IS→OOS decay (1.84→0.33) → modest, possibly decaying further as known; (c) held weeks → swap (L33) erodes the 0.33 net (same engine-cost caveat). Value = **decorrelation + modest positive return**, FTMO-tradeable.

## #4 — Day-of-week (mechanism-FIRST discipline)
Strongest across all instruments: **BTC Monday, t = +3.29 (+50 bps)** — but that is the **max over ~60 instrument×day combos** (expected under the null at that trial count) with **no pre-specified mechanism**. Per the rule (mechanism BEFORE the cut, not after), this is **mining → not pursued.** (BTC-weekend-catch-up is a *plausible* mechanism worth a separate pre-registered test, but not claimed here.)

## #3 — Session-of-day forex
Intraday by construction → hits the **cost + delay+1** wall that killed the ORB family. Not tested in this daily pass; **characterized as cost/delay-fragile** (would need the full intraday-cost + delay treatment, prior = ORB fate). Not the skew+ profile we seek.

## Portfolio picture (candidates, NOT merged — all pending the TSMOM crypto-swap validation)
- **Engine:** TSMOM (multi-asset two-sided trend) — *net return pending crypto-swap measurement; validate before anything is built on it.*
- **Shape diversifier:** MACD — corr 0.08, near-free, pulls cumulative maxDD under the floor (does NOT cover the daily cap).
- **Return diversifier (NEW):** Commodity seasonality — corr 0.10, OOS Sharpe 0.33, decorrelated calendar return; negative-skew caveat.
- Both diversifiers are **decorrelated from the engine AND from each other** (trend-shape vs calendar-return) → genuinely complementary *if* the engine survives the swap test.

**Lesson candidates (named, not numbered):**
- **"crypto/commodity trend is redundant with multi-asset TSMOM (corr ~0.5)"** — selectivity-by-class is *engine tuning* (overweight crypto, where trend Sharpe is 1.12 with skew+), not a new sleeve.
- **"commodity seasonality is the genuinely additional decorrelated brick (corr 0.10, OOS Sharpe 0.33)"** — a calendar RETURN diversifier (negative-skew, so not convexity), the only OOS-stable signal in the archive, FTMO-tradeable.
- **"day-of-week without a pre-specified mechanism is mining"** — BTC-Monday t 3.29 is the expected max over 60 combos; reject absent a mechanism stated first.
- **"crypto is the strongest trend sub-component (Sharpe 1.12, skew+)"** — least-efficient class → argues for crypto overweight inside the engine.

*Reproduce: `mechanism_selectivity.py`. Daily, GATE-0-clean. Stayed in session_basic_trend/; nothing frozen/merged.*
