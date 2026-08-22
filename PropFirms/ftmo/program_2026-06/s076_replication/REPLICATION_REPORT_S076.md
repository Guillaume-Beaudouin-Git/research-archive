# Independent Replication — S076 "Ross Hook" (#76, first KEEP)

**Date:** 2026-06-07 · **Scope:** independent re-implementation of the Ross-Hook *proxy* daily
breakout-continuation strategy, tested on our high-quality broker data, to check the ftmo_lab
result (commit 9dea332, ranked #1/80) isn't an engine artefact and to revalidate on REAL data.
**Independence:** re-coded from `SPEC_S076_ross_hook.md §5` only; **did NOT import/call/read**
`ftmo_lab` or `code/rosshook.py` / `code/strat_s076_*.py`. Code: `rosshook_replication.py`,
`rosshook_run.py`, `prep_daily.py`, `make_report.py` (this folder).

---

## TL;DR verdict

The edge **REPLICATES on independent code + real broker data**, with the *expected* weakening on
our much smaller/shorter universe (7 deployable vs the report's ~21). The class ordering is
reproduced exactly (**crypto > commodity > index ≫ fx**), the **hook adds ~45%** over a no-hook
breakout placebo (report ~40%), the strategy is **strictly causal** (0 genuine trades change under
data truncation; expectancy is stable/rising with entry delay), **market-neutral** (β_mkt ≈ −0.04)
with a **significant — if weaker — covered alpha (t = 2.6 vs report 4.0)**, **robust to costs** (still
+0.017R at +10 bps), and **alive in 2019-2026**. The **FX negative control reproduces** (weakest
class, ~+0.012R, decays to negative out-of-sample → "remove FX" confirmed).

**Net:** not an engine artefact. Headline 30-instrument portfolio Sharpe is **not** reproduced
(and was never the goal — we lack 23/30 instruments and all pre-2012 index history); the *per-class
economic edge and all anti-artefact properties* are.

---

## Method (frozen, no optimization)

- **Strategy = the report's PROXY** (SPEC §3): long when `high[i]` is a new `Min_Setup`=10-bar high
  and `high[i]>high[i-1]`; track the first correction (hook low); enter on resumption `high≥H*`
  within `Max_Hook`=20 bars; short = mirror. **No literal 1-2-3 detection** (same as the engine).
- **Frozen params:** Min_Setup=10, Max_Hook=20, Time=10, ATR=20 (simple TR mean), ATR_Stop=6,
  RISK_FRAC=0.5%, depth_ratio=None. **No grid search** (re-optimizing would re-introduce the
  multiple-testing bias the report controls via DSR).
- **Fill:** PRIMARY = realistic, next day's open `O[e_bar+1]` (delay+1); optimistic `max(O[e_bar],H*)`
  reported for comparison. Exits: quick-stop at hook extreme → 6×ATR catastrophe → 10-day time stop
  (quick tested first). Trades non-overlapping per instrument. R = 6×ATR(detection bar).
- **Returns = MARK-TO-MARKET** daily close-to-close of every open position (SPEC §4 correction), NOT
  an R stretched over the hold. Sharpe = mean/std × √252 on the daily series.
- **Costs:** PRIMARY = real calibrated spread at the day's open (½ in + ½ out) + 1-tick/side slippage
  + small per-class commission; SECONDARY = report's flat per-class RT bps (1.5/2.0/4.0/8.0); stress
  +0/+3/+6/+10 bps. (Real-spread cost ≈ flat-bps cost → 0.0291 vs 0.0289, validating both.)
- **Daily bars:** resampled from M1 at the **EET/EEST broker server-day** boundary (Europe/Bucharest)
  — the MT5/FTMO deployment convention — giving ~258 bars/yr for indices (≈ trading days); a
  UTC-midnight set is built for the sensitivity check. *(We deliberately resample fresh from our
  verified M1, NOT the `oxfordstrat_109/ohlc/*` daily panels, which are UTC-day + mixed yfinance/
  2000-panel source tied to the report's engine.)*

## Universe (mapped to the report's deployable classes)

| class | tested (n) | report (n) | source |
|---|---|---|---|
| indices | US500, US100, US30, GER40, US2000 (5) | ~10 | deep_history_utc (2012/2013-), US2000 panel (2018-) |
| commodities | XAUUSD only (1) | 9 | deep_history_utc gold (2007-) — **real**, vs report's yfinance proxy |
| crypto | BTCUSD (1) | 2 | MT5 panel (2018-, **test-only**, no pre-2016) |
| fx (neg-control) | 10 majors | 9 (excluded) | deep_history_utc (2007-) |

---

## Side-by-side: report vs replication (PER CLASS / dimension)

| dimension | report benchmark | our replication | tag |
|---|---|---|---|
| **expR index** | +0.028 [.019,.039] sig | +0.0150 [−0.0075,+0.0379] (NS) · MTM Sh 0.21 | **WEAKER-BUT-CONSISTENT** |
| **expR commodity** | +0.059 [.038,.082] sig | +0.0380 [+0.0008,+0.0755] · MTM Sh 0.43 | **REPLICATED** (marginal; **real gold**, 1 inst) |
| **expR crypto** | +0.086 [.040,.156] sig | +0.0963 [+0.0206,+0.1842] · MTM Sh 0.91 | **REPLICATED** |
| **expR fx (control)** | +0.012 [−.015,.040] NS | +0.0122 [+0.0001,+0.0244] · decays OOS | **REPLICATED** (neg-control) |
| MTM Sharpe (portfolio) | 0.70 real / 0.96 proxy | 0.439 (deployable, 7 inst) | WEAKER (breadth 7≪21; not comparable) |
| Covered alpha t (mkt+TSMOM) | 5.4 proxy / 4.0 real | **t=2.58**, α=+1.4%/yr, β_mkt=−0.04, β_tsmom=0.06 | WEAKER-BUT-CONSISTENT (sig, market-neutral) |
| Hook contribution | placebo .0235, hook +~40% | placebo .0159, **hook +45.2%** | **REPLICATED** |
| Anti-look-ahead (truncation) | 0 changed | **0 genuine** / 2293 common (2 straddling=expected) | **REPLICATED** |
| Entry-delay robustness | Sh 1.78/1.53/1.49/1.58/1.68 | expR .037/.029/.029/.033/.044 (stable→rises) | **REPLICATED** (no entry-bar leak) |
| Cost +0/3/6/10 bps | .040/.037/.033/.028 | .0291/.0255/.0219/.0171 (real spread) | **REPLICATED** (>0 at +10 bps) |
| Sub-period 2019-2026 | alive (~1.05) | idx +.023 / comm +.041 / crypto +.097 (all+); fx −.009 | **REPLICATED** (deployable alive; fx dead) |
| Daily boundary EET vs UTC | (EET = deployment) | deployable Sharpe 0.44 EET / 0.49 UTC | ROBUST (crypto ~25% boundary-sensitive) |

*(machine-readable: `results/comparison.csv`, `results/per_class.csv`, `results/per_instrument.csv`,
`results/validation.json`)*

---

## Key findings

**1. Class ordering reproduced exactly.** crypto (+0.096) > commodity (+0.038) > index (+0.015) ≫
fx (+0.012). Same ranking as the report (crypto > commodity > index ≫ fx). Crypto matches the report
point-for-point (+0.096 vs +0.086, CIs overlap).

**2. The hook is a ~40-45% refinement of generic breakout-momentum — confirmed.** A no-hook placebo
("buy every new 10-bar high") earns +0.0159R; the hook lifts it to +0.0291R → **+45%** (report ~40%).
The report's own framing holds: ~55-60% of the edge is short-term breakout-momentum, ~40-45% is the
hook refinement. It is **not** a unique "hook alpha".

**3. Strictly causal (no look-ahead).** Re-running on history truncated at 2020-01-01: **0 of 2293**
trades resolved before the cut change (entry/dir/netR bit-identical); the only 2 differences are
positions open *at* the cut, force-closed at the truncation edge (expected). Expectancy is **stable
to rising** with entry delay (+0→+5), so there is no entry-bar information leak.

**4. Market-neutral, weakly-trend-loaded, significant alpha — but weaker than the report.** Deployable
MTM regressed on US500 returns + a 12-month cross-instrument TSMOM factor: **α=+1.4%/yr, t_NW=2.58**,
β_mkt=−0.04, β_tsmom=+0.06. Same *structure* as the report (β≈0 on both factors, alpha survives the
controls) but **t=2.6 vs the report's 4.0 (real) / 5.4 (proxy)** — the expected loss of power on a
7-instrument subset.

**5. Commodity revalidated on REAL gold (addresses reservation §9-i/iv).** The report's commodity
edge was 9 instruments, mostly **yfinance continuous-futures proxy**. On **real broker gold M1
(2007-)** the edge is **+0.038R, marginally significant** [+0.0008,+0.076], MTM Sharpe 0.43, and
positive in every sub-period (2007-11 +0.05, 2012-18 +0.026, 2019-26 +0.041). Weaker than the proxy
headline (+0.059) but **directionally confirmed on real data** — the proxy was not the source of the
edge.

**6. Indices are the weak spot — largely a data-coverage artefact, not a logic failure.** On our
5-index 2012/2013+ sample the class is positive but **not significant** (+0.015 [−0.008,+0.038]);
GER40 is negative (−0.014) and US30 ~0, while US500 (+0.024) and US2000 (+0.061) carry it. The
report's significant +0.028 used **2000+ index history** (incl. the strongly-trending 2008-2011) that
we **do not hold**. Our index edge is flat in 2012-2018 (+0.002) but **positive in 2019-2026
(+0.023)** — "alive recent" still holds. Verdict: weaker-but-directionally-consistent, with the
shortfall attributable to the missing pre-2012 history.

**7. FX negative control reproduced.** FX is the weakest class (+0.012R, = the report's +0.012),
and **decays out-of-sample** (train<2021 +0.019 → test≥2021 −0.005; 2019-2026 −0.009). This confirms
the report's "FX edge not significant → remove" as an implementation consistency check.

**8. Robust to costs and to the daily-bar boundary.** Stays positive at +10 bps (+0.017R); real
calibrated spread ≈ the report's flat per-class bps. EET vs UTC daily boundary: deployable Sharpe
0.44 vs 0.49 — sign and class-ordering stable; only crypto magnitude shifts ~25% (BTC is 24/7 so the
boundary reshuffles bars), confirming results aren't an artefact of the session convention. EET is
the deployment-correct choice (matches MT5/FTMO daily candles).

**9. OOS.** Primary split (train≤2015) is **contaminated by a thin, negative index train**
(2012-2015, n=149, −0.0095) — an honest limitation of our short index history, not a strategy
failure; index test≥2016 is +0.0205. The cleaner secondary split (train<2021) keeps **all deployable
classes positive in test** (idx +0.008, comm +0.025, crypto +0.075) while **FX turns negative**
(−0.005).

Plots: `plots/mtm_equity.png` (MTM equity, deployable + per class), `plots/per_class_sharpe.png`,
`plots/trade_R_dist.png` (deployable vs fx net-R).

---

## Limitations — what could NOT be tested (reported, not invented)

- **8 of 9 commodities missing** (oil, silver, nat-gas, copper, agricultural…): only **gold** is held
  as real broker data. The commodity replication rests on **1 instrument** → wide CI, marginal
  significance. This is the single biggest coverage gap vs the report.
- **5 of 10 indices missing**, and **all pre-2012 index history** (US500 starts 2012-01, others 2013;
  US2000 2018). **No 2008 crisis test for indices** (gold does cover 2008). The report's index edge
  leaned on 2000-2011 trending regimes we cannot test → our index result is necessarily weaker.
- **Crypto = 1 of 2 and test-only** (BTC from 2018-11; no pre-2016 data) → cannot be train/test split;
  the +0.096 is a single-instrument, recent-history estimate (wide CI).
- **Portfolio Sharpe not comparable** (7 deployable vs ~21): we judge per-class/per-instrument, as
  instructed. Deployable Sharpe 0.44 < report real 0.70 is a diversification/breadth effect.
- **Proxy ≠ literal 1-2-3** (inherited from the spec): we replicate the engine's proxy, not Joe Ross's
  literal pattern (SPEC §10 open question — untested here by design).
- **Covered-alpha power** is limited by breadth (t=2.6); the TSMOM factor is built from our 17
  instruments only, not a canonical CTA index.
- **Daily-boundary** for the two EET-naive panels (US2000, BTCUSD) uses naive server dates directly;
  their UTC-set conversion handles DST with a deterministic rule (immaterial at daily scale).

## Verdict per class

| class | verdict | one-line |
|---|---|---|
| **crypto** | ✅ REPLICATED | +0.096R vs +0.086, MTM Sharpe 0.91 — strongest, confirmed (test-only) |
| **commodity** | ✅ REPLICATED (marginal) | real gold +0.038R, positive every sub-period — proxy concern resolved |
| **fx (control)** | ✅ REPLICATED | weakest class +0.012R, decays OOS — "remove FX" confirmed |
| **index** | 🟡 WEAKER-BUT-CONSISTENT | +0.015R (NS on full sample), +0.023R recent — shortfall = missing pre-2012 history |
| **whole edge** | ✅ NOT AN ARTEFACT | causal, market-neutral, hook adds ~45%, cost/boundary-robust, alive recent |
