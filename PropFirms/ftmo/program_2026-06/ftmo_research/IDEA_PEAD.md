# Idea PEAD — Post-Earnings-Announcement Drift — ITERATED FINDINGS
*2026-06-03. Genuine iteration (event study → deployable basket → regime-gated → vol-targeted) before any verdict, per user instruction "don't kill on the first inconclusive attempt." Data: 71 US large-caps adjusted daily 2005–2026 + 6,687 yfinance earnings events (dates + Surprise%).*

## Headline: PEAD is the strongest REAL edge found in the entire program — and the only one that is genuine market-adjusted ALPHA, not beta. But FTMO's structure imprisons it. NOT a signal kill; a container incompatibility.

## Iteration 1 — event study (does PEAD exist?) → YES, significantly
Market-adjusted CAR (vs SPY), entering the trading day AFTER the announcement (causal):

| Horizon | surprise>0 meanCAR | t | surprise<0 | top-quintile CAR |
|---|---:|---:|---:|---:|
| 20d | +0.23% | +2.74 | +0.11% | +0.52% |
| 40d | **+0.52%** | **+4.42** | +0.27% | +1.23% |
| 60d | **+0.77%** | **+5.02** | +0.65% | +1.98% |

Positive-surprise drift is **significant** and **concentrates in the top surprise quintile** (+1.2–2.0%), stronger when the announcement reaction is also positive. **But the long-short spread (pos−neg) is insignificant** (t<0.9) — negative-surprise names *also* drift up (mega-cap bull bias) → no clean short side.

## Iteration 2 — deployable long-only basket (top-quintile surprises, hold 40–60d)
| Config | basket abs (Sharpe) | **alpha vs SPY (Sharpe / t)** | maxDD |
|---|---|---|---|
| q0.8, react+, H60 | +23.6%/yr (0.98) | **+11.4%/yr (0.96 / t 4.46)** | basket −49% / **alpha −24%** |
| q0.9, react+, H40 | +24.4%/yr (0.80) | +12.2%/yr (0.58 / t 2.70) | −47% |

**The alpha is real and significant (Sharpe ~0.96, t=4.46 vs SPY)** — the cleanest result in the project. SPY buy-&-hold is Sharpe 0.64; the PEAD selection genuinely beats the market.

## Iteration 3 — regime-gate (SPY>200MA) + vol-target (compliant attempt to survive the floor)
| Version | maxDD | best FTMO p(funded) / bust |
|---|---|---|
| ungated basket | −59% | 25–27% / 73% |
| SPY-200MA gated | −41% | 28% / 72% |
| gated + vol-target | — | **32% / 68%** (L=5) |

## Why it fails FTMO (the structural trap — identical to stat-arb/5B)
1. **The alpha is only accessible market-neutral** (long top-surprise stocks **/ short the index**). That is "opposing positions on correlated instruments" = **FTMO hedging violation**. The clean alpha (Sharpe 0.96, maxDD −24%) cannot be traded compliantly.
2. **The compliant long-only form carries equity beta** → maxDD −41% to −59% → **breaches the −10% static floor**, even after a regime gate + vol-targeting. The PEAD alpha (+7–11%/yr) is too small relative to the wrapped beta-volatility to reliably reach +10% before −10%. FTMO first-passage caps at **~32% funded / 68% bust**.

## Verdict (after genuine iteration): ❌ KILL *for FTMO* — but ✅ a REAL alpha for a hedging-allowed / no-static-floor account.
- **Not a signal failure.** PEAD is the best, most significant, genuinely-alpha edge found (market-adjusted Sharpe ~0.96, t=4.46). It is **decisively imprisoned by FTMO's two binding constraints**: the no-hedging rule (blocks isolating the neutral alpha) and the −10% static floor (can't tolerate the compliant long-only beta).
- **Deployable elsewhere:** long-top-surprise / short-SPY (market-neutral PEAD) in a normal margin account or a hedging-allowed venue would harvest the +11%/yr, Sharpe ~0.96, −24% maxDD alpha. Logged as a real strategy for a non-FTMO container.

## The sharpened meta-conclusion (this is the valuable part)
Two ideas now have **genuine, cost/delay-robust edges** — PEAD (alpha Sharpe ~0.96) and Gold/Silver rotation (Sharpe 0.77). **Both are killed for FTMO not by absence of edge but by the container:** FTMO's **no-hedging rule** forbids isolating market-neutral alpha, and its **−10% static floor** can't tolerate the volatility/beta of the compliant single-leg forms. *Real retail edges exist; FTMO's constraints are structurally incompatible with harvesting them.* That is a sharper and more useful conclusion than "no edge exists."

*Reproduce: `pead/pead_engine.py` (event study), `pead/pead_deploy.py` (basket + first-passage); data `panels/earnings_dates.csv`.*
