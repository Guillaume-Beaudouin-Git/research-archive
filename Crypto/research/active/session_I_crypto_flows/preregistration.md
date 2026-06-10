# session_I_crypto_flows — PRE-REGISTRATION (frozen BEFORE data contact beyond audit samples)

*2026-06-10. Registry inherited N=115. Trials pre-registered here: **I-1, I-3** (+ conditional I-4
spec, runs only if I-3 passes). I-2 = STOP(data), F-1 = STOP(prior) — NOT pre-registered (no paper
trials), see `phase0_audit.md`. External effect sizes (Keyrock 16k-events, Tokenomist/Animoca,
Kim n=52 preprint) are HYPOTHESIS-TIER ONLY: everything below is re-derived from raw data; no kill
threshold is calibrated on them. Results append below the line at the end — never above.*

---

## Global cost model (all trials)

- Taker fee **5 bps/side** (Binance UM VIP0 4 bps + buffer). Slippage **1 bp/side BTC & ETH**,
  **4 bps/side other alts** ($10-50k clips). Live-book sanity recorded in `phase0_audit.md`
  (BTC ±1bp $170-830k ✓; SOL ±4bp ~$700k ✓; APT ±4bp $3-10k → alts gate also reports a **2×
  slippage stress column**, sensitivity only).
- **Realized per-event funding** on any held perp leg, computed from the historical Binance funding
  series over the exact holding window — NEVER a sample average. Sign convention: positive funding
  ⇒ longs pay shorts (a held short RECEIVES positive, PAYS negative funding).
- Universe floor (ex-ante membership at each entry date): Binance UM perp with **30d median daily
  quote-volume ≥ $20M** AND **listing age ≥ 60 days** (listing date = first Binance Vision monthly
  kline file).
- Delay-1 everywhere: signal at bar T close ⇒ fill at next 1h bar open (L26). UTC native. No
  synthetic data; gaps fail loud.

## TRIAL I-1 — Token-unlock drift (registry +1)

**Mechanism**: scheduled forced supply (cliff unlocks) on a publicly known calendar —
mechanically-constrained persistent flow family.

**Event DB**: DefiLlama datasets bucket (`emissions/{protocol}`), `metadata.events[]` with
`unlockType == "cliff"`. Same-token cliff allocations sharing the same UTC day are merged into one
event (amounts summed). Allocations with `category == "noncirculating"` are excluded from event
size (treasury-internal moves, not market supply). Linear/streaming vesting excluded by
construction (`unlockType != cliff`).

**Event size & filter**: `size_pct = tokens_unlocked / circ_proxy(T-1)` where `circ_proxy(t)` =
cumulative documented unlocked across all labels minus cumulative under labels whose events are
`noncirculating`, evaluated at t. Validation: circ_proxy vs CoinGecko (mcap/price) on 3 tokens × 3
dates, median relative error reported; if median |error| > 50% → fail-loud STOP(data-quality), no
improvised denominator. Filter: **size_pct ≥ 1%**. Universe floor applied at **T-10d**.

**Primary spec (ONE, zero window mining)**: short at close of UTC day **T-7** (fill next 1h open,
delay-1) → cover at close of UTC day **T+3** (fill next 1h open). The −30..+30d event-time profile
is reported DESCRIPTIVE only and is not a selection device. Net per event =
−(price log-return entry→exit) + Σ realized funding(short) − 10 bps taker − 2×slippage.

**Stages**: (a) event DB + coverage report; (b) gross effect + dose-response (deciles by size_pct,
descriptive; Spearman on events); (c) **L11 pre-flight cost gate**: if
`median(per-event all-in cost) ≥ median(per-event gross short drift)` where all-in cost = fees +
slippage − funding_pnl (signed) ⇒ **DEAD at the gate, no backtest run**; (d) full backtest + kills
only if (c) passes.

**Kill criteria (any one kills)**:
- K1: pooled net HAC t < 2.0 (event series time-ordered, Newey-West lag-6).
- K2: placebo — 1000 placebo calendars: for each real event, same token, random date uniform over
  the token's floor-eligible history, ≥15d from any of that token's real events, **matched on
  vol-regime** (same tercile of 30d realized vol, terciles per-token); pooled net mean must exceed
  the placebo distribution's 95th percentile.
- K3: dose-response — Spearman(size_pct, gross short drift) over events: ρ ≤ 0 or p ≥ 0.10 ⇒
  supply mechanism falsified.
- K4: 2024-01-01+ subsample pooled net ≤ 0 ⇒ priced-in/decayed (L31).
- K5: concentration — >60% of total net P&L from one token or one calendar quarter.
- K6: DSR ≤ 0 (Bailey-LdP, probabilistic, on the event-level net series) at the true registry count
  at evaluation (N = 115 + trials run this session).

**Specification check (reported, not a gate)**: category contrast — events whose merged categories
include `insiders` or `privateSale` vs events that are `airdrop/farming/publicSale/Uncategorized`
only. If categories were missing the contrast would be N/A — they are present (D2 audit).

## TRIAL I-3 — Funding-extremes IC study (registry +1; gates I-4)

**Controlling prior (cited, not calibrated on)**: README §6.35 — funding z-score is a momentum
proxy on HL BTC/ETH/SOL 2023-26 at 1-7d (contrarian IC significantly inverted). New cells here:
Binance 2020-2026 (incl. 2020-21 bull = the funding-stays-extreme-for-months trap), 8h horizon,
rolling-1y percentile standardization, 13-symbol universe. Expected outcome under the prior:
momentum-proxy direction ⇒ FAIL ⇒ I-4 void.

**Universe**: BTCUSDT, ETHUSDT, SOLUSDT + top-10 other UM perps by median daily quote-volume over
2024-01→2026-05 among symbols with ≥2y history and meeting the universe floor (rule fixed here;
resulting list reported in Phase 2, no discretion).

**Signal**: at each settled 8h funding timestamp (00/08/16 UTC), percentile of that settled rate
within the trailing 365d of settled rates for that symbol (min 180d warmup). Extreme-high event:
P > 97.5; extreme-low: P < 2.5. Consecutive same-side extremes within 24h collapse to the first
(event de-clustering, fixed).

**Test**: forward log-returns from the next 1h open (delay-1) over **8h / 24h / 72h**. TWO-SIDED
(L25): the high leg must be SHORT-predictive (mean fwd < 0) and the low leg LONG-predictive
(mean fwd > 0), **each leg standalone**. HAC Newey-West: lag 6 (8h), 12 (24h), 24 (72h).
Regime splits: 2020-21 / 2022 / 2023 / 2024-26.

**PASS** (gates I-4) = at ≥1 horizon BOTH legs have |t| ≥ 2.0 in the contrarian direction AND
neither leg's sign flips in any regime split at that horizon. Anything else = FAIL ⇒ **I-4 void**
and the queued directional funding-contrarian candidate is dead (it is already dead by §6.35 —
both recorded in the registry rationale).
Leg (ii) forward liquidation intensity: **N/A(data)** — D3 failed (phase0_audit §2).

## TRIAL I-4 — CONDITIONAL carry-sizing overlay (runs ONLY on I-3 PASS; registry +1 if run)

L19 discipline. Proxy carry book: short-perp funding harvest on the I-3 universe, constant size,
Binance settled funding 2020-2026, 8h marks. Overlay: ONE monotone map, frozen now:
`m(p) = 1 for p ≤ 90; m(p) = 1 − 0.5·(p−90)/10 for p > 90` (taper to 0.5 at p=100), applied to
position size at each settlement; baseline rescaled to the SAME mean gross leverage. Adopt-recommend
ONLY if net Sharpe AND CVaR(5%) of 8h returns BOTH improve vs the rescaled baseline; if one
improves → report, no adoption. Output = recommendation memo; **live Strategy B config and pairs are
never touched**; decision deferred to the N ≥ 250 milestone (L14).

---
*Phase-2 discipline: delay-1, UTC, no same-bar fills (L26), fail-loud gaps, no edits to
`_automation/` or live strategy configs. REGISTER.md +1 per trial actually run. Code and caches
under this directory only; raw fetched data in `cache/` (gitignored, regenerable).*

---

# RESULTS (appended after execution — never above this line)

*Appended 2026-06-10 after execution. Full detail: `report.md`, `i1_results.json`, `i3_results.json`.*

- **I-1: NO-GO — killed by K2 (placebo) and K3 (dose-response).** 578 events / 73 symbols
  (2020-09→2026-05). Gross short drift +369.7 bps/event (HAC t 3.12); cost gate passed trivially
  (median all-in cost 4.6 bps incl. a +13.4 bps median funding CREDIT to the short — the crowded-short
  trap did not materialize; only 33% of events had negative funding). Net +336.8 bps (t 2.90, K1 pass),
  2024+ subsample +382 (K4 pass), concentration OK (K5 pass), DSR 0.94 (K6 pass) — **but the 1000
  vol-matched placebo calendars produce a higher mean on random days (placebo median ≈ +410, p95
  +538.6 > real +336.8 → K2 KILL: disguised unconditional short-alt drift), and dose-response is flat
  (Spearman ρ=0.048, p=0.248 → K3 KILL: supply mechanism falsified).** Category contrast confirms:
  insiders/privateSale +367.8 (n=453) vs other +376.5 (n=125) — no insider gradient. Event-time
  profile: linear −1700 bps escalator over −30..+30d, no kink at the unlock.
- **I-2: STOP(data)** — see `i2_data_memo.md` (no free ≥3y hourly L/S liquidation source; Coinalyze
  key = recommended $0 path). Not pre-registered, +0 trials.
- **I-3: FAIL all horizons → gate not passed.** 2,195 extreme-funding events (999 high / 1,196 low),
  13 symbols, 2020-2026. High-tail (P>97.5) forward returns are POSITIVE (continuation): +20.0 bps @8h
  (t 1.34), +29.9 @24h, +113.2 @72h (t 1.60) — wrong sign for the contrarian short everywhere, worst in
  the 2020-21 trap regime (+239 bps @72h). Low-tail (P<2.5) right-signed at 24h (+38.7, t 1.58) but
  sub-threshold and sign-flipped in 2022 (−12.6 @72h). No horizon passes both-sides + sign-stability.
  Replicates README §6.35 (momentum proxy) on Binance 2020-2026 with the percentile spec.
- **I-4: VOID** (gate failed; frozen overlay map never run, +0 trials). The queued directional
  funding-contrarian candidate is dead (by §6.35 prior + this replication).
- **F-1: STOP(prior)** — `vrp_deribit/DECISION.md` (costs 200% of gross, 0/13 WF folds). +0 trials.

**Registry: 115 → 117** (+2: I-1, I-3). No survivors → no paper-trade spec issued.
