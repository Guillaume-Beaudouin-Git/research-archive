# RESULTS — CS macro momentum, FTMO-targeted (replication of a frozen pre-registration)

Contract: `PREREGISTRATION.md`, frozen and committed (`56c00558`) before any backtest.
Window `2013-10-01 → 2026-06-05`, 3 294 sessions, 17 instruments, true-UTC M1 estate.
Everything below was produced by `code/` in the order (a) panel → (b) V0 → (c) variants+vm → (d) kill rules.

---

## VERDICT — the family is CLOSED

**Two of the four pre-registered kill rules fire.** §6 is a disjunction, so one is enough.

| Kill rule | Threshold (frozen) | Measured | Verdict |
|---|---|---|---|
| 1 — placebo | V0 **and** V2 **and** V3 all ≤ demeaned placebo | V0 0.400 vs 0.278; V2 0.265 vs 0.254; V3 0.220 vs 0.256 | **not triggered** (V0 clears it) |
| 2 — two-sided (L25) | short leg not significant **at zero cost** | short leg **t_HAC = −0.90**, mean −0.85 bps/d, block-boot p = 0.822 — *wrong sign*; long leg t = +3.18 | **TRIGGERED** |
| 3 — β-orthogonality (L38) | R² > 30 % vs vol-targeted index B&H | R² = 15.5 / 16.2 / 22.5 / 14.6 % (V0/V1/V2/V3) | **not triggered** (but α_t = 0.28, see below) |
| 4 — gross vs cost (L43) | gross/rebalance < 1.5 × cost p95 | best ratio observed **0.98** (V1); V0 0.88; V3 0.36 | **TRIGGERED, all 8 runs** |

Decision metric at its own best point: **p(pass global) = 0.400** (V0, vm = 2.0), median
**118 days**, p90 **232 days**, MaxDD at that sizing **−33.8 %**. The source advertised
**65.7 %**. The gap is not a sizing question — it is the swap bill.

The one-line reason: **the signal is real and it is long-only.** At zero cost the long leg
earns +2.93 bps/day (t = 3.18); the mechanically symmetric short leg earns −0.85 bps/day
(t = −0.90). What survives is the long-side drift of indices and metals — L25, and behind it
L11/L38. And the vehicle taxes exactly that: holding four legs permanently on FTMO costs
**3.47 %/yr** in swap against **7.25 %/yr** of gross premium. L36, reproduced number for number.

---

## Deviations from the frozen spec — declared, none of them post-hoc repairs

1. **Universe size.** §2 heads the universe "16" but *enumerates* FX(7) + indices(4) +
   metals(3) + energy(3) = **17** names. The enumeration is explicit, the count is not.
   I traded the 17 enumerated instruments rather than drop an arbitrary one. The breadth
   haircut of §2 was applied as √(17/30) = 0.753 on every reported Sharpe.
2. **Swap anchors cover 4 symbols, not 17.** §4 anchors the swap on `measured_specs` of the
   frozen yaml v2.2.2. That block physically contains **XAUUSD, USDJPY, US100, GER40** only —
   the four legs of the live EA. A measured anchor for the other 13 does not exist in this
   repo and cannot be manufactured without a live broker read. Instead of assuming a number,
   the four anchors were **decomposed** into `fair financing` and `dealer markup`
   (`swap_long = fair − markup`, `swap_short = −fair − markup`) and the financing half was
   **rebuilt from observable 3-month rates** (`data/panels/fx_rates_3m.csv`). The
   reconstruction reproduces the measured carry on the two legs where it can be checked
   independently: US100 −0.989 vs −1.109 bps/night measured, USDJPY +0.641 vs +0.664.
   On gold it reconstructs −0.989 vs −0.591 measured, i.e. **1.7× more expensive than the
   broker** — conservative, kept as is. The markup half is time-constant (a 2026-06-10 read
   applied over 2013-2026); this is the weakest assumption in the study and is stress-tested
   (swap ×0 / ×1 / ×1.5) rather than defended. See `code/costs.py`.
3. **The panel's spread column is ~2.4× cheaper than the live account.** Measured on the four
   anchored legs, 2020+: live `rt_bps_legs` / panel-derived RT = 2.45 (XAU), 1.97 (USDJPY),
   2.28 (US100), 2.77 (GER40). Every result is therefore reported in **two cost modes** —
   `panel` (the literal §4 reading) and `anchor` (panel spread rescaled to the live RT
   anchors). `panel` is the friendlier one; the verdict does not depend on which is used.
4. **FX spread column is unpopulated over parts of 2021-2023** (EURUSD 70-79 % of bars zero,
   USDJPY 57-74 %, GBPUSD 29 % in 2022; indices and metals clean). A zero there is a missing
   measurement, not a free trade: it is replaced by the symbol's median over the sessions
   where the column *is* populated (`repair_zeros`). Without the repair, V0's spread bill
   would be understated by ~25 %.
5. **Points left open by §3, fixed a priori and never revisited:** rebalance days = Monday +
   Thursday; "score positif" read on the only signed component of the spec (an instrument in
   the top 4 is held only if `trend = sign(ret_60d)` is +1); the overlay's "vol réalisée 20 j"
   is the **book's own** trailing vol; `vm = 1` is a risk budget of 10 %-annual before overlay
   (realised vol is reported per vm so the unit is readable, not nominal).
6. **BTC** was excluded from the main window as §2 requires. The separate 2017+ measurement
   §2 contemplates was **not run** — the family is closed on the main window by two kill rules,
   and adding a trial would only deflate what is already dead.
7. Positions are held as fixed fractions of equity between rebalances (no intra-period drift
   accounting) — the standard convention in this repo, worth ~0 over 2-3 day holds.

---

## (a) Panel and data quality

One pass over ~5.5 GB of M1 (`code/build_panel.py`) → `cache/daily_*.parquet`, kept for reuse:
per UTC day, open/high/low/close, **median and p95 of the measured spread**, and the bar count.

**Calendar policy (a choice that matters).** Master calendar = weekdays where at least 4 of the
7 FX pairs printed a full session (3 294 days). An instrument that does not trade on a master
date has its close forward-filled: its return that day is 0, **the position is still held and
the swap is still charged** — what a real holder experiences over an index or commodity
holiday. Dropping those dates would have silently deleted holiday risk *and* holiday carry, in
a study whose whole question is carry. A session counts as non-trading when its bar count falls
below 20 % of the instrument's 63-day rolling median (the density criterion the deep-history
MANIFEST uses itself).

- All 17 instruments simultaneously open: **97.5 %** of sessions.
- Sessions closed per class (mean): FX 0.01 %, indices 0.99 %, metals 0.75 %, commodities 0.91 %.
- Missing closes after the policy: **0** on every instrument.
- No survivorship issue: all 17 exist over the whole window (US30/GER40 start 2013-09-30, which
  is what sets the §2 start date).

Measured spreads, median over the window (bps of price, one-way): EURUSD 0.16, GBPUSD 0.36,
USDJPY 0.26, AUDUSD 0.76, USDCAD 0.39, USDCHF 1.21, NZDUSD 1.51, US30 0.38, US100 1.24,
US500 1.51, GER40 0.72, XAUUSD 1.16, XAGUSD 6.33, COPPER 10.97, UKOIL 7.23, USOIL 7.95,
NGAS 35.09. Full table: `results/panel_quality.csv`, anchor check: `results/spread_anchor_check.csv`.

---

## (b) V0 alone — the cost ladder

Same signal, costs switched on one layer at a time (vm = 1, realised vol 8.7 %/yr — which
happens to sit right on the source's claimed 8.9 %, so this is an apples-to-apples comparison
with the advertised book):

| V0 configuration | Sharpe | CAGR | MaxDD | spread | swap |
|---|--:|--:|--:|--:|--:|
| gross (zero cost) | **0.846** | +7.25 % | −13.8 % | — | — |
| + measured spread | 0.758 | +6.44 % | −14.6 % | 0.77 %/yr | — |
| **+ swap (headline V0)** | **0.361** | +2.81 % | −17.9 % | 0.77 %/yr | **3.47 %/yr** |
| + spread at live anchors | 0.258 | +1.88 % | −19.4 % | 1.68 %/yr | 3.47 %/yr |
| + swap ×1.5 stress | 0.059 | +0.13 % | −21.4 % | 1.68 %/yr | 5.20 %/yr |

**The swap is 48 % of the gross premium.** Over the sample: gross +93.7 % of equity, swap bill
−45.3 %, spread bill −10.1 %.

Per-leg attribution (`results/leg_attribution.csv`), the L36 mechanism in the open:

| class | mean notional (% equity) | gross P&L | swap bill | net |
|---|--:|--:|--:|--:|
| FX | **53.2 %** | −7.8 % | −11.3 % | **−19.0 %** |
| indices | 34.3 % | +49.3 % | −22.7 % | +26.6 % |
| metals | 11.9 % | +52.5 % | −8.4 % | +44.0 % |
| commodities | 4.7 % | −0.3 % | −2.8 % | −3.1 % |

Inverse-vol sizing loads the low-vol legs: FX takes over half the notional, contributes
*negative* gross P&L and a quarter of the swap bill. This is L36 verbatim — "the killer is the
aggregate multi-leg carry, low-vol large-notional legs dominate" — and it is also why the
headline reads as a diversified macro book while the P&L is entirely indices + gold.

Note also **skew −1.26, excess kurtosis 15.8, worst day −7.83 % at vm = 1**: a single day already
breaches the −5 % daily barrier and comes within 2 points of the −10 % floor. That is the L24
"lumpy" profile — the wrong shape for a symmetric-barrier challenge, before any sizing choice.

---

## (c) The four variants × vm sweep — the decision metric

FTMO 2-step, static −10 % floor / −5 % daily, no time limit, `Portfolio/admission/barrier.py`,
**stationary block bootstrap** (Politis-Romano, mean block 10 d, 3 000 paths, paired seed).
`vm` scales the book; Sharpe is invariant to it by construction and is shown for context only.
Cost mode `panel` (the friendlier of the two); `anchor` in `results/vm_sweep.csv`.

| variant | vm | vol/yr | p(pass global) | median d | p90 d | MaxDD | Sharpe (net) | Sharpe ×√(17/30) |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| **V0** base, 2×/wk | 1.0 | 8.7 % | 0.207 | 241 | 359 | −17.9 % | 0.361 | 0.272 |
| | 1.5 | 13.1 % | 0.363 | 176 | 297 | −26.1 % | | |
| | **2.0** | 17.5 % | **0.400** | **118** | **232** | −33.8 % | | |
| | 2.5 | 21.8 % | 0.353 | 79 | 168 | −41.0 % | | |
| | 3.0 | 26.2 % | 0.318 | 57 | 129 | −47.8 % | | |
| | 5.0 | 43.7 % | 0.244 | 24 | 48 | −69.7 % | | |
| **V1** no vol overlay | 1.0 | 7.3 % | 0.145 | 269 | 407 | −13.3 % | 0.414 | 0.312 |
| | 2.0 | 14.7 % | 0.392 | 153 | 277 | −25.4 % | | |
| | **2.5** | 18.3 % | **0.395** | 110 | 229 | −30.9 % | | |
| | 3.0 | 22.0 % | 0.353 | 78 | 169 | −36.2 % | | |
| | 5.0 | 36.7 % | 0.280 | 32 | 68 | −54.5 % | | |
| **V2** monthly | 1.0 | 9.8 % | 0.145 | 224 | 339 | −28.9 % | 0.059 | 0.044 |
| | 2.0 | 19.5 % | 0.259 | 100 | 215 | −53.2 % | | |
| | **2.5** | 24.4 % | **0.265** | 72 | 161 | −63.0 % | | |
| | 5.0 | 48.8 % | 0.190 | 22 | 49 | −91.6 % | | |
| **V3** intraday-flat | 1.0 | 8.6 % | 0.071 | 259 | 373 | −36.6 % | −0.164 | −0.123 |
| | 2.0 | 17.3 % | 0.219 | 121 | 243 | −61.6 % | | |
| | **2.5** | 21.6 % | **0.220** | 80 | 175 | −70.6 % | | |
| | 5.0 | 43.1 % | 0.188 | 25 | 47 | −94.1 % | | |

At the live-anchor cost mode, V3 collapses further: Sharpe −1.01, best p(pass) 0.132, MaxDD −93 %.

**Death decomposition at each variant's best vm** (V0 @2.0): daily-barrier 22.0 %, static floor
32.8 %, timeout 5.2 %. The floor is the primary executioner at the sizing that maximises p(pass) —
raising vm buys speed by trading timeout deaths for floor deaths, and the trade stops paying at
vm ≈ 2. p(pass) never exceeds 0.40 anywhere on the grid, for any variant, in either cost mode.

**What each variant settled:**

- **V1** — *"the ranking is cosmetic, the edge lives in the overlay"* → **false, and the reverse
  is mildly true**: removing the overlay *raises* net Sharpe 0.361 → 0.414 and cuts MaxDD
  −17.9 % → −13.3 %, because the overlay adds turnover (66 → 52 ×/yr) and hence cost without
  adding return (both CAGRs are +2.81 %). The edge is in the ranking; the overlay is a cost.
- **V2** — *carry/rotation sensitivity* → **rotation is where the gross lives**: monthly
  rebalancing cuts gross Sharpe 0.846 → 0.423 while saving only 0.09 pt/yr of cost, since the
  swap (3.38 %/yr) is charged on *held* notional and is nearly rebalance-invariant. Slowing down
  does not escape L36; it only discards the signal. Net Sharpe 0.059.
- **V3** — *L36 escape via intraday-flat* → **retombe exactly on L33b, harder than expected**:
  zeroing the 3.47 %/yr swap costs 6.21 %/yr of spread (13.52 %/yr at live anchors), because
  flattening every night means paying a full round trip on the whole book 252 times a year
  instead of 104 partial ones. Turnover 265 ×/yr. Net Sharpe −0.164 (−1.01 at anchors). The
  escape hatch is more expensive than the thing it escapes.

---

## (d) Kill rules — each with its number

**1. Placebo (demeaned returns, same barriers, same sizing, same paths).** Not triggered: V0
beats its placebo 0.400 vs 0.278 (+12.2 pt, ≈ 15 MC standard errors) — the drift is real, the
p(pass) is not an artifact of path shape. But note V2 clears by +1.1 pt (≈ 1.4 SE, indistinguishable
from noise) and **V3 sits *below* its placebo** (0.220 vs 0.256): at intraday-flat cost, a
zero-mean series with the same shape passes the challenge more often than the strategy does.

**2. Two-sided, L25 — TRIGGERED.** Evaluated at **zero cost**, so the verdict is about the
signal and not the fee:

| leg (zero cost) | mean bps/day | t_HAC(6) | block-bootstrap p | Sharpe |
|---|--:|--:|--:|--:|
| long (top 4, trend > 0) | **+2.93** | **+3.18** | 0.0005 | 0.845 |
| short (bottom 4, trend < 0) | −0.85 | −0.90 | 0.822 | −0.252 |

The short leg is not merely insignificant, it is **negative**: shorting the worst-ranked
instruments *loses* money before any cost. The composite ranking does not identify a
directional edge, it identifies which instruments are drifting up. That is the definition of a
beta harvest under L25, and it is why the vehicle's long-side financing charge is fatal rather
than incidental — the strategy can only ever be on the side that pays.

**3. β-orthogonality, L38 — not triggered, but no alpha either.** Regression on a 10 %-vol-
targeted equal-weight buy-and-hold of the four indices, HAC(6):

| variant | β | R² | α (bps/day) | t(α) |
|---|--:|--:|--:|--:|
| V0 | 0.316 | 15.5 % | +0.24 | 0.28 |
| V1 | 0.271 | 16.2 % | +0.34 | 0.47 |
| V2 | 0.425 | 22.5 % | −1.13 | −1.24 |
| V3 | 0.302 | 14.6 % | −1.53 | −1.84 |

R² stays under the 30 % threshold, so this is formally not "index-beta timing". The honest
reading is weaker than a pass, though: **α is statistically zero** (t = 0.28 on V0). The sleeve
is not *explained* by index beta, and it is also not *distinguishable* from zero once index beta
is removed. Rule 3 does not fire; it does not exonerate either.

**4. Gross per rebalance vs 1.5 × cost p95, L43 — TRIGGERED on all 8 runs.**

| run | gross/period (bps) | cost mean | cost p95 | ratio | pass ≥1.5 ? |
|---|--:|--:|--:|--:|---|
| V0 panel | 7.41 | 4.21 | 8.46 | **0.88** | no |
| V0 anchor | 7.42 | 5.11 | 9.98 | 0.74 | no |
| V1 panel | 6.51 | 3.43 | 6.67 | **0.98** | no |
| V1 anchor | 6.51 | 4.13 | 7.86 | 0.83 | no |
| V2 panel | 36.43 | 30.69 | 68.15 | 0.53 | no |
| V2 anchor | 36.43 | 32.45 | 71.39 | 0.51 | no |
| V3 panel | 4.83 | 6.16 | 13.48 | 0.36 | no |
| V3 anchor | 4.78 | 13.42 | 30.37 | 0.16 | no |

Best observed **0.98** against a required 1.5. V3 lands at **0.36** — numerically identical to
the worst case recorded in L43 for retail FX intraday-flat. The pre-flight ratio was right.

---

## §7 — anti-illusion checks (the ones designed to catch *my* errors)

- **MaxDD.** V0 at the source's own volatility (8.7 % vs their 8.9 %) gives **−17.9 %** against
  their claimed −22.8 %, i.e. 78 % of it. Same order of magnitude, same left-tail shape
  (skew −1.26). The reconstruction is plausibly the same family — §7's "suspiciously shallow
  drawdown" trap does **not** fire. Had it come out at −5 % I would be reporting a broken
  reconstruction instead of a verdict.
- **p(pass).** Maximum over the entire grid (4 variants × 8 vm × 2 cost modes) is **0.400** vs
  the advertised 0.657. No result exceeded the suspicion threshold, so no cost/bootstrap
  re-audit was required on that count.
- **Bootstrap.** Stationary block bootstrap everywhere (barrier campaigns mean block 10 d;
  significance tests mean block 20 d). No iid resampling anywhere in the pipeline. The custom
  two-phase walker was cross-checked against `barrier.simulate_campaign` on identical seeds and
  reproduces it exactly (0.2105 vs 0.2105).
- **Deflation.** §8 requires DSR at **N1 = 4** in-family with a *measured* `std_sr_trials`.
  Measured across the four variants: **0.01706** per-observation, against the analytic H0 value
  1/√T = 0.01742 — the engine's default is correctly calibrated for this family, so the DSR
  figures stand as computed: **V0 0.598, V1 0.670, V2 0.201, V3 0.049**. None approaches 0.95.
  HAC(6) t-stats: 1.37 / 1.58 / 0.23 / −0.63. Walk-forward (5 folds): 80 % / 80 % / 60 % / 40 %.

**On the source's own numbers.** §1 already flagged that CAGR 21.4 % at vol 8.9 % cannot
coexist with Sharpe 1.04. The measurement adds a third contradiction: at that volatility, this
signal on this universe and window produces **7.25 %/yr gross of every cost**. The advertised
return is ~3× what the specified rules generate before a single fee is paid — the discrepancy
is in the claim, not in the cost model.

---

## Recommendation

**Close the family.** `cs_macro_momentum × deep_history_utc 2013-2026 × 17-instrument universe`:
family counter **N1 = 4** consumed (V0-V3), modification budget **0 of 3 consumed** — and no
modification should be spent here. The two rules that fired are structural, not parametric:

- **L25 (rule 2)** says the object is a long-only drift harvest, not a two-sided momentum edge.
  No filter, exit rule or regime overlay converts a t = −0.90 short leg into an edge; the three
  budgeted modifications would be spent decorating beta.
- **L43 (rule 4)** says the gross per rebalance is below the cost p95 in every configuration
  tested, including the two that were designed as escapes (V2 slower, V3 swap-free). The
  cost-ceiling is binding at 0.88-0.98× where 1.5× is required, and the only lever that moves
  the numerator — trading faster — moves the denominator faster still.

The mechanism is now measured rather than assumed: **L36 costs this book 3.47 %/yr against a
7.25 %/yr gross premium, and 53 % of the notional sits in FX legs that contribute negative gross
P&L and a quarter of the swap bill.** Inverse-vol weighting on a mixed macro universe is a swap
amplifier on FTMO. Any future proposal in this family must clear the cost gate *before* a
backtest is written.

Two findings worth carrying beyond this study:

1. **The deep-history spread column understates the live FTMO round trip by ~2.4×** (measured on
   the four anchored legs, 2020+). Any prior study that costed a CFD strategy from that column
   alone is optimistic by that factor. Uplift ratios are in `code/costs.py::ANCHOR_UPLIFT`.
2. **The FX segment of the estate has an unpopulated spread column over parts of 2021-2023**
   (EURUSD 70-79 % of bars). Consumers that average it without a zero-repair are understating FX
   costs materially over that window.

---

## Reproduction

```bash
cd <HOME>/Desktop/Algo_claude
/usr/bin/python3 -m yt_strategy_replications.cs_macro_momentum_ftmo.code.build_panel   # ~12 min, once
/usr/bin/python3 -W ignore -m yt_strategy_replications.cs_macro_momentum_ftmo.code.qc
/usr/bin/python3 -W ignore -m yt_strategy_replications.cs_macro_momentum_ftmo.code.run_v0
/usr/bin/python3 -W ignore -m yt_strategy_replications.cs_macro_momentum_ftmo.code.run_all
/usr/bin/python3 -W ignore -m yt_strategy_replications.cs_macro_momentum_ftmo.code.diagnostics
```

`code/` — `build_panel.py` (M1→daily cache), `panel.py` (alignment + calendar policy),
`costs.py` (spread / commission / swap), `strategy.py` (signal + P&L, T-1→T enforced),
`analysis.py` (metrics, campaign, kill rules), `run_v0.py`, `run_all.py`, `diagnostics.py`.
Read-only dependencies: `yt_strategy_replications/engine/stats.py`,
`Portfolio/admission/barrier.py`, `Portfolio/admission/marginal.py`, `ftmo_live/lib/spec.py`,
`data/deep_history_utc/`, `data/panels/fx_rates_3m.csv`.

`results/` — `panel_quality.csv`, `spread_anchor_check.csv`, `v0_cost_ladder.csv`,
`v0_campaign.json`, `variant_metrics.csv`, `variant_series.parquet`, `vm_sweep.csv`,
`kill_rules.json`, `leg_attribution.csv`.
