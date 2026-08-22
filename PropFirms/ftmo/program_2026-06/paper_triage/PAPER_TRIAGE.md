# Paper-corpus triage — orthogonality to the proven-exhausted box

**Date:** 2026-06-08 · **Task:** READ + CLASSIFY the gathered paper corpus into A (closed-box reject) /
B (structurally orthogonal, testable) / C (method/tooling), filtered by **one** criterion: structural
orthogonality to what is already proven exhausted. **No backtests, no fabricated results.**

**The CLOSED BOX (do not re-enter; 4 converging negatives, cumulative N≈97):** an edge on **free price
data** / the **16 FTMO instruments** / at **daily-and-coarser OR sub-60min index reversion** / under the
**symmetric FTMO barrier** / net of **real costs**. TSMOM + Ross Hook are *real but sub-threshold* — their
killer is **overnight CFD swap + the symmetric barrier**, not signal absence (see `ftmo_survivors_book/`,
`ftmo_portfolio_audit/`, `ftmo_candidate_funnel{,_v2}/`, `edge_improvement/`). Classification is by
**structure**, NOT the paper's claimed Sharpe (published Sharpes decay ~50% OOS, McLean-Pontiff).

**Corpus sources read:** the project's own triage of the 75 REQUIRES_HUMAN items
(`_automation/feasibility/triage/REQUIRES_HUMAN_triage_2026-06-02.md`); PRs **#141** (3 new items + weekly
synthesis) and **#142** (digest, RH-queue=82); arxiv analyses `_automation/arxiv/2026-05-25_analysis.md`
& `2026-06-01_analysis.md`; the q-fin scan `_automation/arxiv/_raw/2026-06-01.xml`; and an
orthogonal-keyword sweep of all 103 `_automation/alpha_hunt/promising/` items.

> **Headline:** under *this* lens the corpus collapses hard. ~**80% is bucket A** (price signals / regime
> overlays / archived families) and most of the rest is **bucket C** (methodology). Only **~3 ideas rest on
> something the 97 trials never touched** (a new data source / a swap-free container). Critically, the prior
> triage's own top "CANDIDATE"s — **C1 (NQ trailing-SL) and C2 (HMM regime filter)** — are **bucket A here**:
> both are free-price-data NQ signals/overlays under the symmetric barrier. Only its C3 (FINRA short-volume)
> survives as orthogonal.

---

## 1. Bucket A — IN THE CLOSED BOX (reject; which prior result covers it)

These cannot escape the proven ceiling. Grouped by structural sub-motif.

| Cluster (representative items) | Why it's in the box | Prior result that already covers it |
|---|---|---|
| **NQ intraday signal variants** — `…trailing-SL iter_11` (triage C1), generic ORB/gap/momentum (#2605.04004 MNQ falsification) | free-price NQ intraday under symmetric barrier; iter_10 *already invalidated* | `strategy_c_iter10_validation_2026-06` (SR 1.52→0.51, p_pass 24%, DSR fail); the MNQ paper **confirms** the box |
| **Regime overlays on existing edges** — `HMM regime filter D3+D5` (triage C2), #2605.27848 HMM+RL, `quantinsti_market_regime_hmm`, `regime_based_allocation`, `k_means_pca_NQ`, `surfing_equity_curve`, `unsupervised_learning` | a regime *filter* on a free-price-data edge is still inside the box; L15 = sub-threshold lift | L15 (regime overlays: ~+1.7%/yr, only matter for MaxDD>20%); `orb_regime_2026-06` (no forward predictor passes \|t\|>1.5) |
| **Strategy-A-v4 mods** — `tweedie v1/v2`, `egarch`, `active_dual_momentum_gtaa`, `rethinking_trend_following`, `why_momentum_struggling` | vol/regime overlays on existing crypto TSMOM (free price) | A FROZEN; these are 3-mod-budget items, not box-escapes |
| **Daily momentum / allocation / GTAA / TAA** — `donchian_channels`, `dual_momentum_gold_btc` (×2), `selecting_TAA` (×3), `revisiting_60/40`, `beyond_60_40` | free-price daily momentum/allocation on liquid ETFs | Commodity-TSMOM-ETF archived (AMTP p=0.808); gold-BTC dual-mom **pre-flight L11 FAIL** (gross 0.85% < 3×cost) |
| **Pairs / stat-arb** — `cointegrated_pairs`, `the_metamorphosis` | price cointegration | Pairs archived (0/19 qualify; Gatev SR −0.44) |
| **FX price signals** — `ai_forex_llm_regime_labels`, `eur_hedge`, `currency_you_didnt_choose` | FX price/regime; USD-base | FX archived n=181 (FX-1→4, Strategy E, L23) |
| **VRP / options-pricing as price-vol** — `vrp_intraday_overnight_clustering`, `option_pricing_SV_jumps` (#2606…PIDE), `vol_surface_DL`, `implied_vol_solvers` (×2) | VRP family archived; pricing-precision ≠ economics | L13 (BTC VRP gross 4.4% < cost 8.9%; SPX VRP IC negative) |
| **Insider / prediction-markets / EM-equities / sentiment-attention** — `insider_trading_alpha_decays`, `who_profits_prediction_markets`, `a_century_without_data` (×2), `attention_factor`, `sentiment_is_not_one_signal` | archived/closed angles or no infra; attention-sentiment exhausted | L17 (FGVD), L18 (Wikipedia attention) — Da-et-al taxonomy exhausted |

**Ruthless note:** ~58 of the 75 RH items + the two HMM arxiv papers land here. The prior triage kept
C1/C2 as "CANDIDATE" on a *path-management / L15* rationale; under the **orthogonality** lens they are
rejects — neither breaks a wall of the box (still free price data, still FTMO/NQ, still symmetric barrier).

---

## 2. Bucket C — METHOD / TOOLING (route to the audit toolkit, not the strategy pipeline)

Not edges; they harden rigor or optimize an *existing* sleeve.

| Item | What it improves | Route to |
|---|---|---|
| **Post-selection Sharpe estimation** `#2606.01650` (task-named) | de-biases the selected-strategy Sharpe → **hardens DSR / L20** | `ftmo_portfolio_audit/code` (firstpassage/DSR) |
| **Non-linear costs of trading** (Concretum, PR #141 `…non_linear_costs…`) | market-impact cost model | enrich `sizing_analysis.py` (L19 slippage) |
| **Crossword puzzle of fitting** (Rob Carver, PR #141) | cross-sectional vs time-series fitting order | methodology note (no edge) |
| **Retrospective simulation / Brownian-bridge path gen** (`quantinsti_retrospective_simulation`) | path generator | `Portfolio/risk/trailing_dd_simulator.py` (L22 calibration) |
| **Spot-perp basis rebalancing** `#2605.05089` | asymmetric rebalance frontiers for **existing Strategy B** | B mainnet prep (~Jul-2026); *not FTMO* |
| **Effective-N / backtests-lie / WF-correlation / conformal / heavy-tails / risk-parity-audit / DPO / Bayesian allocation** | AMTP, stress, allocation tooling | already covered by DSR/HAC/trailing_dd_simulator — low priority |

---

## 3. Bucket B — STRUCTURALLY ORTHOGONAL (testable) — ranked shortlist

Each rests on **≥1 thing the 97 trials never covered**. Ranked by (orthogonality × retail-feasibility ×
cost-to-test). **Data-we-don't-have is flagged, NOT auto-rejected.** The decisive pre-test question is the
one that must be answered *before* any backtest.

### B1 — FINRA short-volume → overnight NQ direction  ★ top pick
*(triage C3; `quantocracy_when_short_sellers_create_overnight_alpha` — Concretum)*
- **Walls broken:** (a) **new free data source** (FINRA Reg SHO daily short volume — never used); (b) the
  **overnight close→open axis** (orthogonal to the daily/sub-60min-reversion box); (c) on **NQ *futures*** an
  overnight hold pays **no CFD swap** → structurally dodges the named killer, *if* run on a container that
  allows the overnight Globex hold (the prop-firm scan flagged **MyFundedFutures**, 6 PM→4:10 PM ET, no swap).
  Bonus: the survivors-book work already found a **real midweek NQ overnight edge** (+4.9 bps, t=4.04,
  `overnight_verification_2026-06`) — a confirmed live axis to build a *directional* signal on top of.
- **Orthogonality HIGH · feasibility HIGH · cost-to-test MED.**
- **DECISIVE pre-test question:** *Does a replicable spec give a numeric IC, and does the FINRA J+1
  short-volume → next-session NQ-futures transfer survive retail-tier costs ($4-6/RT overnight slippage) at
  N≥50/yr?* (the equities-short→index-futures transfer is the load-bearing assumption.)
- **Required data:** FINRA Reg SHO daily CSV (free, 2009+) + **survivorship-corrected historical QQQ
  constituents** (the real acquisition cost) + NQ overnight OHLC (local `Dataset_NQ_1min`).

### B2 — Options-implied (put-call disparity / skew) as a directional/regime signal
*(PR #141 `…research_review_5_june_2026…` — put-call disparity bubble detection, Jarrow-Kwok)*
- **Wall broken:** **options-implied data** (put-call ratio / implied skew) — a data source the 97
  price-only trials never used. Targets NQ or crypto.
- **Orthogonality HIGH · feasibility MED · cost-to-test MED.** *Caveat:* framed as bubble/**regime**
  detection — risk of collapsing into a bucket-A regime overlay unless it yields a *standalone* directional
  edge.
- **DECISIVE pre-test question:** *Can we obtain a clean, long historical put-call / implied-skew series
  cheaply for a tradable underlying (CBOE equity/index PCR & VIX-family — free; or Deribit BTC/ETH options —
  free API), and does it predict **direction/forward return** rather than just realized vol?*
- **Required data:** CBOE put-call ratios + VIX term structure (free) **or** Deribit options chain (free API).

### B3 — Event-microstructure: earnings/announcement-day direction
*(arxiv q-fin `Predicting Stock Price Direction on Earnings Announcement Days, Multi-modal DL`)*
- **Wall broken:** a **new return source** (scheduled-event microstructure) + **alt-data** (multimodal),
  not price momentum/reversion. (The project's pre-FOMC-drift finding shows scheduled-event drift *can* be
  real — `ftmo_top10_rigorous_2026-06`, L42 candidate.)
- **Orthogonality MED-HIGH · feasibility LOW · cost-to-test HIGH** (equities universe + earnings calendar +
  the per-name edge is sparse → needs breadth; the paper's multimodal-DL is over-infra for retail).
- **DECISIVE pre-test question:** *Is there a low-infra, retail-executable reduction — e.g. index-level
  pre/post-earnings-season drift or a single-name event-drift on FTMO-listed stock CFDs — that captures the
  effect without per-stock multimodal DL?*
- **Required data:** earnings calendar (free-ish) + equities intraday (don't have at scale) — **FLAGGED**.

### B4 — Central-bank / monetary-policy text sentiment
*(`arxiv…monetary_policy_in_the_media_spotlight`; `quantocracy_lazy_prices` 10-K NLP as a sibling)*
- **Wall broken:** **alt-data text** edge (central-bank language / 10-K textual change) — orthogonal to
  price. *Distinct* from the exhausted attention-velocity sentiment (L17/L18 were Wikipedia/F&G *attention*,
  not policy-text *content*); and pre-FOMC drift is independently real.
- **Orthogonality MED · feasibility LOW · cost-to-test HIGH** (no NLP pipeline; the project closed
  low-infra sentiment but not a *content* pipeline).
- **DECISIVE pre-test question:** *Can a **pre-built, published** hawkishness/sentiment index (off-the-shelf,
  e.g. a central-bank-communication index) be used as the signal — avoiding building a bespoke NLP pipeline?*
  If only a bespoke pipeline works → **BACKLOG**, not test.
- **Required data:** a published FOMC/ECB-tone index **or** SEC EDGAR 10-K corpus + NLP — **FLAGGED**.

*(Shortlist capped at 4 with real orthogonality; B3/B4 are orthogonal-but-data-blocked → flagged, not
auto-rejected, per the hard rule. No 5th/6th idea in the corpus clears the orthogonality bar without also
being archived or pure tooling.)*

**Ranking:** **B1 ≫ B2 > B3 ≈ B4.** B1 is the only idea that breaks **three** walls at once (new data +
overnight axis + swap-free futures container) *and* has free data + a confirmed adjacent live edge. B2 is the
cleanest *new-data* test with cheap free data but risks being a regime overlay. B3/B4 are genuinely
orthogonal return sources but **gated on data/infra we don't have** — they belong in B (flagged) so they
aren't lost, not in A.

---

## 4. Explicitly rejected for RE-ENTERING the closed box

The following were attractive on the *prior* (pre-orthogonality) triage but are rejected here precisely
because they stay inside the proven-exhausted box:

- **Trailing-SL NQ iter_11** (prior triage P2/C1) — free-price NQ intraday, symmetric barrier; iter_10
  already invalidated; "path management" is not a wall-break (`orb_pushpass_2026-06`: K5's gain was path
  management, DSR-fail).
- **HMM regime filter on D3+D5** (prior triage P1/C2, #2605.27848, quantinsti HMM) — a **regime overlay on
  existing free-price NQ edges**; explicitly the closed box; L15 caps the lift.
- **All Strategy-A-v4 vol/regime mods** (tweedie, EGARCH, active-dual-momentum, rethinking-trend, surfing-
  equity-curve, why-momentum-struggling) — overlays on free-price crypto TSMOM, inside the box.
- **GTAA / dual-momentum / Donchian / TAA-selection** — free-price daily momentum/allocation; GTAA-ETF +
  commodity-TSMOM-ETF archived; gold-BTC dual-mom fails pre-flight L11.
- **Cointegrated pairs / "Metamorphosis"** — pairs archived (0/19, Gatev SR −0.44).
- **VRP-clustering / option-pricing precision / vol-surface DL** — VRP archived (L13); better pricing math
  doesn't change the economics.

---

## 5. Honest limitations

- **Classification is structural, not empirical** — no backtests run, no Sharpes recomputed; bucket A
  rejections lean on the documented prior negatives (cited by lesson/memory), bucket B is *potential*
  orthogonality, not validated edge.
- **Two PR #141/#142 items not deep-read** (the put-call report rendered empty to the fetcher; the
  non-linear-costs report) — classified from the PR-body summaries; B2's exact mechanism needs the full
  article before pre-registration.
- **Corpus is mostly methodology/RSS noise** — the arxiv-econ.em scraper over-collects econometrics method
  papers (forecasting/conformal/GARCH variants) that are neither edges nor relevant tooling; counted under A
  (archived/closed) or C (method) without individual deep-reads where the title is unambiguous.
- **Bucket-B data costs are estimates** — FINRA is free but survivorship-corrected QQQ constituents and any
  options/NLP history carry real acquisition cost/effort; each B item's decisive question is precisely the
  *data-feasibility* gate that must clear before a full backtest.
- **No new strategy was pre-registered here** — that is deliberate (anti-data-snooping); B1 would be the
  first to advance, and only after its decisive question (FINRA→NQ transfer + numeric IC) is answered.
