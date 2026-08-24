# AUDIT — Anatomie des busts FUNDED + cash-flow mensuel (funded_anatomy_2026-07)

Independent auditor (author≠auditor). Adversarial re-derivation with `/usr/bin/python3`. Every number
below was re-computed **by the auditor** from the raw `tables/*.csv`, the canonical
`panel_rets.parquet`, and by **re-running the engine** (self-EQUIV re-run + a step-density sweep + a
clean-room re-implementation of the cash-flow MC) — **not** by trusting `aggregate_*.py`/`cashflow.py`.

## VERDICT: **CONFIRM-WITH-CAVEATS**

All five claim-blocks reproduce: the self-EQUIV gate re-passes bit-for-bit (382 runs, 0 divergence),
the baseline (58/30.4%/EV +$677) is engine-reproducible, the whole anatomy, all Volet-2 overlay Δ/EV
with CIs, and the entire cash-flow decomposition (including the vm0.85 link and scaling) reproduce to
rounding / MC noise. **No computational bug alters any headline.** The caveats are (a) one real,
undisclosed **pre-registration deviation** (anatomy run at step 12, not the pre-registered step 6) that
makes the flagship "**3 unique days**" undercount by one — the density-converged count is **4** (adds
2016-11-09); (b) a **cosmetic label swap** in the §1 narrative (the 2015 and 2021 leg tags are
inverted); (c) a **NaN artifact** behind the "0.00" gold vol-percentile. None of these overturn the
mechanism or the numbers; all three run mildly *in favour* of the cleaner story, so they warrant
"with-caveats", not CONFIRM. Nothing warrants REJECT.

---

## 1. Independently reproduced (auditor numbers vs claim)

### 1.1 Self-EQUIV (Scrutiny A) — **re-run, PASS**
- Re-ran `run_v0_equiv.py`: **382 runs (191 starts × {close, low}), 0 divergence** on
  (busted, wd, payouts, life, residual) [36 s]. Matches claim 1.
- Code-level confirmation the clone is a **true no-op wrapper**: diffing `run_funded_anat` against the
  audited `LC.run_funded` line-by-line, the *only* differences are observation-only — `bal_start`/
  `gap_day` locals, the `bust_log`/`wd_log` appends, and an `amt` temp identical to `bal-INIT`. **No
  control-flow or return change.** The overlay gates (`gold_gate`/`jpy_gate`) are applied **externally**
  to the weight matrix `WT` in `run_all_funded.py::wt_for` (exactly like the J1 gate), **not** inside
  the clone — which is precisely why self-EQUIV holds. (See D5: the engine docstring misdescribes this.)

### 1.2 Baseline reproduces real_metrics (Scrutiny A) — **engine-reproduced**
- `runs_baseline.csv`: **191 runs, 58 busts, 30.37 %**, E[extr] **$1661.1**, VAL **$1424.9**,
  EV **+$677.3** (`0.697·1424.9 − 3.29·96`). Matches "58 / 30.4 % / +$677".
- Closing the loop: I **re-ran the funded engine at step 12** (gate ON, low, vm1) → **58 busts, 3
  unique days**, bit-matching `busts_baseline.csv`. The raw bust log is genuinely engine-produced.

### 1.3 Volet 1 anatomy (Scrutiny B, C) — from `busts_baseline.csv`
| dimension | auditor | claim | match |
|---|---|---|---|
| unique bust days (`date.nunique`) | **3** (2015-08-24 ×4, 2021-01-07 ×22, 2023-12-07 ×32) | 3 | ✓ (but see D1) |
| daily vs max-loss | **57 / 1 = 98.3 % daily** | 98.3 % | ✓ |
| median day-loss | **$509.5** (54/58 ∈ [500,520]; **4 deep >$550, all 2015-08-24**, max $661.7) | $510 | ✓ |
| dom-leg | **USDJPY 36 / XAUUSD 22** | 36 / 22 | ✓ |
| type | **at_open 0.0 % (100 % intraday), gap 6.9 %** | 100 % intraday | ✓ |
| life | **median 169, q25 89, q75 254, min 1** | 169/89/254/1 | ✓ |
| payouts | **93.1 % ≥1 payout, median banked $1161** | 93 %, $1161 | ✓ |
- The single **max_loss** bust is on **2021-01-07** (dom XAU, day-loss $500). The 3 dates are real
  market-stress days (see 1.4).

### 1.4 Regime mechanism (Scrutiny E) — recomputed from `panel_rets.parquet`
Causal 20d-realized-vol percentile of the **dom leg** as of T-1:
| date | dom leg | auditor volpct | note |
|---|---|---|---|
| 2015-08-24 | USDJPY | **0.413** | China "Black Monday": JPY −2.75 %, AUDJPY −5.1 %, gold only −0.49 % |
| 2021-01-07 | XAUUSD | **0.318** (robust) / 0.00 raw | gold −3.36 %, JPY *+0.76 %*; raw 0.00 is a NaN artifact (D3) |
| 2023-12-07 | USDJPY | **0.359** | BOJ-pivot: JPY −2.04 %, EURJPY −1.81 % |
- **Median 0.36, max 0.41, 0 % > p80** — matches "median 0.36, 0 % > p80". The market moves confirm
  the dom-leg attributions are **economically correct**, and hence that the §1 tags are inverted (D2).

### 1.5 Volet 2 overlays (Scrutiny D) — re-derived from `runs_*.csv`
| overlay | busts | Δbust pp [CI90 seed23] | EV | ΔEV | saved/harmed/both | match |
|---|---|---|---|---|---|---|
| baseline | 58 | — | +$677.3 | — | — | — |
| gold_gate | 58 | **+0.00** [−1.0,+1.0] | +$715.4 | **+$38** | 1 / 1 / 57 | ✓ net-0 |
| jpy_gate | 65 | **+3.66** [+0.0,+9.4] | +$547.8 | **−$130** | 0 / 7 / 58 | ✓ harmful |
| **vm085** | **4** | **−28.27** [−44.0,−13.6] | **+$833.9** | **+$156.5** | **55 / 1 / 3** | ✓ Pareto |
| vm070 | 0 | −30.37 [−45.0,−16.2] | +$701.4 | +$24 | 58 / 0 / 0 | ✓ |
| vm050 | 0 | −30.37 [−45.0,−16.2] | +$659.8 | −$18 | 58 / 0 / 0 | ✓ |
- **vm085 Pareto is real, not a VAL artifact.** VAL rises **only** because E[extr] rises $1661→$1942:
  converting 55 busted (extr≈0) runs into survivors outweighs the −15 % per-trade gain. vm085 is also
  the EV-max of the whole grid (inverted-U: 0.70→$701, 0.50→$660). CI **[−44.0,−13.6] excludes 0** and
  is seed-stable (seed777 [−43.5,−14.1]).
- **Paired accounting verified** (same `run_id` set, asserted in code): the 4 vm085 busts are
  {396, 408, 420, 492}, **all on 2015-08-24** (the deep-breach day; vm085 shrinks its day-loss to
  $501–555 but 3 still clear $500). The lone **harmed** run is **396** (start 2015-04-09) — survived at
  vm1, busts at vm0.85 by genuine path-dependence. So saved 55 / harmed 1 / both 3 → 4 busts. Exact.
- **Mechanism verified**: gold-gate can't arm on the 2021-01-07 gold bust (dom-leg vol low + holiday
  NaN → flag False), so it saves 0 of the 22 gold busts (net-0); jpy-gate removes JPY carry/trend on
  616/627 high-vol days that contain **none** of the 3 shock days → strictly harmful. "Gates can't
  catch a calm-then-shock tail; sizing can" holds.

### 1.6 Volet 3 cash-flow (Scrutiny F) — **independent clean-room MC** (I re-implemented `one_campaign`)
| metric (BASE vm1) | auditor (seed23) | seed999 | claim |
|---|---|---|---|
| break-even month | med **5**, p10 2, p90 16 | 5 / 2 / 16 | 5 / 2 / 16 ✓ |
| never in 24 mo | **31.2 %** | 32.0 % | 31 % ✓ |
| cum @24 mo | med **$522**, p10 −$646, p90 $3173, **mean $907** | $510 / −$664 / $3169 | $522 / −$646 / $3173 ✓ |
| P(>0) | **65.6 %** | 65.3 % | 66 % ✓ |
| $/month funded | med **$197** | $197 | $197 ✓ |
- **EV-consistency check passes**: mean cum24 **$907 ≈ 1.43 campaigns × EV $677 = $968** (small gap =
  fee-lumping + 730-day truncation). The 31 % never-positive is **not** in tension with the 69.7 %
  challenge pass — the latter is per-attempt (the enterprise rebuys to near-certain funding); the 31 %
  is driven by funded busts (30 %) + fee drag (mean 3.29 att × $96) + 24-mo truncation. **No
  double-counting / refund bug**: fee refund is +$96 once per funded account (not per attempt), fees
  lumped at campaign start (declared conservatism).
- **vm085 link** (my MC): cum24 med **$730** (claim $732), P(>0) **69.3 %** (claim 69 %), p10 **−$549**
  (claim −$511, MC/impl noise), $/mo **$194** (claim $192) → Pareto on cash-flow **confirmed**.
- **Scaling** (my MC): cum24 med **$719** (claim $714), p90 **$5282** (claim $5319), BE **5** → upside-
  only, break-even unchanged. **Discounting** 0.5 %/mo: BE of the *mean* series month 9 nominal = month 9
  discounted (unchanged) ✓; the med-draw BE (5) vs mean BE (9) gap is the disclosed skew/non-funder gap.

---

## 2. Discrepancies / bugs

No bug changes a headline. Five issues, in descending importance:

- **D1 — Pre-reg deviation on step density → "3 unique days" undercounts (the substantive one).**
  Pre-reg §1 explicitly specifies **step 6 (≈380 starts) "pour la couverture de l'anatomie"**. The
  study ran the anatomy (and self-EQUIV, and overlays) at the canonical `FUNDED_STEP=12` (191 starts).
  I re-ran the baseline sweep at 12 / 6 / 3:

  | step | starts | busts | rate | **unique days** |
  |---|---|---|---|---|
  | 12 (used) | 191 | 58 | 30.4 % | **3** |
  | **6 (pre-reg)** | 380 | 120 | 31.6 % | **4** — adds **2016-11-09** |
  | 3 | 759 | 237 | 31.2 % | **4** (converged) |

  The rate/EV are density-stable, but the flagship anatomy count is **not**: at the *pre-registered*
  density it is **4**, not 3. The 4th day (2016-11-09, US-election night) is a **single, weak
  intraday max_loss** bust ($310 drift, dom XAU, vol-pct 0.09) — fully consistent with the low-vol /
  intraday narrative, but a distinct 4th event that step-12 undersampling drops. This deviation is
  **undisclosed** and runs *in favour* of the cleaner "3 days" headline. Recommend restating as
  "**3–4 unique days (density-dependent)**" and noting the step-12-vs-pre-reg-step-6 deviation.

- **D2 — §1 narrative leg labels are inverted (cosmetic).** The STUDY §1 "3 jours uniques" row reads
  "**2015-08 (OR, déval. Chine) · 2021-01 (JPY)**". The data say the opposite: **2015-08-24 =
  USDJPY-dominant** (gold moved only −0.49 % that day) and **2021-01-07 = XAUUSD-dominant** (JPY was
  *+0.76 %*, gold −3.36 %). The author's own `unique_bust_days.csv` has the **correct** dom_leg, and the
  aggregate "USDJPY 36 / XAU 22, 1 OR day + 2 JPY days" is correct — only the two day↔leg tags in that
  one prose row are swapped. Fix the labels: 2015-08 = JPY, 2021-01 = OR.

- **D3 — gold vol-pct "0.00" is a NaN artifact (cosmetic).** `unique_bust_days.csv` reports
  `volpct_dom = 0.000000` for 2021-01-07 XAU. The trailing-20 gold window (to 2021-01-06) holds **4
  holiday NaNs** (Dec 25, Dec 28, Jan 1, Jan 4), so `rolling(20).std()` → NaN and `(NaN > win).mean()`
  → 0.00 (spurious 0th percentile). Robust recompute (`min_periods=15`) = **0.318**. The headline
  median (0.36) and "0 % > p80" are **unchanged** (the JPY day is the median), so the mechanism holds —
  but any reading that the gold day sat at the absolute vol floor is an artifact; the true value is
  "moderately low (~0.32)".

- **D4 — `overlay_summary.json` `E_extr` column is a simple mean, not the VAL input (cosmetic).**
  `val_ev` correctly builds VAL from the IS/OOS-**balanced** E[extr], but the row's `E_extr` field
  prints `d.extr.mean()` (simple mean). The two differ (e.g. vm085 1941.9 vs 1975.1) but **VAL/EV are
  computed from the balanced value and are correct** (VAL identical in `meta_funded.json` and
  `overlay_summary.json`). Display-only mismatch.

- **D5 — `funded_anat_engine.py` docstring misdescribes the code (harmless).** The docstring claims the
  clone "Adds … `cfg["gold_gate"]/cfg["jpy_gate"]` boolean per-date masks applied as weight
  suspension". The clone body contains **no** such logic; the gates are applied externally to `WT` in
  `run_all_funded.py`. The docstring is stale/aspirational — but the *absence* of gate logic in the
  clone is exactly what makes self-EQUIV pass, so this is benign. Fix the docstring.

---

## 3. Reservations

- **R1 (small-N, the important one).** The whole anatomy rests on **3–4 historical days over 13 years**
  (D1). The author does prominently disclose the "N=3 événements uniques" caveat (§1, §4b, §6). Reader
  must not over-read a 3–4-day pattern; a future 4th/5th day could differ in character (the 2016-11-09
  day is already a *different* mechanism — a drift/max_loss, not a fresh daily shock).

- **R2 (vm correctly SIGNALED-not-decided).** The pre-reg §3c ("CHIFFRER … NE PAS trancher") and STUDY
  §2/§4c ("vm — SIGNALÉ, NON TRANCHÉ") honour the instruction not to decide vm. Good. But the **exact
  0.85 threshold is a low-check knife-edge**: 54/58 busts sit at day-loss $500–520, so whether ×0.85
  ($425–442) "clears" $500 hinges entirely on the ~$10–20 the low-check *overestimates* the loss by.
  The **direction** (de-lever ↓ tail) is robust; the **level** 0.85 is not. The author declares exactly
  this (§2 last bullet, §6).

- **R3 (low-check overestimate caveat is load-bearing and IS applied).** Because 54/58 busts are
  marginal, the entire "vm0.85 converts them" result depends on the low-check's $509.5 being a **high
  bound** vs a real liquidation ≈ $500. Author states this (§1 note, §6). Consequence: if real
  liquidation ≈ $500, an unknown share of the 54 marginal "busts" are borderline non-busts at vm1
  already — i.e. both the 30.4 % baseline and the vm0.85 conversion are the most bid/M5-sensitive
  numbers in the study. (Inherited R4 of the real_metrics audit.)

- **R4 (prospective gap, inherited).** Sample ends **2026-06-05**, excluding the in-zone intervention
  flashes (2026-07-02/03) that motivated the gate. The 0 %-in-zone tail and the null in-sample gate
  value are partly a **sample thin in the intervention regime**; the gate's value is explicitly
  prospective and is not folded into any number here. Correct framing (same as the sibling audit R1).

- **R5 (leg coverage, inherited).** US100/GER40 lohi coverage 83–84 % (missing bars → lo=hi=close, no
  adverse) may marginally understate those two legs' tail. The two dominant carriers (USDJPY 99.9 %,
  XAU 94 %) are well covered, so the headline is unaffected.

---

### Auditor's re-derivations, in one place
self-EQUIV **382/0 PASS (re-run)** · baseline **58 / 30.37 % / EV +$677.3** (engine-reproduced) ·
anatomy **3 days / 98.3 % daily / $509.5 / JPY36-XAU22 / life 169 / 93.1 % payout** · regime **0.36
med, 0 % > p80** (gold robust 0.32) · overlays **gold +0.0pp/+$38, jpy +3.66pp/−$130, vm085
−28.27pp[−44,−13.6]/+$156.5 saved55-harmed1-both3, vm070/050 → 0** · cash-flow **BE 5 / 31.2 % never /
cum24 $522 (mean $907) / P(>0) 65.6 % / $197-mo**, vm085 **$730 / 69.3 %**, scaling **$719 / BE 5**.
**Only deviation from the report of consequence: the pre-registered step-6 density yields 4 unique bust
days, not 3.**
