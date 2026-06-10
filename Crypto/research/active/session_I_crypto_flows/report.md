# session_I_crypto_flows — REPORT (crypto structural-flow edges, 2026-06 screen)

*2026-06-10. Track: CRYPTO, exchange-perp cost model (FTMO blockers untouched). Scope held at the
5 pre-registered candidates, funnel-staged; excluded families per task not expanded.
Pre-registration frozen & committed BEFORE data contact (`preregistration.md`, commit `97bf99e`).
Registry: inherited **N=115** → leaves **N=117** (+2: I-1, I-3 run; I-2/F-1 stopped, I-4 void).*

---

## EXECUTIVE VERDICT

**Zero survivors out of five candidates; two trials run, two stopped without consuming registry
slots, one void.** **I-1 (token-unlock drift): NO-GO** — the unlock short "works" (+337 bps net/event,
HAC t 2.90, N=578, undecayed, DSR 0.94) **but it is not an unlock effect**: 1000 vol-matched placebo
calendars on the same tokens bleed MORE on random days (real mean sits below the placebo median,
far under the pre-registered 95th-percentile gate → K2 kill), dose-response in unlock size is flat
(ρ=0.048, p=0.25 → K3 kill), there is no insider/investor category gradient, and the event-time
profile is a linear −1,700 bps escalator across −30..+30d with no kink at the unlock day. The
Keyrock-class "unlocks are followed by declines" claim replicates only because liquid mid-cap alt
perps decline unconditionally — disguised short-alt beta, the exact failure mode K2 was registered
to catch. **I-3 (funding-extremes IC): FAIL on all horizons** — extreme-high funding (P>97.5,
n=999) precedes *continuation* (+20/+30/+113 bps at 8h/24h/72h), worst in the 2020-21
funding-stays-extreme regime (+239 bps @72h against the contrarian short); the low tail is
sub-threshold and regime-unstable. This replicates README §6.35's momentum-proxy verdict on
Binance 2020-2026 with an independent spec → **I-4 (carry-sizing overlay) is VOID** and the queued
directional funding-contrarian candidate is dead twice over. **I-2: STOP(data)** (no free ≥3y hourly
long/short liquidation history; $0 acquisition path memo'd). **F-1: STOP(prior)** (vrp_deribit
DECISION.md: costs 200% of gross, 0/13 WF folds, L13). A clean kill is the deliverable — twice.

| Trial | Verdict | Kill reason (verbatim where killed) | Registry |
|---|---|---|---|
| I-1 unlock drift | **NO-GO** | K2: real net mean +336.8 bps ≤ placebo p95 +538.6 ("disguised unconditional drift, kill"); K3: Spearman ρ=0.048, p=0.248 ("dose-response flat or non-monotone ⇒ supply mechanism falsified") | **+1** |
| I-2 cascade reversal | **STOP(data)** | D3 audit: no adequate free source (`i2_data_memo.md`) | +0 |
| I-3 funding extremes | **FAIL (gate)** | "P > 97.5 must be short-predictive" → measured +20.0 bps @8h (t +1.34), +113.2 @72h — wrong sign at every horizon; 2020-21 "sign flip here kills" leg: +239 bps @72h continuation | **+1** |
| I-4 carry overlay | **VOID** | conditional on I-3 pass — gate failed; frozen map never run | +0 |
| F-1 VRP feasibility | **STOP(prior)** | `Crypto/research/archived/options/vrp_deribit/DECISION.md`: "Retail option costs (8.89%/yr) exceed the gross VRP premium (4.44%/yr) by a factor of 2×. … Zero folds positive across all 13 WF windows" | +0 |

---

## TRIAL I-1 — Token-unlock drift — NO-GO (K2 + K3)

**Event DB (stage a, `i1_coverage.md`):** DefiLlama datasets bucket → 331 protocols, 22,424
day-merged cliff events (ex-noncirculating), 2,901 ≥1% of circulating proxy, 1,782 with a Binance UM
perp ever listed, **578 events / 73 symbols passing the ex-ante floor** (perp age ≥60d, 30d median
quote-vol ≥$20M at T-10), 2020-09-16 → 2026-05-24. Circ-proxy validated vs CoinGecko mcap/price:
median |rel err| ≈ 16% (worst APT −42%, bias direction = inclusive). One symbol (RIVERUSDT) dropped
fail-loud on REST. Coverage bias documented (post-2022 survivor skew at the calendar source).

**Stage (b) — gross effect & dose-response:** mean gross short drift **+369.7 bps/event, HAC-6
t = 3.12**. But Spearman(size, drift) **ρ = 0.048, p = 0.248**; deciles non-monotone (D0 +447,
D1 +17, D2 +491, D4 +54, D8 +839, D9 +509) → **K3 kill registered**. Figure:
`figures/i1_dose_response.png`.

**Stage (c) — L11 pre-flight cost gate (fees / slippage / funding SEPARATELY):**

| Component (median per event) | bps |
|---|---|
| Taker fees (2 × 5 bps) | 10.0 |
| Slippage (2 × 1 bp majors / 2 × 4 bps alts) | 8.0 (alts) |
| Realized short-leg funding over (entry, exit], 30 settlements | **+13.4 (CREDIT)** |
| **All-in median cost** | **4.6** |
| All-in at 2× slippage stress (APT-depth caveat) | 12.6 |
| Median gross drift | 397.9 |

The pre-registered trap (crowded pre-unlock shorts ⇒ negative funding ⇒ the short pays) did **not**
materialize: only **33%** of events had net-negative funding for the short; the median event paid
the short. Gate: 4.6 ≪ 397.9 → **PASS** (backtest licensed).

**Stage (d) — backtest & kills:** net **+336.8 bps/event, HAC-6 t = 2.90** (K1 pass);
2024+ subsample +382 bps, n=431 (K4 pass — not decayed); max token share 11.7%, max quarter share
32.4% (K5 pass); DSR at N=117 trials = 0.94 (K6 pass). **K2 placebo — KILL:** 1000 placebo
calendars (same token, random floor-eligible days, vol-tercile-matched, ±15d exclusion with
documented ±10d fallback for monthly-cliff tokens; 0 events excluded): placebo distribution mean
≈ +410 bps, **p95 = +538.6 bps vs real +336.8** — the real unlock calendar sits *below the placebo
median*. Random short days on these tokens out-bleed the unlock windows. Figures:
`figures/i1_placebo.png`, `figures/i1_event_profile.png` (linear escalator, no unlock kink — same
"drift accrues off-event" signature as the announcement_premium kill).

**Specification check (category):** insiders/privateSale events +367.8 bps (n=453) vs all-other
+376.5 bps (n=125) — **no insider gradient**, second independent falsification of the
forced-supply mechanism.

**What survives factually:** liquid mid-cap alt perps bled ~+340 bps net per 10-day short window
*unconditionally* 2020-2026 (incl. +382 in 2024+) — that is short-alt beta (L11 family), not an
event edge, and not a deployable claim from this trial (no short-basket strategy was pre-registered;
funding/squeeze regime risk untested at portfolio horizon).

## TRIAL I-2 — Post-liquidation-cascade reversal — STOP(data)

D3 failed all free routes (Binance Vision has no liquidationSnapshot type; `forceOrder` is live-only
and throttled 1 msg/s since 2021-04; Coinalyze 401-keyed; Bybit public none; HL archive none).
OI-delta reconstruction explicitly not acceptable. **Deliverable = `i2_data_memo.md`**: recommended
$0 path (user creates a free Coinalyze API key, verify ≥2022-06 depth + censoring caveat), fallback
Coinglass ~$29-79/mo one month to backfill. Trial not pre-registered, no paper trial, +0.

## TRIAL I-3 — Funding-extremes IC — FAIL (gates I-4 → VOID)

Universe (frozen rule, fail-loud ranking with Vision fallback for delisted-from-REST symbols):
BTC, ETH, SOL + 1000PEPE, DOGE, XRP, WIF, SUI, BNB, ADA, ENA, ORDI, WLD. Settled funding normalized
to 8h-equivalent; causal trailing-365d percentile (≥180d warmup); events de-clustered 24h;
**2,195 events** (999 high / 1,196 low); forward returns from next 1h open (delay-1, L26); 5 events
skipped on bar gaps (fail-loud, counted).

| Horizon | Leg | n | mean bps | HAC t | contrarian sign? | 2020-21 | 2022 | 2023 | 2024-26 |
|---|---|---|---|---|---|---|---|---|---|
| 8h | high (want <0) | 999 | **+20.0** | +1.34 | ✗ | +79.1 (t 1.67) | +19.7 | +6.1 | +11.5 |
| 8h | low (want >0) | 1196 | +2.8 | +0.16 | ✓ ns | **−40.1** | +13.2 | +63.0 | +2.6 |
| 24h | high | 999 | **+29.9** | +1.05 | ✗ | +143.9 | −19.6 | −12.6 | +32.3 |
| 24h | low | 1196 | +38.7 | +1.58 | ✓ ns | +151.6 | +10.9 | +104.4 | +25.5 |
| 72h | high | 999 | **+113.2** | +1.60 | ✗ | **+239.0** | −118.5 | +66.2 | +126.6 |
| 72h | low | 1196 | +51.8 | +1.17 | ✓ ns | +105.2 | **−12.6** | +120.5 | +55.7 |

No horizon passes "both legs |t|≥2 contrarian AND regime-sign-stable" — the high leg is
wrong-signed everywhere (momentum continuation), and 2020-21 is the worst case exactly as the
pre-registration warned ("funding-stays-extreme-for-months trap"). The 24h low-tail bounce
(+38.7, t 1.58) is the only contrarian-signed cell — sub-threshold and 2022-unstable. Leg (ii)
(liquidation intensity) N/A(data). **Replication note:** independent spec (Binance vs HL, 2020-26 vs
2023-26, percentile vs z-score, 13 vs 3 symbols) reproduces README §6.35's verdict — funding
extremes confirm momentum, they do not signal reversal. **I-4 VOID; the queued directional
funding-contrarian candidate dies with it (and was already dead by §6.35 — both recorded).**

## F-1 — VRP feasibility — STOP(prior)

Full Phase-3 verdict already on disk (2026-05-23, n_tests 153→156):
`Crypto/research/archived/options/vrp_deribit/DECISION.md` — gross +4.44%/yr vs costs 8.89%/yr
(fees 49% / spread 49% / hedge 2%, "no single cost to fix"), net −4.46%/yr, Sharpe HAC −2.68,
**0/13 WF folds positive**, "VRP premium exists structurally (DVOL > RV 80% of time) but is not
retail-accessible". The paid-chain-data question is thereby answered: **NO-GO** — the binding
constraint is the cost structure, which better data cannot change. D4 (DVOL API) audited PASS as a
footnote. Follow-up flagged: `Crypto/research/active/vrp_short_gamma/` (0-test bootstrap planning
the same DVOL-vs-RV object) should be archived onto this prior.

---

## Registry — delta and chain check

Chain: `positive_dsr_register/REGISTER.md` audit **108** (2026-06-09) → announcement_premium +4 →
112 → backwardation_oil +3 → **115** (2026-06-10, incl. session_H +0) → **session_I +2 (I-1, I-3)
→ 117**. Ledger line appended to REGISTER.md. Queued-candidate rationale recorded: directional
funding-contrarian = dead (README §6.35 + I-3); unlock-drift = dead (I-1 K2/K3); VRP paid-data = dead
(F-1 prior). No survivors → **no paper-trade spec issued** (methodology step 5 not reached).

## Candidats-leçons (NOMMÉS, non numérotés — max graven L = L24, candidates cited to L44)

> **LESSON-CANDIDATE: unlock-drift-is-short-alt-beta** — a calendar-event claim on a structurally
> bleeding universe must clear a *matched placebo calendar*, not just significance/decay/DSR gates:
> the unlock short shows net +337 bps/event, t 2.90, N=578, undecayed, DSR 0.94 — **and sits below
> the placebo MEDIAN of random vol-matched days on the same tokens** (p95 +539). Flat dose-response
> (ρ 0.05) + zero insider-category gradient + a linear event-time escalator with no unlock kink
> complete the falsification. Family: L11 β-dominance; same signature as announcement_premium's
> "drift accrues off-event". External unlock studies (Keyrock-class) that lack placebo calendars are
> measuring the universe, not the event.

> **LESSON-CANDIDATE: funding-extremes-confirm-momentum-across-exchange-and-cycle** — §6.35 (HL,
> z-score, 2023-26, BTC/ETH/SOL) now replicated independently (Binance, trailing-1y percentile,
> 2020-26, 13 symbols, 2,195 events): extreme-high funding precedes CONTINUATION at 8h/24h/72h,
> +239 bps @72h in 2020-21 — the contrarian short is structurally wrong-signed, and a
> funding-percentile carry-sizing overlay has no IC foundation (I-4 void without data contact).
> The funding-contrarian family is closed at the exchange-perp tier; only the sub-threshold,
> regime-unstable 24h low-tail bounce (+39 bps, t 1.6) even carries the contrarian sign.

---
*Discipline: delay-1 everywhere; UTC native; no same-bar fills (L26 — entry==funding-timestamp
resolves to next); no synthetic data; gaps failed loud (5 events skipped I-3, 1 symbol dropped I-1,
3+1 delisted symbols resolved via Vision archive fallback, all logged). `_automation/` and live
strategy configs untouched; Strategy B untouched. Artifacts: `preregistration.md` (+ appended
results), `phase0_audit.md`, `i1_coverage.md`, `i1_results.json`, `i3_results.json`,
`i2_data_memo.md`, `figures/`, `code/` (lib_data, i1_build_events, i1_run, i3_fetch, i3_run,
make_figs). Caches regenerable, gitignored. No orphan reports — everything in this directory is
committed (commit-or-delete, session_H lesson).*
