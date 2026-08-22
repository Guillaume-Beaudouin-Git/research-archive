# Basic discretionary trend setups — PROFILE study (session_basic_trend)
*2026-06, MEASURED. Goal: **skew at the holding (per-trade) horizon + decorrelation**, NOT standalone Sharpe. GATE-0 first. Daily only (OOM-safe). Scope: session_basic_trend; nothing frozen/merged.*

## GATE-0 — FTMO-tradeable ✅
Universe used: **US500, US100, GER40** (FTMO index CFDs), **BTC, ETH** (FTMO crypto CFDs), **gold & silver** (GLD/SLV as backtest proxies → deploy on FTMO **XAUUSD/XAGUSD CFDs**). All in the FTMO universe. (No bonds/ETF-as-such/options. USO/oil dropped — broken proxy.) Unlike Long-vol (VXX, perso-only), **trend-on-these-instruments is FTMO-deployable.**

## TL;DR — thesis confirmed
**The 4 naked trend setups all have the target profile: strongly POSITIVE per-trade skew (+4 to +26) AND decorrelation from long-equity (corr −0.07 to −0.22)** — exactly the convexity + decorrelation we want for the survival book, *even though their standalone Sharpe is modest (0.2–0.55)*. **Pullback-in-uptrend is the opposite — negative skew (−5.4) + positive equity correlation (+0.27)** = a convexity-SELLER / disguised dip-buy → **wrong profile, rejected.** **Decisive test settles it (see below): only MACD survives as an additional brick** — Donchian/EMA/Momentum are redundant with TSMOM (corr 0.55), but **MACD (corr 0.08 to TSMOM) is genuinely additional, near-free (net −0.07%/mo), and pulls the combined maxDD from −13.7% to −9.1% — under the −10% floor.** It's a diversification/shape brick, not a crash-hedge or a return engine.

## Profile per setup (skew at HOLDING horizon; Sharpe secondary)

| Setup | trades | med-hold | **trade-skew** | win | meanR | daily Sharpe | corr→equity | profile? |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| EMA 50/200 | 190 | 91d | **+9.7** | 33% | +22% | 0.44 | −0.07 | ✅ skew+ / decorrelated |
| Donchian 55 | 434 | 61d | **+6.9** | 38% | +3.4% | 0.21 | −0.20 | ✅ skew+ / **decorrelated (low turnover)** |
| Momentum MA200 | 936 | 3d | **+25.6** | 15% | +5.4% | 0.55 | −0.22 | ✅ skew+ / decorrelated (but high turnover) |
| MACD cross | 3010 | 9d | **+4.2** | 33% | +0.4% | 0.33 | −0.18 | ✅ skew+ / **decorrelated AND distinct (fast trend)** |
| Pullback-in-uptrend | 1692 | 1d | **−5.4** | 48% | +0.3% | 0.26 | +0.27 | ❌ **neg skew + equity-correlated = convexity-seller, WRONG profile** |

*Per-trade skew (entry→exit, the holding horizon) is the right metric: trend setups win ~15–38% of trades but the winners run huge → strongly positive skew. The 48%-win pullback is the tell of the wrong profile — high hit-rate, negative skew (buy-the-dip = sell convexity).*

## Correlation structure (daily) — which are complementary bricks

| | EMA | Donch | Mom | MACD | Pullbk | Equity |
|---|---:|---:|---:|---:|---:|---:|
| EMA 50/200 | 1.00 | 0.57 | 0.76 | −0.18 | 0.49 | −0.07 |
| Donchian 55 | 0.57 | 1.00 | 0.76 | 0.01 | 0.23 | −0.20 |
| Momentum MA200 | 0.76 | 0.76 | 1.00 | 0.05 | 0.40 | −0.22 |
| **MACD cross** | −0.18 | 0.01 | 0.05 | 1.00 | −0.41 | −0.18 |
| Pullback | 0.49 | 0.23 | 0.40 | −0.41 | 1.00 | +0.27 |

- **EMA / Donchian / Momentum are one slow-trend factor** (mutually 0.57–0.76) → redundant; pick ONE representative.
- **MACD is a genuinely DISTINCT brick** (corr ~0 with the slow trio, −0.18 with equity, −0.41 with pullback) — a *faster* trend signal (9-day hold) → it adds a decorrelated dimension, not a duplicate.

## DECISIVE TEST — carry vs DD-avoided + additionality to TSMOM (the verdict)

A negative-carry convexity brick is *insurance*: keep it only if **additional to the TSMOM engine** AND **DD-avoided > carry-paid**. Measured on the common window (2000–2026, n=7971):

**(1) Additionality — corr to TSMOM:**
- **Donchian ↔ TSMOM = 0.55 → REDUNDANT** (TSMOM is already slow two-sided trend; it *contains* the Donchian factor).
- **MACD ↔ TSMOM = 0.08 → genuinely ADDITIONAL** (fast trend, distinct frequency). (Donchian↔MACD = 0.00.)

**(2) Overlay on TSMOM, maxDD / worst-day (brick vol-matched):**

| Portfolio | maxDD | worst-day |
|---|---:|---:|
| TSMOM alone | −13.7% | −5.9% |
| +15% Donchian | −13.5% | −5.2% |
| +30% Donchian | −13.5% | −4.6% |
| **+15% MACD** | **−10.5%** | −5.1% |
| **+30% MACD** | **−9.1% (UNDER floor)** | −4.3% |

On TSMOM's worst-20 days: TSMOM −3.11%, Donchian −2.18% (also down, no help), **MACD −0.95% (cushions** — less-down, though it doesn't profit → diversifier, not crash-hedge).

**(3) Carry (transparent est.: measured equity swap ~4.46 bps/trading-day, ~0.5× notional, 21d/mo):**
- Donchian: gross +0.24%/mo − swap 0.47% = **net −0.23%/mo**.
- MACD: gross +0.40%/mo − swap 0.47% = **net −0.07%/mo (near-free)**.

**(4) Decision:**
- **Donchian → DROP.** Redundant with TSMOM (corr 0.55), avoids ~no DD in overlay (−13.7→−13.5), and pays −0.23%/mo carry. Negative on both criteria.
- **MACD → KEEP** as a diversifying convexity brick. **DD-avoided (maxDD −13.7→−9.1 at 30%, *under the −10% floor*; worst-day −5.9→−4.3) >> carry-paid (~−0.07%/mo ≈ −0.1 to −0.4% over a 2–6mo challenge).** It is additional (corr 0.08) and near-free.

## Portfolio-brick verdict (revised by the decisive test)
- **KEEP: MACD cross (fast trend)** — the one genuinely-additional, near-free, FTMO-tradeable convexity brick: corr 0.08 to TSMOM, pulls the combined maxDD **under the −10% floor** at ~zero carry. Its mechanism is **decorrelation/diversification** (lowers combined vol & cushions TSMOM's worst days), **not crash-hedging** (it's still trend → it doesn't *profit* in the crash; a true crash hedge = long-vol = perso-only).
- **DROP: Donchian / EMA / Momentum** — redundant with TSMOM (the slow-trend factor TSMOM already carries; Donchian↔TSMOM 0.55).
- **REJECT: Pullback-in-uptrend** — negative skew + equity-correlated (convexity seller).

**Honest limit:** MACD is near-zero NET return → a *shape/diversification* brick, not a return engine; and it does **not** eliminate the single-day correlated-crash tail (both it and TSMOM are trend → both down that day, just MACD less so). The combined maxDD under the floor is largely the standard decorrelation-lowers-vol effect plus worst-day cushioning — real and useful for the L7 survival objective, but it's risk-shaping, not alpha.

## Honest caveat (profile ≠ free return)
These bricks have the **right shape** (skew+, decorrelated) but **modest-to-zero net-of-cost return**: they HOLD positions for weeks → they pay the held-notional **swap** (L33), which the TSMOM work showed erodes the trend edge to ~0 net. So, net of FTMO swap, these are **negative-carry convexity bricks** — their portfolio value is **shape (convexity + decorrelation), not return**, much like long-vol (VXX) — *except these are FTMO-tradeable, where VXX was perso-only.* Whether the convexity/decorrelation is worth the carry drag is the portfolio-construction (L7) question, to be settled when sizing the combined book — not a per-brick verdict.

**Lesson candidates (named, not numbered):**
- **"naked trend = skew+ profile even when it doesn't win standalone"** — confirmed: EMA/Donchian/Momentum/MACD all carry +4 to +26 trade-skew at modest Sharpe. The profile is the deliverable, not the P&L.
- **"buy-the-dip/pullback = negative skew = convexity seller"** — the 48%-win pullback is equity-correlated and negative-skew → the wrong profile, the mirror of trend.
- **"MACD is a decorrelated fast-trend brick"** — distinct from the slow EMA/Donchian/Momentum cluster (corr ~0) → a genuine second trend dimension.
- **"trend-on-FTMO-instruments = the FTMO-tradeable convexity brick"** — where long-vol (VXX) failed GATE-0 (perso-only), FTMO-instrument trend provides skew+/decorrelation that IS tradeable — at the price of held-notional swap carry.

*Reproduce: `trend_profile.py`. Daily, GATE-0-clean. Nothing frozen/merged; stayed in session_basic_trend/.*
