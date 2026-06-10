# session_H — Calendar-flow residue: PHASE-0 DOUBLE-STOP (no trial run)

*2026-06-10. Scope as mandated: 2 trials max (ToM cash indices; KMW fixing reversion).
Outcome: **both trials STOPPED at the mandatory Phase-0 registry check — prior tests exist
with decisive verdicts. Zero new tests, zero data contact, registry delta +0.** Phase 1
(pre-registration) intentionally not executed: pre-registering trials that will not run
would put dead contracts in the registry. A clean stop is the deliverable.*

> **ADDENDUM 2026-06-10 (same day, second pass)** — the Phase-0 dossier below is completed at the
> end of this file: one factual correction (IDEA_TOM was *moved*, not deleted — it is the
> controlling prior art, exact window, full treatment, KILL) plus three further independent prior
> kills (session_E #3 = the K2 question; funnel `D1.tom.*` = the K5 question; session_3 B5).
> The Trial-A "caveat recorded for auditability" is **closed** by the addendum. Verdicts unchanged.

---

## Executive verdict

Both session_H candidates were already falsified by prior work, more thoroughly than this
session's own design would have: **Trial A** (turn-of-the-month, equity indices) was
measured and archived dead-gross in the dated-flows batch (`session_cowork`, 2026-06) —
a dead-gross screen cannot be revived by adding spread and swap; **Trial B** (KMW fixing
reversion) was killed twice — at literature stage (Strategy E, L23) and empirically on
19 years of TRUE-UTC EURUSD M1 after the 2026-06-10 timezone migration (pooled fix-window
gross t = 0.59, i.e. no W-shape exists in our data at all, which is precisely this trial's
pre-registered stage-1 kill). Re-running either would violate the repo rule "do not
re-propose without strong new evidence" and consume registry trials to confirm known kills.

| Trial | Status | Prior verdict (verbatim) | Source of record |
|---|---|---|---|
| A — ToM FTMO cash indices | **STOPPED (Phase 0)** | "plain TOM-equity dead (archive)"; fade variant "⚑ wrong-profile (MR fade, neg skew)" | `data/skew_research/session_cowork/exploration_datedflows_2026-06.md` (batch 3, candidate 5) |
| B — KMW fixing reversion | **STOPPED (Phase 0)** | "absence totale de signal au fix" (Pattern A, t 0.59, N 15,039, 2007-2026 TRUE UTC); Pattern B gross real (t 3.55) "tué uniquement par le tier de coût retail" | `Forex/research/active/fix_reversal/FIX_REVERSAL_TZ_MIGRATION.md` §4 + `Forex/research/archived/strategy_e_fix_flow/POSTMORTEM.md` |

---

## Trial A — Turn-of-the-month, FTMO cash indices: STOPPED

**Prior art found (Phase-0 grep, exact match on hypothesis family and instrument class):**

1. `data/skew_research/session_cowork/exploration_datedflows_2026-06.md` — dated
   mechanical-flow sleeves, batch 3 ("dated flows": NFP/CPI, treasury, roll, expiry,
   **month-end**). Phase-1 measured table, candidate 5:
   - Month-end FADE (perf-conditioned, last 3d): n = 951, mean +7.4 bps, t = +2.05,
     skew **−0.24** → "⚑ wrong-profile (MR fade, neg skew); **plain TOM-equity dead
     (archive)**".
   - Session bilan line: batch 3 month-end ∈ "no-edge/cost/archived-neg".
2. `data/ftmo_research/IDEA_TOM_seasonality.md` — referenced in the old arc; ~~file removed
   by the 2026-06-10 cleanup (its conclusion is subsumed by the dated-flows session above)~~
   **[CORRECTED same day — see ADDENDUM §A]**: the file was NOT removed. The P2 consolidation
   moved it to `PropFirms/ftmo/program_2026-06/ftmo_research/IDEA_TOM_seasonality.md`
   (CLAUDE.md repo-layout note: old paths `data/ftmo_research/…` are historical citations,
   not rewritten). It is a **full pre-registered treatment of the exact session_H window,
   verdict ❌ KILL (2026-06-03)** — the controlling prior art, strictly stronger than the
   dated-flows line above.

**Why STOP is decisive and not a scope dodge:** the prior screen measured the *gross* edge
(Phase 1, raw edge + skew, no costs) and found the plain long-ToM dead. Session_H's design
only ADDS frictions the screen ignored (spread per event + ~4 swap nights/event at the
measured FTMO index swaps — cf. `session_F_integration/verdict_final.md`: US500 alone
carries 2.26%/yr swap drag at vol-targeted notional). A candidate dead at gross cannot
survive net; the full McConnell-Xu treatment (panel, K1-K6) could only re-document the
kill at the price of +1 registry trial. The only variant that showed any gross life
(perf-conditioned month-end FADE, t 2.05) was killed on the skew profile and is in any
case a different mechanism (mean-reversion, not reinvestment-flow drift) — pursuing it
would be window/condition mining (L10).

**Caveat recorded for auditability:** the dated-flows screen ran on daily data with the
session_cowork calendar (2020–2026 core) — shorter than session_H's intended 10y+ panel
and not the exact {-1,+1,+2,+3} window. This difference is noted, and judged insufficient
to overturn a dead-gross verdict on the same mechanism + instrument class (repo rule:
"DO NOT re-propose without strong new evidence" — a longer sample of the same free data
is not new evidence; cf. PROGRAM_DECISION_MEMO: stop searching price).
**[CAVEAT CLOSED same day — ADDENDUM §A]:** the exact {−1,+1,+2,+3} window WAS tested, on
NQ databento 2010–2026 and US500/US100 close panels 2000–2026, in `IDEA_TOM_seasonality.md`
(pre-registered 2026-06-03, baseline K_first=3/K_last=1 ≡ the McConnell-Xu return-day set,
plus a 6-config grid): diff-vs-non-ToM t = **−0.10** (NQ), **+0.75/+0.80** (panels), grid
0.51–1.43 — never significant. The residual doubt this caveat carried is gone.

## Trial B — KMW fixing reversion (W-shape, USD majors): STOPPED

**Prior art found — two independent closures, the second on corrected timestamps:**

1. **Literature-stage closure (2026-05):** `Forex/research/archived/strategy_e_fix_flow/
   POSTMORTEM.md` — Strategy E (WMR fix + EOM USD flow), CLOSED: E1 intra-month W-shape
   1-4 bp gross vs 6-7 bp retail RT → net < 0; BIS 2015 window widening (1→5 min) makes
   pre-2015 magnitudes non-predictive (**L23**). KMW's own sample (1999-2019) straddles
   the reform.
2. **Empirical closure on TRUE-UTC data (2026-06-10):** `Forex/research/active/
   fix_reversal/FIX_REVERSAL_TZ_MIGRATION.md` — the 2026-06-02 EET-era results were
   invalidated (2-3h window shift; "Tokyo fix" was the broker rollover) and the
   pre-registered Krohn/Ranaldo hypotheses re-tested as written on
   `deep_history_utc/EURUSD_M1.csv` (TRUE UTC, 2007→2026, the repaired estate):
   - **Pattern A (fix reversal): pooled N = 15,039, gross 0.07 bps, t = 0.59 → "Il n'y a
     pas de fix-reversal mesurable sur EURUSD"** (London 0.05 / ECB −0.03 / Tokyo 0.19 bps).
   - Pattern B (Ranaldo session segmentation): the only gross survivor (two-sided, t = 3.55,
     gross SR 0.73) — killed by the retail cost tier alone (needs < ~1 bps RT/leg; measured
     2.48 bps/leg at the London fix). **L34 candidate (institutional-tier-only) confirmed.**
   - The "EOM up-sizing" and "2023+ emergence" angles were tz artifacts; gone on TRUE UTC.

**Mapping onto session_H's pre-registered kill:** Trial B stage 1 read "Replication
2007-2019: does the W-shape exist in OUR data at all? No → kill immediately (our data
tier cannot see it)." That exact question is already answered on 2007-2026 (a superset),
on the tightest pair (EURUSD), at the corrected timestamps: **no W-shape, gross t 0.59.**
Extending to GBPUSD/USDJPY (wider spreads, same mechanism) cannot flip a no-signal verdict
on the best pair. The 3×3.0 bps L11 gate is unreachable when the gross amplitude is
~0.1 bps.

---

## Discipline accounting

- **Data contact this session: NONE** (reports and code greps only; no price file opened).
- **Phase 1 pre-registration: not executed** — no trial survived Phase 0; committing
  contracts for stopped trials would create registry ambiguity.
- **Registry delta: +0** (prompt rule: "+1 per trial actually run"; none ran). Cumulative
  count unchanged at the registry file's value (REGISTER.md canonical, 115 at the
  2026-06-10 reconciliation; untouched).
- **Scope: not expanded** — no substitute trials proposed; the source review's other
  branches remain closed per session_F/G, L32/L36/L37, L27/L28, L33/L33-bis.
- **No portfolio integration proposed** (blockers stand: ORB spread sessions 2-5;
  ETH/SOL swap validation).
- Follow-up owned elsewhere (not this session): promote **L34** (reformulated without the
  L25-asymmetry clause) and archive `fix_reversal/` with POSTMORTEM — already queued in
  `_meta/current_focus.md` "Décisions pendantes".

---
---

# ADDENDUM (2026-06-10, same day) — Phase-0 dossier completed; verdicts unchanged

*Why this addendum: the first pass grepped the historical path `data/ftmo_research/` and concluded
the strongest ToM artifact had been deleted by the cleanup. It had not — the 2026-06-10 P2
consolidation moved the whole FTMO program to `PropFirms/ftmo/program_2026-06/` and CLAUDE.md
explicitly says historical citations were not rewritten. Re-sweeping at the consolidated path turns
Trial A's stop from "dead-gross screen + acknowledged window caveat" into "four unanimous direct
kills incl. the exact pre-registered window, full treatment". This addendum is, like the body, a
READ-ONLY collation (REGISTER.md convention): zero data contact, zero re-runs, +0 trials.*

## §A — Trial A: the complete prior-art dossier

| # | Artifact (path) | Date | Universe | Spec vs Trial A | Verdict found |
|---|---|---|---|---|---|
| 1 | `PropFirms/ftmo/program_2026-06/ftmo_research/IDEA_TOM_seasonality.md` (engine: `…/ftmo_research/seasonality_tom/tom_engine.py`) | 2026-06-03, **pre-registered before results** | NQ databento 2010–26 (primary) + US500/US100 close panels 2000–26 (validated, return-corr 0.997) | **Exact window**: baseline K_first=3/K_last=1 ≡ return days **{−1,+1,+2,+3}** (McConnell-Xu set) + grid K_first∈{2,3,4}×K_last∈{1,2}; long-in-window/flat-else; decay by decade; cost; multi-index; FTMO first-passage + DSR | **❌ KILL** |
| 2 | `data/skew_research/session_E_event_calendar_sleeves/exploration_2026-06.md` §#3 | 2026-06-04 | US500/US100/US30 | ToM-day premium vs non-ToM, gross + net-CFD (swap −2.5 bps/night, spread 1.5 bps/side) | **❌ MEURT (beta)** |
| 3 | `PropFirms/ftmo/program_2026-06/ftmo_candidate_funnel/results/all_trials.csv` rows `D1.tom.{US500,US100,US30,GER40,XAU}` + `D1.tomIDX` | 2026-06 (funnel iter 1, N=66 trials) | US500, US100, US30, **GER40**, XAU + index sleeve | ToM cells inside the powered funnel | **❌ all archived**: `sharpe_is` −0.34 (GER40) … +0.33 (XAU); `dsr_oos` 0.012–0.065 (best = tom-XAU 0.065, banded "OOS-luck / beta-baseline / event-thin" in `positive_dsr_register/REGISTER.md` row 16) |
| 4 | `data/skew_research/session_3/exploration_2026-06.md` §B5 | 2026-06-04 | SPY, TLT, IEF, DBC, GLD (N=643 windows) | ToM window (last + 3 first), multi-asset | **❌ "null toutes classes"** (best GLD +6.0 bps t=1.3; TLT −0.7 t=−0.17) |
| 5 | `Equities/research/archived/indices_swing/results/verdict.md` `s3_tom` | old arc (the "swing deep-dive" the task pointed at) | SPY, QQQ, EWQ × horizons {1,3,5,10} | [−1,+3] business-day dummy | **❌ 12/12 cells NO-GO** |

**Controlling verdict, verbatim (IDEA_TOM_seasonality.md):**

> **VERDICT: ❌ KILL — TOM premium too weak/insignificant, and the long-only form still eats
> crash-window drawdowns → fails the barrier.**
> - NQ databento (2010–2026): TOM-day +7.39 bps **vs** non-TOM +7.92 bps → **diff t = −0.10**.
>   Panels US500/US100: TOM higher (+5.5/+8.2 bps) but **diff t only +0.75/+0.80**. Grid (6
>   configs) diff_t 0.51–1.43 — **never significant**.
> - **Not decayed** (stable ~6–11 bps/TOM-day, max t 1.74, 2010s US100) — real-but-tiny, *never*
>   statistically strong. Rules out "arbitraged away"; it simply was never big enough.
> - In cash ~81% of the time, yet **maxDD −15% (NQ) to −36% (US100)**, Sharpe **0.14–0.18** —
>   TOM windows landing in crash months (Oct'08, Mar'20) are still long-beta.
> - **FTMO 2-step first-passage: p(funded) 15–25%, bust 74–84%** (L=3–12).

**Distinctness kill, verbatim (session_E §#3 — this is exactly Trial A's K2 placebo question):**

> **#3 ToM** : le premium ToM (+2,4 à +4,4 bps/j vs non-ToM) n'est **pas distinct du beta long**
> (HAC t≤0,81 gross, net t≤1,24) → c'est de la concentration de beta sur quelques jours, pas un
> edge. Le test two-sided/distinctness tranche : MEURT.

### Universe coverage — 100% of the feasible panel

`data/deep_history_utc/` (canonical M1 estate, MANIFEST.md) contains exactly **four** cash indices:
US500, US100, US30, GER40. The task's expected EU50/UK100/JP225 legs **do not exist in canonical
data**, and the NQ-databento "robustness extension" was already artifact #1's *primary* instrument.
Per-instrument record: US100/NQ diff-t −0.10 (#1), funnel sharpe_is −0.05 (#3); US500 diff-t +0.75
(#1), net t≤1.24 (#2), funnel dsr 0.012 (#3); US30 net t≤1.24 (#2), funnel dsr 0.041 (#3); GER40
funnel sharpe_is **−0.34**, dsr 0.037 (#3). Every tradeable leg of Trial A is directly covered;
the mechanism's home market (US, McConnell-Xu 2008, sample ending 2005 — so the whole modern panel
is post-publication, the task's own K3 concern) is covered three times over.

### The six pre-registered kills are all already answered

| Pre-registered kill | Answered by | Value on record → outcome |
|---|---|---|
| K1 pooled net HAC t < 2.0 | #1 grid, #2 net | diff_t ≤ 1.43 gross; net t ≤ 1.24 → **kills** |
| K2 placebo (α-vs-β) | #2 distinctness | "pas distinct du beta long" = disguised unconditional drift, the exact pre-registered failure mode → **kills** |
| K3 OOS ≤2015 / ≥2016 | #1 by-decade | stable, never significant (max t 1.74) — no decay, nothing to rescue; K1/K2 stand |
| K4 concentration | #1/#3/#4 per-instrument | no leg carries a significant premium → moot |
| K5 DSR ≤ 0 at registry N | #3 funnel cells | dsr_oos 0.012–0.065 at N=66; at N=115 → ≈0 → **kills** |
| K6 daily-cap excursion | #1 container | maxDD −15%/−36%, crash-window beta; p(funded) 15–25%, bust 74–84% → **kills** |

**Cost decomposition on record (spread vs swap, per task spec — collation):** spread ≈ 1.5 bps/side
(session_E model) × ~12 events/yr → immaterial, "swept anyway" (#1). Swap: −2.5 bps/night model
(session_E) × ~4–5 nights + month-boundary weekend ≈ −10…−18 bps/event; the one *measured* FTMO
index swap on record is **asymmetric exactly as L30 warns** (US100.cash long −662.4 / short +28.58,
units as quoted in `ftmo_research/_FTMO_ETAT_CANONIQUE.md` §5). Against a differential premium
statistically equal to zero, the swap leg only deepens the kill. **No placebo figure / OOS table
generated — no run**; the placebo question is answered by #1's diff-t and #2's distinctness test,
the OOS question by #1's by-decade table.

## §B — Trial B: completion notes

1. The family is **also burn-listed in the currently-active FX program**:
   `Forex/research/active/fx_intraday_deepdive/PRE_REGISTRATION.md` burns **B5** (WMR fix, Strategy
   E, L23/L23b) and **B6** (fix-reversal Krohn/Ranaldo, L34) — and its SYNTHESIS extends the kill
   from these specific windows to the whole retail FX intraday-flat space.
2. **Gate arithmetic made explicit:** Trial B's pre-registered feasibility gate was gross round-trip
   ≥ 3 × 3.0 bps = **9.0 bps** (L33-bis cost). Measured gross at the true fix (TRUE-UTC 2007–2026,
   N=15,039): pooled **0.07 bps** (t=0.59); per-fix ≤ 0.19 bps; best EOM subset 0.18 bps. That is
   **~50× below the gate**. Even at the *measured* fix-window cost stack on record (step0 TRUE-UTC:
   London/ECB **2.48 bps RT** = spread p95 0.71 + commission 0.44 + slippage 1.33; Tokyo 2.92 —
   the old "Tokyo 4 bps spread" was the broker-rollover artifact), the gate would be 7.4–8.8 bps:
   same answer. Stage-1 replication and stage-2 hold-out are both inside the already-tested
   2007–2026 sample; EURUSD is the tightest of the three task pairs, so GBPUSD/USDJPY (wider costs,
   same mechanism) cannot flip a zero-gross verdict. **1 trial regardless of pair count — already
   consumed by `fix_reversal` (2 n_tests, 2026-06-02; tz re-run +0, 2026-06-10).**

## §C — Registry chain, made precise

`positive_dsr_register/REGISTER.md` audit: **N=108** (2026-06-09) → `ftmo_research/
announcement_premium/report.md` +4 (97→101 in its own stale numbering; reconciled) → **112** →
`ftmo_research/backwardation_oil/report.md` +3 (T109–T111 as frozen), header reconciles
**112 → 115** (2026-06-10). The task's "97 at last audit" is the same stale base the other two
06-10 tasks carried; both reconciled upward on contact with the registry, as mandated ("the
registry file is the source of truth, not this prompt"). **session_H inherits N=115, consumes +0,
leaves N=115.**

## §D — Candidat-leçon (NOMMÉ, non numéroté — convention de l'arc)

> **LESSON-CANDIDATE: registry-check-must-sweep-consolidated-paths** — un registry-check qui ne
> grep que le chemin *historique* (`data/ftmo_research/`) après une consolidation (P2 2026-06-10 →
> `PropFirms/ftmo/program_2026-06/`) produit un faux « fichier supprimé » et a failli rétrograder
> un STOP en « caveat » : l'artefact contrôlant (IDEA_TOM, fenêtre exacte, full treatment, KILL
> 06-03) vivait au chemin consolidé. Règle : sweeper les DEUX chemins (ancien cité + consolidé) +
> `data/skew_research/session_*` + funnel CSVs avant tout verdict de Phase 0. Coût du re-sweep :
> ~0 compute ; gain ici : 2 slots de registre à N=115 préservés sur dossier blindé (4 kills
> unanimes au lieu d'1 screen gross avec caveat) — chaque essai évité protège le DSR de tous les
> candidats futurs. Le résidu d'une revue externe n'est un résidu que si le registre — complet —
> le dit.

---
*Addendum: collation pure, refs en chemin ; aucun contact data ; 0/2 trials consommés ; registre
115 → 115. Réconcilié : IDEA_TOM (06-03), session_E #3 (06-04), session_3 B5 (06-04), funnel
D1.tom.* + REGISTER.md (06-09), indices_swing s3_tom (vieil arc), session_cowork dated-flows
(06), strategy_e_fix_flow (05-25), fix_reversal + tz-migration (06-02/06-10), fx_intraday_deepdive
burn-list (06-09), announcement_premium + backwardation_oil (06-10) — pas de re-preuve.*
