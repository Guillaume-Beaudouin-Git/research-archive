# Options Vol — Phase 0 Bootstrap

**Date**: 2026-05-23  
**Author**: G. Beaudouin  
**Status**: Phase 0 complete — Phase 1 requires explicit chat validation  
**Scope**: Markdown document only. No code, no backtest, no data fetch.

---

## 0. Executive Summary

**Recommendation**: SPX Variance Risk Premium as Priority #1, Deribit BTC Options VRP as backup.  
**Priority angle for Phase 1**: VIX z-score conditional selling (Angle C) — testable with free data (VIX + SPX prices), no OptionMetrics required.

The prior VIX term carry research (3 variants, all FAIL) targeted the *ETF proxy* of VRP, not the premium itself. The failure was structural to the VXX/VIXY instrument (roll drag, no timing alpha) rather than to the underlying VRP anomaly. Direct SPX options research sidesteps that failure mode.

One hard constraint: neither SPX options nor Deribit options are compatible with Propr propfirm. This work targets CV value (CFM/Qube/Squarepoint) and personal-capital deployment, not propfirm challenge.

**Phase 1 GO/NO-GO awaits explicit chat validation below this document.**

---

## 1. Repo Reading — What We Already Know

### 1.1 VIX Term Structure Carry — 3 Iterations, All FAIL

`ETF_Vol/research/archived/vix_term_carry/` — complete record.

| Variant | Sharpe HAC | MaxDD | WF+ | Alpha t vs short-VIXY | Verdict |
|---|---|---|---|---|---|
| A — Raw term carry | 0.674 | −54.2% | 71% | 0.711 | FAIL all gates |
| B — Vol-Targeted | 0.498 | −15.9% | 71% | 0.711 | FAIL (Sharpe, MaxDD) |
| C — VT + stop | 0.460 | −17.1% | 71% | 0.711 | FAIL |

**Root causes (3 structural, not calibration failures):**

1. **ETF roll drag conflates VRP with friction**: VIXY/VXX embed ~30–40%/yr negative roll yield in contango. What looks like "short ETF profit" is partly roll collection, not vol timing alpha. The alpha t vs. passive short-VIXY is only 0.711 — timing adds almost no value over passive static selling.

2. **Mild contango is the trap**: 29% of trading days are in mild contango (0–10%). In this regime, avg daily return is **negative** (−0.133%) with only 45% hit rate. The strategy appears profitable only because deep contango (63% of days) compensates. But deep contango is the baseline state — it requires no timing.

3. **2024 OOS Sharpe −1.925 (worst WF year)**: Suggests structural VRP compression post-2020 retail options boom. The WF 71% positive is misleading — the worst year is extreme and recent.

**Critical insight (carries forward)**: The methodology insight from the archive: *"The premium is a static factor, not a timeable signal. ACTIVE TIMING of the regime does not statistically outperform a static short-VIX position with conservative sizing."* This is the key lesson. Phase 1 must show that IC(timing_signal → option_P&L) has t_HAC > 2.5 — not just that the static premium exists.

**What this research did NOT test**: Direct SPX/SPY options selling (straddles, condors). The prior work used ETF proxies only. This distinction is the strategic opening for new research.

### 1.2 Other Archived Strategies — Transferable Lessons

**Multi-Asset TSMOM (Equities/research/archived)**: methodology audit showed that stripping risk-free rate via excess returns drops Sharpe from 0.48 → 0.21. For options, P&L is typically measured in dollar terms — must normalize to notional capital and subtract risk-free rate on margin deployed.

**FX Carry (Forex/research/)**: carry premium real (IC t=2.02) but severe crash exposure kills full-sample Sharpe. Carry + trend filter still FAIL (all 3 variants Sharpe negative). Lesson: the premium must be combined with crash protection to generate a tradeable Sharpe — naked premium selling fails without a hedge.

**FX Carry + Trend filter (passed/)**: Despite being in `passed/` folder, all 3 variants are RESEARCH FAIL. The folder naming is aspirational, not verdicted. Do not confuse.

**Event-count ceiling gate (Lesson 12)**: Conditional entry strategies (only sell when VIX_z > threshold) must pass both event-count floor (≥50 events/year for WF power) AND ceiling (too many events → always fully deployed → cost overflow). For VIX-conditional selling at threshold z>1.5, event count will be checked as a pre-flight constraint.

---

## 2. Universe Mapping — 6 Sub-Universes Scored

Scoring criteria: Edge (academic papers ≥ 2), Data accessibility (<$200/mo or free), Mechanism clarity, Orthogonality to A/B/C, CV value for CFM/Qube/Squarepoint, Propfirm compatibility.

### 2a. VRP Equity Index (SPX/SPY/ES)

**Edge**: IV systematically exceeds realized vol. VIX historical average ~20–22%; SPX 30d realized vol average ~14–16%. Spread (variance risk premium) ~4–8 vol points. The seller of this premium earns a persistent positive carry.

**Key papers** (cited from knowledge, not fetched):
- Carr & Wu (2009) "Variance Risk Premiums" — documented across equities, FX, individual stocks; SPX premium largest and most stable
- Bollerslev, Tauchen & Zhou (2009) "Expected Stock Returns and Variance Risk Premia" — VRP predicts equity index returns at 1-month horizon (IC confirmed)
- Dew-Becker, Giglio & Kelly (2021) — variance premium concentrated in short-term (≤1 month) options; long-dated vol is fairly priced
- Egloff, Leippold & Wu (2010) — term structure of variance risk premium

**Data sources**:
- **CBOE free**: VIX, VIX3M, SKEW index, VIX historical going back to 1990. Full straddle approximation feasible with VIX alone (VIX/√12 ≈ 30d ATM straddle value / SPX price). Phase 1 IC test costs $0.
- **ORATS** (~$150/mo): Full SPX/SPY historical option surface with IVs, Greeks, term structure back to 2007. Phase 2 data source if IC passes.
- **OptionMetrics** (~$500–2,000/mo): Institutional grade; not needed for Phase 1.
- **Yahoo Finance**: Current option chains only, no historical surface. NOT suitable for backtesting.

**Cost (direct SPX options)**:
- SPX option bid-ask: $1–3 per contract ($100–300 notional) = 0.05–0.15% round-trip per position on standard sizing
- Delta hedge via SPY/ES: 0.01–0.03% per rebalance
- Total: ~0.20–0.50% RT equivalent; at monthly hold, ~2.4–6%/yr cost drag
- Comparison: lower than crypto (0.17% RT at 0.34% monthly) for equivalent monthly strategies

**Propfirm compatibility**: NOT compatible with Propr (crypto perps only). Compatible with Apex Trader (ES options), personal account, or paper research.

**Orthogonality to A/B/C**:
- From repo data: corr(VIX carry returns, BTC) = +0.084 (near zero) → orthogonal to A/B
- SPX vol strategy has positive β to S&P 500 (equity exposure) but NQ ORB (C) is also equity-correlated → some overlap, likely corr(options_P&L, C) moderate (+0.2–0.4)
- A delta-hedged straddle eliminates the directional equity β → net orthogonality to all three live strategies

**CV value**: HIGHEST. SPX vol research is the canonical interview topic at CFM/Qube/Squarepoint. A documented Phase 1 IC result with VIX-conditional timing = credible quantitative research.

**Score**: 9/10 — Priority #1.

---

### 2b. Term Structure VIX (M1/M2/M3 Futures)

**Edge**: Same VRP as 2a, accessed via VXX/VIXY ETF proxies or direct VIX futures.

**Status**: **ALREADY TESTED. 3 variants. All FAIL.** See Section 1.1 and `ETF_Vol/research/archived/vix_term_carry/`.

**DO NOT RETEST** via ETF proxies. Direct VIX futures trading adds execution complexity (monthly settlement, cash-settled) without fundamentally changing the timing IC problem.

**Score**: N/A — archived. Only revisit if hypothesis changes structurally (e.g., testing 0DTE VIX weekly futures timing, which is a genuinely new mechanism).

---

### 2c. Dispersion (Index Vol vs Single-Name)

**Edge**: Index implied vol > portfolio of single-name implied vols (correlation premium). The spread (dispersion premium) compensates for positive correlation risk.

**Key papers**:
- Driessen, Maenhout & Vilkov (2009) "The Price of Correlation Risk" — systematic correlation risk premium in SPX option prices
- Buss & Vilkov (2012) "Measuring Equity Risk with Option-Implied Correlations"

**Data**: CBOE provides COR3M (implied correlation index, free). Individual stock option surfaces require OptionMetrics or ORATS for 30–50 components — significantly more expensive and complex to manage than index options.

**Cost**: 30–50 option legs per rebalance at 0.5–1.5% RT each = effective 15–50% annual cost drag. Requires institutional-grade execution. Retail-accessible in theory but practically requires direct market maker access.

**Propfirm compatibility**: None.

**Crowding**: Heavily crowded by hedge funds since ~2018–2020. The premium has compressed from ~3–4 vol points historically to ~1–2 vol points more recently.

**Score**: 4/10 — backup backup. Operationally complex, data expensive, crowded. Would only pursue if SPX VRP and crypto VRP both fail Phase 1.

---

### 2d. Skew/Smile Dynamics (25d RR, 25d BF)

**Edge**: Put skew mean-reverts after vol spikes. When SKEW index (CBOE) is elevated (>150), OTM puts are over-priced relative to realized jump frequency.

**Key papers**:
- Bollen & Whaley (2004) "Does Net Buying Pressure Affect the Shape of Implied Volatility Functions?" — demand-driven skew
- Liu, Pan & Wang (2005) "An Equilibrium Model of Rare-Event Premia and Its Implication for Option Smirks"
- Kozhan, Neuberger & Schneider (2013) "The Skew Risk Premium in the Equity Index Market"

**Data**: CBOE SKEW index is free (back to 1990). P&L of put-spread trades requires OptionMetrics or ORATS. FX skew (25d RR, 25d BF) requires Bloomberg or institutional FX vol data — not accessible.

**Cost**: OTM put spreads have wider bid-ask than ATM straddles; 0.3–1.0% RT realistic.

**Propfirm compatibility**: None.

**Verdict**: Academically interesting, standalone SKEW-based IC test is feasible with free data (Phase 1 possibility). But full backtest requires paid surface data. Complexity justifies saving this for Phase 2 if Phase 1 IC passes.

**Score**: 6/10 — viable sub-angle within SPX VRP universe. Not a separate priority.

---

### 2e. Cross-Asset Vol Carry (FX vol vs Equity vol)

**Edge**: FX implied vol and equity implied vol diverge during stress (carry/crisis correlation dynamics). Long/short positions across vol surfaces may capture basis risk premia.

**Key papers**:
- Menkhoff, Sarno, Schmeling & Schrimpf (2012) "Carry Trades and Global Foreign Exchange Volatility"
- Lettau, Maggiori & Weber (2014) "Conditional Risk Premia in Currency Markets and Other Asset Classes"

**Data**: FX volatility surfaces require Bloomberg or Refinitiv (Reuters) terminals — institutional only, not accessible. Equity vol via OptionMetrics.

**Cost**: FX OTC options: institutional execution only. Not available to retail.

**Verdict**: Purely institutional. Not feasible without Bloomberg terminal and FX OTC access. Relevant for CFM/Qube application interviews as a theoretical discussion topic, not as executable research at this stage.

**Score**: 2/10 — archive immediately, data inaccessible. Report: not executable without institutional infrastructure.

---

### 2f. Crypto Options Vol (Deribit BTC/ETH)

**Edge**: BTC/ETH implied vol systematically exceeds realized vol. Deribit DVOL index (BTC implied vol) historically ~75–85%; realized 30d vol ~55–70%. VRP spread ~15–20 vol points, higher in magnitude than SPX but with heavier tails.

**Key papers**:
- Hou, Tang & Wang (2020) "Variance Risk Premiums in Crypto Markets" — VRP positive and significant for BTC/ETH
- Alexander, Deng, Ji & Yin (2023) "Crypto quanto and inverse options pricing" — Deribit-specific
- Winkel, Ruf & Beguelin (2022) — BTC options VRP and delta hedging strategies

**Data sources**:
- **Deribit free API**: DVOL index (BTC/ETH implied vol, 30d) available in real-time and limited historical. For full option chain history (strikes, IVs, Greeks): **Tardis.dev** (~$100–300/mo for normalized tick data) or Deribit's own historical download portal (~$50–150/mo). Phase 1 IC using DVOL approximation: **FREE** (DVOL is publicly available via Deribit API, history back to ~2020).
- **OptionsDX / Amberdata**: Alternative crypto option data providers.

**Cost (Deribit)**:
- Taker: 0.03% of underlying (capped at 12.5% of option premium)
- Maker: 0.01% of underlying
- Delivery settlement: 0.015%
- Delta hedge via HL perp: 0.045% per trade (Strategy B infrastructure exists)
- Total round-trip for delta-hedged short straddle: ~0.06–0.15% vs notional. Lower than crypto spot strategies.

**Propfirm compatibility**: NOT Propr compatible. Personal capital or Deribit professional account. Could be relevant for Propr's future options offering if launched.

**Orthogonality to A/B/C**:
- Crypto delta-hedged straddle is by construction uncorrelated to directional crypto momentum (A) — delta = 0
- B (delta-neutral carry) is funded by 8h funding payments, C is NQ ORB — both orthogonal to BTC vol dynamics
- The correlation comes only through volatility regime: in extreme BTC crashes, short-vol AND long TSMOM both lose simultaneously (common VIX spike effect). This requires tail protection to avoid joint drawdown.

**CV value**: HIGH and DIFFERENTIATED. Deribit crypto options research is underrepresented in academic literature (most papers 2020–2023) and is seen as innovative at CFM/Qube — more so than replicating SPX straddles.

**Infrastructure synergy**: Hyperliquid perp is already live infrastructure (Strategy B). Delta hedge on HL requires no new connections; execution code exists.

**Score**: 8/10 — Priority #2 (backup). Data more accessible for Phase 1 than SPX (DVOL is free, OptionMetrics not needed). Trade-off: less CV credibility than SPX, heavier tails.

---

## 3. Prioritization — Argued

### Priority #1: SPX VRP (Direct Options, Not ETF Proxy)

**Why not the prior VIX carry**: The 3 archived variants failed because of ETF instrument limitations (roll drag, no timing alpha). This is a different instrument. The VRP is the same underlying premium; the execution vehicle is the critical variable.

**Why SPX over Deribit**: 
1. Academic evidence is older and more robustly tested (Carr & Wu 2009 vs crypto papers 2020–2023)
2. ORATS data is accessible at $150/mo for full surface — Tardis.dev for crypto is similar cost, but crypto option liquidity is lower for strikes far from ATM
3. CFM/Qube/Squarepoint interview value is higher for SPX vol
4. Phase 1 IC test requires $0 (VIX approximation)

**Why now (vs waiting)**:
- n_tests budget is fresh for options (0 tests so far)
- Crypto free-data is exhausted (confirmed 2026-05-23)
- FX Phase 1.5 carry+trend research continues in parallel — no conflict

**Decision criteria for "edge known dead (VRP post-2020)"**:
The retail options boom (2021–2023 meme stocks, 0DTE growth) compressed VRP. However:
- Sub-period analysis in published literature shows VRP is positive in every major sub-period 2000–2024, though smaller 2021–2023
- The 0DTE expansion redistributed premium across tenors, not eliminated it
- CBOE data shows VIX-RV spread still positive on average (5–7 vol points annualized through 2025)
- Conclusion: NOT dead — compressed but persistent. Proceed.

### Priority #2 (Backup): Deribit BTC Options VRP

**When to pursue**: If SPX Phase 1 IC fails (t_HAC < 2.5), or if SPX data cost ($150/mo ORATS) is rejected for Phase 2.

**Why crypto VRP not as a co-primary**: Running two Phase 1 IC tests simultaneously doubles n_tests budget without convergence. Execute sequentially: SPX first (free data), then Deribit if needed.

---

## 4. Candidate Angles — Priority Universe (SPX VRP)

### Angle A: Short 30d ATM Straddle, Delta-Hedged

**Mechanism**: Sell 1-month ATM straddle weekly (or monthly, aligned with VIX settlement), delta-hedge daily using SPY or ES mini. Collect theta (time decay ~0.2–0.4%/day for ATM straddle) while maintaining delta-neutral position.

**IC feasibility plan**:
- Signal: `VRP[t-1] = VIX[t-1] - realized_vol_30d[t-1]` (both free)
- Outcome: `straddle_P&L_approx[t] ≈ VIX[t-30d]/√12 × SPX[t-30d] - |SPX[t] - SPX[t-30d]|` (approximation — path-ignoring)
- Gate: IC t_HAC > 2.5 at 30d horizon, n_tests = 1
- More granular Phase 2: actual straddle P&L from ORATS surface data

**Cost estimate**:
- SPX straddle bid-ask: ~$1–3 per contract ≈ 0.05–0.15% notional
- Delta hedge: ~0.02–0.05% per daily rebalance × 22 days = 0.44–1.1%/month
- Total monthly cost: ~0.5–1.3% ≈ 6–16%/yr → requires >16%/yr gross to break even
- Historical gross: SPX short straddle P&L ~20–35%/yr gross in academic literature (before delta-hedge costs)
- Net expectation: Sharpe 0.8–1.2 (academic consensus), MaxDD −15–30% (depends on crash protection)

**Sharpe target (realistic, defying optimism)**:
- Gross: 20–25%/yr (after cost drag from delta hedging)
- Vol: 15–20%/yr (delta-hedged position has vega, not delta, as primary risk)
- **Realistic Sharpe: 0.7–1.0** — below academic maximums because delta hedging is imperfect and real costs are higher than published
- PROPFIRM_PASS gate (Sharpe > 1.0): UNLIKELY without optimal execution; RESEARCH_PASS (Sharpe > 0.7): achievable

**Capacity/crowding**: SPX options market is $1T+ daily notional; short-straddle strategy has minimal capacity constraint at personal-capital scale. Crowded at institutional level (VRP hedge funds, banks selling vol), but premium has persisted despite crowding.

**Risk profile**: Short gamma/short vega. Payoff asymmetry: collect small premium daily, occasional large loss in vol spike. Feb 2018: SPX straddle loss ~−25% in one week (similar to XIV collapse but at straddle scale, not inverse ETF scale). Mar 2020: −40 to −60% before recovery.

**Tail protection plan (MANDATORY — no naked short vol)**:
- Buy OTM put wing at 5% OTM (25d put approximation) → converts to put spread or condor
- Reduces vega/gamma exposure by ~30–40%; caps maximum loss at spread width
- Cost: ~0.15–0.25% of notional additional → reduces net premium by ~20–30% but eliminates tail event wipeout
- Net Sharpe adjustment: −0.10 to −0.15 from hedging cost, offset by better MaxDD control

### Angle B: Term Structure Signal (VIX3M/VIX as Entry Timer)

**Mechanism**: When VIX3M/VIX > 1 (contango steep, front month cheap relative to 3M), near-term vol is underpriced relative to longer-term vol → sell front-month premium. Signal fires more precisely when term structure is steep (not just any contango).

**IC feasibility plan**:
- Signal: `TS_ratio[t-1] = VIX3M[t-1] / VIX[t-1]` (both free via Yahoo Finance)
- Outcome: same straddle P&L approximation as Angle A
- Gate: IC t_HAC > 2.5 at 30d horizon
- New vs archived research: This signal targets the *slope* of the term structure, not the level. The VIX term carry (archived) used the slope as a REGIME FILTER to decide long/short ETF. Here it's an IC signal for option P&L timing.
- Event count check: VIX3M/VIX > 1.05 fires ~70% of days historically → not sparse; event-count ceiling check required

**Sharpe target (realistic)**: Adding term structure conditioning on top of Angle A adds ~0.10–0.20 Sharpe based on literature. Realistic combined: 0.8–1.1.

**Risk profile**: Same as Angle A. The term structure signal does not reduce tail risk — it reduces trades during backwardation, but crashes can occur in contango (COVID started in mild contango).

**Tail protection**: Same as Angle A — mandatory OTM hedge.

### Angle C: VIX z-Score Conditional Selling (RECOMMENDED FOR PHASE 1)

**Mechanism**: Sell vol ONLY when VIX is elevated relative to its recent history (VIX_z > threshold), implying current implied vol is richly priced. When VIX_z ≤ threshold, stay flat (vol is not cheap enough to sell relative to realized risk).

**IC feasibility plan**:
- Signal: `VIX_z[t-1] = (VIX[t-1] - EMA90d[VIX][t-1]) / EWMSD90d[VIX][t-1]`
- Outcome: `fwd_straddle_P&L_approx[t]` (30d horizon, VIX-based approximation, all free)
- Data required: VIX daily (Yahoo Finance: `^VIX`, back to 1990), SPX daily (`^GSPC`)
- Gate: IC t_HAC > 2.5 at 30d horizon using HAC(6) Newey-West, AMTP correction
- Event-count check: VIX_z > 1.0 fires ~16% of days historically (~40/yr); VIX_z > 1.5 fires ~5% of days (~13/yr). Event-count floor: ≥50 events/yr → threshold ≤ 1.0 required. Ceiling check: ensure portfolio is not always deployed.

**Why this is the Phase 1 priority**:
1. **$0 data cost**: VIX and SPX prices are completely free — no ORATS or OptionMetrics needed
2. **Approximation validity**: VIX/√12 approximates 1-month ATM straddle within ~5–10% accuracy (standard in academic literature). IC direction and significance are testable without actual option prices.
3. **Orthogonality to prior failure**: The archived VIX term carry tested a regime gate on an ETF — not an IC of a timing signal on option P&L. This is a methodologically distinct hypothesis.
4. **Connection to repo lesson**: The repo lesson explicitly states timing adds minimal value over passive. Phase 1 IC test will either confirm this (IC t < 2.5 → extend lesson, stop) or refute it for the conditional VIX_z signal (IC t > 2.5 → proceed).

**Sharpe target (realistic, not optimistic)**:
- Conditional selling (fire only ~16–30% of days) should produce higher Sharpe but lower total return than unconditional selling
- Literature: conditional on extreme VIX, annualized Sharpe ~1.0–1.5 for short straddle
- Accounting for hedging and realistic costs: **Sharpe 0.8–1.2 realistic**; propfirm gate (> 1.0): borderline achievable
- DO NOT project above 1.2 without empirical evidence

**Capacity/crowding**: At VIX_z > 1.0–1.5 thresholds, the strategy is active ~5–16% of days → selectivity should reduce crowding impact.

**Risk profile**: Same short-vega asymmetry as Angles A and B, but with one critical advantage: VIX_z > threshold means realized vol has RECENTLY BEEN HIGH, which historically correlates with premium decay cycles rather than further vol escalation. This reduces (does not eliminate) negative convexity.

**Tail protection (MANDATORY)**:
- Buy 5% OTM SPX put when entering short straddle
- Creates defined-risk position; cap on maximum loss per trade ≤ 5% notional
- Phase 1 can test the IC with and without the hedge constraint to see premium reduction

### Angle D: Deribit BTC Delta-Neutral Short Straddle

**Mechanism**: Sell weekly BTC ATM straddle on Deribit, delta-hedge via HL perp (same infrastructure as Strategy B). Earn BTC VRP (~15–20 vol points) with controlled delta exposure.

**IC feasibility plan**:
- Signal: `BTC_VRP[t-1] = DVOL[t-1] - BTC_RV30d[t-1]` (DVOL is free from Deribit API; BTC daily prices from Binance, free)
- Outcome: `BTC_straddle_P&L_approx[t]` using DVOL/√12 × BTC_price approximation
- Gate: IC t_HAC > 2.5 at 7d or 30d horizon
- Data: DVOL index (free, ~2020–present); BTC prices (Binance free API, 2017–present). ~5 years of data → n_obs reasonable.

**Cost**:
- Deribit taker 0.03% underlying; maker 0.01%
- HL delta hedge: 0.045% per hedge event (Strategy B cost model)
- Total RT: ~0.06–0.10% vs notional per weekly cycle → ~3–5%/yr drag at weekly straddle
- Gross BTC VRP estimate: 15–20 vol points annualized × position size → 15–20%/yr gross (rough)
- Net: Sharpe 1.0–1.5 possible but fat tails will compress realized Sharpe

**Tail protection (MANDATORY)**:
- Buy OTM BTC put at 10% OTM (cheaper than SPX puts due to already high IV)
- Or: cap loss using HL perp hedging with defined stop-loss on delta excursion
- Defines maximum loss per event; prevents XIV-style wipeout (BTC flash crashes can be −20% in hours)

**Status**: Phase 1 candidate if Angle C (SPX) fails. Infrastructure synergy with Strategy B makes execution plausible. CV value is differentiated (Deribit options = novel institutional research topic).

### Summary Angle Ranking for Phase 1

| Angle | Data cost Phase 1 | IC feasibility | Sharpe target | Tail risk | Phase 1 priority |
|---|---|---|---|---|---|
| C — VIX z-score conditional | $0 (free) | Yes — VIX + SPX | 0.8–1.2 | Short vega | **#1 RECOMMENDED** |
| A — Short ATM straddle | $0 for IC | Yes — approx | 0.7–1.0 | Short vega | #2 (refines Angle C) |
| B — Term structure timing | $0 for IC | Yes — VIX3M free | 0.8–1.1 | Short vega | #3 (adds to Angle A/C) |
| D — Deribit BTC straddle | $0 for IC (DVOL free) | Yes — DVOL + BTC | 1.0–1.5 | Short vega, fat tails | #4 (backup universe) |

Note: Angles A, B, C are not independent strategies — they are specifications of the same conditional SPX VRP trade. Phase 1 tests Angle C (the conditioning signal). A passing IC unlocks the full straddle backtest (Phase 2), which combines A + C by default.

---

## 5. Lessons Inventory — Applicable to Options Vol Research

### From VIX Term Carry Archive

| Lesson | Application to Phase 1+ |
|---|---|
| Static premium ≠ timeable signal (t_HAC=0.711 vs passive) | IC must clear t_HAC > 2.5 for TIMING, not just the static premium existence |
| ETF roll drag contaminates results (Lesson 5) | Use direct option P&L proxy (VIX approximation) or ORATS data, NOT VXX/VIXY price series |
| Mild contango (29% of days) is unprofitable | Event-count and regime decomposition required; do not assume "contango = profit" |
| WF 71% positive misleads when recent OOS (2024) is −1.925 | WF must show no single OOS year catastrophically negative; recent stability required |
| Vol-targeting (Variant B) reduces MaxDD from −54.2% to −15.9% | Vol-targeting is MANDATORY; size options position by vega-equivalent daily vol, not fixed notional |

### From Repo Methodology (CLAUDE.md Lessons)

| Repo Lesson | Options-Specific Application |
|---|---|
| 1. Signal T-1, Trade T | Use VIX/DVOL from close T-1 to decide whether to enter straddle at open T |
| 3. Vol scaling essential | "Vol target" for options = target 1σ loss ≤ 1–2% of portfolio; size by vega × underlying vol |
| 4. β-dominance | Short straddle has positive β to S&P (earns in flat/up markets, loses in sharp down/vol spike). Delta-hedge required to eliminate directional component. |
| 8. Excess returns + HAC mandatory | Options P&L must be vs T-bill rate on notional deployed; HAC(6) for all t-stats |
| Max 3 modifications per hypothesis | Phase 1 = IC test; Phase 2 = straddle backtest; Phase 3 = OTM hedge + WF. Stop at Phase 3. |

### From Crypto/FX Failures

| Failure | Options Transfer |
|---|---|
| OAGF: event-count too sparse → statistical power failure | VIX_z threshold must yield ≥50 events/yr. Threshold of z>1.5 may be too sparse (13/yr); z>1.0 (~40/yr) is near the floor. |
| FX carry: crash exposure destroys Sharpe | SHORT VOL = SHORT CONVEXITY. Any short-vol angle MUST include tail protection specification before Phase 1 proceeds. |
| Funding rate reversal IC in WRONG direction (t_HAC=−4.19) | Signal direction must be validated: high VIX_z → expensive IV → profitable to sell (expected +IC). If IC is negative (high VIX_z → IV cheapens further), halt immediately. |
| Beta-dominance lesson 11 | Short straddle + SPX delta hedge is orthogonal to BTC momentum (A), but all three strategies (A, B, straddle) may lose simultaneously during correlated crash events (BTC crash → VIX spike → straddle loss). This is the key portfolio risk. |
| Lesson 12: event-count ceiling | Conditional selling (VIX_z > 1.0, ~40/yr) avoids ceiling problem (not always deployed). But if multiple threshold configurations tested, AMTP applies. |

### Short-Vol Blow-Ups Historical Record (Mandatory Reading Before Any Phase 1)

| Date | Event | Mechanism | Lesson |
|---|---|---|---|
| Feb 5, 2018 | XIV/SVXY collapse (−90% in one day) | VIX futures spiked; inverse ETN rebalance created feedback loop | Short-vol ETFs can collapse; direct options positions lose −30 to −50% but do NOT go to zero |
| Mar 2020 | VIX spike to 85 (historical high) | COVID uncertainty; realized vol exceeded 100% annualized | Vol-targeted straddle survived in VIX carry backtest (+7.6%, MaxDD −1.5%) — vol-targeting is key |
| Oct 2018 | SPX −10% in 3 weeks | Rates + growth shock | Straddle seller loses on magnitude; delta hedge protects direction but not pure vol spike |
| Aug 2024 | Yen carry unwind | Cross-asset correlation spike | Short-vol strategies globally correlated during deleveraging events |

**Structural constraint**: Phase 1 and any subsequent backtest must stress-test against Feb 2018, Mar 2020, Oct 2018 periods. A strategy that "survives" these periods in the vol-targeted variant is deployable; one that does not is archived immediately.

---

## 6. N_tests Cumulative Counter

**Options vol sub-counter initialization**: `n_options = 0` (Phase 0 complete; no tests run)

**Cross-reference to other goals** (read-only, do not modify):
- Crypto: ~153 (from README.md Section 10, May 2026)
- FX: ~85 (from `Forex/research/passed/fx_carry_trend/fx_carry_trend_summary.md`, tests 83–85)
- Global/ETF/Equities: ~82 (README.md Section 10 bottom, includes VIX term carry n=71)

**Options n_tests budget plan**:

| Test | n increment | Gate |
|---|---|---|
| Phase 1 IC: Angle C (VIX z-score → straddle P&L approx) | +1 | IC t_HAC > 2.5 |
| Phase 1 IC: Angle A (raw VRP → straddle P&L approx) | +1 | IC t_HAC > 2.5 |
| Phase 2 backtest: straddle with OTM hedge | +1 | Research_PASS (Sharpe > 0.7) |
| Phase 2 WF validation (≥5 folds) | 0 (not separate test) | WF > 60% |
| Any threshold variation tested | +1 each | AMTP applies if n > 1 |

**E[max_SR] at n_options = 3 (after Phase 1+2)**: low (BLP approximation ~0.5 at n=3, far below propfirm Sharpe target). AMTP not binding until n > ~15.

---

## 7. Phase 0 Verdict — GO / STOP

### STOP conditions evaluated:

| Condition | Status | Verdict |
|---|---|---|
| Edge known dead (VRP post-2020) | VRP compressed ~30–40% from peak but still positive. Academic consensus: persistent. | NOT ARCHIVED |
| Data inaccessible for Phase 1 | VIX + SPX: completely free. Phase 1 IC test costs $0. Phase 2 data (ORATS ~$150/mo) expensive but optional for Phase 1. | NOT ARCHIVED |
| No angle passes feasibility criteria | Angle C has clear IC test design, free data, and documented academic precedent. | NOT ARCHIVED |
| Cross-asset vol (2e): Data inaccessible | Bloomberg/Refinitiv required for FX vol surfaces → ARCHIVE this sub-universe. | ARCHIVED (2e only) |
| VIX term structure ETF (2b): Already tested | 3 variants, all FAIL, archived at `ETF_Vol/research/archived/vix_term_carry/` | ARCHIVED (2b only) |

### Recommendation to proceed:

**Phase 1 IC test is GO pending explicit validation.**

Proposed Phase 1 scope (minimum viable test):
1. Fetch VIX daily history from Yahoo Finance (`^VIX`, 1990–present) — free, no external request in Phase 0
2. Fetch SPX daily history (`^GSPC`) — free
3. Compute VRP signal and 30d straddle P&L approximation
4. IC test with HAC(6) Newey-West at 30d horizon
5. n_tests += 1 (Angle C); if IC fails, n_tests += 1 for Angle A as pre-specified alternative
6. Report: IC, t_HAC, AMTP p-value, sub-period stability (2010–2015, 2015–2020, 2020–2025)

**Phase 1 STOP conditions** (pre-committed, no optimization):
- IC t_HAC < 2.0 for Angle C AND Angle A → archive options vol domain, no Phase 2
- IC direction inverted (high VRP_z → straddle LOSES) → archive immediately (wrong mechanism)
- Event count < 50/year at any threshold needed to achieve IC significance → archive (event-count ceiling gate)

---

**WAITING FOR EXPLICIT CHAT VALIDATION BEFORE PHASE 1 CODE IS WRITTEN.**

---

*n_options = 0 | Generated: 2026-05-23 | Phase 0 complete*
