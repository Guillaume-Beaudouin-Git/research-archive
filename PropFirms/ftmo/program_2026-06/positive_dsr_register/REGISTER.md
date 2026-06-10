# Positive-DSR register — what genuinely works but falls short of the propfirm bar

> **Trial-count ledger (appended; the collation below is frozen as of 2026-06-09, N=108):**
> 2026-06-10 announcement_premium +4 → 112 · backwardation_oil +3 → 115 · session_H +0 (double
> STOP Phase 0) · **session_I_crypto_flows +2 (I-1 unlock drift NO-GO K2/K3; I-3 funding extremes
> FAIL; I-2 STOP-data, F-1 STOP-prior, I-4 void) → N = 117** —
> `Crypto/research/active/session_I_crypto_flows/report.md`. NB: I-1's event series carries DSR 0.94
> standalone but is **beta-in-disguise** (below placebo median) — it does NOT join the tables above.

**Date:** 2026-06-09 · **Type:** READ-ONLY collation of *already-computed* numbers. **Zero new backtests,
zero recomputation, N stays 108 — this run consumes no trials.** Every figure is copied from a deliverable
on disk; where a source reports a DSR without its trial count it is flagged **[N unstated]**; where a
source never computed it, it says **not computed** (never fabricated).

> **Honest header — read first.**
> 1. **Nothing here clears the propfirm bar** (Sharpe>1.0 / DSR>0.5). That is the *point* of the list: a
>    register of real-but-sub-threshold edges for a future non-symmetric container / personal book / CV.
> 2. **Two incompatible "DSR" conventions coexist in the corpus — do not compare across them:**
>    - **(P) probabilistic DSR** (Bailey-López de Prado, ∈[0,1], bar **>0.5**) — funnels, iter_10, the books,
>      paper_triage. *This is the propfirm-gate convention.*
>    - **(S) deflated-Sharpe SR_DSR** (a deflated Sharpe number, bar ≈**1.0/threshold**) — Ross-Hook upstream,
>      sector_hothand, ORB, breakout deepdive. A "2.63" here is **not** comparable to a "0.47" there.
>    Tables are split by convention; sort is within-convention.
> 3. **DSR(P) is bounded [0,1]; ~every backtested candidate is therefore ≥0.** "Positive" is near-universal,
>    so the meaningful list is DSR(P)≳0.05; the **~76** funnel candidates with DSR(P)<0.05 are
>    *statistically indistinguishable from zero* (Bailey-LdP) and are counted, not listed.
> 4. **The single most important honest fact:** in the v1 funnel `step2_validation.csv`, **`dsr_full_primary`
>    = 0.00 for *every* validated candidate** (incl. the top TSMOM-K200). The positive DSRs below are almost
>    all **OOS-window** values that the funnel itself flags as a **2024-25 trend-regime artifact** (their
>    *in-sample* Sharpe is often negative). Full-history primary DSR ≈ 0 across the board.

---

## 1A. Probabilistic DSR (Bailey-LdP, bar >0.5) — sorted by DSR desc

> **★ ROSS HOOK #76 — probabilistic DSR NOW COMPUTED** (fills the register's one "not computed" cell;
> `dsr.py` verbatim on `research/s076_replication/results/mtm_deployable.csv::ret`, real broker data, β_mkt
> −0.04 genuine alpha). Convention: Bailey-LdP **probabilistic DSR ∈[0,1]**, PPY=252, **rf=0** (the series
> is a 0.5%-risk strategy P&L, matching the replication's Sharpe 0.44; dsr.py's default rf=0.02 would force
> SR negative from the low-leverage sizing → DSR≈0, a *sizing* artifact, so rf=0 is the honest edge figure).
> Detail → `research/positive_dsr_register/rosshook_dsr.json`.
>
> | N (attribution) | SR\*₀ used | DSR full (T=5866) | DSR OOS≥2016 (T=3501) | clears 0.5? |
> |---|---|---|---|---|
> | **N=1 — honest primary** (pre-specified single Joe-Ross strategy, replicated from spec, tested once; SR\*=0 ⇒ standard PSR) | **0.00** | **0.983** | **0.981** | **YES** |
> | **N=108 — conservative floor** (as if one more pick from the whole program; std_sr 0.845) | **2.161** (std1.0: 2.558) | **0.000** | **0.000** | no |
>
> SR(ann, rf=0) = **0.44** full / 0.56 OOS · skew **+0.48** · **excess kurtosis 45.4** full / 36.1 OOS (high —
> enters the DSR denominator; effect small here because the daily SR≈0.028 makes the SR² term tiny). **N=1 is
> the methodologically correct attribution** (Ross Hook was NOT selected as the max of a search grid). **N=108
> is the worst-case floor only.** Propfirm read: at N=1 it **clears the DSR>0.5 half**, but Sharpe 0.44 < 1.0
> **misses the Sharpe>1.0 half** → still sub-threshold overall; at N=108 it fails the DSR half too. This is the
> **only** register item whose DSR clears 0.5 — and only under its honest pre-specified N=1.

| # | strategy / sleeve | source | DSR (P) · N · window | Sharpe (full / OOS) | alpha vs beta | shortfall vs 0.5 | status | killer |
|---|---|---|---|---|---|---|---|---|
| 1 | **3-sleeve "decorrelated" book** (RSI2+BTC-mom+US30-MR) | `ftmo_portfolio_audit/AUDIT_REPORT.md` | **0.47** (N=100) / 0.28 (N=500) · regen full @SR 0.95 | full ~0.95 (regen; 1.39 claim unreprod.) / — | book of 3 sleeves, **decorrelated \|ρ\|<0.07** but 2 sign-flip vs spec | ~0.03 short (N100); fails at N500 | NOT-CONFIRMED / superseded | stacked optimism + thin Sharpe × 3-month symmetric clock |
| 2 | **iter_10 NQ Opening-Range** (Strategy C) | `data/ftmo_research/VALIDATION_strategyC_iter10_2010_2026.md:16` | **0.45** (N=26, **full** 2010-26) / 0.15 (cherry-pick) | full→SR 0.51 (16y) / — | **DIRECTIONAL — LONG-only** (no short edge) | ~0.05 short | archived (NO-GO paper) — supersedes the old CLAUDE.md "SR_DSR 1.0-1.1" claim | lumpy momentum × symmetric barrier (L24); long-only |
| 3 | **TSMOM-K200** multi-asset basket (`B1.tsmom.k200`) | `ftmo_candidate_funnel/results/all_trials.csv` + `SHORTLIST.md` | **0.447** (N=66, **OOS**) · **full-primary 0.00** (N=70) · lenient 0.826 | full 0.48 / OOS 1.80 | DIRECTIONAL — two-sided trend (shorts down-trends) but trend-exposed | ~0.05 short on OOS; **0 on full** | still-live "watchlist" near-miss (flagged, not for trading) | OOS=2024-25 regime artifact (IS 0.40); swap; lumpy-momentum barrier misfit |
| 4 | **F1_lowvol_broad** (long idx when calm, broad) | `ftmo_candidate_funnel/results/step2_validation.csv` | **0.455** (N=70, OOS) · full-primary 0.00 · lenient 0.001 | full 0.42 / OOS 1.98 | **BETA** — long equities in low-vol regimes | ~0.045 short OOS; 0 full | watchlist | disguised long-equity beta; OOS-only |
| 5 | **TSMOM-XAU** (`B2.tsmom100.XAUUSD`) | `…/all_trials.csv` + `step2_validation.csv` | **0.408** (N=66, OOS) · full-primary 0.00 · lenient 0.79 | full 0.27 / OOS 1.62 | DIRECTIONAL — gold trend | ~0.09 short OOS; 0 full | watchlist | OOS regime artifact; swap on the short side |
| 6 | **TSMOM-K200 vol-targeted** (`TSMOM_K200_voltgt`) | `…/step2_validation.csv` | 0.375 (N=70, OOS) · full-primary 0.00 · **lenient 0.093** | full 0.70 / OOS 1.68 | DIRECTIONAL — trend | ~0.13 short | watchlist | same trend-artifact family |
| 7 | **edge_improvement RH-alone (I2)** | `edge_improvement/RESULTS_AND_VERDICT.md` | **0.334** (N=103) / 0.174 (N=500) | IS 0.63 / **OOS −0.10** | Ross-Hook (see B-table for direction) | ~0.17 short | superseded (best of the improvement run, still fails) | RH had a weak 2025-26; excess kurtosis 40; +TSMOM dilutes |
| 8 | **COMBO tsmom+lowvol** | `…/step2_validation.csv` | 0.306 (N=70, OOS) · full-primary 0.00 · lenient 0.024 | full 0.55 / OOS 1.59 | DIRECTIONAL+BETA blend | ~0.19 short | watchlist | both legs OOS-only |
| 9 | **zfade-AUDUSD** (`A1.zfade10.AUDUSD`) | `…/all_trials.csv` | 0.211 (N=66, OOS) · lenient 0.68 | **IS −0.13** / OOS 1.47 | mean-reversion fade — **[market-beta untested]** | ~0.29 short | archived | negative IS → OOS-luck |
| 10 | **A.xsmom_idxgold_k60** (v2) | `ftmo_candidate_funnel_v2/results/v2_all_trials.csv` | 0.209 (N=97, OOS) | **IS −0.46** / OOS 1.50 | XS idx/gold momentum — **non-compliant (hedge)** | ~0.29 short | archived | FTMO-non-compliant + IS-negative (OOS-luck) |
| 11 | **zfade-USDJPY** (`A1.zfade10.USDJPY`) | `…/all_trials.csv` | 0.206 (N=66, OOS) · lenient 0.62 | IS −0.08 / OOS 1.43 | mean-reversion — **[market-beta untested]** | ~0.29 short | archived | negative IS → OOS-luck |
| 12 | **TSMOM-K100** (`B1.tsmom.k100`) | `…/all_trials.csv` | 0.182 (N=66, OOS) · lenient 0.57 | full 0.34 / OOS 1.17 | DIRECTIONAL — trend | ~0.32 short | archived | trend-family, OOS-tinged |
| 13 | **F1_lowvolLong_IDX** (`F1.lowvolLong_IDX`) | `…/all_trials.csv` + `SHORTLIST.md` | 0.130 (N=66, OOS) · lenient 0.48 | IS 0.49 / OOS 1.08 | **BETA-tinged** (long idx when calm) — *cleanest FTMO-shape, all 2020-26 yrs +* | ~0.37 short | watchlist (best *shape*) | disguised long-equity beta |
| 14 | **zfade-EURJPY** | `…/all_trials.csv` | 0.123 (N=66, OOS) | IS −0.22 / OOS 1.28 | mean-reversion [beta untested] | ~0.38 short | archived | IS-negative |
| 15 | **B.tsmom_trendstr0.5** (v2) | `…/v2_all_trials.csv` | 0.101 (N=97, OOS) | IS 0.55 / OOS 1.26 | DIRECTIONAL — loose-filter TSMOM ≈ unconditioned | ~0.40 short | archived | "already-known sub-threshold premium, not new" |
| 16 | **rsi2-GER40 / maLongIDX / tsmom-k50 / zfade-US30 / tom-XAU / rsi2-XAU / zfade-NZDUSD / preFOMC-XAU** | `…/all_trials.csv` | 0.050–0.092 (N=66, OOS) | mixed, mostly IS≤0 | mixed MR / beta-baseline / event | ~0.41–0.45 short | archived | OOS-luck / beta-baseline / event-thin |
| 17 | **commodity long-energy trend** (energy-2 / energy-silver-3) | `paper_triage/REPORT.md:188` | energy-2 **0.03**, energy-silver-3 **0.15** (N≈110, full) | energy-2 full +0.10 / OOS +1.09 | **BETA/directional** — long-only energy tailwind | ~0.35–0.47 short | archived (= prior commod-carry NO-GO) | swap kills the short side (L32); long = directional tailwind, not 2-sided edge |
| 18 | **survivors book** (Ross Hook + swap-net TSMOM, L=2.0) | `ftmo_survivors_book/REPORT.md:121` | **0.11** (N=100) / 0.04 (N=500) · OOS | deployable ~0.05 full / 0.92 OOS | 2 momentum legs, **decorrelated but no orthogonal diversifier** | ~0.39 short | superseded | real overnight CFD **swap** eats TSMOM; thin post-cost Sharpe |

*Also (NQ-ORB / Strategy-C family, same family as iter_10 row 2):* **NQ-ORB per-trade filters** — REMINING
Phase-2 (`data/ftmo_research/REMINING_clean.md`): **H1** (PDH+gap) DSR_p **0.23**, **H4** (vol) DSR_p
**0.11**, both **N=150, full** 2010-26; DIRECTIONAL long-biased ORB; **archived** (no filter passes all
criteria) — killer: filter adds no robust cross-regime per-trade edge + fails 1.5×cost+0.05R-slip stress.

*Long tail (counted, not listed): ~**76** funnel candidates have DSR(P) ∈ (0, 0.05) — indistinguishable
from zero (Bailey-LdP). See `…/all_trials.csv` (66 rows) + `…/v2_all_trials.csv` (27 rows) for the full set.*

## 1B. Deflated-Sharpe DSR (SR_DSR, different convention — bar ≈1.0; mostly flagged) — sorted desc

| strategy | source | SR_DSR · N | Sharpe | alpha/beta | status / flag |
|---|---|---|---|---|---|
| **PDH/PDL + trail-ATR breakout** | `data/ftmo_research/breakout_deepdive_ftmo.md:7` | **4.6** **[N unstated]** | +0.260R IS / **−0.014R OOS** | [direction untested] | **ARTIFACT** — OOS collapses, 99% bust; IS-only |
| **F1 ORB (3-verif build)** | `data/ftmo_research/F1_bughunt.md:23` | **3.49** **[N unstated]** | — | — | **BUGGED** — verifs blind to a direction bug; invalid |
| **Ross Hook #76 (upstream ftmo_lab proxy)** | `data/oxfordstrat_109/REPORT_S076_ross_hook.md:18` | **2.63** > 1.78 **[N unstated; 30-instrument proxy]** | upstream MTM 0.96 proxy / **0.70 real** | **GENUINE ALPHA** (β_mkt≈0) per upstream | upstream deflated-Sharpe convention; the **independent-replication probabilistic DSR is now computed → see §1A★ (N=1 0.98 / N=108 0.00)** |
| **sector_hothand (Equities)** | `CLAUDE.md:281` | **2.01** **[N unstated]** | SR_net 2.05, WF 5/5, MDD −13.3% | claims alpha (t_HAC 10.38) — **[direction untested]** | **RED-FLAG** — t-stat 10 implausible, audit-pending, unconfirmed |
| **ORB-CFD V2+E7 (NQ, push-pass family)** | `data/ftmo_research/OPTIM_ORB_propfirm.md:306` | **0.70** (n_trials=18) | 1.54 gross | DIRECTIONAL — long-biased breakout-momentum | archived; n=18 mods=8 **violates L10 (≤3 mods)**; lumpy-barrier misfit; < ~1.0 bar |

## 1C. DSR ≤ 0 / not computed (for completeness)

- **Full-history primary DSR = 0.00** for the entire v1 step-2 validated set (TSMOM-K200/K100/XAU,
  F1_lowvol, COMBO, voltgt) — `step2_validation.csv` `dsr_full_primary`. Positive only on OOS / lenient.
- **commodity_carry long-only** (`paper_triage/REPORT.md`): full Sharpe 0.14, **DSR ≈ 0**; symmetric variant
  full −1.07 (DSR n/a, rejected by L32 swap).
- **s076 Ross-Hook replication** (`research/s076_replication/`): probabilistic DSR **NOW COMPUTED** (2026-06-09)
  → **§1A★** (N=1 = 0.98 clears 0.5; N=108 = 0.00). This was the register's single "not computed" cell.
- **container_eval** (`research/container_eval/`): reports **p(pass)** (best 0.371 FundedNext), **no DSR** —
  reuses the survivors-book series at different barriers; not a new edge.
- **b1_feasibility** (FINRA short-volume) and **commodity_carry_feasibility**: **pre-test feasibility docs,
  no backtest / no DSR computed.**
- Most CLAUDE.md archived families (n=322 ledger) carry **no DSR** (killed at earlier gates) — not listed.

---

## 2. Split — genuine alpha vs beta/directional vs direction-untested

**GENUINE ALPHA (market-neutral by the source's own diagnostic — reusable as a decorrelated sleeve):**
- **Ross Hook #76** — the only item with a *clean market-beta regression on real data*: s076 replication
  **β_mkt = −0.04, covered-alpha t_NW = 2.58** (market+TSMOM controls). Market-neutral, weakly-trend-loaded.
  **Probabilistic DSR now computed (§1A★): N=1 = 0.98 (clears 0.5), N=108 = 0.00** — the only register item to
  clear the DSR half of the bar, and only under its honest pre-specified N=1 (Sharpe 0.44 still misses Sharpe>1.0).
- **(weak) zfade / RSI2 mean-reversion family** — orthogonal to trend (see §3), but **IS Sharpe negative**
  → the positive DSR is OOS-luck, and **market-beta was not formally tested** → really "[direction untested]".
  The 3-sleeve book's RSI2 + US30-MR legs are the deployed instances (decorrelated \|ρ\|<0.07, book DSR 0.47).

**BETA / DIRECTIONAL (exposure, not a standalone edge):**
- TSMOM-K200/K100/K50/XAU and all trend variants (lumpy long-biased trend; two-sided but trend-exposed).
- F1_lowvol(_IDX/_broad), maLongIDX, D2 halloween — long-equity beta in calm/seasonal regimes.
- iter_10 NQ ORB + ORB-CFD V2+E7 — long-biased breakout-momentum.
- commodity long-energy (energy-2/silver-3) — directional swap tailwind.

**DIRECTION-UNTESTED / INVALID:**
- sector_hothand (claims alpha t=10.38 but red-flagged, no two-sided/L25 check on disk).
- event drifts (preFOMC/preCPI/turn-of-month/six-month) — directional drifts, no formal beta test.
- breakout PDH/PDL (ARTIFACT) and F1 ORB build (BUGGED) — excluded from the alpha/beta judgment (invalid).

---

## 3. Cross-correlation between surviving items (existing series on disk — NOT regenerated)

From `ftmo_candidate_funnel/results/{watchlist_corr.csv, step2_corr.csv}`, `s076_replication/decorr_check/`,
`ftmo_portfolio_audit` — all already computed:

- **Trend ⊥ mean-reversion is real:** TSMOM-K200 vs zfade-AUDUSD **0.04**, vs zfade-USDJPY **−0.01**;
  zfade-AUDUSD vs zfade-USDJPY 0.25. The only genuine orthogonality in the funnel is *trend vs zfade*.
- **Trend family is internally correlated:** TSMOM-K200↔K100 0.64, ↔XAU 0.48, ↔vol-targeted 0.94;
  F1_lowvol↔TSMOM 0.15–0.28 (lowish, but F1 is beta).
- **Ross Hook ↔ TSMOM-deployed = 0.30** (Pearson; `decorr_check.md`) — mildly correlated, not orthogonal.
- **3-sleeve book (RSI2 / BTC-mom / US30-MR): \|ρ\| < 0.07** (`ftmo_portfolio_audit`) — genuinely decorrelated.
- **Decorrelation does NOT rescue the bar:** `ftmo_survivors_book` + `edge_improvement` both show the √N
  combination fails — on FTMO-correct instruments the second (swap-net TSMOM) leg is *net-negative*, so it
  dilutes rather than diversifies. Decorrelation is real; the legs are individually too thin post-cost.

*(No series were regenerated. Where a pairwise correlation isn't on disk it is omitted, not computed.)*

---

## 4. Closing (honest)

Every DSR above is deflated at the **stated N** (or flagged **[N unstated]**) and tagged by window
(full / OOS); the two DSR conventions are kept separate. **This is a collation, not new evidence —
nothing here clears Sharpe>1.0 / DSR>0.5.** The recurring honest pattern: the *clean* probabilistic DSRs
cluster at **0.45–0.47 just under the 0.5 bar** (3-sleeve book 0.47, iter_10 0.45, TSMOM-K200 OOS 0.447),
each with a documented killer (**swap · symmetric barrier · thin Sharpe · disguised beta · OOS-only**);
the **full-history** primary DSR of the validated funnel set is **0.00**; and the only items reporting
high SR_DSR (≥2) are **artifact / bugged / red-flagged / upstream-proxy**. The one item with a clean
market-neutral alpha diagnostic on real data is **Ross Hook** (β≈0, alpha t 2.58); its probabilistic DSR is
now computed (§1A★) and is the **only** register entry to clear DSR>0.5 — **but only at its honest N=1
(0.98); at the program-wide N=108 it is 0.00, and its Sharpe 0.44 still misses the Sharpe>1.0 half** of the
bar. So even the program's best honest edge does not clear the propfirm bar outright — consistent with the
whole register. *(One DSR computation on an existing series; N program-wide stays 108.)*
