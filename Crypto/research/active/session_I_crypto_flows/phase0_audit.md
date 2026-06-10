# session_I_crypto_flows — PHASE 0: registry sweep + data audit

*2026-06-10. Zero trials consumed in this phase. Registry inherited: **N = 115** (chain:
`positive_dsr_register/REGISTER.md` 108 @06-09 → +4 `announcement_premium` → 112 → +3
`backwardation_oil` → 115; session_H +0 — see `data/skew_research/session_H_calendar_flow/report.md`).
Max graven L in CLAUDE.md = **L24**; candidates referenced up to L44 in session reports → all
session_I lesson candidates are NAMED, never numbered (no collision possible).*

---

## 1. Registry sweep (consolidated paths included, per session_H lesson)

Swept: `Crypto/research/{active,archived,_meta}/`, `data/skew_research/session_*`,
`PropFirms/ftmo/program_2026-06/` (consolidated program dir incl. funnel CSVs), `README.md`
(research journal §6.x), `STRATEGY_RESEARCH_LOG.md`, `strategies/`, `_automation/alpha_hunt/promising/`,
`Multi_Asset/`. Patterns: unlock/vesting/cliff · liquidation/cascade/ADL ·
funding+(asym|extreme|percentile|contrarian|z-score|condition) · DVOL/VRP/variance risk premium.

| Trial | Hits | Prior verdict? | Disposition |
|---|---|---|---|
| I-1 unlocks | `Crypto/research/active/token_unlocks/_bootstrap_notes.md` (2026-05-23) + compass/landscape idea-tier docs | **NO** — Phase-0 bootstrap only; `_meta/sanity_check_2026_05_23.md`: "token_unlocks/ … correctly in Phase 0 state — no hypothesis consumption yet, no n_tests spent ✓". NB: bootstrap sketched a DIFFERENT window (T-30→T+7, >5% circ) — superseded by this session's single pre-registered spec (T-7→T+3, ≥1%); the bootstrap was never a frozen contract. | **PROCEED** (data-gated by D2) |
| I-2 cascades | `Crypto/research/active/_bootstrap_v2_notes.md` §6.34 + Angle 3: "Liquidation Signal (Crash Recovery): No historical liquidation data; gross IC unverified — Data structural: HL liquidation feed not accessible historically" | **NO verdict on the hypothesis** — a data-gap note (HL only). Adjacent prior: README §6.34 crash-recovery (price-defined dips) = continuation, NOT reversal — cited as prior, but §6.34 events are price-defined, not liquidation-flagged; I-2's placebo (matched non-cascade moves) is exactly the §6.34-vs-cascade contrast. | **PROCEED iff D3 passes** |
| I-3 funding extremes | **`README.md` §6.35 "Extreme Funding Rate Reversal (Contrarian)"** — Status: **SKIP — IC is NEGATIVE (wrong direction); extreme funding confirms momentum continuation, not reversal.** BTC/ETH/SOL, HL funding May-2023→Apr-2026, z-score 30d, holds 1-7d: IC(z, −fwd) = −0.026 (t −1.05, 1d) → −0.089 (**t −4.19**, 7d); contrarian backtest PF 0.587, Sharpe **−1.484**; "Archetype 3 confirmed: funding z-score is a momentum proxy". Also: CS-FS IC t=1.54 FAIL, FRA t=1.01 FAIL (`_bootstrap_v2_notes.md` §6.37-6.38), h31_cs_fs_dn all-gates FAIL (cross-sectional family). | **PARTIAL** — the contrarian *directional strategy* is dead on HL/3-majors/2023-26/1-7d. NOT covered: Binance 2020-2026 (incl. the 2020-21 funding-stays-extreme trap regime this session must test), 8h horizon (B's operating frequency), 1y-percentile standardization, 13-symbol universe, and the I-4 gating purpose. | **PROCEED** as I-4 gate, §6.35 = controlling prior (expected direction: momentum-proxy). **The queued directional funding-contrarian candidate is ALREADY dead by §6.35 prior art** — recorded here; I-3's outcome can only confirm, not revive it. |
| F-1 VRP | **`Crypto/research/archived/options/vrp_deribit/DECISION.md`** (2026-05-23, n_tests 153→156): "**VERDICT: ARCHIVE** — Retail option costs (8.89%/yr of underlying notional) exceed the gross VRP premium (4.44%/yr) by a factor of 2×. Net P&L = −4.46%/yr. Sharpe HAC = −2.68. Zero folds positive across all 13 WF windows (2022-2026). … *VRP premium exists structurally (DVOL > RV 80% of time, gross positive) but is not retail-accessible net of realistic Deribit option fees and bid-ask spreads.*" Cost split: fees 49% / bid-ask 49% / hedge 2% — "There is no single cost to fix." L13 graven in CLAUDE.md. | **YES — full Phase-3 verdict.** F-1's question ("GO/NO-GO on acquiring paid historical options-chain data") is answered: the binding constraint is the *cost structure*, which more/better data cannot change; the gross level, persistence (80% of time), regime dependence (DVOL-level table in DECISION.md) and tail (worst cycle −1.46% vs +0.122%/cycle gross ≈ 12 cycles ≈ 5 months of premium) are already measured. | **STOP(prior)** — NO-GO on paid chain data stands. The active `vrp_short_gamma/_bootstrap_vrp_notes.md` (0 tests) plans the same DVOL-vs-RV object → effectively closed by the same prior; flagged for archive. |

## 2. Data audit (fail-loud; probes on record, no synthetic fallback)

**D1 — Binance Vision UM bulk: PASS.**
S3 listing probes (2026-06-10): `klines/BTCUSDT/1h/` starts **2020-01** ✓; `fundingRate/BTCUSDT/`
spans **2020-01 → 2026-05** ✓; delisted retention confirmed — `LUNAUSDT` 1h files **2021-01 → 2022-05**
(delisting month) ✓; listing dates recoverable as first monthly file per symbol ✓.

**D2 — Unlock schedules: PASS (via DefiLlama free datasets bucket; paid-API detour documented).**
`api.llama.fi/emissions*` now returns "Upgrade to the paid API plan" — **the documented free primary
is paywalled**. Working free equivalent (the bucket the DefiLlama frontend reads):
`defillama-datasets.llama.fi/emissionsProtocolsList` (protocol index) +
`defillama-datasets.llama.fi/emissions/{protocol}` per-protocol JSON with `metadata.events[]`:
`{timestamp, noOfTokens, category ∈ {insiders, privateSale, publicSale, airdrop, farming,
noncirculating, Uncategorized…}, unlockType ∈ {cliff, linear_start…}}` — **cliffs explicitly typed,
categories present** → I-1 category contrast feasible (insiders/privateSale vs rest).
Coverage bias (explicit): (a) list skews to protocols alive/notable post-2022 — tokens dead before
~2022 largely absent → events for early-cycle corpses missing (survivorship at the SOURCE);
(b) schedules are DefiLlama-documented backfills of project docs — revision risk on old entries;
(c) `% of circulating` denominator is NOT directly historical: pre-registered proxy = cumulative
documented unlocked minus `noncirculating` labels at T-1, sample-validated vs CoinGecko mcap/price
(3 tokens × 3 dates) with the validation error reported. CryptoRank free-tier cross-check: **N/A —
requires an account/API key that cannot be created autonomously**; not improvised, recorded as a gap.

**D3 — Liquidation history: FAIL → Trial I-2 = STOP(data) + acquisition memo (`i2_data_memo.md`).**
- Binance Vision: **no** `liquidationSnapshot` data type under `futures/um/daily/` (available types:
  aggTrades, bookDepth, bookTicker, indexPriceKlines, klines, markPriceKlines, metrics,
  premiumIndexKlines, trades — probed 2026-06-10); `forceOrder` websocket is live-only (and throttled
  to 1 msg/s/symbol since 2021-04-27 → any vendor relaying it under-counts notional).
- Coinalyze REST: **HTTP 401** without API key — free tier exists but requires registration
  (cannot be done autonomously in this session).
- Bybit `public.bybit.com`: no liquidation folder (kline_for_metatrader4, premium_index, spot_index,
  trading, spot only).
- Hyperliquid: no historical liquidation archive in the free API (prior note, `_bootstrap_v2_notes.md`).
⇒ No adequate free source with ≥3y × hourly × long/short split. OI-delta reconstruction is
explicitly NOT acceptable as primary evidence (per task). I-2 is not pre-registered (no paper trials).
Consequence for I-3: leg (ii) forward *liquidation intensity* = **N/A(data)**.

**D4 — Deribit DVOL: PASS** (`get_volatility_index_data`, resolution="1D", data from index launch
~2021-03-24; probe returned OHLC vol bars for 2021-05) — **moot for this session** (F-1 STOP(prior)).

**Slippage sanity (live book, 2026-06-10, fapi depth, 100 levels):**
BTCUSDT spread 0.02 bps, ±1 bp depth ≈ $170k-830k/side → 1 bp at $10-50k clips conservative ✓.
SOLUSDT spread 1.6 bps, ±4 bp ≈ $700k/side ✓. APTUSDT spread 1.6 bps but **±4 bp visible depth only
$3-10k** → for mid-tier alts the global 4 bps is OPTIMISTIC at $50k clips; the I-1 cost gate therefore
also reports a 2× slippage stress column (sensitivity only — the pre-registered gate stays at the
global model).

## 3. Trial roster out of Phase 0

| Trial | Status | Registry impact |
|---|---|---|
| I-1 unlock drift | RUN (staged a-d) | +1 when run |
| I-2 cascade reversal | **STOP(data)** → `i2_data_memo.md` | +0 |
| I-3 funding extremes | RUN (I-4 gate; §6.35 prior cited) | +1 when run |
| I-4 carry overlay | conditional on I-3 pass | +1 only if run |
| F-1 VRP | **STOP(prior)** — vrp_deribit DECISION.md verbatim above | +0 |
