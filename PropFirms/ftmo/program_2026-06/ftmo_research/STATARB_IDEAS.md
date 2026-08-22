# Stat-arb on FTMO — 10 candidate strategies for review
*Clean slate. 5 asset classes × 2 ideas. Each designed to be FTMO-compliant and barrier-aware. You pick where we start.*

## The 3 constraints that shape every idea (read first)

1. **No two-leg market-neutral pairs (FTMO hedging rule).** FTMO forbids "hedging or holding opposing positions on the same or highly correlated instruments." So the textbook *long A / short correlated-B* trade is a flag risk. **Every idea below is expressed single-leg**, via one of three compliant patterns:
   - **(P1) Trade a symbol that IS the spread** — an FX cross (AUDNZD, EURGBP) is a pre-packaged two-currency spread but a *single* FTMO symbol → fully compliant.
   - **(P2) Signal-only, trade the dislocated leg** — use the pair/ratio z-score as the *signal*, then take a single outright position in the cheap (or rich) leg toward convergence.
   - **(P3) Single-instrument reversion** — model one instrument's deviation from its own stochastic fair value (Ornstein-Uhlenbeck / Kalman) and fade it. No second leg at all.
2. **Cost decides (turnover × CFD spread+swap).** Stat-arb is high-turnover and small-edge; FTMO instruments are CFDs (floating spread, overnight swap, 0 commission on indices). Every idea must be tested at *measured* cost — a thin reversion edge flips sign under realistic spread. This is the make-or-break test for all of them.
3. **Negative skew vs the 5% daily / 10% static barrier.** Reversion = many small wins + rare large loss when the spread keeps diverging. That rare blow-out is exactly what breaches the daily cap. Every idea needs a **hard spread/time stop and vol-targeted sizing** so a non-convergence can't take >5% in a day.

**Why stat-arb is still worth a fresh look for FTMO:** high win-rate + smooth equity suits hitting +10%/+5% steadily, and a *fast* single-leg reversion carries little persistent directional risk (kind to the 10% total floor). The edge is real *if* cost and the blow-out tail are engineered around. Leverage: FX 1:100 (best), indices/commodities lower, crypto lowest.

---

## ASSET 1 — FX crosses *(best capital efficiency: 1:100, and crosses are pre-packaged spreads)*

**1A — AUD/NZD mean-reversion (the cleanest FTMO stat-arb).**
The AUDNZD cross *is* the AUD-vs-NZD spread, traded as one compliant symbol (P1). Both are commodity/Antipodean currencies with tight macro linkage (RBA↔RBNZ policy, China demand, dairy/metals terms-of-trade) → the cross oscillates in a band.
- *Signal:* z-score of AUDNZD vs a rolling/Kalman fair value; Ornstein-Uhlenbeck half-life for entry/exit timing; fade |z|>2, exit at z→0 or half-life.
- *Key risk to test:* rate-divergence regimes (RBA/RBNZ decouple) → the cross trends → the negative-skew loss. Stop on z>3 or N-day non-convergence.
- *Data:* AUDNZD M1/M5 (have AUDUSD, NZDUSD; can synth or fetch the cross).

**1B — EUR-bloc cross OU reversion (EUR/GBP, or NOK/SEK Scandi).**
Another single-symbol spread (P1). EURGBP is range-prone (deep UK↔EU trade/financial linkage); NOK/SEK links two small open European economies (oil-tilted NOK). 
- *Signal:* OU/Kalman residual on the single cross; fade extremes; regime filter to stand aside in trending (Brexit-type) episodes.
- *Key risk:* event-driven repricing (policy divergence, oil shock for NOK) and wider exotic-cross spreads (cost). 
- *Data:* EURGBP M1 (have it); NOK/SEK would need a fetch.

---

## ASSET 2 — Equity indices *(cash CFD, ~1:20–30, ultra-liquid, tight spread)*

**2A — SPX↔NDX ratio, traded single-leg (RV-informed directional).**
You can't hold US500 long + US100 short (highly correlated → hedging flag). Instead use the **NDX/SPX ratio z-score as the signal** and take ONE outright position in the dislocated index (P2): when NDX is statistically rich vs SPX, short US100 outright (or long US500) betting on convergence.
- *Signal:* beta-adjusted log-ratio z-score; enter the leg that should converge; this carries some market beta (honest — not neutral).
- *Key risk:* a tech-led trend (2023–24) keeps the ratio stretched → the convergence bet bleeds. Needs a trend/regime gate + stop.
- *Data:* US500 + US100 (have clean intraday).

**2B — Single-index intraday OU reversion (US500 around a stochastic anchor).**
Pure single-instrument stat reversion (P3): model intraday deviation of US500 from a Kalman/VWAP fair value, fade stretched moves back to anchor. No second leg.
- *Signal:* standardized deviation from anchor; fade |z|>2; time-boxed exit; only on range/low-trend days.
- *Key risk:* trend days (the classic MR killer) + **turnover × index CFD spread (L33)** — this is the one most exposed to the cost test.
- *Data:* US500 1-min (have it).

---

## ASSET 3 — Commodities *(metals + energy; watch overnight swap = L33)*

**3A — Gold/Silver ratio, single-leg.**
The XAU/XAG ratio oscillates in wide bands (it spiked to ~125 in 2020, reverts toward 60–90). Use the **ratio z-score as signal**, trade the dislocated metal outright (P2): ratio very high → silver cheap → long XAGUSD; ratio very low → long XAUUSD.
- *Key risk:* the ratio *trends* hard in crises (the negative-skew); silver's higher vol needs smaller sizing for the 5% cap.
- *Data:* XAUUSD, XAGUSD (FTMO offers both; need to fetch).

**3B — WTI/Brent convergence (USOIL vs UKOIL), single-leg.**
FTMO offers both crude grades. The WTI–Brent differential mean-reverts (quality/transport/storage arb, oscillates ~$2–8). Two-leg would be the natural trade but = opposing correlated positions (**hedging-flag risk → trade single-leg**, the diverged grade toward convergence).
- *Key risk:* structural regime shifts in the differential (pipeline/export changes) + **oil CFD overnight swap** (L33) if held.
- *Data:* USOIL + UKOIL (need to fetch; verify both symbols on the account).

---

## ASSET 4 — Crypto *(FTMO: BTC/ETH/LTC/XRP/ADA/DOT/DOGE; or Propr — vol is the enemy of the 5% daily cap)*

**4A — ETH/BTC ratio, single-leg.**
The most liquid crypto relative-value. Use the **ETH/BTC log-ratio z-score as signal**, trade ETH outright toward convergence (P2): ETH cheap vs BTC → long ETH; rich → flat/short.
- *Key risk:* alt-season *trends* the ratio (negative-skew), and **crypto vol makes the 5% daily breach trivial** → hard vol-targeting + small size mandatory. Crypto CFD spread+funding (L33) is large.
- *Data:* BTC, ETH (fetch; have ETH/SOL/ADA from before).

**4B — Single-coin OU reversion / dislocated-alt (P3 or P2).**
Either pure BTC intraday reversion around a stochastic fair value (P3), or rank the alts vs their BTC-beta-implied level and long the single most-dislocated laggard (P2). One position at a time.
- *Key risk:* crypto fat tails + funding cost; reversion is weakest exactly when vol is highest.
- *Data:* BTC + top alts.

---

## ASSET 5 — US single-name stocks *(only ~23 names on FTMO; lower leverage; overnight swap; earnings gaps)*

**5A — Same-sector RV, single-leg (KO/PEP, V/MA, XOM/CVX).**
Pick the tightest cointegrated same-sector duo in the 23-name universe; **z-score as signal, trade only the dislocated name outright** (P2) toward convergence. Never hold both (correlated → hedging flag).
- *Key risk:* idiosyncratic news/earnings = the large-loss tail → **hard rule: no positions across earnings dates**; hard stops. Sizing on $10k with no fractional shares is clunky.
- *Data:* the FTMO 23 US stock CFDs (fetch; verify the exact list).

**5B — Cross-sectional short-horizon reversion (single-leg rotation over the 23 names).**
Rank the 23 names by 1–5-day return; the extreme short-term loser tends to bounce. **Hold ONE name at a time** (the most-extreme laggard long), rotating — compliant (no opposing legs), naturally diversified over time.
- *Key risk:* turnover × stock CFD spread+swap (L33); regime (reversion fails in strong-trend/momentum markets); thin 23-name breadth.
- *Data:* daily + intraday for the 23 names.

---

## My read on FTMO-fit (to help you choose — your call)

| # | Idea | Compliance | Cost risk | Leverage | Barrier-fit | Data ready | Overall |
|---|---|---|---|---|---|---|---|
| **1A** | **AUD/NZD cross reversion** | ✅ single symbol | med | ✅ 1:100 | good | ~ | **★ top pick** |
| 1B | EUR-bloc cross OU | ✅ single symbol | med | ✅ 1:100 | good | partial | ★ strong |
| 2A | SPX↔NDX single-leg | ✅ (1 leg) | low | med | med (beta) | ✅ | ★ strong |
| 2B | US500 intraday OU | ✅ single | **high (L33)** | med | med (trend) | ✅ | test cost first |
| 3A | Gold/Silver ratio | ✅ (1 leg) | med | med | med | fetch | solid |
| 3B | WTI/Brent | ⚠ keep 1-leg | **high (swap)** | med | med | fetch | solid |
| 4A | ETH/BTC ratio | ✅ (1 leg) | **high** | low | **hard (vol)** | fetch | high-risk |
| 4B | Crypto OU / alt | ✅ single | **high** | low | **hard (vol)** | partial | high-risk |
| 5A | Sector pair single-leg | ✅ (1 leg) | med-high | low | med (gaps) | fetch | niche |
| 5B | 23-name x-sec reversion | ✅ rotation | high | low | med | fetch | niche |

**If you want my one-line steer:** the **FX crosses (1A/1B)** are the structurally cleanest FTMO stat-arb — the cross is a single compliant symbol, 1:100 leverage gives the capital efficiency a small reversion edge needs, and the relationship is genuinely cointegrated. **2A (SPX↔NDX)** is the best-data, lowest-cost place to prototype the single-leg-RV machinery fast. The crypto ideas have the richest edge but the vol fights the 5% daily cap hardest.

**Tell me which to start with** (or which 2–3 to prototype in parallel) and I'll build the cointegration/OU test rig + a measured-cost FTMO first-passage sim for it.

---
*Sources: [FTMO Forbidden Practices](https://ftmo.com/en/forbidden-trading-practices/), [FTMO instruments/strategies FAQ](https://ftmo.com/en/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/), [FTMO Symbols](https://ftmo.com/en/symbols/).*
